"""真题页文本 → (题干, 解析) 纯切分（无 IO，便于单测）。

策略：在页文本里以「行首题号」为边界切出本题块（题号 N 到 N+1），
块内以 答案/解析 标记（【答案】【解析】【详解】解：）切分题干与解析。
切分失败（找不到本题号锚点）→ fallback：整页归解析段。
"""
from __future__ import annotations

import re

_ANS_MARK = re.compile(r"(【答案】|【解析】|【详解】|^解[：:])", re.M)


def _qno_anchor(qno: int) -> re.Pattern:
    # 行首题号：1．/ 1. / 1、（全/半角点顿号），允许前导空白
    return re.compile(rf"^\s*{qno}\s*[．.、]", re.M)


def segment_by_qno(page_text: str, qno: int) -> dict:
    """返回 {题干, 解析, fallback}。"""
    m = _qno_anchor(qno).search(page_text)
    if not m:
        return {"题干": "", "解析": page_text.strip(), "fallback": True}
    start = m.start()
    nxt = _qno_anchor(qno + 1).search(page_text, m.end())
    block = page_text[start: nxt.start() if nxt else len(page_text)]
    am = _ANS_MARK.search(block)
    if am:
        stem, sol = block[: am.start()], block[am.start():]
    else:
        stem, sol = block, ""
    return {"题干": stem.strip(), "解析": sol.strip(), "fallback": False}
