"""修复 renumber 致 stale 号链：`[[旧号-裸名|显示]]` → `[[当前号-裸名|显示]]`。

根因：fix_wikilinks.py LINK_RE 只处理无管线 `[[X]]`，跳过带管线
`[[X|Y]]`；历次 renumber 后真题 md / 索引里的 `[[旧号-裸名|显示]]`
（exam_render/exam_index 产出，恒带管线）成 stale，无人修。

策略（保守、幂等、表格转义保真）：
- 仅当 target 形如 `\\d+-裸名` 且 `target.md` 不在当前文件集，
  且裸名在当前词条恰好唯一映射到 `当前号-裸名.md` 时改写。
- 0 或 多候选 → 不动，记录（避免误指）。
- 无管线 `[[旧号-裸名]]` 同样修，并补显示为裸名（Obsidian 干净显示）。
- `\\|`（表格行转义）与 `|` 原样保持。
默认 dry-run；--apply 落盘。
"""
import re, io, sys, argparse, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUBJ = ["数学", "物理", "化学", "生物", "英语", "语文", "生活与社会"]

# 当前权威：所有 .md stem 集合 + 裸名→stems
cur_stems = set()
bare2stems = collections.defaultdict(list)
for s in SUBJ:
    for p in (REPO / s).glob("*.md"):
        cur_stems.add(p.stem)
        bare2stems[re.sub(r"^\d+-", "", p.stem)].append(p.stem)
for p in (REPO / "真题").rglob("*.md"):
    cur_stems.add(p.stem)

LINK = re.compile(r"\[\[([^\[\]]+?)\]\]")
NUMPFX = re.compile(r"^(\d+)-(.+)$")


def split_inner(inner: str):
    """→ (target, sep, display)；sep ∈ {'\\\\|','|',''}。"""
    m = re.search(r"\\\||\|", inner)
    if not m:
        return inner.strip(), "", ""
    sep = m.group(0)
    i = m.start()
    return inner[:i].strip(), sep, inner[m.end():]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    scopes = sorted((REPO / "真题").rglob("*.md")) + \
        sorted((REPO / "索引" / "真题").glob("*.md"))
    n_files = n_fix = 0
    ambig = collections.Counter()
    gone = collections.Counter()
    per_scope = collections.Counter()

    for f in scopes:
        txt = f.read_text(encoding="utf-8")
        cnt = 0

        def repl(mm: re.Match) -> str:
            nonlocal cnt
            inner = mm.group(1)
            target, sep, disp = split_inner(inner)
            if "#" in target:
                return mm.group(0)
            pm = NUMPFX.match(target)
            if not pm:
                return mm.group(0)
            if target in cur_stems:
                return mm.group(0)               # 号链有效，不动
            bare = pm.group(2)
            cands = bare2stems.get(bare, [])
            if len(cands) != 1:
                (gone if not cands else ambig)[bare] += 1
                return mm.group(0)               # 0/多候选 → 不动
            new_target = cands[0]
            if new_target == target:
                return mm.group(0)
            cnt += 1
            if sep == "":                        # 原无管线 → 补裸名显示
                return f"[[{new_target}\\|{bare}]]" if _in_table(txt, mm.start()) \
                    else f"[[{new_target}|{bare}]]"
            return f"[[{new_target}{sep}{disp}]]"

        new = LINK.sub(repl, txt)
        if cnt:
            n_files += 1
            n_fix += cnt
            per_scope[f.parent.name] += cnt
            if args.apply:
                f.write_text(new, encoding="utf-8", newline="")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] 改写 {n_fix} 处 stale 号链 / {n_files} 文件")
    print("按目录：" + ", ".join(f"{k}={v}" for k, v in sorted(per_scope.items())))
    if gone:
        print(f"裸名无当前词条(不动, top): "
              + ", ".join(f"{k}×{v}" for k, v in gone.most_common(8)))
    if ambig:
        print(f"裸名多候选(不动, top): "
              + ", ".join(f"{k}×{v}" for k, v in ambig.most_common(8)))


def _in_table(txt: str, pos: int) -> bool:
    ls = txt.rfind("\n", 0, pos) + 1
    le = txt.find("\n", pos)
    line = txt[ls: le if le != -1 else len(txt)].strip()
    return line.startswith("|") and line.count("|") >= 2


if __name__ == "__main__":
    main()
