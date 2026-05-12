"""OCR 抽样校验：v4-flash 比对 pdfplumber 切分文本 vs 原 PDF 文本

属于工作流 B v2 Step 3。每张卷随机抽 N 题，把 questions.json 里的 stem
与原 PDF 同位置文本送给 DeepSeek v4-flash 判断 OCR/切分质量。

输入: questions.json（parse_exam_pdf.py 的产出）
输出: JSONL 报告，每题一行 {paper_id, qno, has_issue, issue_type, summary}

用法
----
    # 校验单张卷
    python 00-元/scripts/ocr_sample_check.py \
        --questions docs/superpowers/working/吉林-数学-2024-不分-新课标Ⅱ-questions.json \
        --sample 3 \
        --out docs/superpowers/working/ocr_check.jsonl

    # 批量反向跑 working 目录下所有卷
    python 00-元/scripts/ocr_sample_check.py \
        --working-dir docs/superpowers/working/ \
        --sample 3 \
        --out docs/superpowers/working/ocr_check.jsonl

退出码
------
    0  全部样本通过（has_issue 全部 false）或仅 issue_type=无
    1  存在 has_issue=true 的样本
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
from _llm_router import LLMError, Task, call  # noqa: E402
from _utils import REPO_ROOT, setup_utf8  # noqa: E402


PROMPT_TEMPLATE = """对照下面两段文本，判断"切分版本"是否完整准确反映"原 PDF 片段"中第 {qno} 题题面。

[原 PDF 片段]
{pdf_window}

[切分版本]
{stem}

关注: 公式符号 / 上下标 / 选项 A B C D 齐全 / 跨题污染 / 字符缺失。

按下面两行格式输出，不要额外内容:
第一行: 通过 或 公式乱码 或 选项缺失 或 跨题污染 或 字符缺失
第二行: 一句话理由（不超过 30 字）
"""

VALID_ISSUE_TYPES = {"通过", "公式乱码", "选项缺失", "跨题污染", "字符缺失"}


def extract_pdf_fulltext(pdf_path: Path) -> str:
    """重新提取整张 PDF 全文（与 parse_exam_pdf 保持一致的策略）。"""
    chunks: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            chunks.append(t)
    return "\n".join(chunks)


def find_question_window(fulltext: str, qno: int, window: int = 600) -> str:
    """在原 PDF 全文里定位题号 qno 周围 ±window 字符。

    若找不到（题号格式异常），返回前 1200 字符兜底。
    """
    # 同 parse_exam_pdf 的 QNO_RE 模式
    pat = re.compile(rf"(^|\n)\s*{qno}\s*[\.、．]\s*", re.MULTILINE)
    m = pat.search(fulltext)
    if not m:
        return fulltext[:1200]
    start = max(0, m.start() - 100)
    end = min(len(fulltext), m.end() + window)
    return fulltext[start:end]


def parse_llm_verdict(text: str) -> dict[str, Any]:
    """从 LLM 半结构化输出抽 verdict。

    期望两行格式:
        通过
        切分版本完整对应原文

    容忍 "结论: 通过" / "结果: 公式乱码" 之类的前缀，逐字段抽。
    LLM 偶发空输出 → 标记为"调用失败"由调用方决定重试。
    """
    if not text or not text.strip():
        return {
            "has_issue": True,
            "issue_type": "调用失败",
            "summary": "LLM 返回空内容",
        }
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return {
            "has_issue": True,
            "issue_type": "调用失败",
            "summary": "LLM 返回空行",
        }
    # 第一行：抽 issue type
    first = lines[0]
    if ":" in first or "：" in first:
        first = re.split(r"[:：]", first, maxsplit=1)[-1].strip()
    issue_type = "未识别"
    for t in VALID_ISSUE_TYPES:
        if t in first:
            issue_type = t
            break
    summary = lines[1] if len(lines) >= 2 else first
    has_issue = issue_type != "通过"
    return {
        "has_issue": has_issue,
        "issue_type": "无" if issue_type == "通过" else issue_type,
        "summary": summary[:80],
    }


def check_one_question(
    qa: dict[str, Any], q: dict[str, Any], pdf_fulltext: str
) -> dict[str, Any]:
    pdf_window = find_question_window(pdf_fulltext, q["qno"])
    prompt = PROMPT_TEMPLATE.format(
        pdf_window=pdf_window[:1500],  # 控住上下文
        qno=q["qno"],
        stem=q["stem"][:1500],
    )
    try:
        result = call(prompt, task=Task.SIMPLE, temperature=0.0, max_tokens=400)
        verdict = parse_llm_verdict(result.text)
        # v4-flash 偶发空输出，重试 1 次升 v4-pro
        if verdict.get("issue_type") == "调用失败":
            result = call(prompt, task=Task.COMPLEX, temperature=0.0, max_tokens=400)
            verdict = parse_llm_verdict(result.text)
        verdict["model"] = result.model
    except LLMError as e:
        verdict = {
            "has_issue": True,
            "issue_type": "调用失败",
            "summary": str(e)[:100],
        }
    verdict["paper_id"] = qa.get("paper_id", "")
    verdict["qno"] = q["qno"]
    return verdict


def check_paper(qa_path: Path, sample: int, seed: int = 42) -> list[dict[str, Any]]:
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    pdf_rel = qa.get("source_pdf", "")
    pdf_path = REPO_ROOT / pdf_rel if pdf_rel else None
    if pdf_path is None or not pdf_path.exists():
        return [
            {
                "paper_id": qa.get("paper_id", ""),
                "qno": 0,
                "has_issue": True,
                "issue_type": "PDF 缺失",
                "summary": f"source_pdf 路径不存在: {pdf_rel}",
            }
        ]

    fulltext = extract_pdf_fulltext(pdf_path)
    rng = random.Random(seed)
    n = min(sample, len(qa["questions"]))
    picked = rng.sample(qa["questions"], n)
    picked.sort(key=lambda x: x["qno"])
    return [check_one_question(qa, q, fulltext) for q in picked]


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--questions", help="单张卷 questions.json")
    src.add_argument("--working-dir", help="批量扫目录下所有 *-questions.json")
    ap.add_argument("--sample", type=int, default=3, help="每张卷抽样题数（默认 3）")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", required=True, help="输出 JSONL 报告路径")
    args = ap.parse_args()

    if args.questions:
        qa_paths = [Path(args.questions)]
    else:
        qa_paths = sorted(Path(args.working_dir).glob("*-questions.json"))
    if not qa_paths:
        sys.exit(f"ERROR: 未找到 questions.json")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    issues = 0
    total = 0
    with out_path.open("w", encoding="utf-8") as f:
        for qa_path in qa_paths:
            print(f"[check] {qa_path.name}", file=sys.stderr)
            results = check_paper(qa_path, args.sample, seed=args.seed)
            for r in results:
                total += 1
                if r.get("has_issue"):
                    issues += 1
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                flag = "⚠️" if r.get("has_issue") else "✅"
                print(
                    f"  {flag} qno={r['qno']:>2} type={r.get('issue_type', '无')} | {r.get('summary', '')[:50]}",
                    file=sys.stderr,
                )

    print(
        f"\n抽样 {total} 题 / 标记问题 {issues} 题 → {out_path}",
        file=sys.stderr,
    )
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
