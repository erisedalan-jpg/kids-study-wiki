"""候选 tag 生成器（不调用 LLM）。

输入: 题块 JSON + 白名单 JSON
输出: 给每题加 tag_candidates: [...] 字段，按命中频次降序

LLM 终审在 plan Task 9 由 sonnet 子代理完成（独立步骤），
本脚本仅产出客观可重现的关键词命中候选。

用法:
    python 00-元/scripts/tag_questions.py \
        --questions docs/superpowers/working/吉林-数学-2024-不分-新课标Ⅱ-questions.json \
        --lexicon  00-元/scripts/_数学_lexicon.json
    # 写回输入 JSON（原地修改）
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _utils import setup_utf8  # noqa: E402


def _hit_counts(text: str, lex: dict[str, dict]) -> Counter[str]:
    """统计 text 中每个白名单 term 出现次数（聚合到 bare-name）。"""
    cnt: Counter[str] = Counter()
    for term, meta in lex.items():
        if len(term) < 2:
            continue
        n = text.count(term)
        if n > 0:
            cnt[meta["bare"]] += n
    return cnt


def tag_paper(qa: dict[str, Any], lex: dict[str, dict]) -> dict[str, Any]:
    """在 qa["questions"] 每题上加 tag_candidates 字段。"""
    for q in qa["questions"]:
        text = "\n".join([q.get("stem", ""), q.get("answer", ""), q.get("solution", "")])
        cnt = _hit_counts(text, lex)
        q["tag_candidates"] = [t for t, _ in cnt.most_common(8)]
    return qa


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    ap.add_argument("--lexicon", required=True)
    args = ap.parse_args()

    qa = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    lex = json.loads(Path(args.lexicon).read_text(encoding="utf-8"))
    tag_paper(qa, lex)
    Path(args.questions).write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(q["tag_candidates"]) for q in qa["questions"])
    print(f"OK: 候选写回 {args.questions}（{len(qa['questions'])} 题，共 {total} 个候选 tag）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
