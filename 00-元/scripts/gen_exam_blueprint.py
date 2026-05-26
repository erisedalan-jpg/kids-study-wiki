"""吉林数学高考题位考点速查 — 打印优化单 HTML 生成器。

按卷型三段（08-22 旧/2023 过渡/24+ 最新）× 题位 (题型,题号) 聚合真题考点频次，
经归一表合并同义后按频次排，渲染 A4 打印 CSS 的单 HTML。

P1：只含考点频次（无公式/方法/易错速查库，那是 P2）。

CLI:
  python 00-元/scripts/gen_exam_blueprint.py                 # dry-run 打印各段题位统计
  python 00-元/scripts/gen_exam_blueprint.py --dump-考点      # 导去重考点+频次（喂归一表）
  python 00-元/scripts/gen_exam_blueprint.py --apply         # 写 docs/student/数学题位速查.html
"""
from __future__ import annotations

import argparse
import collections
import html
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, read_frontmatter, setup_utf8  # noqa: E402

EXAM_DIR = REPO_ROOT / "真题" / "吉林-数学"
OUT_HTML = REPO_ROOT / "docs" / "student" / "数学题位速查.html"
NORMALIZE_YAML = Path(__file__).parent / "normalize_考点_数学.yaml"

ERA_ORDER = ["旧结构(08-22)", "过渡(2023)", "最新(24+)"]
TYPE_ORDER = {"选择": 0, "填空": 1, "解答": 2}
DIFF_RANK = {"易": 0, "中": 1, "难": 2}


def parse_kaodian(v: str) -> list[str]:
    v = (v or "").strip()
    if v.startswith("[") and v.endswith("]"):
        return [x.strip() for x in v[1:-1].split(",") if x.strip()]
    return [v] if v else []


def era_of(year: int) -> str | None:
    if 2008 <= year <= 2022:
        return "旧结构(08-22)"
    if year == 2023:
        return "过渡(2023)"
    if year >= 2024:
        return "最新(24+)"
    return None


def difficulty_mode(diffs: list[str]) -> str:
    if not diffs:
        return "?"
    c = collections.Counter(diffs)
    top = max(c.values())
    cands = [d for d, n in c.items() if n == top]
    return max(cands, key=lambda d: DIFF_RANK.get(d, -1))


def canon(name: str, normalize: dict[str, str]) -> str:
    return normalize.get(name, name)


def aggregate(rows: list[dict], normalize: dict[str, str]) -> dict:
    """rows = 真题 frontmatter 字典列表 → {段: {(题型,题号): {n, 难度倾向, 考点:[(名,次)...]}}}"""
    bucket: dict = {}
    diffs: dict = {}
    counts: dict = {}
    for r in rows:
        try:
            year = int(r.get("年份") or 0)
        except ValueError:
            continue
        era = era_of(year)
        if era is None:
            continue
        if era == "旧结构(08-22)" and r.get("文理") != "理":
            continue
        try:
            qno = int(r.get("题号") or 0)
        except ValueError:
            continue
        slot = (r.get("题型", ""), qno)
        key = (era, slot)
        counts[key] = counts.get(key, 0) + 1
        diffs.setdefault(key, []).append(r.get("难度", ""))
        kc = bucket.setdefault(key, collections.Counter())
        for kp in parse_kaodian(r.get("考点", "")):
            kc[canon(kp, normalize)] += 1
    out: dict = {}
    for (era, slot), kc in bucket.items():
        out.setdefault(era, {})[slot] = {
            "n": counts[(era, slot)],
            "难度倾向": difficulty_mode(diffs[(era, slot)]),
            "考点": kc.most_common(),
        }
    return out
