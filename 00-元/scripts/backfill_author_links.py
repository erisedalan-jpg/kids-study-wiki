"""
作品 → 作家反链回填工具。

对所有 `*-{作家}.md` 形式的作品词条，若其"相关词条"段落未引用
`[[古代作家-{作家}]]`，则自动追加。

支持两种"相关词条"格式：
1. 单行 dot-separated: `[[A]] · [[B]] · [[C]]`
2. 多行 list:
       - [[A]]
       - [[B]]

用法
----
    python 00-元/scripts/backfill_author_links.py            # 自动找出并回填
    python 00-元/scripts/backfill_author_links.py --dry-run  # 仅预览
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from analyze_links import collect_all  # noqa: E402
from _utils import setup_utf8  # noqa: E402

WORK_RE = re.compile(r"-([一-鿿]{1,4})$")
RELATIONS_HEADER_RE = re.compile(r"^(##\s*🔗?\s*相关词条\s*)$", re.MULTILINE)


def find_relations_block(text: str) -> tuple[int, int, str] | None:
    """返回 (start, end, content) 表示相关词条段落的边界与正文。

    end 指向下一个 `---` 或下一个 `##` 之前；若末尾就是文件末则到末尾。
    """
    m = RELATIONS_HEADER_RE.search(text)
    if not m:
        return None
    start = m.end()
    # 找下一个分隔（##、---、文件末）
    rest = text[start:]
    next_section = re.search(r"\n##\s|\n---\s*\n|\Z", rest)
    if next_section:
        end = start + next_section.start()
    else:
        end = len(text)
    return start, end, text[start:end]


def append_link(block: str, link: str) -> str:
    """根据现有格式（dot-separated / list）追加新链接。"""
    # 尝试找到非空内容
    lines = block.split("\n")
    # 找包含 [[ 的最末一行
    last_link_line_idx = -1
    for i, line in enumerate(lines):
        if "[[" in line:
            last_link_line_idx = i

    if last_link_line_idx < 0:
        # 无既有链接，直接放第一行
        return f"\n\n{link}\n"

    line = lines[last_link_line_idx]
    stripped = line.lstrip()
    if stripped.startswith("- ") or stripped.startswith("* "):
        # 列表格式
        indent = line[: len(line) - len(stripped)]
        prefix = stripped[:2]
        new_line = f"{indent}{prefix}{link}"
        lines.insert(last_link_line_idx + 1, new_line)
    else:
        # 单行 dot-separated 格式
        # 在该行末尾追加 ` · {link}`
        if line.rstrip().endswith("·"):
            lines[last_link_line_idx] = line.rstrip() + f" {link}"
        else:
            lines[last_link_line_idx] = line.rstrip() + f" · {link}"
    return "\n".join(lines)


def process(p: Path, author: str, dry_run: bool) -> bool:
    text = p.read_text(encoding="utf-8")
    target_link = f"[[古代作家-{author}]]"
    target_alias = f"[[{author}]]"
    if target_link in text or target_alias in text:
        return False
    block_info = find_relations_block(text)
    if not block_info:
        # 无相关词条段，跳过（不强行创建）
        print(f"  WARN: {p.name} 缺少'相关词条'段，跳过")
        return False
    start, end, block = block_info
    new_block = append_link(block, target_link)
    new_text = text[:start] + new_block + text[end:]
    if new_text == text:
        return False
    if dry_run:
        print(f"  DRY  {p.name} <- {target_link}")
    else:
        p.write_text(new_text, encoding="utf-8")
        print(f"  OK   {p.name} <- {target_link}")
    return True


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files, _, _ = collect_all()
    existing_authors = {
        k.replace("古代作家-", "")
        for k in files
        if k.startswith("古代作家-")
    }

    targets: list[tuple[Path, str]] = []
    for k, p in files.items():
        if k.startswith(("古代作家-", "近代作家-", "现代作家-")):
            continue
        m = WORK_RE.search(k)
        if not m:
            continue
        author = m.group(1)
        if author not in existing_authors:
            continue
        targets.append((p, author))

    print(f"扫描候选 {len(targets)} 个作品词条")
    fixed = 0
    for p, author in targets:
        if process(p, author, args.dry_run):
            fixed += 1
    print(f"完成：{fixed}/{len(targets)} ({'dry-run' if args.dry_run else 'written'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
