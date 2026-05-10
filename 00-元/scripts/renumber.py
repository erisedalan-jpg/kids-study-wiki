"""
通用学科目录序号化脚本。

替代历史一次性脚本（renumber_chemistry.py / _biology.py / _chinese.py 等）。

两种模式
--------
默认（增量）：
    保留所有已编号文件的现有顺序；只为无前缀的新文件按 frontmatter
    学期/主题 排序后插入末尾，重新连续编号。

--rebuild（完全重排）：
    完全忽略现有前缀，按 frontmatter 学段/学期/主题/主题分组重新排序所有文件。
    仅在导入新教材或大规模整理时使用。

用法
----
    python 00-元/scripts/renumber.py 化学              # 增量，自动 3 位前缀
    python 00-元/scripts/renumber.py 数学 --width 2    # 强制 2 位
    python 00-元/scripts/renumber.py 语文 --dry-run    # 只看不改
    python 00-元/scripts/renumber.py 化学 --rebuild --dry-run  # 完全重排预览

排序规则（无前缀文件 + --rebuild 模式）
----------------------------------------
    1. xueqi_key(学段, 学期, 主题) — 扫描多字段找已知学期键
    2. frontmatter 主题字典序
    3. bare-name 字典序

边界
----
    - 目标文件名已存在会跳过并记录警告（不强制覆盖）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import (  # noqa: E402
    PREFIX_RE, REPO_ROOT, iter_entries, read_frontmatter, setup_utf8,
    strip_prefix, xueqi_key,
)


def collect(subject: str) -> list[tuple[Path, dict[str, str]]]:
    subject_dir = REPO_ROOT / subject
    if not subject_dir.is_dir():
        sys.exit(f"ERROR: 学科目录不存在: {subject_dir}")
    return [(p, read_frontmatter(p)) for p in iter_entries(subject_dir)]


def existing_prefix(name: str) -> int:
    """已有前缀数字；无前缀返回 -1 排在最前以便插入或返回大数排末尾。"""
    m = PREFIX_RE.match(name)
    return int(m.group(1)) if m else -1


def sort_key_rebuild(item: tuple[Path, dict[str, str]]) -> tuple[int, str, str]:
    p, fm = item
    return (
        xueqi_key(fm.get("学段", ""), fm.get("学期", ""), fm.get("主题", "")),
        fm.get("主题", "").strip(),
        strip_prefix(p.name),
    )


def sort_key_incremental(item: tuple[Path, dict[str, str]]) -> tuple[int, int, str, str]:
    """已有前缀按数字升序；无前缀文件按 frontmatter 学期键排（追加在末尾）。"""
    p, fm = item
    pref = existing_prefix(p.name)
    if pref >= 0:
        return (0, pref, "", "")
    return (
        1,  # 无前缀的排在所有有前缀的之后
        xueqi_key(fm.get("学段", ""), fm.get("学期", ""), fm.get("主题", "")),
        fm.get("主题", "").strip(),
        strip_prefix(p.name),
    )


def renumber(subject: str, width: int, rebuild: bool, dry_run: bool) -> int:
    items = collect(subject)
    items.sort(key=sort_key_rebuild if rebuild else sort_key_incremental)
    fmt = f"{{:0{width}d}}-{{}}"
    moves: list[tuple[Path, Path]] = []
    for idx, (p, _fm) in enumerate(items, start=1):
        bare = strip_prefix(p.name)
        new_name = fmt.format(idx, bare)
        if p.name == new_name:
            continue
        moves.append((p, p.with_name(new_name)))

    mode = "rebuild" if rebuild else "incremental"
    print(f"[{subject}] {len(items)} entries, {len(moves)} renames (mode={mode})")
    skipped = 0
    for old, new in moves:
        if new.exists() and new != old:
            print(f"  SKIP: target exists -> {new.name}")
            skipped += 1
            continue
        if dry_run:
            print(f"  DRY:  {old.name} -> {new.name}")
        else:
            old.rename(new)
            print(f"  OK:   {old.name} -> {new.name}")
    print(f"[{subject}] done. skipped={skipped} dry_run={dry_run}")
    return 0


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description="学科目录词条序号化")
    ap.add_argument("subject", help="学科目录名，如 化学/语文/物理")
    ap.add_argument("--width", type=int, default=0, help="前缀位数；0 = 自动 (≤99 用 2 位，>99 用 3 位)")
    ap.add_argument("--rebuild", action="store_true",
                    help="完全重排：忽略现有前缀，按 frontmatter 重新排序所有文件")
    ap.add_argument("--dry-run", action="store_true", help="只打印不改名")
    args = ap.parse_args()

    items = collect(args.subject)
    width = args.width or (3 if len(items) > 99 else 2)
    return renumber(args.subject, width, args.rebuild, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
