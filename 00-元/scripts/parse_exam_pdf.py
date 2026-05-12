"""PDF 解析卷 → 题块 JSON。

策略:
1. pdfplumber 提取全文（保留行序）
2. 用 question_patterns[学科] 切分题号边界
3. 解析卷的"【答案】"/"【解析】"段附在对应题块上

输出: <working_dir>/<paper_id>-questions.json

用法:
    python 00-元/scripts/parse_exam_pdf.py \
        --pdf "<.../2024年高考数学试卷（新课标Ⅱ卷）（解析卷）.pdf>" \
        --subject 数学 --province 吉林 --year 2024 \
        --out docs/superpowers/working/
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402
from _exam_utils import load_config, normalize_gender, normalize_paper  # noqa: E402

# 题号边界识别（不区分学科的通用版）
QNO_RE = re.compile(r"^\s*(\d{1,2})\s*[\.、．]\s*", re.MULTILINE)
ANSWER_TAG_RE = re.compile(r"【答案】([^\n【]*)")
SOLUTION_TAG_RE = re.compile(r"【解析】([^【]+)")

# 真题章节起始标记：真题部分从这里开始（PDF 头部的"考生须知"在此之前）
# 高考数学卷标准章节：一、单项选择题/二、多项选择题/三、填空题/四、解答题
PREAMBLE_END_RE = re.compile(r"一[、，．,]\s*单项选择题|一[、，．,]\s*选择题")

# 结构化标记：以下开头的行视为题面/答案/解析内容，**不是**游离数学行
_STRUCT_MARKER = re.compile(
    r"^\s*("
    r"【|"                                 # 【答案】/【解析】/【分析】/【详解】/【小问 N 详解】/【点睛】
    r"故|综上|因为|所以|则|又|设|当|对|若|由|若|根据|证明|解|"  # 解答常见开头连词
    r"第\s*\d+\s*页|"                    # 页码 "第 1 页 共 27 页"
    r"\d+\s*[\.、．]\s|"                  # 题号 "1. xxx"
    r"[A-D]\s*[\.、．]\s|"                # 选项 "A. xxx"
    r"[①②③④⑤⑥⑦⑧⑨⑩]"                       # 序号项
    r")"
)

# 游离数学行识别：含数学符号或单字母上下标的简短行
_ORPHAN_MATH_PAT = re.compile(
    r"[=∈∉⊂⊃⊆⊇∪∩×÷√∑∏∫π∞≤≥≠≈±²³⁴⁵{}|]|"  # 关键数学符号
    r"\b[a-zA-Z]\s*[=∈]|"                       # 变量赋值 "x =" "a ∈"
    r"\{[^}]*\}"                                # 集合 {a,b,c}
)


def _is_orphan_math_line(line: str) -> bool:
    """判断一行是否是"游离数学定义行"。

    典型游离行（应合并到下一题 stem 头部）:
    - "M ={2,4,6,8,10},N ={ x -1< x<6 }"
    - "M ∩ N ="
    - "x²" / "x2"（pdfplumber 把上标拆为单独行）
    非游离行: 题号 / 答案块标记 / 选项 / 页码 / 普通中文句子。
    """
    s = line.strip()
    if not s:
        return False
    if _STRUCT_MARKER.match(s):
        return False
    if len(s) > 80:
        return False  # 长句子不太可能是数学定义行
    if s[-1] in "。.，；！？":
        return False  # 普通句子以标点结尾排除
    # 整行是简短数学变量+上下标（如 "x²"、"x2"、"y3"）
    # 要求首字符是字母 + 末字符是数字或上下标，避免把纯数字（如 "10"、"16" 页码碎片）误判
    if len(s) <= 5 and re.fullmatch(r"[a-zA-Z][a-zA-Z\d²³⁴⁵√^_]*[\d²³⁴⁵√]", s):
        return True
    if _ORPHAN_MATH_PAT.search(s):
        return True
    return False


def _extract_trailing_orphan(text: str) -> tuple[str, str]:
    """从 text 尾部反扫，把连续的"游离数学行"段切出来。

    返回 (text_without_orphans, orphan_text)。无游离尾时 orphan_text 为空串。
    """
    lines = text.split("\n")
    end = len(lines) - 1
    while end >= 0 and not lines[end].strip():
        end -= 1
    if end < 0:
        return text, ""
    start = end
    while start >= 0:
        stripped = lines[start].strip()
        if not stripped:
            start -= 1
            continue
        if _is_orphan_math_line(stripped):
            start -= 1
        else:
            break
    first_orphan_idx = start + 1
    if first_orphan_idx > end:
        return text, ""
    orphan = "\n".join(lines[first_orphan_idx : end + 1])
    kept = "\n".join(lines[:first_orphan_idx] + lines[end + 1 :]).rstrip()
    return kept, orphan


def _classify_qtype(stem: str, qno: int, total_q: int) -> str:
    """题型分类（题号兜底 + stem 启发式校验）。

    新高考卷（2017+ 新课标Ⅱ/全国乙等，总题数 19-22）固定结构：
      Q1-11 = 选择（前 8 单选 + 后 3 多选）
      Q12-14 = 填空
      Q15+ = 解答
    老高考卷（2008-2016，总题数 21-22）结构：
      Q1-12 = 选择
      Q13-16 = 填空
      Q17+ = 解答
    """
    if total_q <= 20:
        # 新高考结构（19-20 题）
        if qno <= 11:
            return "选择"
        if qno <= 14:
            return "填空"
        return "解答"
    else:
        # 老高考结构（21-22 题）
        if qno <= 12:
            return "选择"
        if qno <= 16:
            return "填空"
        return "解答"


def _classify_score(qno: int, qtype: str) -> int:
    """高考数学典型分值。"""
    if qtype == "选择":
        return 5
    if qtype == "填空":
        return 5
    if qno >= 17:
        return 12 if qno < 22 else 17
    return 12


def _split_questions(full_text: str) -> list[tuple[int, str]]:
    """按题号边界把全文切成 [(qno, body)] 列表。

    先跳过"考生须知"段落（找到"一、单项选择题"标记之前的所有 "1./2./..." 编号
    都属于须知），再按题号递增约束切分真题。

    切分后做一次"游离数学行归属"修正：题号 N. 之前/上一题答案之后的简短数学
    定义行（如 "M ={2,4,6,8,10}"、"x²"）原本会被丢失，修正后 prepend 到 Q_N 的
    stem 头部。修复历史 OCR 报告中约 40% 的"题面不完整"误差。
    """
    pre = PREAMBLE_END_RE.search(full_text)
    text = full_text[pre.start():] if pre else full_text

    matches = list(QNO_RE.finditer(text))
    raw: list[tuple[int, int, int, int]] = []  # (qno, qno_start, body_start, body_end)
    for i, m in enumerate(matches):
        qno = int(m.group(1))
        if raw and qno != raw[-1][0] + 1:
            continue
        if not raw and qno != 1:
            continue
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw.append((qno, m.start(), body_start, body_end))

    if not raw:
        return []

    bodies: list[list] = [[qno, text[bs:be].strip()] for qno, _, bs, be in raw]

    # 1) Q1 之前的游离数学行（PREAMBLE 后 → Q1 题号前）prepend 到 Q1 stem
    pre_q1 = text[: raw[0][1]]
    _, orphan_lead = _extract_trailing_orphan(pre_q1)
    if orphan_lead:
        bodies[0][1] = orphan_lead + "\n" + bodies[0][1]

    # 2) 题间游离行：上一题 body 尾部的游离行剥离并 prepend 到下一题
    for i in range(len(bodies) - 1):
        kept, orphan_tail = _extract_trailing_orphan(bodies[i][1])
        if orphan_tail:
            bodies[i][1] = kept
            bodies[i + 1][1] = orphan_tail + "\n" + bodies[i + 1][1]

    return [(qno, body.strip()) for qno, body in bodies]


def parse_pdf(pdf_path: Path, *, subject: str, province: str, year: int) -> dict[str, Any]:
    cfg = load_config()
    fname = pdf_path.name
    paper = normalize_paper(fname, cfg)
    gender = normalize_gender(fname, cfg)
    paper_id = f"{year}-{gender}-{paper}"

    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join((page.extract_text() or "") for page in pdf.pages)

    raw = _split_questions(text)
    total_q = len(raw)
    questions: list[dict[str, Any]] = []
    for qno, body in raw:
        ans_m = ANSWER_TAG_RE.search(body)
        sol_m = SOLUTION_TAG_RE.search(body)
        stem_end = min(
            ans_m.start() if ans_m else len(body),
            sol_m.start() if sol_m else len(body),
        )
        stem = body[:stem_end].strip()
        if not stem or len(stem) < 5:
            continue
        qtype = _classify_qtype(stem, qno, total_q)
        questions.append({
            "qno": qno,
            "qtype": qtype,
            "score": _classify_score(qno, qtype),
            "stem": stem,
            "answer": ans_m.group(1).strip() if ans_m else "",
            "solution": sol_m.group(1).strip() if sol_m else "",
        })

    rel_pdf = pdf_path.relative_to(REPO_ROOT) if pdf_path.is_relative_to(REPO_ROOT) else pdf_path
    return {
        "paper_id": paper_id,
        "year": year,
        "gender": gender,
        "paper": paper,
        "subject": subject,
        "province": province,
        "source_pdf": str(rel_pdf).replace("\\", "/"),
        "questions": questions,
    }


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--province", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out", default="docs/superpowers/working/")
    args = ap.parse_args()

    result = parse_pdf(Path(args.pdf), subject=args.subject, province=args.province, year=args.year)
    out_dir = REPO_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.province}-{args.subject}-{result['paper_id']}-questions.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: 切分 {len(result['questions'])} 题 → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
