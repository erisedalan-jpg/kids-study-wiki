r"""修复 复习/<科>/*.md 数学区里 KaTeX 0.16 不支持的写法（只在 $...$ / $$...$$ 内改，幂等）。

由 katex_lint.js 实测归纳的 5 类机械替换：
1. 间距命令 \, \; \! \: 后紧跟 ^ 或 _ → 插 {}（否则 KaTeX 报 'internal' 组错）
2. \male / \female → \text{♂} / \text{♀}（KaTeX 无此命令）
3. \buildrel{T}\over{B} → \overset{T}{B}（KaTeX 无 \buildrel）
4. \text{..·..} 内中点 · (U+00B7) → 拆成 \text{..}\cdot\text{..}（· 在 text 模式非法）
5. 残余中点 ·（text 外）→ \cdot

少数真·内容损坏（\text{mg/^\circ}、多余 }、截断的 \righta 等）不在此列，需人工。
用法: python 00-元/scripts/fix_katex_compat.py --subject 化学 [--apply]    或 --all
验证: node 00-元/scripts/katex_lint.js <科>   （应 0 失败）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from _utils import REPO_ROOT, setup_utf8  # noqa: E402

SCIENCE = ["数学", "物理", "化学", "生物"]
MIDDOT = "·⋅・‧"
_MID_RE = re.compile(f"[{MIDDOT}]")
_SPACE_SUP = re.compile(r"(\\[,;:!])\s*([\^_])")
_GROUP = r"\{(?:[^{}]|\{[^{}]*\})*\}"
_BUILDREL = re.compile(rf"\\buildrel\s*({_GROUP})\s*\\over\s*({_GROUP})")
_TEXT = re.compile(r"\\text\{([^{}]*)\}")
_MATH = re.compile(r"\$\$.*?\$\$|\$[^\$\n]+?\$", re.DOTALL)


def _fix_text_middot(m: re.Match) -> str:
    inner = m.group(1)
    if not _MID_RE.search(inner):
        return m.group(0)
    return "\\cdot ".join(f"\\text{{{p}}}" for p in _MID_RE.split(inner))


def fix_formula(s: str) -> str:
    """对单个数学公式（含 $ 定界符）做 5 类替换，幂等。"""
    s = _SPACE_SUP.sub(r"\1{}\2", s)
    s = s.replace("\\female", "\\text{♀}").replace("\\male", "\\text{♂}")
    s = _BUILDREL.sub(r"\\overset\1\2", s)
    s = _TEXT.sub(_fix_text_middot, s)
    s = _MID_RE.sub("\\\\cdot ", s)
    return s


def fix_text(md: str) -> str:
    """只替换数学区，正文散文不动。"""
    return _MATH.sub(lambda m: fix_formula(m.group(0)), md)


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description="修复复习材料 KaTeX 不兼容写法")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--subject")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--apply", action="store_true", help="写盘（默认 dry-run）")
    args = ap.parse_args()
    subjects = SCIENCE if args.all else [args.subject]

    total_files = total_changed = 0
    for sub in subjects:
        d = REPO_ROOT / "复习" / sub
        if not d.exists():
            print(f"跳过（无目录）：{sub}")
            continue
        changed = 0
        for p in sorted(d.glob("*.md")):
            src = p.read_text(encoding="utf-8")
            out = fix_text(src)
            if out != src:
                changed += 1
                if args.apply:
                    p.write_text(out, encoding="utf-8")
        total_files += len(list(d.glob("*.md")))
        total_changed += changed
        print(f"[{sub}] 改动文件 {changed}")
    tag = "已写盘" if args.apply else "dry-run（加 --apply 写盘）"
    print(f"合计改动 {total_changed} 文件 · {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
