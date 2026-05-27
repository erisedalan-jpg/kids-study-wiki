"""复习 md 格式修复：LaTeX 反斜杠定界符 → Obsidian $ 定界符 + 删代码围栏。幂等。

CLI:
  python fix_review_format.py --subject 数学            # dry-run
  python fix_review_format.py --subject 数学 --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402

# 代码围栏整行匹配：``` 或 ```lang（保留围栏内内容，仅删标记行）
_FENCE = re.compile(r"^\s*```[\w-]*\s*$")


def fix_text(md: str) -> str:
    """修复复习 md 的格式问题。幂等。

    变换规则：
    1. \\( → $   \\) → $        （行内数学定界符）
    2. \\[ → $$  \\] → $$       （块级数学定界符）
       例外：\\[ 后紧跟数字时视为 LaTeX 行距命令（如 \\[3pt]、\\[2ex]），不转换。
       实现：re.sub 仅在 \\[ 后方 **不是** 数字时替换；\\] 全量替换。
    3. 删除整行代码围栏标记（如 ``` 或 ```python），保留围栏内实际内容。
    """
    # 行内定界符
    md = md.replace(r"\(", "$").replace(r"\)", "$")
    # 块级定界符：\[ 后紧跟数字（行距命令）不转；其余 \[ → $$
    md = re.sub(r"\\\[(?!\d)", "$$", md)
    # \] → $$（假设所有裸 \] 都是关闭的块级定界符；行距命令的 ] 已被 \[3pt] 整体保留，
    # 其 ] 仍保留原文，此处全量替换不影响它们，因为行距命令形如 \[3pt]，其 ] 是普通字符）
    md = md.replace(r"\]", "$$")
    # 删整行代码围栏标记（保留围栏内内容）
    md = "\n".join(ln for ln in md.split("\n") if not _FENCE.match(ln))
    return md


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description="修复复习 md 的 LaTeX 定界符 + 代码围栏")
    ap.add_argument("--subject", default="数学", help="学科目录名，默认数学")
    ap.add_argument("--apply", action="store_true", help="实际写盘（默认 dry-run）")
    args = ap.parse_args()
    d = REPO_ROOT / "复习" / args.subject
    if not d.is_dir():
        print(f"[ERROR] 目录不存在：{d}", file=sys.stderr)
        return 1
    n = 0
    for p in sorted(d.glob("*.md")):
        t = p.read_text(encoding="utf-8")
        fixed = fix_text(t)
        if fixed != t:
            n += 1
            if args.apply:
                p.write_text(fixed, encoding="utf-8")
    print(f"{'[APPLY]' if args.apply else '[dry-run]'} 修复 {n} 文件（复习/{args.subject}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
