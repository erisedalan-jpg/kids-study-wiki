"""lexicon 前置体检 + OCR 完整性双校验

属于工作流 B v2 Step 1。对每道题让 DeepSeek v4-pro 同时做两件事：
1. 抽出 2-5 个核心数学概念（用于对比 lexicon 找出 alias/缺词条缺口）
2. 校验题面是否完整

⚠️ 已知噪声 (2026-05-12)：
    v4-pro 在「OCR 完整性判断」（输出的第二行）噪声率高 — 实测对 87 题判定
    80% "不完整"，但 Opus 抽样核对显示真实字符级 bug 只占 ~5%。原因：v4-pro
    把任何 PDF 提取的字符级渲染问题（如 ∩→I、{}→ð 这类编码 outlier）都标
    "不完整"，但这些不是"游离行切丢"类的可修问题。
    用于「概念抽取」这一职责仍可靠。
    未来如需重新跑 OCR 完整性判断，按工作流 v3 路由规则改用：
      - Opus 主会话（最准，量大时上下文成本高）
      - Sonnet subagent 并行（推荐，sonnet quota 充足时）

输出：每题一行 JSONL 报告 + 末尾汇总（topN 缺口概念）。
Opus 终审阶段读报告，决定每个缺口是"加 alias 到现有词条"还是"缺词条，攒批次"。

用法
----
    # 单卷
    python 00-元/scripts/lexicon_health_check.py \
        --questions docs/superpowers/working/吉林-数学-2024-不分-新课标Ⅱ-questions.json \
        --lexicon 00-元/scripts/_数学_lexicon.json \
        --out docs/superpowers/working/lexicon_health.jsonl

    # 批量反向跑
    python 00-元/scripts/lexicon_health_check.py \
        --working-dir docs/superpowers/working/ \
        --lexicon 00-元/scripts/_数学_lexicon.json \
        --out docs/superpowers/working/lexicon_health.jsonl

退出码
------
    0  全部跑完（即便有缺口，也算正常 finished）
    1  存在 LLM 调用失败的题（需 retry）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _llm_router import LLMError, Task, call  # noqa: E402
from _utils import setup_utf8  # noqa: E402


SYSTEM_PROMPT = (
    "你是一个高考数学题考点标注员。"
    "回答必须简短直接，不展开推理过程，严格按指定格式输出。"
)

PROMPT_TEMPLATE = """任务: 阅读一道高考数学题题面，输出该题考查的核心数学概念，并校验题面是否完整。

[题面]
{stem}

按下面两行格式输出，不要额外内容:
第一行: 逗号分隔的 2-5 个核心数学概念名称（如: 集合的运算, 并集, 函数最值）
第二行: 完整 或 不完整:<具体说明 30 字内>
"""


def parse_llm_output(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        return {
            "concepts": [],
            "ocr_complete": False,
            "ocr_note": "",
            "parse_error": "LLM 返回空内容",
        }
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return {
            "concepts": [],
            "ocr_complete": False,
            "ocr_note": "",
            "parse_error": "LLM 返回空行",
        }
    # 第一行：抽概念，去前缀 "考点:" / "概念:" 之类
    first = lines[0]
    if ":" in first or "：" in first:
        first = re.split(r"[:：]", first, maxsplit=1)[-1].strip()
    concepts = [c.strip() for c in re.split(r"[,，、；;]", first) if c.strip()]

    # 第二行：抽 ocr 完整性
    second = lines[1] if len(lines) >= 2 else ""
    ocr_complete = second.startswith("完整") and not second.startswith("不完整")
    ocr_note = ""
    if not ocr_complete and (":" in second or "：" in second):
        ocr_note = re.split(r"[:：]", second, maxsplit=1)[-1].strip()
    return {
        "concepts": concepts,
        "ocr_complete": ocr_complete,
        "ocr_note": ocr_note[:80],
    }


def compare_to_lexicon(concepts: list[str], lex: dict[str, Any]) -> tuple[list[str], list[str]]:
    """返回 (matched, gaps)。lex 顶层 key 是 term（含 alias）。"""
    matched = [c for c in concepts if c in lex]
    gaps = [c for c in concepts if c not in lex]
    return matched, gaps


def check_one_question(qa: dict[str, Any], q: dict[str, Any], lex: dict) -> dict[str, Any]:
    stem = q["stem"][:2000]
    prompt = PROMPT_TEMPLATE.format(stem=stem)
    try:
        result = call(
            prompt,
            task=Task.COMPLEX,
            system=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=400,
        )
        parsed = parse_llm_output(result.text)
        # v4-pro 在 temperature=0 / 无 system 时偶发空 content，已用 system+t=0.3 缓解；
        # 仍空 → 再 retry 一次拉高 temperature
        if parsed.get("parse_error"):
            result = call(
                prompt,
                task=Task.COMPLEX,
                system=SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=600,
            )
            parsed = parse_llm_output(result.text)
        model = result.model
    except LLMError as e:
        return {
            "paper_id": qa.get("paper_id", ""),
            "qno": q["qno"],
            "call_failed": True,
            "error": str(e)[:200],
        }

    if parsed.get("parse_error"):
        return {
            "paper_id": qa.get("paper_id", ""),
            "qno": q["qno"],
            "call_failed": True,
            "error": parsed["parse_error"],
            "model": model,
        }

    matched, gaps = compare_to_lexicon(parsed["concepts"], lex)
    return {
        "paper_id": qa.get("paper_id", ""),
        "qno": q["qno"],
        "extracted_concepts": parsed["concepts"],
        "matched_in_lexicon": matched,
        "lexicon_gap": gaps,  # 待 Opus 审：alias 还是缺词条
        "ocr_complete": parsed["ocr_complete"],
        "ocr_note": parsed["ocr_note"],
        "model": model,
    }


def check_paper(qa_path: Path, lex: dict) -> list[dict[str, Any]]:
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    return [check_one_question(qa, q, lex) for q in qa["questions"]]


def write_summary(records: list[dict[str, Any]], out: Path) -> None:
    """末尾追加汇总段：缺口 topN + OCR 不完整列表 + 失败列表。"""
    gap_counter: Counter[str] = Counter()
    ocr_issues: list[str] = []
    failures: list[str] = []
    for r in records:
        if r.get("call_failed"):
            failures.append(f"{r['paper_id']} Q{r['qno']}: {r.get('error', '')[:60]}")
            continue
        for g in r.get("lexicon_gap", []):
            gap_counter[g] += 1
        if not r.get("ocr_complete", True):
            ocr_issues.append(f"{r['paper_id']} Q{r['qno']}: {r.get('ocr_note', '')}")

    summary = {
        "__summary__": True,
        "total_questions": sum(1 for r in records if not r.get("call_failed")),
        "lexicon_gap_top": gap_counter.most_common(30),
        "ocr_incomplete": ocr_issues,
        "call_failures": failures,
    }
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--questions", help="单张卷 questions.json")
    src.add_argument("--working-dir", help="批量扫目录下所有 *-questions.json")
    ap.add_argument("--lexicon", required=True, help="lexicon JSON 路径")
    ap.add_argument("--out", required=True, help="输出 JSONL 路径")
    args = ap.parse_args()

    lex = json.loads(Path(args.lexicon).read_text(encoding="utf-8"))

    if args.questions:
        qa_paths = [Path(args.questions)]
    else:
        qa_paths = sorted(Path(args.working_dir).glob("*-questions.json"))
    if not qa_paths:
        sys.exit("ERROR: 未找到 questions.json")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()  # 重跑覆盖

    all_records: list[dict[str, Any]] = []
    with out_path.open("a", encoding="utf-8") as f:
        for qa_path in qa_paths:
            print(f"[check] {qa_path.name}", file=sys.stderr)
            records = check_paper(qa_path, lex)
            for r in records:
                all_records.append(r)
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                if r.get("call_failed"):
                    flag = "❌"
                    note = f"FAIL {r.get('error', '')[:40]}"
                elif not r.get("ocr_complete", True):
                    flag = "⚠️"
                    note = f"OCR不完整 {r.get('ocr_note', '')[:30]}"
                else:
                    flag = "✅"
                    gaps = r.get("lexicon_gap", [])
                    note = f"gap={len(gaps)}" + (f" {gaps[:3]}" if gaps else "")
                print(f"  {flag} qno={r['qno']:>2} {note}", file=sys.stderr)

    write_summary(all_records, out_path)
    failures = sum(1 for r in all_records if r.get("call_failed"))
    incomplete = sum(1 for r in all_records if not r.get("call_failed") and not r.get("ocr_complete", True))
    print(
        f"\n跑完 {len(all_records)} 题 / 调用失败 {failures} / OCR 不完整 {incomplete} → {out_path}",
        file=sys.stderr,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
