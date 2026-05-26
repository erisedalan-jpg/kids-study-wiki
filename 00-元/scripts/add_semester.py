# -*- coding: utf-8 -*-
"""按 topics.jsonl 的 semester 注入词条 frontmatter 的 `学期` 字段，供 renumber 排序。

gen_atom_skeleton 不写学期；本工具按裸名匹配补齐。两条安全约定（皆为踩坑后固化）：
  - **空值守卫**（默认）：仅填当前学期为空的条目，绝不覆盖已有学期
    （防止在混学段目录里把已编号的他段条目学期改掉）。--overwrite 可强制覆盖。
  - **块式感知**：新增的 `学期: X` 行插在 `主题` 行之前（顶层键锚点），
    不插在 `学段:` 行后——后者会打散块式 `学段:\n  - 初中` 的 YAML 列表。

用法
----
    python 00-元/scripts/add_semester.py 历史 docs/superpowers/working/topics_高中历史.jsonl
    python 00-元/scripts/add_semester.py 历史 topics.jsonl --overwrite   # 强制覆盖已有学期
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, bare_name, read_frontmatter, setup_utf8  # noqa: E402

XQ_LINE = re.compile(r"(?m)^学期\s*[:：].*$")
TOPIC_LINE = re.compile(r"(?m)^主题\s*[:：]")
STATE_LINE = re.compile(r"(?m)^状态\s*[:：]")


def set_semester(text: str, sem: str) -> str | None:
    """把学期写入 text；返回新文本，若无法定位锚点则返回 None。"""
    if XQ_LINE.search(text):
        return XQ_LINE.sub(f"学期: {sem}", text, count=1)
    # 插在「主题」行前（顶层键，块式/行内 学段 皆安全）；退而求其次插「状态」前
    for anchor in (TOPIC_LINE, STATE_LINE):
        m = anchor.search(text)
        if m:
            return text[: m.start()] + f"学期: {sem}\n" + text[m.start():]
    return None


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("subject", help="学科目录名")
    ap.add_argument("topics", help="topics.jsonl 路径")
    ap.add_argument("--overwrite", action="store_true",
                    help="强制覆盖已有学期（默认仅填空值）")
    args = ap.parse_args()

    sem_of: dict[str, str] = {}
    for line in Path(args.topics).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            sem_of[r["title"]] = r["semester"]

    sub_dir = REPO_ROOT / args.subject
    if not sub_dir.is_dir():
        sys.exit(f"ERROR: 学科目录不存在: {sub_dir}")

    n_set = n_guard = n_nomatch = n_noanchor = 0
    for p in sub_dir.glob("*.md"):
        sem = sem_of.get(bare_name(p))
        if not sem:
            n_nomatch += 1
            continue
        if not args.overwrite and str(read_frontmatter(p).get("学期", "")).strip():
            n_guard += 1  # 已有学期 → 守卫跳过
            continue
        text = p.read_text(encoding="utf-8")
        new = set_semester(text, sem)
        if new is None:
            n_noanchor += 1
            print(f"⚠️  无锚点，跳过: {p.name}")
            continue
        p.write_text(new, encoding="utf-8")
        n_set += 1

    print(f"{args.subject}: 注入 {n_set} / 守卫跳过(已有学期) {n_guard} "
          f"/ 无匹配 {n_nomatch} / 无锚点 {n_noanchor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
