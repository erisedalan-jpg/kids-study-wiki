"""吉林数学高考题位考点速查 — 打印优化单 HTML 生成器。

按卷型三段（08-22 旧/2023 过渡/24+ 最新）× 题位 (题型,题号) 聚合真题考点频次，
经归一表合并同义后按频次排，渲染 A4 打印 CSS 的单 HTML。

P1：只含考点频次（无公式/方法/易错速查库，那是 P2）。

CLI:
  python 00-元/scripts/gen_exam_blueprint.py                 # dry-run 打印各段题位统计
  python 00-元/scripts/gen_exam_blueprint.py --dump-考点      # 导去重考点+频次（喂归一表）
  python 00-元/scripts/gen_exam_blueprint.py --apply         # 写 docs/student/数学题位速查.html
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
        if era == "旧结构(08-22)" and r.get("文理") != "理":
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


def read_rows() -> list[dict]:
    return [read_frontmatter(p) for p in sorted(EXAM_DIR.glob("*.md"))]


def load_normalize(path: Path = NORMALIZE_YAML) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {str(k): str(v) for k, v in data.items()}


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
<script defer src="./vendor/katex/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body,{delimiters:[
    {left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],
    throwOnError:false});"></script>
"""


def render_html(agg: dict) -> str:
    parts = []
    for era in ERA_ORDER:
        slots = agg.get(era, {})
        if not slots:
            continue
        rows_html = []
        for slot in sorted(slots, key=lambda s: (TYPE_ORDER.get(s[0], 9), s[1])):
            d = slots[slot]
            kp_html = "".join(
                f'<span class="kp"><b>{html.escape(k)}</b> ×{n}</span>'
                for k, n in d["考点"]
            )
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
<title>数学题位考点速查（吉林）</title>
<link rel="stylesheet" href="./vendor/style.css">
{PRINT_CSS}{KATEX_HEAD}</head>
<body><div class="bp-wrap">
<h1>数学题位考点速查 · 吉林高考</h1>
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
    args = ap.parse_args()

    rows = read_rows()
    print(f"读取 {len(rows)} 题（{EXAM_DIR.name}）", flush=True)

    if args.dump:
        for name, n in dump_kaodian(rows):
            print(f"{n:>4}  {name}")
        return 0

    normalize = load_normalize()
    agg = aggregate(rows, normalize)
    for era in ERA_ORDER:
        slots = agg.get(era, {})
        print(f"\n=== {era} ===（{len(slots)} 题位）")
        for slot in sorted(slots, key=lambda s: (TYPE_ORDER.get(s[0], 9), s[1])):
            d = slots[slot]
            top = "  ".join(f"{k}×{n}" for k, n in d["考点"][:4])
            print(f"  {slot[0]}{slot[1]:>2} (n={d['n']}, {d['难度倾向']}): {top}")

    if not args.apply:
        print("\n(dry-run) 加 --apply 写 HTML。")
        return 0

    html_out = render_html(agg)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html_out, encoding="utf-8", newline="")
    print(f"\n[APPLY] → {OUT_HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
