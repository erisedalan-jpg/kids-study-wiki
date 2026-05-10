"""学科 → 白名单 JSON。

扫描 <repo>/<subject>/*.md 的 frontmatter `aliases`，提取所有
bare-name + alias，输出 _<subject>_lexicon.json。

输出 schema:
    {
      "<term>": {"bare": "<bare-name>", "seq": 265 | null},
      ...
    }

用法:
    python 00-元/scripts/build_subject_lexicon.py --subject 数学
    # 写出 00-元/scripts/_数学_lexicon.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, bare_name, iter_entries, setup_utf8  # noqa: E402
from analyze_links import parse_aliases  # noqa: E402

PREFIX_NUM_RE = re.compile(r"^(\d{2,4})-")
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _seq_of(path: Path) -> int | None:
    m = PREFIX_NUM_RE.match(path.name)
    return int(m.group(1)) if m else None


def build_lexicon(subject_dir: Path) -> dict[str, dict]:
    """扫描目录，返回 term → {bare, seq} 映射。"""
    lex: dict[str, dict] = {}
    for p in iter_entries(subject_dir):
        bare = bare_name(p)
        seq = _seq_of(p)
        text = p.read_text(encoding="utf-8", errors="replace")
        m = FM_RE.match(text)
        aliases = parse_aliases(m.group(1)) if m else []
        # bare 必入
        lex.setdefault(bare, {"bare": bare, "seq": seq})
        for a in aliases:
            lex.setdefault(a, {"bare": bare, "seq": seq})
    return lex


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True, help="学科名（如 数学）")
    ap.add_argument("--out", help="输出路径（默认 00-元/scripts/_<subject>_lexicon.json）")
    args = ap.parse_args()

    subject_dir = REPO_ROOT / args.subject
    if not subject_dir.is_dir():
        sys.exit(f"ERROR: 找不到学科目录 {subject_dir}")

    lex = build_lexicon(subject_dir)
    out = Path(args.out) if args.out else REPO_ROOT / "00-元" / "scripts" / f"_{args.subject}_lexicon.json"
    out.write_text(json.dumps(lex, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: 写出 {out}（{len(lex)} 个 term，覆盖学科={args.subject}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
