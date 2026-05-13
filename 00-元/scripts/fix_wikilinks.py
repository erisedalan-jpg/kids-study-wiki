"""把所有 `[[X]]` (无 `|`) 改写为 `[[实际文件名|X]]`。

Obsidian 的 `[[X]]` link resolver 只看文件名，不读 frontmatter aliases。
所以含数字前缀的文件（如 `017-减法.md`）必须用 `[[017-减法|减法]]` 才能
跳转。本脚本把全仓 `[[X]]` 自动改写为带显示别名的完整链接。

策略
----
1. 收集所有学科 + 真题词条 .md 的 stem → 同时记录 bare-name 和 aliases。
2. 扫所有 .md（学科 + 真题 + 学习路径 + 索引）正文里的 `[[X]]`：
   - X 含 `/` 或 `\\`：路径型链接（教材路径），跳过
   - X 命中 stem（如 `[[017-减法]]` / `[[2022-文-01]]`）：已规范化，跳过
   - X 命中 alias / bare-name：改写为 `[[<stem>|X]]`
   - X 同时含 `#section`：保留 section，写成 `[[<stem>#section|X]]`
   - X 解析不到（lexicon 缺口）：跳过 + 记到 unresolved.log
3. 跨学科同名冲突：保留第一个出现的（按字典序学科）。

CLI
---
    python 00-元/scripts/fix_wikilinks.py --dry-run     # 默认: 仅打印统计
    python 00-元/scripts/fix_wikilinks.py --dry-run --sample 5  # 同时打印 5 个样例 diff
    python 00-元/scripts/fix_wikilinks.py --apply        # 真改文件
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import (  # noqa: E402
    REPO_ROOT, SUBJECT_DIRS, bare_name, iter_entries, iter_exam_dirs,
    setup_utf8,
)
from analyze_links import parse_aliases  # noqa: E402


FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# `[[X]]` 不含 `|`（已经规范化的 `[[X|Y]]` 跳过）
LINK_RE = re.compile(r"\[\[([^\]\[|#]+)(#[^\]\[|]*)?\]\]")


def collect_targets() -> tuple[dict[str, str], dict[str, str]]:
    """返回 (stem_set, lookup)。

    stem_set: 所有 .md 的 stem (含前缀) 集合。
    lookup: alias / bare-name → 规范 stem 的映射，首次写入优先。
    """
    stem_set: set[str] = set()
    lookup: dict[str, str] = {}

    def add_alias(key: str, stem: str) -> None:
        if key and key not in lookup:
            lookup[key] = stem

    def process_file(p: Path) -> None:
        stem = p.stem
        stem_set.add(stem)
        bare = bare_name(p)
        add_alias(bare, stem)
        text = p.read_text(encoding="utf-8", errors="replace")
        m = FM_RE.match(text)
        if not m:
            return
        for a in parse_aliases(m.group(1)):
            add_alias(a, stem)

    for s in SUBJECT_DIRS:
        d = REPO_ROOT / s
        if not d.is_dir():
            continue
        for p in iter_entries(d):
            process_file(p)
    for exam_dir in iter_exam_dirs():
        for p in iter_entries(exam_dir):
            process_file(p)
    return stem_set, lookup


def rewrite_text(
    text: str, stem_set: set[str], lookup: dict[str, str]
) -> tuple[str, int, list[str]]:
    """对单文件正文做改写。返回 (new_text, fixed_count, unresolved_targets)."""
    unresolved: list[str] = []
    fixed = 0

    def replace(m: re.Match) -> str:
        nonlocal fixed
        target = m.group(1).strip()
        section = m.group(2) or ""  # 形如 '#xxx' 或 ''
        # 路径型链接（教材 / 学习路径 子目录）：跳过
        if "/" in target or "\\" in target:
            return m.group(0)
        # 空 target：跳过
        if not target:
            return m.group(0)
        # 已经是规范 stem：跳过
        if target in stem_set:
            return m.group(0)
        # 命中 alias / bare-name → 改写
        if target in lookup:
            fixed += 1
            return f"[[{lookup[target]}{section}|{target}]]"
        # 解析不到 → 记为 unresolved，保持原样
        unresolved.append(target)
        return m.group(0)

    new_text = LINK_RE.sub(replace, text)
    return new_text, fixed, unresolved


def canonicalize_files(paths: list[Path]) -> tuple[int, list[str]]:
    """对指定文件做 `[[X]]` → `[[stem|X]]` 局部规范化。

    适合在生成脚本（exam_render / gen_atom_skeleton / ...）写盘后调用，
    只规范化"刚写出的那批文件"，不动其他文件。

    Returns
    -------
    (rewritten_count, unresolved_targets) :
        改写的链接数 + 未能解析的 link target 列表（保持原样的）。
    """
    stem_set, lookup = collect_targets()
    total_fixed = 0
    all_unresolved: list[str] = []
    for p in paths:
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        new_text, fixed, unresolved = rewrite_text(text, stem_set, lookup)
        all_unresolved.extend(unresolved)
        if fixed:
            p.write_text(new_text, encoding="utf-8")
            total_fixed += fixed
    return total_fixed, all_unresolved


def iter_all_md() -> list[Path]:
    """所有需要扫描的 .md 路径（学科 + 真题 + 学习路径 + 索引 + 元目录）。"""
    out: list[Path] = []
    # 学科
    for s in SUBJECT_DIRS:
        d = REPO_ROOT / s
        if d.is_dir():
            out.extend(iter_entries(d))
    # 真题
    for exam_dir in iter_exam_dirs():
        out.extend(iter_entries(exam_dir))
    # 其他目录（学习路径 / 索引 / 元）
    for extra in ("00-元", "索引", "docs"):
        d = REPO_ROOT / extra
        if d.is_dir():
            for p in d.rglob("*.md"):
                if p.name.lower() in {"readme.md", "index.md"}:
                    continue
                out.append(p)
    return out


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="真改文件 (否则 dry-run)")
    ap.add_argument("--sample", type=int, default=0, help="dry-run 时打印 N 个 diff 样例")
    args = ap.parse_args()

    print("📚 收集所有词条 stem + alias ...")
    stem_set, lookup = collect_targets()
    print(f"   stem: {len(stem_set)} / alias→stem: {len(lookup)}")

    files = iter_all_md()
    print(f"📂 扫描 {len(files)} 个 .md ...")

    total_fixed = 0
    files_touched = 0
    unresolved_counter: dict[str, int] = defaultdict(int)
    sample_diffs: list[tuple[Path, list[tuple[str, str]]]] = []

    for p in files:
        text = p.read_text(encoding="utf-8", errors="replace")
        new_text, fixed, unresolved = rewrite_text(text, stem_set, lookup)
        for u in unresolved:
            unresolved_counter[u] += 1
        if fixed == 0:
            continue
        total_fixed += fixed
        files_touched += 1
        if args.apply:
            p.write_text(new_text, encoding="utf-8")
        elif len(sample_diffs) < args.sample:
            # 收集前 5 个改写片段作为样例
            diffs: list[tuple[str, str]] = []
            for m in LINK_RE.finditer(text):
                target = m.group(1).strip()
                if (
                    target
                    and "/" not in target
                    and "\\" not in target
                    and target not in stem_set
                    and target in lookup
                ):
                    section = m.group(2) or ""
                    diffs.append(
                        (m.group(0), f"[[{lookup[target]}{section}|{target}]]")
                    )
                    if len(diffs) >= 3:
                        break
            if diffs:
                sample_diffs.append((p, diffs))

    print()
    print("=" * 60)
    print(f"  files touched:    {files_touched}")
    print(f"  links rewritten:  {total_fixed}")
    print(f"  unresolved tgts:  {len(unresolved_counter)} 唯一 / "
          f"{sum(unresolved_counter.values())} 总次数")
    print("=" * 60)

    if not args.apply and sample_diffs:
        print()
        print("=== 改写样例（dry-run）===")
        for p, diffs in sample_diffs:
            rel = p.relative_to(REPO_ROOT)
            print(f"\n  📄 {rel}")
            for old, new in diffs:
                print(f"     -  {old}")
                print(f"     +  {new}")

    if unresolved_counter:
        print()
        print("=== Top 20 unresolved targets（保持原样）===")
        for u, n in sorted(
            unresolved_counter.items(), key=lambda x: -x[1]
        )[:20]:
            print(f"  {n:>3}  [[{u}]]")

    if not args.apply:
        print()
        print("👉 dry-run 完毕。加 --apply 真写文件。")
    else:
        print()
        print(f"✅ 已改 {files_touched} 个文件 / {total_fixed} 条链接。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
