"""
统计学科词条数 → 输出 markdown 进度块 → 幂等注入 CLAUDE.md。

CLAUDE.md 中需有锚点（HTML 注释）包裹要被替换的内容：

    <!-- AUTO-PROGRESS-START -->
    （此区块由 stats.py 自动维护）
    <!-- AUTO-PROGRESS-END -->

用法
----
    python 00-元/scripts/stats.py                # 打印进度块到 stdout
    python 00-元/scripts/stats.py --write        # 替换 CLAUDE.md 锚点之间内容
    python 00-元/scripts/stats.py --check        # 检查是否需要更新（CI 用）
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, SUBJECT_DIRS, iter_entries, setup_utf8  # noqa: E402

CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
START = "<!-- AUTO-PROGRESS-START -->"
END = "<!-- AUTO-PROGRESS-END -->"


def count_subject(name: str) -> int:
    d = REPO_ROOT / name
    if not d.is_dir():
        return 0
    return sum(1 for _ in iter_entries(d))


def render() -> str:
    rows = []
    for s in SUBJECT_DIRS:
        n = count_subject(s)
        if n > 0:
            rows.append((s, n))
    total = sum(n for _, n in rows)

    lines = [
        START,
        "",
        f"_由 `00-元/scripts/stats.py` 生成，共 {total} 词条 / {len(rows)} 学科。_",
        "",
        "| 学科 | 词条数 |",
        "|---|---:|",
    ]
    for s, n in rows:
        lines.append(f"| {s} | {n} |")
    lines.append(f"| **合计** | **{total}** |")
    lines.append("")
    lines.append(END)
    return "\n".join(lines)


def inject(block: str) -> bool:
    """替换 CLAUDE.md 中两个锚点之间的内容。返回 True 表示发生变化。"""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(START) + r".*?" + re.escape(END),
        re.DOTALL,
    )
    if not pattern.search(text):
        sys.exit(
            f"ERROR: CLAUDE.md 缺少锚点 {START} / {END}。\n"
            "请先在 CLAUDE.md 适当位置加入这对 HTML 注释。"
        )
    new = pattern.sub(block, text)
    if new == text:
        return False
    CLAUDE_MD.write_text(new, encoding="utf-8")
    return True


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="写回 CLAUDE.md")
    ap.add_argument("--check", action="store_true", help="仅检查是否需要更新（不写入）")
    args = ap.parse_args()

    block = render()
    if args.check:
        text = CLAUDE_MD.read_text(encoding="utf-8")
        pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
        m = pattern.search(text)
        if not m or m.group(0) != block:
            print("STALE: CLAUDE.md 进度块需要更新（运行 --write）")
            return 1
        print("OK: 进度块与实际词条数一致")
        return 0

    if args.write:
        changed = inject(block)
        print("UPDATED CLAUDE.md" if changed else "NO CHANGE")
        return 0

    print(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
