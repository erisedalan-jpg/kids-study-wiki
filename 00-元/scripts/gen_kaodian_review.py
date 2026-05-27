# gen_kaodian_review.py（本任务仅 build_prompt + 模板加载；主流程下个任务）
from __future__ import annotations

import re
from pathlib import Path

_PROMPT = Path(__file__).parent / "_prompts" / "kaodian_review.md"


def _load_template() -> str:
    return _PROMPT.read_text(encoding="utf-8")


def build_prompt(subject: str, kaodian: str, info: dict, rep_n: int = 3) -> str:
    items = info["真题"]
    rep_ids = {it["_bare"] for it in items[:rep_n]}   # 近年优先（已降序）
    blocks = []
    for it in items:
        mark = "【代表题】" if it["_bare"] in rep_ids else ""
        blocks.append(
            f"### {mark}{it['_bare']}（{it.get('年份','')}）\n"
            f"题干：{it.get('题干文本','') or it.get('摘要','')}\n"
            f"解析：{it.get('解析文本','')}"
        )
    corpus = "\n\n".join(blocks)
    y0, y1 = info["年份跨度"]
    return _load_template().format(
        subject=subject, kaodian=kaodian, parent=info["父主题"],
        n=info["真题数"], y0=y0, y1=y1, corpus=corpus,
    )
