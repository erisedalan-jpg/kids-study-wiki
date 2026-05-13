"""真题索引 + 反链回填（v2 Step 5）。

输出 4 份索引到 索引/真题/:
  - <省份><学科>-高频考点.md
  - <省份><学科>-题型×考点交叉表.md
  - <省份><学科>-缺口词条清单.md
  - <省份><学科>-试卷地图.md

同时把"该考点命中的真题题号列表"作为反链段追加到 学科/<考点>.md 末尾。
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, bare_name, iter_entries, read_frontmatter, setup_utf8  # noqa: E402


BACKLINK_START = "<!-- exam-backlinks-start -->"
BACKLINK_END = "<!-- exam-backlinks-end -->"
NATURAL_QTYPE_ORDER = ["选择", "填空", "解答"]


def parse_atom_fm(text: str) -> dict[str, Any]:
    """解析真题词条 frontmatter（含 list 字段如 考点）。"""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm: dict[str, Any] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        # list 字段
        if v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            fm[k] = [t.strip() for t in inner.split(",") if t.strip()]
        else:
            fm[k] = v
    return fm


def collect_atoms(province: str, subject: str) -> list[dict[str, Any]]:
    """扫真题/<province>-<subject>/ 下所有 .md。"""
    exam_dir = REPO_ROOT / "真题" / f"{province}-{subject}"
    if not exam_dir.is_dir():
        return []
    atoms: list[dict] = []
    for p in sorted(exam_dir.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"[skip] 读取失败 {p.name}: {e}")
            continue
        fm = parse_atom_fm(text)
        if fm:
            fm["_path"] = p
            fm["_bare"] = p.stem
            atoms.append(fm)
    return atoms


def build_freq_table(atoms: list[dict]) -> Counter:
    counter: Counter = Counter()
    for a in atoms:
        for tag in a.get("考点", []):
            counter[tag] += 1
    return counter


def build_qtype_cross(atoms: list[dict]) -> dict[str, Counter]:
    """题型 → 考点 频次。"""
    cross: dict[str, Counter] = defaultdict(Counter)
    for a in atoms:
        qtype = a.get("题型", "未知")
        for tag in a.get("考点", []):
            cross[qtype][tag] += 1
    return cross


def build_gap_list(atoms: list[dict], existing_concepts: set[str]) -> Counter:
    """缺口：真题命中但 学科目录 无对应词条。"""
    gaps: Counter = Counter()
    for a in atoms:
        for tag in a.get("考点", []):
            if tag not in existing_concepts:
                gaps[tag] += 1
    return gaps


def build_paper_map(atoms: list[dict]) -> dict[str, dict]:
    """试卷地图: (年份, 卷别, 文理) → 题数 + 题型分布。"""
    pmap: dict[tuple, dict] = defaultdict(lambda: {"total": 0, "by_qtype": Counter()})
    for a in atoms:
        key = (a.get("年份"), a.get("卷别"), a.get("文理"))
        pmap[key]["total"] += 1
        pmap[key]["by_qtype"][a.get("题型", "未知")] += 1
    return pmap


def write_freq_index(freq: Counter, out_path: Path, label: str) -> None:
    lines = [f"# {label} · 高频考点（按出现次数）\n"]
    lines.append("| 排名 | 考点 | 出现 |")
    lines.append("|---:|---|---:|")
    for i, (tag, cnt) in enumerate(freq.most_common(50), 1):
        lines.append(f"| {i} | [[{tag}]] | {cnt} |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_qtype_cross(cross: dict[str, Counter], out_path: Path, label: str) -> None:
    all_tags = sorted({t for c in cross.values() for t in c})
    lines = [f"# {label} · 题型 × 考点 交叉表\n"]
    qtypes = [q for q in NATURAL_QTYPE_ORDER if q in cross]
    qtypes += sorted(set(cross.keys()) - set(NATURAL_QTYPE_ORDER))
    header = ["考点"] + qtypes + ["合计"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for tag in all_tags:
        row = [f"[[{tag}]]"] + [str(cross[q].get(tag, 0)) for q in qtypes]
        total = sum(cross[q].get(tag, 0) for q in qtypes)
        row.append(str(total))
        lines.append("| " + " | ".join(row) + " |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_gap_list(gaps: Counter, out_path: Path, label: str) -> None:
    lines = [f"# {label} · 缺口词条清单\n"]
    lines.append("真题命中但学科目录未建对应词条的考点：\n")
    lines.append("| 缺口考点 | 命中次数 |")
    lines.append("|---|---:|")
    for tag, cnt in gaps.most_common(50):
        lines.append(f"| {tag} | {cnt} |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_paper_map(pmap: dict, out_path: Path, label: str) -> None:
    lines = [f"# {label} · 试卷地图\n"]
    lines.append("| 年份 | 卷别 | 文理 | 题数 | 选择 | 填空 | 解答 |")
    lines.append("|---|---|---|---:|---:|---:|---:|")

    def _pm_sort_key(item):
        (y, p, g), _ = item
        return (str(y or ""), p or "", g or "")

    for (year, paper, gender), stat in sorted(pmap.items(), key=_pm_sort_key):
        lines.append(
            f"| {year} | {paper} | {gender} | {stat['total']} | "
            f"{stat['by_qtype'].get('选择', 0)} | "
            f"{stat['by_qtype'].get('填空', 0)} | "
            f"{stat['by_qtype'].get('解答', 0)} |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def backfill_backlinks(atoms: list[dict], subject: str) -> int:
    """把"该考点命中的真题题号"作为反链段追加到 学科/<考点>.md 末尾。"""
    # tag → list[atom_bare_name]
    tag_to_atoms: dict[str, list[str]] = defaultdict(list)
    for a in atoms:
        for tag in a.get("考点", []):
            tag_to_atoms[tag].append(a["_bare"])

    # 找 学科/<tag>.md（用 bare_name 匹配）
    subject_dir = REPO_ROOT / subject
    if not subject_dir.is_dir():
        return 0
    bare_to_path: dict[str, Path] = {}
    for p in iter_entries(subject_dir):
        bare_to_path[bare_name(p)] = p

    updated = 0
    section_re = re.compile(
        re.escape(BACKLINK_START) + r".*?" + re.escape(BACKLINK_END),
        re.DOTALL,
    )
    for tag, exam_atoms in tag_to_atoms.items():
        path = bare_to_path.get(tag)
        if not path:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            body = "\n".join([f"- [[{atom}]]" for atom in sorted(set(exam_atoms))])
            section = (
                f"\n{BACKLINK_START}\n## 高考真题命中\n{body}\n{BACKLINK_END}\n"
            )
            if BACKLINK_START in text:
                new_text = section_re.sub(section.strip(), text)
            else:
                new_text = text.rstrip() + "\n" + section
            if new_text != text:
                path.write_text(new_text, encoding="utf-8")
                updated += 1
        except (OSError, UnicodeDecodeError) as e:
            print(f"[skip] 反链回填失败 {path.name}: {e}")
            continue
    return updated


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--province", required=True)
    ap.add_argument("--subject", required=True)
    args = ap.parse_args()

    atoms = collect_atoms(args.province, args.subject)
    if not atoms:
        sys.exit(f"ERROR: 真题/{args.province}-{args.subject}/ 下无词条")

    # 收集 学科目录现有 bare
    subject_dir = REPO_ROOT / args.subject
    existing = (
        {bare_name(p) for p in iter_entries(subject_dir)}
        if subject_dir.is_dir()
        else set()
    )

    freq = build_freq_table(atoms)
    cross = build_qtype_cross(atoms)
    gaps = build_gap_list(atoms, existing)
    pmap = build_paper_map(atoms)

    out_dir = REPO_ROOT / "索引" / "真题"
    out_dir.mkdir(parents=True, exist_ok=True)
    label = f"{args.province}{args.subject}"

    write_freq_index(freq, out_dir / f"{label}-高频考点.md", label)
    write_qtype_cross(cross, out_dir / f"{label}-题型×考点交叉表.md", label)
    write_gap_list(gaps, out_dir / f"{label}-缺口词条清单.md", label)
    write_paper_map(pmap, out_dir / f"{label}-试卷地图.md", label)

    updated = backfill_backlinks(atoms, args.subject)
    print(f"OK: 4 份索引 + 反链回填 {updated} 词条（{args.province}-{args.subject}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
