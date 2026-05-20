"""初始化错题本 / mastery 字段默认值（一次性）。

给所有真题 md 加：
  我的状态: 未做
  首次做: null
  最后做: null
  错次: 0
  模考批次: []
  我的笔记: ""

给所有学科词条 md 加：
  mastery: 未学
  last_review: null
  wrong_count: 0
  review_count: 0

已存在的字段不动（幂等）。CLI：
  python 00-元/scripts/init_review_fields.py --dry-run
  python 00-元/scripts/init_review_fields.py --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import (  # noqa: E402
    REPO_ROOT, SUBJECT_DIRS, iter_entries, iter_exam_dirs, setup_utf8,
)

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

EXAM_DEFAULTS = {
    "我的状态": "未做",
    "首次做": "null",
    "最后做": "null",
    "错次": "0",
    "模考批次": "[]",
    "我的笔记": '""',
}

ATOM_DEFAULTS = {
    "mastery": "未学",
    "last_review": "null",
    "wrong_count": "0",
    "review_count": "0",
}


def upsert_defaults(text: str, defaults: dict[str, str]) -> tuple[str, int]:
    """在 frontmatter 末追加缺失字段；已存在的不动。返回 (新文本, 加几条)。"""
    m = FM_RE.match(text)
    if not m:
        return text, 0
    fm_body = m.group(1)
    existing = set()
    for line in fm_body.splitlines():
        if ":" in line:
            existing.add(line.split(":", 1)[0].strip())
    to_add = [(k, v) for k, v in defaults.items() if k not in existing]
    if not to_add:
        return text, 0
    new_fm = fm_body.rstrip() + "\n" + "\n".join(f"{k}: {v}" for k, v in to_add)
    return text[: m.start(1)] + new_fm + text[m.end(1) :], len(to_add)


def process(paths, defaults, apply: bool, label: str) -> tuple[int, int, int]:
    n_files = n_changed = n_added = 0
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        n_files += 1
        new_text, added = upsert_defaults(text, defaults)
        if added > 0:
            n_changed += 1
            n_added += added
            if apply:
                p.write_text(new_text, encoding="utf-8", newline="")
    print(f"  [{label}] 扫 {n_files} / 改 {n_changed} / 加字段 {n_added}", flush=True)
    return n_files, n_changed, n_added


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] 初始化错题本 / mastery 默认字段", flush=True)

    print("\n真题 md：")
    exam_paths: list[Path] = []
    for sub in iter_exam_dirs():
        exam_paths.extend(sub.glob("*.md"))
    process(exam_paths, EXAM_DEFAULTS, args.apply, "真题")

    print("\n学科词条 md：")
    atom_paths: list[Path] = []
    for s in SUBJECT_DIRS:
        sd = REPO_ROOT / s
        if sd.is_dir():
            atom_paths.extend(iter_entries(sd))
    process(atom_paths, ATOM_DEFAULTS, args.apply, "学科")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
