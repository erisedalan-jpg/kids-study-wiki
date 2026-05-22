"""删词条 `## 🧒 给 3-6 岁（共读版）` 整段（小学起不再要学前层）。

删除范围：从 `## 🧒 给 3-6 岁` 标题行 起，到下一个 `## ` 标题 或 `---` 分隔线
（不含）止；保留其后内容。仅删该段，不动 📚 / 🎓。

CLI:
  python 00-元/scripts/strip_kid_layer.py --dir 数学 --grade 小学 --dry
  python 00-元/scripts/strip_kid_layer.py --dir 数学 --grade 小学 --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, iter_entries, read_frontmatter, setup_utf8  # noqa: E402

KID_HEADER = re.compile(r"^##\s*🧒\s*给\s*3-6\s*岁.*$", re.MULTILINE)


def strip_kid_section(text: str) -> tuple[str, bool]:
    """删 🧒3-6 段，返回 (新文本, 是否改动)。"""
    m = KID_HEADER.search(text)
    if not m:
        return text, False
    start = m.start()
    rest = text[m.end():]
    end_rel = len(rest)
    for stop in re.finditer(r"^(##\s|---\s*$)", rest, re.MULTILINE):
        end_rel = stop.start()
        break
    end = m.end() + end_rel
    new = text[:start] + text[end:]
    new = re.sub(r"\n{3,}", "\n\n", new)
    return new, True


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="学科目录，如 数学")
    ap.add_argument("--grade", default="小学", help="仅处理 学段 含此值的词条")
    ap.add_argument("--apply", action="store_true", help="写盘；否则 dry-run")
    args = ap.parse_args()

    base = REPO_ROOT / args.dir
    n_hit = n_write = 0
    for p in iter_entries(base):
        fm = read_frontmatter(p)
        if not fm or args.grade not in str(fm.get("学段", "")):
            continue
        text = p.read_text(encoding="utf-8")
        new, changed = strip_kid_section(text)
        if changed:
            n_hit += 1
            print(f"  🧒 {p.relative_to(REPO_ROOT)}")
            if args.apply:
                p.write_text(new, encoding="utf-8", newline="")
                n_write += 1
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n[{mode}] 含 🧒 段词条 {n_hit} / 写盘 {n_write}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
