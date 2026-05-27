"""复习 md 体检门：缺区块/缺字段/代码围栏/LaTeX 定界符/wikilinks。

CLI: python validate_review.py --subject 数学   # 扫 复习/<科>/，非0退出码=有故障
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402

_REQ_FIELDS = ("考点:", "父主题:", "学科:", "状态:")
_REQ_BLOCKS = ("## 考点定位", "## 知识精要", "## 解题方法与套路",
               "## 高频易错", "## 代表题精讲", "## 全部真题清单", "## 关联")
_LATEX = re.compile(r"\\\(|\\\)|(?<!\\)\\\[(?!\d)|(?<!\\)\\\]")


def check(md: str) -> list[str]:
    errs: list[str] = []
    fm = md.split("---", 2)
    head = fm[1] if len(fm) >= 3 else ""
    for f in _REQ_FIELDS:
        if f not in head:
            errs.append(f"缺 frontmatter 字段：{f}")
    for b in _REQ_BLOCKS:
        if b not in md:
            errs.append(f"缺区块：{b}")
    if "```" in md:
        errs.append("含代码围栏 ```")
    if _LATEX.search(md):
        errs.append("含 LaTeX 定界符 \\(\\)\\[\\]（须改 $...$）")
    return errs


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="数学")
    args = ap.parse_args()
    d = REPO_ROOT / "复习" / args.subject
    bad = 0
    for p in sorted(d.glob("*.md")):
        errs = check(p.read_text(encoding="utf-8"))
        if errs:
            bad += 1
            print(f"✗ {p.name}")
            for e in errs:
                print(f"    - {e}")
    print(f"体检：{bad} 个文件有故障（复习/{args.subject}）")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
