"""学习路径知识点 vs 现有词条 覆盖 diff。

期望知识点 = 路径文档内 [[链接目标]]（裸名）∪「重点知识点全单」加粗术语。
经 alias-aware 解析（复用 analyze_links.collect_all）映射到现有词条；
未命中 = GAP。

CLI:
  python 00-元/scripts/coverage_matrix.py --paths 00-元/学习路径/小学/数学 --dir 数学
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402

LINK_RE = re.compile(r"\[\[([^\[\]|#]+?)(?:\|[^\]]*)?\]\]")
BOLD_RE = re.compile(r"\*\*([^*]+?)\*\*")
SECTION_RE = re.compile(r"##\s*重点知识点全单(.*?)(?:\n##\s|\Z)", re.DOTALL)


def extract_concepts(doc: str) -> list[str]:
    """返回去重、保序的期望知识点裸名清单。"""
    out: list[str] = []
    seen: set[str] = set()

    def add(name: str):
        n = re.sub(r"^\d{2,4}-", "", name.strip())
        if n and n not in seen:
            seen.add(n)
            out.append(n)

    for m in LINK_RE.finditer(doc):
        tgt = m.group(1).strip()
        if "/" in tgt:
            continue
        add(tgt)
    sec = SECTION_RE.search(doc)
    if sec:
        for bm in BOLD_RE.finditer(sec.group(1)):
            add(bm.group(1))
    return out


def classify_concept(name: str, targets: dict[str, str]) -> tuple[str, str]:
    """name → ('covered', stem) | ('GAP', '')。targets: bare/alias -> stem。"""
    stem = targets.get(name)
    return ("covered", stem) if stem else ("GAP", "")


def _build_targets() -> dict[str, str]:
    """裸名/alias -> 词条 stem（复用 analyze_links）。"""
    import analyze_links as al
    files, aliases, _ = al.collect_all()
    targets: dict[str, str] = {}
    for bare in files:
        targets[bare] = bare
    for alias, bare in aliases.items():
        targets.setdefault(alias, bare)
    return targets


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", required=True, help="学习路径目录")
    ap.add_argument("--dir", required=True, help="学科目录（仅用于报告标题）")
    args = ap.parse_args()

    targets = _build_targets()
    paths_dir = REPO_ROOT / args.paths
    rows: list[tuple[str, str, str, str]] = []
    gap_n = cov_n = 0
    for p in sorted(paths_dir.glob("*.md")):
        doc = p.read_text(encoding="utf-8")
        for concept in extract_concepts(doc):
            status, stem = classify_concept(concept, targets)
            rows.append((p.stem, concept, status, stem))
            if status == "GAP":
                gap_n += 1
            else:
                cov_n += 1

    print(f"覆盖矩阵 [{args.dir}]：已覆盖 {cov_n} / 缺口 {gap_n}\n")
    print("== 缺口清单（GAP）==")
    for ce, concept, status, _ in rows:
        if status == "GAP":
            print(f"  [{ce}] {concept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
