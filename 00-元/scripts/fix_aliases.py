"""
为词条 frontmatter 自动补齐缺失的 bare-name alias。

读取 analyze_links.py 报告的 missing_bare_alias 列表，对每个文件：
- 已有 aliases 行：在首位插入 bare-name（自动加引号包裹特殊字符）
- 无 aliases 行：在 title 行后新增

用法
----
    python 00-元/scripts/fix_aliases.py            # 自动检测并补齐
    python 00-元/scripts/fix_aliases.py --dry-run  # 只打印不修改
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import (  # noqa: E402
    REPO_ROOT, SUBJECT_DIRS, bare_name, iter_entries, setup_utf8,
)
from analyze_links import build_graph, collect_all  # noqa: E402

ALIASES_LINE = re.compile(r"^(aliases\s*:\s*)(\[.*?\])(\s*)$", re.MULTILINE)
TITLE_LINE = re.compile(r"^(title\s*:.*?)$", re.MULTILINE)
NEEDS_QUOTE = re.compile(r"[,\[\]\{\}\"'#@&*!|>%`?…？。！，；：（）()]")


def quote_if_needed(s: str) -> str:
    """给含特殊字符的 alias 加双引号；本身含 `"` 改用单引号；都含就转义。"""
    if not NEEDS_QUOTE.search(s):
        return s
    if '"' not in s:
        return f'"{s}"'
    if "'" not in s:
        return f"'{s}'"
    return '"' + s.replace('"', '\\"') + '"'


def insert_into_aliases_line(line_inner: str, bare: str) -> str:
    """`[a, b]` -> `[<bare>, a, b]`；幂等：bare 已在则原样返回。"""
    inner = line_inner.strip()[1:-1].strip()  # strip [ ]
    quoted = quote_if_needed(bare)
    if not inner:
        return f"[{quoted}]"
    # 检查是否已含（识别裸/带引号两种）
    parts = [p.strip() for p in re.split(r",(?=(?:[^\"']|\"[^\"]*\"|'[^']*')*$)", inner)]
    bare_norm = bare.strip()
    for p in parts:
        if p.strip("\"'") == bare_norm:
            return f"[{inner}]"  # 已含，不重复
    return f"[{quoted}, {inner}]"


def process(path: Path, bare: str, dry_run: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    m = ALIASES_LINE.search(text)
    if m:
        new_inner = insert_into_aliases_line(m.group(2), bare)
        new_line = m.group(1) + new_inner + (m.group(3) or "")
        if new_line == m.group(0):
            return False  # 已含
        new_text = text[:m.start()] + new_line + text[m.end():]
    else:
        # 无 aliases 行，在 title 后插入一行
        tm = TITLE_LINE.search(text)
        if not tm:
            print(f"  WARN: {path} 无 title 行，跳过")
            return False
        quoted = quote_if_needed(bare)
        insert_at = tm.end()
        new_text = text[:insert_at] + f"\naliases: [{quoted}]" + text[insert_at:]

    if dry_run:
        print(f"  DRY: {path.name} <- {bare}")
    else:
        path.write_text(new_text, encoding="utf-8")
        print(f"  OK:  {path.name} <- {bare}")
    return True


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files, aliases, _ = collect_all()
    _, _, _, missing = build_graph(files, aliases)

    print(f"发现 {len(missing)} 个缺 bare-name alias 的词条")
    bare_to_path = {bare: p for bare, p in files.items()}
    fixed = 0
    for bare in missing:
        p = bare_to_path.get(bare)
        if not p:
            print(f"  WARN: 找不到 {bare} 对应文件")
            continue
        if process(p, bare, args.dry_run):
            fixed += 1
    print(f"完成：{fixed}/{len(missing)} ({'dry-run' if args.dry_run else 'written'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
