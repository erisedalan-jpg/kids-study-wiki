"""真题页文本 → (题干, 解析) 纯切分（无 IO，便于单测）。

策略：在页文本里找「行首题号」的所有出现；对每个出现，块=该题号到下一题号(qno+1)。
优先选「块内含解析标记」的那个出现（跳过须知页里的「1．答题前…」等无解析块）。
块内以解析标记切分题干与解析；新旧解析卷标记兼容：
  新卷 【答案】【解析】【详解】；旧卷 【考点】【专题】【分析】【解答】【点评】；行首 解：。
找不到任何题号锚点 → fallback：整页归解析段。
"""
from __future__ import annotations

import re

_ANS_MARK = re.compile(
    r"(【答案】|【解析】|【详解】|【解答】|【分析】|【考点】|【点评】|【专题】|^解[：:])", re.M
)


def _qno_anchor(qno: int) -> re.Pattern:
    # 行首题号：1．/ 1. / 1、（全/半角点顿号），允许前导空白
    return re.compile(rf"^\s*{qno}\s*[．.、]", re.M)


def segment_by_qno(page_text: str, qno: int) -> dict:
    """返回 {题干, 解析, fallback}。"""
    anchors = list(_qno_anchor(qno).finditer(page_text))
    if not anchors:
        return {"题干": "", "解析": page_text.strip(), "fallback": True}
    nexts = list(_qno_anchor(qno + 1).finditer(page_text))

    def block_for(m: re.Match) -> str:
        nxt = next((n for n in nexts if n.start() > m.end()), None)
        return page_text[m.start(): nxt.start() if nxt else len(page_text)]

    # 优先选块内含解析标记的题号出现（跳过须知里的"1．答题前"等无解析块）
    chosen = next((m for m in anchors if _ANS_MARK.search(block_for(m))), anchors[0])
    block = block_for(chosen)
    am = _ANS_MARK.search(block)
    if am:
        stem, sol = block[: am.start()], block[am.start():]
    else:
        stem, sol = block, ""
    return {"题干": stem.strip(), "解析": sol.strip(), "fallback": False}
