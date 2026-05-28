"""考点名语义近义归并检测：词法相似度扫描 canonical 规范名 → 报告 + 合并草案。
纯函数 + 薄 CLI。绝不改 canonical/词条；合并是人工复核草案后的独立动作。
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from _utils import setup_utf8  # noqa: E402

# ── 去噪：删除不影响语义的虚词，使「函数的单调性」≡「函数单调性」 ──
_NOISE = ("的", "之")
_TAIL = ("运算", "问题")
# _NOISE/_TAIL 可按需扩充


def _denoise(s: str) -> str:
    for ch in _NOISE:
        s = s.replace(ch, "")
    return s.strip()


def _strip_tail(s: str) -> str:
    for t in _TAIL:
        if s.endswith(t) and len(s) > len(t):
            return s[: -len(t)]  # 最多剥一个尾缀
    return s


def _bigrams(s: str) -> set[str]:
    # 单字符无 bigram，退化为字级集合（保证自身相似=1）
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def s_bigram(a: str, b: str) -> float:
    ba, bb = _bigrams(a), _bigrams(b)
    if not ba or not bb:
        return 0.0
    return len(ba & bb) / len(ba | bb)


def s_jaccard(a: str, b: str) -> float:
    ca, cb = set(a), set(b)
    if not ca or not cb:
        return 0.0
    return len(ca & cb) / len(ca | cb)


def _lev(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def s_edit(a: str, b: str) -> float:
    m = max(len(a), len(b))
    return 1.0 - _lev(a, b) / m if m else 0.0


def s_contain(a: str, b: str) -> float:
    """a,b 已去噪。去尾缀后相等或互为子串 → 0.95。"""
    na, nb = _strip_tail(a), _strip_tail(b)
    if not na or not nb:
        return 0.0
    if na == nb or na in nb or nb in na:
        return 0.95
    return 0.0


def name_similarity(a: str, b: str) -> float:
    """词法相似度 ∈[0,1]。可插拔接口——嵌入层日后替换此函数。"""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    na, nb = _denoise(a), _denoise(b)
    if na == nb:
        return 0.97
    weighted = 0.6 * s_bigram(na, nb) + 0.25 * s_jaccard(na, nb) + 0.15 * s_edit(na, nb)
    return max(s_contain(na, nb), weighted)


def load_contrast_groups(subject: str) -> list[set[str]]:
    """读 contrast_terms.yaml，返回 通用 + 该科 的词组（set 列表）。"""
    path = Path(__file__).parent / "contrast_terms.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    groups: list[set[str]] = []
    for key in ("通用", subject):
        for grp in data.get(key, []) or []:
            if grp:
                groups.append(set(grp))
    return groups


def is_contrast_pair(a: str, b: str, groups: list[set[str]]) -> bool:
    """a 把某组内一词换成同组另一词后 == b → 对立项。差一个对立词即命中。"""
    for grp in groups:
        for t1 in grp:
            if t1 in a:
                for t2 in grp:
                    if t2 != t1 and a.replace(t1, t2) == b:
                        return True
    return False
