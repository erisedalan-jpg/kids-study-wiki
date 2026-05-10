"""
扫描所有学科目录，找出 bare-name 跨学科重名。

用法
----
    python 00-元/scripts/check_naming_conflicts.py
    python 00-元/scripts/check_naming_conflicts.py --candidates "蛋白质,糖类,DNA"

退出码
------
    0  无冲突
    1  发现冲突（报告到 stdout）

为何重要
--------
    跨学科重名会让 [[蛋白质]] 等链接随机解析。批量分发新词条前，先用
    `--candidates` 预检计划写入的概念清单，提前安排消歧后缀（如
    `蛋白质（生物）`、`蛋白质（化学）`）。
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, SUBJECT_DIRS, bare_name, iter_entries, setup_utf8  # noqa: E402


def scan() -> dict[str, list[Path]]:
    """bare-name → [所有出现位置]"""
    index: dict[str, list[Path]] = defaultdict(list)
    for s in SUBJECT_DIRS:
        d = REPO_ROOT / s
        if not d.is_dir():
            continue
        for p in iter_entries(d):
            # 已带消歧后缀（含括号）的视作独立条目，跳过
            base = bare_name(p)
            stem = base.split("（", 1)[0]  # 全角括号
            stem = stem.split("(", 1)[0]   # 半角括号
            index[stem].append(p)
    return index


def report_existing() -> int:
    index = scan()
    conflicts = {k: v for k, v in index.items() if len(v) > 1}
    if not conflicts:
        print("OK: 当前无跨学科重名冲突")
        return 0
    print(f"发现 {len(conflicts)} 个跨学科重名:")
    for name, paths in sorted(conflicts.items()):
        print(f"  {name}:")
        for p in paths:
            rel = p.relative_to(REPO_ROOT)
            print(f"    - {rel}")
        print(f"    建议消歧: {name}（学科）.md")
    return 1


def report_candidates(candidates: list[str]) -> int:
    index = scan()
    hit = []
    for c in candidates:
        c = c.strip()
        if not c:
            continue
        if c in index:
            hit.append((c, index[c]))
    if not hit:
        print(f"OK: {len(candidates)} 个候选名均无冲突")
        return 0
    print(f"候选清单中 {len(hit)} 个名称已存在:")
    for name, paths in hit:
        print(f"  {name}:")
        for p in paths:
            print(f"    - existing: {p.relative_to(REPO_ROOT)}")
        print(f"    建议命名: {name}（学科）.md 或 {name}（高中）.md")
    return 1


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default="", help="逗号分隔的待写入 bare-name 清单")
    args = ap.parse_args()

    if args.candidates:
        return report_candidates(args.candidates.split(","))
    return report_existing()


if __name__ == "__main__":
    raise SystemExit(main())
