"""聚合 考点 → {父主题, 真题(按年份降序), 真题数, 题位, 难度分布, 年份跨度}。纯函数。"""
from __future__ import annotations

import collections


def _year(a: dict) -> int:
    try:
        return int(a.get("年份") or 0)
    except ValueError:
        return 0


def build_kaodian_map(atoms: list[dict], group: dict[str, str]) -> dict[str, dict]:
    """atoms: 真题 frontmatter 列表（含 _bare/考点/年份/难度/题型/题号/摘要）。
    返回仅含有 ≥1 真题的考点。"""
    by: dict[str, list[dict]] = collections.defaultdict(list)
    for a in atoms:
        for kp in a.get("考点", []) or []:
            by[kp].append(a)
    out: dict[str, dict] = {}
    for kp, items in by.items():
        items = sorted(items, key=lambda x: -_year(x))
        diffs = collections.Counter(x.get("难度", "") for x in items)
        qpos = sorted({(x.get("题型", ""), int(x.get("题号") or 0)) for x in items},
                      key=lambda t: (t[0], t[1]))
        years = [_year(x) for x in items if _year(x)]
        out[kp] = {
            "父主题": group.get(kp, "其他"),
            "真题": items,
            "真题数": len(items),
            "题位": qpos,
            "难度分布": dict(diffs),
            "年份跨度": (min(years), max(years)) if years else (0, 0),
        }
    return out
