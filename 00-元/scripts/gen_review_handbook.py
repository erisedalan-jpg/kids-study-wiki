"""每科可打印复习手册 HTML 生成器。

将「题位速查脑图」（顶部）与「考点专题复习」内容（主体）合并为一份
自包含 A4 可打印单页 HTML。

输出路径：docs/student/<科>复习手册.html

CLI:
  python 00-元/scripts/gen_review_handbook.py --subject 数学 --apply
  python 00-元/scripts/gen_review_handbook.py --subject 物理 --apply
  python 00-元/scripts/gen_review_handbook.py --subject 物理 --apply --page-map /tmp/map.json
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

import markdown

sys.path.insert(0, str(Path(__file__).parent))
from _utils import (  # noqa: E402
    REPO_ROOT, mask_math, read_frontmatter, setup_utf8, unmask_math,
)
from gen_exam_blueprint import (  # noqa: E402
    ERA_ORDER, TYPE_ORDER, PRINT_CSS, KATEX_HEAD,
    paths_for, read_rows, load_normalize, load_group,
    aggregate, attach_trees, tree_to_lines,
)
from gen_kaodian_review import _safe_name  # noqa: E402

OUT_DIR = REPO_ROOT / "docs" / "student"
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\[\]#|]+?)(?:#[^|\]]+)?(?:\|([^\]]+))?\]\]")

# Target visible column for dot-leader padding in the tree TOC
_TREE_TOC_COL = 50


def _vis_width(s: str) -> int:
    """Compute visible width of string (CJK chars count as 2)."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


# ---------------------------------------------------------------------------
# Public helper — used in tests
# ---------------------------------------------------------------------------

def anchor_id(kaodian: str) -> str:
    """考点 → HTML id 属性值，用于脑图 href 与正文 section id 的一致锚点。"""
    return f"kp-{_safe_name(kaodian)}"


# ---------------------------------------------------------------------------
# Tree rendering with hyperlinks
# ---------------------------------------------------------------------------

def _tree_lines_linked(
    tree: list[tuple[str, int, list[tuple[str, int]]]],
    has_review: set[str],
    page_map: dict[str, int] | None = None,
) -> list[str]:
    """与 tree_to_lines 相同的树形格式，但子考点带 <a href> 跳转；无复习 md 的保持纯文本。
    若 page_map 给出且考点在其中，则在行末添加点状引导线 + 页码（目录式，填充右侧空白）。
    """
    lines: list[str] = []
    n = len(tree)
    for i, (parent, pfreq, kids) in enumerate(tree):
        p_last = (i == n - 1)
        p_branch = "└─" if p_last else "├─"
        star = " ★" if i == 0 and parent != "其他" else ""
        # 父主题行：纯文本（无跳转目标）
        lines.append(
            f"{p_branch} {html.escape(parent)} ({pfreq}){star}"
        )
        cn = len(kids)
        indent = "   " if p_last else "│  "
        for j, (child, cfreq) in enumerate(kids):
            c_branch = "└─" if j == cn - 1 else "├─"
            if child in has_review:
                aid = anchor_id(child)
                child_html = (
                    f'<a href="#{html.escape(aid)}" class="kp-link">'
                    f"{html.escape(child)}</a>"
                )
            else:
                child_html = html.escape(child)

            # Build the page-ref suffix if available
            if page_map and child in has_review and child in page_map:
                page_num = page_map[child]
                # Visible prefix (plain text, no HTML) for width measurement
                visible_prefix = f"{indent}{c_branch} {child} ×{cfreq}"
                vis_w = _vis_width(visible_prefix)
                n_dots = max(1, _TREE_TOC_COL - vis_w)
                pad_dots = "·" * n_dots
                page_ref = f" p.{page_num}"
                lines.append(
                    f"{indent}{c_branch} {child_html} ×{cfreq}{pad_dots}{page_ref}"
                )
            else:
                lines.append(f"{indent}{c_branch} {child_html} ×{cfreq}")
    return lines


# ---------------------------------------------------------------------------
# Review .md loading
# ---------------------------------------------------------------------------

def _fm_get(fm: dict[str, str], key: str, default: str = "") -> str:
    return (fm.get(key) or default).strip()


def load_zhuanti(subject: str) -> list[dict[str, Any]]:
    """读取 复习/<subject>/*.md，返回每个考点的元数据 + 正文（frontmatter 已剥离）。"""
    rd = REPO_ROOT / "复习" / subject
    if not rd.is_dir():
        return []
    entries = []
    for p in sorted(rd.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = read_frontmatter(p)
        body = FM_RE.sub("", text, count=1).strip()
        entries.append({
            "考点": _fm_get(fm, "考点") or _fm_get(fm, "title") or p.stem,
            "父主题": _fm_get(fm, "父主题") or "（未分类）",
            "weight": int(_fm_get(fm, "weight", "0") or 0),
            "真题数": int(_fm_get(fm, "真题数", "0") or 0),
            "body": body,
            "stem": p.stem,
        })
    return entries


def _render_body(body: str) -> str:
    """Markdown 正文 → HTML（含公式占位；wikilink 渲染为纯文本）。"""
    # 去 wikilinks：保留显示文字
    def strip_wiki(m: re.Match) -> str:
        disp = m.group(2) or m.group(1)
        return html.escape(disp)

    body = WIKILINK_RE.sub(strip_wiki, body)
    # 公式 $...$ 先屏蔽再转换、转换后还原：防 markdown 吃掉 \{ \} \\ 等反斜杠
    masked, math_store = mask_math(body)
    md = markdown.Markdown(extensions=["tables", "fenced_code"])
    return unmask_math(md.convert(masked), math_store)


# ---------------------------------------------------------------------------
# HTML assembly
# ---------------------------------------------------------------------------

HANDBOOK_EXTRA_CSS = """
<style>
  /* 固定 A4 + 统一基础字号：四科一致（≈生物），防 Chromium 按内容宽度整体缩放 */
  @page { size: A4; margin: 12mm; }
  body { font-size: 11.5pt; }
  /* 手册专用样式（补充 PRINT_CSS 基础样式） */
  .hb-wrap { max-width: 960px; margin: 0 auto; padding: 16px; overflow-wrap: anywhere; word-break: break-word; }
  .hb-title { font-size: 1.8em; font-weight: bold; margin: 12px 0 4px; }
  .hb-subtitle { color: #666; font-size: 0.95em; margin-bottom: 16px; }

  /* 题位速查节 */
  .tree-section { margin-bottom: 24px; }
  .tree-section > h2 { border-bottom: 2px solid #333; padding-bottom: 4px; font-size: 1.2em; }
  .slot-block { border: 1px solid #ccc; border-radius: 6px; padding: 8px 10px;
                margin: 6px 0; break-inside: avoid; page-break-inside: avoid; }
  .slot-title { font-weight: bold; font-size: 1em; margin-bottom: 4px; }
  .slot-meta  { color: #666; font-weight: normal; font-size: 0.85em; }
  .bp-tree { font-family: "Cascadia Mono", Consolas, "Microsoft YaHei", monospace;
             white-space: pre; font-size: 0.88em; line-height: 1.5; margin: 4px 0 0; }
  .kp-link { color: #0055cc; text-decoration: none; }
  .kp-link:hover { text-decoration: underline; }

  /* 考点专题节 */
  .parent-group { margin-top: 28px; }
  .parent-group > h2 { font-size: 1.25em; border-left: 4px solid #555;
                       padding-left: 8px; margin-bottom: 8px; }
  .kp-zhuanti { margin-top: 16px; padding: 12px 14px 8px;
                border: 1px solid #ddd; border-radius: 6px;
                break-inside: avoid; page-break-inside: avoid;
                overflow-wrap: anywhere; word-break: break-word; }
  .kp-header  { font-size: 1.1em; font-weight: bold; margin-bottom: 6px; color: #1a1a1a; }
  .kp-meta    { font-size: 0.85em; color: #888; margin-bottom: 8px; }
  .kp-zhuanti h2 { font-size: 1em; border-bottom: 1px solid #eee;
                   padding-bottom: 2px; margin: 10px 0 4px; }
  .kp-zhuanti h3 { font-size: 0.95em; margin: 8px 0 2px; }
  .kp-zhuanti p  { margin: 4px 0 6px; font-size: 0.93em; line-height: 1.55; }
  .kp-zhuanti ul, .kp-zhuanti ol { margin: 4px 0 6px 18px; font-size: 0.93em; }
  .kp-zhuanti table { border-collapse: collapse; font-size: 0.88em; margin: 6px 0; }
  .kp-zhuanti th, .kp-zhuanti td { border: 1px solid #ccc; padding: 3px 7px; }
  .kp-zhuanti pre { background: #f6f6f6; padding: 8px; font-size: 0.85em;
                    overflow-x: auto; border-radius: 4px; }
  /* KaTeX 同时输出可见的 .katex-html + 无障碍用的 .katex-mathml(<math> 树)。
     后者在本地 Chromium 原生 MathML 下以全宽(数百~千 px)参与布局，把内容撑宽，
     逼出 Chromium 整页 shrink-to-fit(化学曾被压到 0.66/正文 7.1pt)。
     PDF 不需要 MathML 无障碍副本，display:none 彻底移出布局(视觉等价)。 */
  .katex-mathml { display: none !important; }

  @media print {
    .hb-wrap { max-width: none; padding: 0; }
    .tree-section { page-break-before: always; }
    .tree-section:first-of-type { page-break-before: avoid; }
    .kp-zhuanti { page-break-before: always; }
    a { color: #000; text-decoration: none; }
    .kp-link { color: #000; }
    .slot-block { break-inside: avoid; page-break-inside: avoid; }
  }
</style>
"""


def _render_tree_section(
    era: str,
    slots: dict,
    has_review: set[str],
    page_map: dict[str, int] | None = None,
) -> str:
    """渲染一个时代的题位树（含超链接子考点）。"""
    rows_html = []
    for slot in sorted(slots, key=lambda s: (TYPE_ORDER.get(s[0], 9), s[1])):
        d = slots[slot]
        tree = d.get("树", [])
        linked_lines = _tree_lines_linked(tree, has_review, page_map)
        tree_html = '<div class="bp-tree">' + "".join(
            f"<div>{line}</div>" for line in linked_lines
        ) + "</div>"
        thin = (
            '<span style="color:#a00;font-size:0.85em;">（样本仅 %d，规律参考）</span>'
            % d["n"]
        ) if d["n"] <= 2 else ""
        rows_html.append(
            f'<div class="slot-block">'
            f'<div class="slot-title">{html.escape(slot[0])}{slot[1]}'
            f'<span class="slot-meta"> · n={d["n"]} · 难度{html.escape(d["难度倾向"])}'
            f"</span>{thin}</div>"
            f"{tree_html}</div>"
        )
    return (
        f'<div class="tree-section">'
        f"<h2>{html.escape(era)}</h2>"
        + "".join(rows_html)
        + "</div>"
    )


def build_handbook_html(
    subject: str,
    tree_eras: dict,
    zhuanti_entries: list[dict[str, Any]],
    page_map: dict[str, int] | None = None,
) -> str:
    """纯函数：组装手册 HTML（不含完整 <html> 外壳）。

    tree_eras: aggregate + attach_trees 的输出（同 gen_exam_blueprint 格式）
    zhuanti_entries: list of {考点, 父主题, weight, 真题数, body_html}
    page_map: {考点: 页码} 用于目录式页码标注（可选；来自第一次渲染后 fitz 抽取）
    返回 <body> 内可插入的 HTML 片段。
    """
    has_review: set[str] = {e["考点"] for e in zhuanti_entries}

    # ── 题位速查脑图 ────────────────────────────────────────────────────
    tree_parts = []
    for era in ERA_ORDER:
        slots = tree_eras.get(era, {})
        if not slots:
            continue
        tree_parts.append(_render_tree_section(era, slots, has_review, page_map))
    tree_section = (
        '<div id="blueprint-section">'
        f'<h1>题位速查 · {html.escape(subject)}（吉林高考）</h1>'
        + "".join(tree_parts)
        + "</div>"
    )

    # ── 考点专题 ─────────────────────────────────────────────────────────
    # 按父主题分组，父组按组内 weight 总和 desc，组内按 weight desc / 真题数 desc
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in zhuanti_entries:
        groups[e["父主题"]].append(e)

    def group_weight(parent: str) -> int:
        return sum(e.get("weight", 0) for e in groups[parent])

    sorted_parents = sorted(groups.keys(), key=group_weight, reverse=True)

    zhuanti_parts = []
    for parent in sorted_parents:
        items = sorted(
            groups[parent],
            key=lambda e: (-e.get("weight", 0), -e.get("真题数", 0)),
        )
        kp_sections = []
        for e in items:
            kp = e["考点"]
            aid = anchor_id(kp)
            w = e.get("weight", 0)
            cnt = e.get("真题数", 0)
            body_html = e.get("body_html", "")
            # Hidden locator token (white text on white background) so fitz can find the page.
            # Must NOT use visibility:hidden/display:none — those prevent text from entering
            # the PDF text layer. White color makes it invisible to human eyes but fitz can
            # still extract it via text search.
            safe = _safe_name(kp)
            tok = f'<span style="color:#ffffff;font-size:1px">@@{safe}@@</span>'
            kp_sections.append(
                f'<section class="kp-zhuanti" id="{html.escape(aid)}">'
                f'<div class="kp-header">{tok}{html.escape(kp)}</div>'
                f'<div class="kp-meta">weight {w} · 真题数 {cnt} · 父主题：{html.escape(parent)}</div>'
                f"{body_html}"
                "</section>"
            )
        zhuanti_parts.append(
            f'<div class="parent-group">'
            f"<h2>{html.escape(parent)}</h2>"
            + "".join(kp_sections)
            + "</div>"
        )

    zhuanti_section = (
        '<div id="zhuanti-section">'
        f'<h1>{html.escape(subject)}考点专题复习</h1>'
        + "".join(zhuanti_parts)
        + "</div>"
    )

    return tree_section + "\n" + zhuanti_section


# ---------------------------------------------------------------------------
# Full HTML page
# ---------------------------------------------------------------------------

def _katex_head() -> str:
    """返回 KaTeX head 片段（同 gen_exam_blueprint.KATEX_HEAD，路径 ./vendor/...）。"""
    return KATEX_HEAD


def build_full_html(subject: str, body_html: str) -> str:
    """包裹完整 <html> 外壳（A4 打印 CSS + KaTeX）。"""
    return (
        f"<!DOCTYPE html>\n"
        f'<html lang="zh-CN"><head><meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"<title>{html.escape(subject)}复习手册</title>\n"
        f'<link rel="stylesheet" href="./vendor/style.css">\n'
        f"{PRINT_CSS}"
        f"{HANDBOOK_EXTRA_CSS}"
        f"{_katex_head()}"
        f"</head>\n"
        f"<body><div class=\"hb-wrap\">\n"
        f'<div class="hb-title">{html.escape(subject)}复习手册 · 吉林高考冲刺</div>\n'
        f'<div class="hb-subtitle">题位速查脑图（顶部）+ 考点专题（正文）| Ctrl+P → A4 PDF</div>\n'
        f"{body_html}\n"
        f"</div>\n"
        f"{_FIT_SCRIPT}\n"
        f"</body></html>"
    )


# KaTeX 渲染后，把超出页宽的公式/表格用 font-size 局部缩小到恰好适配。
# 这样没有元素超出页宽，Chromium 不再对整本做"适配页宽"缩放 → 四科正文字号统一。
#
# 关键点（踩坑见 docs/superpowers/working/_handbook_pdf_handoff.md）：
#  1) 必须用 font-size 而非 zoom：CSS zoom 只缩"绘制矩形"，不改布局宽度，父容器仍溢出
#     → Chromium "整体缩放适配纸宽"照旧触发（化学曾被压到 0.66，正文 7.1pt）。
#  2) ⭐不能用 .katex 盒宽(getBoundingClientRect().width)判超宽：display 公式的
#     .katex/.katex-html 是 block，宽度被容器钳到 ≈596px，但内部 .base(inline-block;
#     white-space:nowrap)会以真实宽(如 1058px)溢出盒子。只测盒宽 → 判 596<697 漏判 →
#     .base 溢出顶高 wrap.scrollWidth → 整页缩放照旧。必须测「自身 + 全部非 SVG 后代的
#     最右边缘」(contentW)才是公式真实宽。跳过 SVG 内部：<path> 的 getBoundingClientRect
#     是 viewBox 几何坐标，虚高到数千 px，会污染测量。
#  3) MathML 副本由 CSS .katex-mathml{display:none} 移出布局(见 HANDBOOK_EXTRA_CSS)，
#     否则 <math> 树以全宽参与布局，是化学整页缩放的主因(占溢出元素 ~97%)。
#  4) 必须用真实打印宽而非 wrap.clientWidth：JS 在 screen 布局执行（视口≈800px），
#     与打印实际内容宽（A4 210mm − 2×12mm 边距 = 186mm ≈ 703px @96dpi）不符。
_FIT_SCRIPT = """
<script>
function hbFit() {
  var wrap = document.querySelector('.hb-wrap');
  if (!wrap) return;
  var W = (186 * 96 / 25.4) - 4;   // 打印内容宽 ≈703px，留 4px 安全余量
  var SVGNS = 'http://www.w3.org/2000/svg';
  // 元素「右边缘」(相对 wrap 左)才是是否超页宽的判据；同时取「左偏移」(相对 wrap)。
  //   右边缘 = 元素自身 + 全部非 SVG 后代的最右边缘（display 公式 .katex 盒宽被容器钳住，
  //            内部 .base 会溢出盒子，必须扫后代——详见上方注释②）。
  //   左偏移 = 列表缩进/padding，不随 font-size 缩放，缩公式时要按 (W − 左偏移) 留出缩进空间，
  //            否则缩到内容宽=W 后右边缘=左偏移+W 仍溢出（数学手册 0.94 残留缩放即此因）。
  function edges(el) {
    var wl = wrap.getBoundingClientRect().left;
    var box = el.getBoundingClientRect();
    var leftRel = box.left - wl, maxR = box.right;
    var ch = el.getElementsByTagName('*');
    for (var i = 0; i < ch.length; i++) {
      var c = ch[i];
      if (c.namespaceURI === SVGNS) continue;   // 跳过 <path> 等 SVG 几何坐标虚高
      var r = c.getBoundingClientRect();
      if ((r.width || r.height) && r.right > maxR) maxR = r.right;
    }
    return { leftRel: leftRel, rightRel: maxR - wl };
  }
  var sel = ['.bp-tree', '.katex', '.kp-zhuanti table', 'table', '.kp-zhuanti pre'];
  document.querySelectorAll(sel.join(',')).forEach(function (el) {
    el.style.fontSize = '';
    // 迭代收敛：宽度不随 font-size 严格线性，单次可能欠缩，重测再缩，最多 6 次。
    for (var k = 0; k < 6; k++) {
      var e = edges(el);
      if (e.rightRel <= W) break;
      var contentWidth = e.rightRel - e.leftRel;   // 随 font 缩放的部分
      var avail = W - e.leftRel;                   // 扣除固定缩进后留给内容的宽
      if (avail <= 0) break;                        // 极端缩进，放弃(罕见)
      var fs = parseFloat(getComputedStyle(el).fontSize);
      el.style.fontSize = (fs * avail / contentWidth).toFixed(2) + 'px';
    }
  });
}
window.addEventListener('load', function () { setTimeout(hbFit, 500); });
</script>
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description="生成每科可打印复习手册 HTML")
    ap.add_argument("--subject", default="数学", help="学科（数学/物理/化学/生物），默认 数学")
    ap.add_argument("--apply", action="store_true", help="写盘；否则仅预览统计")
    ap.add_argument("--page-map", default=None,
                    help="JSON 文件路径 {考点: 页码}，用于目录式页码标注（第二次渲染时传入）")
    args = ap.parse_args()

    subject = args.subject
    exam_dir, norm_yaml, group_yaml, _ = paths_for(subject)

    # 0) 可选页码映射
    page_map: dict[str, int] | None = None
    if args.page_map:
        map_path = Path(args.page_map)
        if map_path.exists():
            with map_path.open(encoding="utf-8") as f:
                page_map = json.load(f)
            print(f"页码映射：{len(page_map)} 个考点（{map_path}）", flush=True)
        else:
            print(f"[WARN] --page-map 文件不存在：{map_path}", flush=True)

    # 1) 题位树
    rows = read_rows(exam_dir)
    print(f"真题：{len(rows)} 题（{exam_dir.name}）", flush=True)
    normalize = load_normalize(norm_yaml)
    agg = aggregate(rows, normalize)
    group = load_group(group_yaml)
    attach_trees(agg, group)

    # 2) 复习专题
    zhuanti_raw = load_zhuanti(subject)
    print(f"复习专题：{len(zhuanti_raw)} 个考点（复习/{subject}/）", flush=True)

    # 渲染正文 HTML
    for e in zhuanti_raw:
        e["body_html"] = _render_body(e["body"])

    if not args.apply:
        # dry-run：展示父主题分布
        from collections import Counter
        parent_ctr: Counter = Counter(e["父主题"] for e in zhuanti_raw)
        print("\n父主题分布（top 10）：")
        for p, cnt in parent_ctr.most_common(10):
            print(f"  {p}: {cnt}")
        print(f"\n(dry-run) 加 --apply 写 {subject}复习手册.html")
        return 0

    # 3) 组装 HTML
    body_html = build_handbook_html(subject, agg, zhuanti_raw, page_map=page_map)
    full_html = build_full_html(subject, body_html)

    out_path = OUT_DIR / f"{subject}复习手册.html"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(full_html, encoding="utf-8", newline="")
    size_kb = out_path.stat().st_size // 1024
    print(f"\n[APPLY] → {out_path}  ({size_kb} KB, {len(zhuanti_raw)} 考点)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
