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
    """按题号边界把全文切成 [(qno, body)] 列表。"""
    matches = list(QNO_RE.finditer(full_text))
    out: list[tuple[int, str]] = []
    for i, m in enumerate(matches):
        qno = int(m.group(1))
        if out and qno != out[-1][0] + 1:
            continue
        if not out and qno != 1:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        out.append((qno, full_text[start:end].strip()))
    return out


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
