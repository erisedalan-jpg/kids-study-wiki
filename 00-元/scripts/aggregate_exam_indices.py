"""真题原子词条 → 4 份索引 + 反链回填到现有词条。

4 份索引:
1. <province><subject>-高频考点.md
2. <province><subject>-题型×考点交叉表.md
3. <province><subject>-缺口词条清单.md
4. <province><subject>-试卷地图.md

反链区段定界:
    <!-- exam-backlinks-start -->
    ## 高考真题命中
    - [[YYYY-...]]
    ...
    <!-- exam-backlinks-end -->

幂等：重跑覆盖整段。

用法:
    python 00-元/scripts/aggregate_exam_indices.py --province 吉林 --subject 数学
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).parent))
from _exam_utils import is_in_tag_pool, load_config  # noqa: E402
from _utils import REPO_ROOT, bare_name, iter_entries, read_frontmatter, setup_utf8  # noqa: E402

BL_START = "<!-- exam-backlinks-start -->"
BL_END = "<!-- exam-backlinks-end -->"
BL_RE = re.compile(re.escape(BL_START) + r".*?" + re.escape(BL_END), re.DOTALL)
PREFIX_NUM_RE = re.compile(r"^(\d{2,4})-")


def _read_atom(p: Path) -> dict[str, Any]:
    fm = read_frontmatter(p)
    text = p.read_text(encoding="utf-8", errors="replace")
    gaps: list[str] = []
    gap_m = re.search(r"##\s*白名单缺口[^\n]*\n((?:- [^\n]+\n)+)", text)
    if gap_m:
        gaps = [line[2:].strip() for line in gap_m.group(1).splitlines() if line.startswith("- ")]
    tags_raw = fm.get("考点", "")
    tags = []
    tm = re.match(r"\[(.*)\]", tags_raw.strip())
    if tm:
        tags = [t.strip() for t in tm.group(1).split(",") if t.strip()]
    return {
        "title": fm.get("title", p.stem),
        "year": int(fm.get("年份", 0) or 0),
        "qtype": fm.get("题型", ""),
        "paper": fm.get("卷别", ""),
        "tags": tags,
        "gaps": gaps,
        "path": p,
    }


def _frequency_index(atoms: list[dict], tag_pool: Callable[[str, int], bool], seq_lookup: Callable[[str], int]) -> str:
    cnt: Counter[str] = Counter()
    years_of: dict[str, set[int]] = defaultdict(set)
    for a in atoms:
        for t in a["tags"]:
            seq = seq_lookup(t) or 0
            if not tag_pool(t, seq):
                continue
            cnt[t] += 1
            years_of[t].add(a["year"])
    lines = ["# 高频考点", "", "| 排名 | 考点 | 命中题数 | 命中年份 |", "|---:|---|---:|---|"]
    for i, (t, n) in enumerate(cnt.most_common(), 1):
        ys = ", ".join(str(y) for y in sorted(years_of[t], reverse=True))
        lines.append(f"| {i} | [[{t}]] | {n} | {ys} |")
    lines.append("")
    return "\n".join(lines)


def _qtype_x_tag_index(atoms: list[dict], tag_pool: Callable[[str, int], bool], seq_lookup: Callable[[str], int]) -> str:
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    for a in atoms:
        for t in a["tags"]:
            seq = seq_lookup(t) or 0
            if not tag_pool(t, seq):
                continue
            matrix[t][a["qtype"]] += 1
    lines = ["# 题型 × 考点交叉表", "", "| 考点 | 选择 | 填空 | 解答 | 总计 |", "|---|---:|---:|---:|---:|"]
    for t in sorted(matrix, key=lambda x: -sum(matrix[x].values())):
        c = matrix[t]
        total = sum(c.values())
        lines.append(f"| [[{t}]] | {c.get('选择',0)} | {c.get('填空',0)} | {c.get('解答',0)} | {total} |")
    lines.append("")
    return "\n".join(lines)


def _gap_index(atoms: list[dict]) -> str:
    cnt: Counter[str] = Counter()
    sources: dict[str, set[str]] = defaultdict(set)
    for a in atoms:
        for g in a["gaps"]:
            cnt[g] += 1
            sources[g].add(a["title"])
    lines = ["# 白名单缺口词条清单", "", "下列概念在真题中出现但现有学科目录无对应词条，建议补建：", "",
             "| 概念 | 出现题数 | 来源 |", "|---|---:|---|"]
    for t, n in cnt.most_common():
        srcs = ", ".join(f"[[{s}]]" for s in sorted(sources[t]))
        lines.append(f"| {t} | {n} | {srcs} |")
    lines.append("")
    return "\n".join(lines)


def _paper_map_index(atoms: list[dict]) -> str:
    by_paper: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for a in atoms:
        by_paper[(a["year"], a["paper"])].append(a)
    lines = ["# 试卷地图", "", "| 年份 | 卷别 | 题数 | 选择 | 填空 | 解答 |", "|---:|---|---:|---:|---:|---:|"]
    for (year, paper) in sorted(by_paper.keys()):
        atoms_p = by_paper[(year, paper)]
        c = Counter(a["qtype"] for a in atoms_p)
        lines.append(f"| {year} | {paper} | {len(atoms_p)} | {c.get('选择',0)} | {c.get('填空',0)} | {c.get('解答',0)} |")
    lines.append("")
    return "\n".join(lines)


def _write_backlinks(atoms: list[dict], subject: str, subject_root: Path, tag_pool, seq_lookup):
    """在每个被命中且 in pool 的现有词条末尾维护反链区段。

    subject_root 通常传仓库根；函数扫 <subject_root>/<subject>/*.md。
    """
    by_tag: dict[str, list[dict]] = defaultdict(list)
    for a in atoms:
        for t in a["tags"]:
            seq = seq_lookup(t) or 0
            if not tag_pool(t, seq):
                continue
            by_tag[t].append(a)

    name_to_path: dict[str, Path] = {}
    target_dir = subject_root / subject
    if target_dir.is_dir():
        for p in iter_entries(target_dir):
            name_to_path[bare_name(p)] = p

    for tag, hits in by_tag.items():
        path = name_to_path.get(tag)
        if not path:
            continue
        hits_sorted = sorted(hits, key=lambda a: -a["year"])[:5]
        section = "\n".join([
            BL_START,
            "## 高考真题命中",
            *(f"- [[{a['title']}]]" for a in hits_sorted),
            BL_END,
        ])
        text = path.read_text(encoding="utf-8")
        if BL_RE.search(text):
            new = BL_RE.sub(section, text)
        else:
            sep = "\n\n" if not text.endswith("\n") else "\n"
            new = text + sep + section + "\n"
        if new != text:
            path.write_text(new, encoding="utf-8")


def aggregate(*, province: str, subject: str,
              atom_root: Path, indices_root: Path, subject_root: Path,
              tag_pool: Callable[[str, int], bool],
              seq_lookup: Callable[[str], int]):
    atom_dir = atom_root / f"{province}-{subject}"
    atoms = [_read_atom(p) for p in atom_dir.glob("*.md")]
    indices_root.mkdir(parents=True, exist_ok=True)
    (indices_root / f"{province}{subject}-高频考点.md").write_text(_frequency_index(atoms, tag_pool, seq_lookup), encoding="utf-8")
    (indices_root / f"{province}{subject}-题型×考点交叉表.md").write_text(_qtype_x_tag_index(atoms, tag_pool, seq_lookup), encoding="utf-8")
    (indices_root / f"{province}{subject}-缺口词条清单.md").write_text(_gap_index(atoms), encoding="utf-8")
    (indices_root / f"{province}{subject}-试卷地图.md").write_text(_paper_map_index(atoms), encoding="utf-8")
    _write_backlinks(atoms, subject, subject_root, tag_pool, seq_lookup)


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--province", required=True)
    ap.add_argument("--subject", required=True)
    args = ap.parse_args()

    cfg = load_config()
    lex_path = REPO_ROOT / "00-元" / "scripts" / f"_{args.subject}_lexicon.json"
    lex = json.loads(lex_path.read_text(encoding="utf-8")) if lex_path.exists() else {}

    def tag_pool(t: str, seq: int) -> bool:
        return is_in_tag_pool(t, seq, args.subject, cfg)

    def seq_lookup(t: str) -> int:
        meta = lex.get(t)
        return (meta or {}).get("seq") or 0

    aggregate(
        province=args.province, subject=args.subject,
        atom_root=REPO_ROOT / "真题",
        indices_root=REPO_ROOT / "索引" / "真题",
        subject_root=REPO_ROOT,
        tag_pool=tag_pool, seq_lookup=seq_lookup,
    )
    print(f"OK: 4 份索引 + 反链回填完成（{args.province}-{args.subject}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
