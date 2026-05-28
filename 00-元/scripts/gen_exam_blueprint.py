"""吉林数学高考题位考点速查 — 打印优化单 HTML 生成器。

按卷型三段（08-22 旧/2023 过渡/24+ 最新）× 题位 (题型,题号) 聚合真题考点频次，
经归一表合并同义后按频次排，渲染 A4 打印 CSS 的单 HTML。

P1：只含考点频次（无公式/方法/易错速查库，那是 P2）。

CLI（--subject 默认 数学，可选 物理/化学/生物）:
  python 00-元/scripts/gen_exam_blueprint.py                          # 数学 dry-run
  python 00-元/scripts/gen_exam_blueprint.py --dump-考点               # 导去重考点+频次
  python 00-元/scripts/gen_exam_blueprint.py --apply                  # 写 数学题位速查.html
  python 00-元/scripts/gen_exam_blueprint.py --subject 物理 --apply   # 写 物理题位速查.html
"""
from __future__ import annotations

import argparse
import collections
import html
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, read_frontmatter, setup_utf8  # noqa: E402

EXAM_DIR = REPO_ROOT / "真题" / "吉林-数学"
OUT_HTML = REPO_ROOT / "docs" / "student" / "数学题位速查.html"
NORMALIZE_YAML = Path(__file__).parent / "normalize_考点_数学.yaml"
GROUP_YAML = Path(__file__).parent / "group_考点_数学.yaml"
OTHER = "其他"


def paths_for(subject: str) -> tuple[Path, Path, Path, Path]:
    """按学科解析 (真题目录, 归一表, 分组表, 输出HTML)。
    归一表优先 normalize_考点_<科>.yaml（数学），缺则用 canonical_考点_<科>.yaml
    （物化生——真题已迁移为 canonical，再套等幂）。"""
    here = Path(__file__).parent
    exam_dir = REPO_ROOT / "真题" / f"吉林-{subject}"
    norm = here / f"normalize_考点_{subject}.yaml"
    if not norm.exists():
        norm = here / f"canonical_考点_{subject}.yaml"
    group = here / f"group_考点_{subject}.yaml"
    out = REPO_ROOT / "docs" / "student" / f"{subject}题位速查.html"
    return exam_dir, norm, group, out

ERA_ORDER = ["旧结构(08-22)", "过渡(2023)", "最新(24+)"]
TYPE_ORDER = {"选择": 0, "填空": 1, "解答": 2}
DIFF_RANK = {"易": 0, "中": 1, "难": 2}


def parse_kaodian(v: str) -> list[str]:
    v = (v or "").strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].replace("，", ",").replace("、", ",")
        return [x.strip() for x in inner.split(",") if x.strip()]
    return [v] if v else []


def era_of(year: int) -> str | None:
    if 2008 <= year <= 2022:
        return "旧结构(08-22)"
    if year == 2023:
        return "过渡(2023)"
    if year >= 2024:
        return "最新(24+)"
    return None


def difficulty_mode(diffs: list[str]) -> str:
    if not diffs:
        return "?"
    c = collections.Counter(diffs)
    top = max(c.values())
    cands = [d for d, n in c.items() if n == top]
    return max(cands, key=lambda d: DIFF_RANK.get(d, -1))


def canon(name: str, normalize: dict[str, str]) -> str:
    return normalize.get(name, name)


def aggregate(rows: list[dict], normalize: dict[str, str]) -> dict:
    """rows = 真题 frontmatter 字典列表 → {段: {(题型,题号): {n, 难度倾向, 考点:[(名,次)...]}}}"""
    bucket: dict = {}
    diffs: dict = {}
    counts: dict = {}
    for r in rows:
        try:
            year = int(r.get("年份") or 0)
        except ValueError:
            continue
        era = era_of(year)
        if era is None:
            continue
        # 旧结构去文科卷（数学保留理科；物化生为「不分」理综，不受影响）
        if era == "旧结构(08-22)" and r.get("文理") == "文":
            continue
        try:
            qno = int(r.get("题号") or 0)
        except ValueError:
            continue
        slot = (r.get("题型", ""), qno)
        key = (era, slot)
        counts[key] = counts.get(key, 0) + 1
        diffs.setdefault(key, []).append(r.get("难度", ""))
        kc = bucket.setdefault(key, collections.Counter())
        for kp in parse_kaodian(r.get("考点", "")):
            kc[canon(kp, normalize)] += 1
    out: dict = {}
    for (era, slot), kc in bucket.items():
        out.setdefault(era, {})[slot] = {
            "n": counts[(era, slot)],
            "难度倾向": difficulty_mode(diffs[(era, slot)]),
            "考点": kc.most_common(),
        }
    return out


def build_tree(kp_freq: list[tuple[str, int]],
               group: dict[str, str]) -> list[tuple[str, int, list[tuple[str, int]]]]:
    """考点频次列表 + 分组表 → [(父主题, 父频, [(子考点,子频)...])...]。
    父按频降序，但 OTHER 恒排末；子在父下沿用输入顺序（输入已按频降序）。"""
    parents: dict[str, list[tuple[str, int]]] = {}
    for name, freq in kp_freq:
        p = group.get(name, OTHER)
        parents.setdefault(p, []).append((name, freq))
    tree = []
    for p, kids in parents.items():
        tree.append((p, sum(f for _, f in kids), kids))
    tree.sort(key=lambda t: (t[0] == OTHER, -t[1]))
    return tree


def tree_to_lines(tree: list[tuple[str, int, list[tuple[str, int]]]]) -> list[str]:
    """树 → 带 ├─└─│ 连接线的文本行；首个非 OTHER 父类加 ★。"""
    lines: list[str] = []
    n = len(tree)
    for i, (parent, pfreq, kids) in enumerate(tree):
        p_last = (i == n - 1)
        p_branch = "└─" if p_last else "├─"
        star = " ★" if i == 0 and parent != OTHER else ""
        lines.append(f"{p_branch} {parent} ({pfreq}){star}")
        cn = len(kids)
        indent = "   " if p_last else "│  "
        for j, (child, cfreq) in enumerate(kids):
            c_branch = "└─" if j == cn - 1 else "├─"
            lines.append(f"{indent}{c_branch} {child} ×{cfreq}")
    return lines


def read_rows(exam_dir: Path = EXAM_DIR) -> list[dict]:
    return [read_frontmatter(p) for p in sorted(exam_dir.glob("*.md"))]


def load_normalize(path: Path = NORMALIZE_YAML) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {str(k): str(v) for k, v in data.items()}


def load_group(path: Path = GROUP_YAML) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {str(k): str(v) for k, v in data.items()}


def attach_trees(agg: dict, group: dict[str, str]) -> None:
    """给每题位就地加 '树' 字段（build_tree(考点, group)）。"""
    for slots in agg.values():
        for d in slots.values():
            d["树"] = build_tree(d["考点"], group)


def dump_kaodian(rows: list[dict]) -> list[tuple[str, int]]:
    c: collections.Counter = collections.Counter()
    for r in rows:
        for kp in parse_kaodian(r.get("考点", "")):
            c[kp] += 1
    return c.most_common()


PRINT_CSS = """
<style>
  body { font-family: -apple-system, "Microsoft YaHei", sans-serif; color:#222; margin:0; }
  .bp-wrap { max-width: 980px; margin: 0 auto; padding: 16px; }
  h1 { font-size: 1.5em; margin: 8px 0; }
  .era { margin-top: 18px; }
  .era > h2 { border-bottom: 2px solid #333; padding-bottom: 4px; }
  .slot { border: 1px solid #ccc; border-radius: 6px; padding: 8px 10px; margin: 8px 0;
          break-inside: avoid; page-break-inside: avoid; }
  .slot-h { font-weight: bold; margin-bottom: 4px; }
  .slot-meta { color:#666; font-weight: normal; font-size: 0.85em; }
  .kp { display: inline-block; margin: 2px 8px 2px 0; padding: 1px 6px;
        background: #f0f0f0; border-radius: 4px; font-size: 0.92em; }
  .kp b { color:#000; }
  .bp-tree { font-family: "Cascadia Mono", Consolas, "Microsoft YaHei", monospace;
    white-space: pre; font-size: 0.9em; line-height: 1.55; margin: 4px 0 0; }
  .bp-tree .tline { margin: 0; }
  .thin { color:#a00; font-size: 0.85em; }
  .legend { color:#666; font-size: 0.85em; margin: 6px 0 14px; }
  @media print {
    .bp-wrap { max-width: none; padding: 0; }
    .era { page-break-before: always; }
    .era:first-of-type { page-break-before: avoid; }
    .slot { break-inside: avoid; page-break-inside: avoid; }
    a { color:#000; text-decoration: none; }
  }
</style>
"""

KATEX_HEAD = """
<link rel="stylesheet" href="./vendor/katex/katex.min.css">
<script defer src="./vendor/katex/katex.min.js"></script>
<script defer src="./vendor/katex/contrib/mhchem.min.js"></script>
<script defer src="./vendor/katex/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body,{delimiters:[
    {left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],
    throwOnError:false});"></script>
"""


def render_html(agg: dict, subject: str = "数学") -> str:
    parts = []
    for era in ERA_ORDER:
        slots = agg.get(era, {})
        if not slots:
            continue
        rows_html = []
        for slot in sorted(slots, key=lambda s: (TYPE_ORDER.get(s[0], 9), s[1])):
            d = slots[slot]
            tree_lines = tree_to_lines(d["树"])
            kp_html = '<div class="bp-tree">' + "".join(
                f'<div class="tline">{html.escape(line)}</div>' for line in tree_lines
            ) + '</div>'
            thin = ('<span class="thin">（样本仅 %d，规律参考）</span>' % d["n"]) \
                if d["n"] <= 2 else ""
            rows_html.append(
                f'<div class="slot"><div class="slot-h">{html.escape(slot[0])}{slot[1]}'
                f'<span class="slot-meta"> · 样本 n={d["n"]} · 难度{html.escape(d["难度倾向"])}</span>'
                f'{thin}</div>{kp_html}</div>'
            )
        parts.append(
            f'<div class="era"><h2>{html.escape(era)}</h2>' + "".join(rows_html) + "</div>"
        )
    body = "".join(parts)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}题位考点速查（吉林）</title>
<link rel="stylesheet" href="./vendor/style.css">
{PRINT_CSS}{KATEX_HEAD}</head>
<body><div class="bp-wrap">
<h1>{subject}题位考点速查 · 吉林高考</h1>
<p class="legend">按卷型三段 × 逐题位，考点按真题频次降序。旧结构按理科卷统计；
样本 ≤2 标「规律参考」。Ctrl+P 可存 A4 PDF。</p>
{body}
</div></body></html>"""


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="写盘 HTML")
    ap.add_argument("--dump-考点", dest="dump", action="store_true",
                    help="导去重考点+频次（喂归一表）")
    ap.add_argument("--subject", default="数学",
                    help="学科（数学/物理/化学/生物），默认 数学")
    args = ap.parse_args()

    exam_dir, norm_yaml, group_yaml, out_html = paths_for(args.subject)
    rows = read_rows(exam_dir)
    print(f"读取 {len(rows)} 题（{exam_dir.name}）", flush=True)

    if args.dump:
        for name, n in dump_kaodian(rows):
            print(f"{n:>4}  {name}")
        return 0

    normalize = load_normalize(norm_yaml)
    agg = aggregate(rows, normalize)
    group = load_group(group_yaml)
    attach_trees(agg, group)
    for era in ERA_ORDER:
        slots = agg.get(era, {})
        print(f"\n=== {era} ===（{len(slots)} 题位）")
        for slot in sorted(slots, key=lambda s: (TYPE_ORDER.get(s[0], 9), s[1])):
            d = slots[slot]
            roots = "  ".join(f"{p}({pf})" for p, pf, _ in d["树"][:4])
            print(f"  {slot[0]}{slot[1]:>2} (n={d['n']}, {d['难度倾向']}): {roots}")

    if not args.apply:
        print("\n(dry-run) 加 --apply 写 HTML。")
        return 0

    html_out = render_html(agg, args.subject)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html_out, encoding="utf-8", newline="")
    print(f"\n[APPLY] → {out_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
