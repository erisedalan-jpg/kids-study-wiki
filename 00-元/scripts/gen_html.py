"""学生 HTML 静态站生成器（吉林冲刺 · 数物化生 4 科 weight ≥ 阈值）。

输出 docs/student/：
  index.html                    入口（4 科 + 总览）
  数学.html / 物理.html / 化学.html / 生物.html / 总览.html  科目列表
  atoms/{stem}.html             词条详情页
  exam/{stem}.html              真题题级页
  vendor/style.css              移动响应式样式

设计：
- 完全离线：file:// 直接打开；图片用相对路径指向 ../../素材/真题截图/
- 公式：保留原始 $...$；如需渲染，HTML 头部预留 KaTeX 钩子（vendor/katex/* 用户自备）
- wikilink：[[NN-X|Y]] → atoms/NN-X.html；失链 → 灰色虚链
- weight 着色：top15% 金 / 16-40% 红 / 余蓝

CLI：
  python 00-元/scripts/gen_html.py --apply --threshold 10
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import markdown

sys.path.insert(0, str(Path(__file__).parent))
from _utils import (  # noqa: E402
    REPO_ROOT, iter_entries, iter_exam_dirs,
    read_frontmatter, setup_utf8,
)

OUT_DIR = REPO_ROOT / "docs" / "student"
SUBJECTS = ["数学", "物理", "化学", "生物"]

# KaTeX 0.16.11 离线包（首次需联网下载；之后完全离线）
KATEX_VERSION = "0.16.11"
KATEX_CDN = f"https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist"
KATEX_FILES = [
    "katex.min.css",
    "katex.min.js",
    "contrib/auto-render.min.js",
]
KATEX_FONTS = [  # 仅 woff2（现代浏览器够用）
    "KaTeX_AMS-Regular", "KaTeX_Caligraphic-Bold", "KaTeX_Caligraphic-Regular",
    "KaTeX_Fraktur-Bold", "KaTeX_Fraktur-Regular",
    "KaTeX_Main-Bold", "KaTeX_Main-BoldItalic", "KaTeX_Main-Italic",
    "KaTeX_Main-Regular",
    "KaTeX_Math-BoldItalic", "KaTeX_Math-Italic",
    "KaTeX_SansSerif-Bold", "KaTeX_SansSerif-Italic", "KaTeX_SansSerif-Regular",
    "KaTeX_Script-Regular",
    "KaTeX_Size1-Regular", "KaTeX_Size2-Regular",
    "KaTeX_Size3-Regular", "KaTeX_Size4-Regular",
    "KaTeX_Typewriter-Regular",
]


def fetch_katex(vendor_dir: Path) -> None:
    """从 jsdelivr 下载 KaTeX 全套到 vendor/katex/（一次性，需联网）。"""
    import urllib.request
    katex_dir = vendor_dir / "katex"
    katex_dir.mkdir(parents=True, exist_ok=True)
    (katex_dir / "contrib").mkdir(exist_ok=True)
    (katex_dir / "fonts").mkdir(exist_ok=True)
    n_ok = n_skip = 0
    for f in KATEX_FILES:
        dst = katex_dir / f
        if dst.exists():
            n_skip += 1
            continue
        url = f"{KATEX_CDN}/{f}"
        print(f"  fetch {f} ... ", end="", flush=True)
        try:
            urllib.request.urlretrieve(url, dst)
            print("ok")
            n_ok += 1
        except Exception as e:
            print(f"FAIL: {e}")
    for name in KATEX_FONTS:
        f = f"fonts/{name}.woff2"
        dst = katex_dir / f
        if dst.exists():
            n_skip += 1
            continue
        url = f"{KATEX_CDN}/{f}"
        try:
            urllib.request.urlretrieve(url, dst)
            n_ok += 1
        except Exception as e:
            print(f"  font FAIL {name}: {e}")
    print(f"  KaTeX: 新下载 {n_ok} / 已存在 {n_skip}")


def katex_head_html_at_depth(depth: int) -> str:
    """生成 KaTeX <link>+<script> 注入；若 vendor/katex/ 不存在则返回空。"""
    katex_root = OUT_DIR / "vendor" / "katex"
    if not (katex_root / "katex.min.css").exists():
        return ""
    prefix = "." if depth == 0 else "/".join([".."] * depth)
    return f"""
<link rel="stylesheet" href="{prefix}/vendor/katex/katex.min.css">
<script defer src="{prefix}/vendor/katex/katex.min.js"></script>
<script defer src="{prefix}/vendor/katex/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body,{{
    delimiters:[
      {{left:'$$',right:'$$',display:true}},
      {{left:'$',right:'$',display:false}}
    ],
    throwOnError:false
  }});"></script>
"""

WIKILINK_RE = re.compile(r"\[\[([^\[\]#|]+?)(?:#([^|\]]+))?(?:\|([^\]]+))?\]\]")
BACKLINK_RE = re.compile(
    r"<!-- exam-backlinks-start -->(.*?)<!-- exam-backlinks-end -->", re.DOTALL
)
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def parse_list(v: str) -> list[str]:
    v = (v or "").strip()
    if v.startswith("[") and v.endswith("]"):
        return [x.strip() for x in v[1:-1].split(",") if x.strip()]
    return [v] if v else []


def fm_get(fm: dict[str, str], key: str, default: str = "") -> str:
    return (fm.get(key) or default).strip()


def build_link_resolver(included: set[str], atom_titles: dict[str, str],
                        exam_atom_map: dict[tuple[str, str], str]) -> callable:
    """构造 wikilink → HTML 链接转换器。

    - 目标在 included 学科子集 → atoms/{stem}.html
    - 目标 stem 在 exam_atom_map[(current_subject, stem)] → exam/{学科}/{stem}.html
      （按当前 atom 所属学科匹配，避免跨学科同 stem 互指；如化学词条引
      `[[2008-全国Ⅱ-04]]` → exam/化学/2008-全国Ⅱ-04.html 而非误指物理/英语）
    - fallback：任意学科有该 stem 时取字典序首学科
    - 否则 → dead link

    返回函数签名：(match, current_dir, current_subject) → html str
    """
    # 反查：stem → set(学科)
    stem_to_subjects: dict[str, set[str]] = defaultdict(set)
    for (subj, stem) in exam_atom_map:
        stem_to_subjects[stem].add(subj)

    def resolve(m: re.Match, depth: int = 0, current_subject: str = "") -> str:
        raw_target = m.group(1).strip()
        disp = m.group(3) or raw_target
        prefix = "." if depth == 0 else "/".join([".."] * depth)

        if raw_target in included:
            href = f"{prefix}/atoms/{html.escape(raw_target)}.html"
            return f'<a href="{href}">{html.escape(disp)}</a>'

        subjects = stem_to_subjects.get(raw_target)
        if subjects:
            # 优先当前学科；否则字典序首
            if current_subject in subjects:
                pick = current_subject
            else:
                pick = sorted(subjects)[0]
            href = (f"{prefix}/exam/{html.escape(pick)}/"
                    f"{html.escape(raw_target)}.html")
            return f'<a href="{href}">{html.escape(disp)}</a>'

        if raw_target in atom_titles:
            stem = atom_titles[raw_target]
            if stem in included:
                href = f"{prefix}/atoms/{html.escape(stem)}.html"
                return f'<a href="{href}">{html.escape(disp)}</a>'
        return f'<a class="dead" title="未收录">{html.escape(disp)}</a>'

    return resolve


def md_to_html(body: str, resolve: callable, depth: int,
               relative_repo_prefix: str, current_subject: str = "") -> str:
    """词条 markdown 主体 → HTML。

    - 先剥反链段（单独渲染卡片）
    - 替换 wikilink → <a>（按 current_subject 跨学科消歧）
    - 图片路径加 ../{..}/ 前缀（指向仓库根的 素材/）
    - markdown 库渲染剩余 markdown
    - 公式 $...$ 保留原文（套 <span class="math-source">）
    """
    bl_m = BACKLINK_RE.search(body)
    backlink_section = bl_m.group(1) if bl_m else ""
    main_body = BACKLINK_RE.sub("", body)

    main_body = WIKILINK_RE.sub(lambda m: resolve(m, depth, current_subject),
                                main_body)

    # 图片路径：源 md 内可能是 `../../素材/...`（相对源 md 位置）或
    # 裸 `素材/...`（仓库根相对）。先归一到仓库根相对，再加 HTML 位置的前缀。
    def fix_img(m: re.Match) -> str:
        alt, src = m.group(1), m.group(2).strip()
        if src.startswith(("http://", "https://", "data:")):
            return m.group(0)
        s = src.lstrip("/")
        while s.startswith("../"):
            s = s[3:]
        if not s.startswith(("素材", "00-元", "真题", "数学", "物理", "化学",
                             "生物", "英语", "语文")):
            return m.group(0)
        return f"![{alt}]({relative_repo_prefix}{s})"
    main_body = IMG_RE.sub(fix_img, main_body)

    # 公式 $...$ 保留原文，包 span（可选 KaTeX 渲染钩子）
    # 不破坏 markdown 表格 / 列表
    md = markdown.Markdown(extensions=["tables", "fenced_code", "attr_list"])
    html_body = md.convert(main_body)

    if backlink_section:
        bl_text = WIKILINK_RE.sub(
            lambda m: resolve(m, depth, current_subject), backlink_section)
        # 剥原始 `## 高考真题命中` 行（card 已有 h3 标题，避免双重）
        bl_text = re.sub(r"^##+\s*高考真题命中\s*$\n?", "", bl_text, flags=re.M)
        bl_md = markdown.Markdown(extensions=["tables", "fenced_code"])
        bl_html = bl_md.convert(bl_text)
        html_body += (
            '\n<div class="backlink-card">'
            '<h3>📌 高考真题命中</h3>'
            f'{bl_html}</div>'
        )
    return html_body


def weight_class(w: int, thresholds: dict[str, int]) -> str:
    if w >= thresholds["gold"]:
        return "gold"
    if w >= thresholds["red"]:
        return "red"
    return "blue"


def render_page(title: str, content_html: str, depth: int,
                extra_head: str = "") -> str:
    """完整 HTML 页（带 head + nav + footer）。

    depth = 当前页相对 docs/student/ 的目录深度：
      0 = 根（index.html / 学科.html / 总览.html）
      1 = atoms/ 下
      2 = exam/{学科}/ 下
    """
    prefix = "." if depth == 0 else "/".join([".."] * depth)
    style_href = f"{prefix}/vendor/style.css"
    katex_head = katex_head_html_at_depth(depth)
    nav_links = [
        ("总览", f"{prefix}/index.html"),
        ("数学", f"{prefix}/数学.html"),
        ("物理", f"{prefix}/物理.html"),
        ("化学", f"{prefix}/化学.html"),
        ("生物", f"{prefix}/生物.html"),
    ]
    nav_html = '<div class="nav">' + "".join(
        f'<a href="{href}">{html.escape(label)}</a>' for label, href in nav_links
    ) + "</div>"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{style_href}">
{katex_head}
{extra_head}
</head>
<body>
<div class="wrap">
{nav_html}
{content_html}
</div>
</body>
</html>"""


def gen_atom_page(path: Path, fm: dict[str, str], body: str,
                  resolve: callable) -> str:
    title = fm_get(fm, "title", path.stem)
    weight = int(fm_get(fm, "weight", "0") or 0)
    aliases = parse_list(fm_get(fm, "aliases"))
    subject = fm_get(fm, "学科")
    period = fm_get(fm, "学段")
    topic = fm_get(fm, "主题")
    jl = fm_get(fm, "吉林反链", "0")
    path_cnt = fm_get(fm, "学习路径出现", "0")

    meta = (
        '<div class="meta-card">'
        f'<span><strong>权重</strong>{weight}</span>'
        f'<span><strong>吉林命中</strong>{jl}</span>'
        f'<span><strong>路径</strong>{path_cnt}</span>'
        f'<span><strong>学段</strong>{html.escape(period)}</span>'
        f'<span><strong>主题</strong>{html.escape(topic)}</span>'
        '</div>'
    )
    if aliases:
        meta += (
            f'<p style="font-size:0.9em;color:#666;">'
            f'<strong>aliases</strong>: {html.escape(", ".join(aliases))}</p>'
        )

    current_subject = fm_get(fm, "学科")
    body_html = md_to_html(body, resolve, depth=1, relative_repo_prefix="../../../",
                            current_subject=current_subject)
    content = (
        f'<h1>{html.escape(title)}</h1>{meta}{body_html}'
    )
    return render_page(title, content, depth=1)


def gen_exam_page(path: Path, fm: dict[str, str], body: str,
                  resolve: callable, current_dir_depth: int = 4) -> str:
    title = fm_get(fm, "title", path.stem)
    year = fm_get(fm, "年份")
    paper = fm_get(fm, "卷别")
    gender = fm_get(fm, "文理")
    qno = fm_get(fm, "题号")
    qtype = fm_get(fm, "题型")
    diff = fm_get(fm, "难度")
    province = fm_get(fm, "省份")
    points = parse_list(fm_get(fm, "考点"))

    meta = (
        '<div class="meta-card">'
        f'<span><strong>{html.escape(province)}</strong>{html.escape(year)}</span>'
        f'<span><strong>卷</strong>{html.escape(paper)}</span>'
        f'<span><strong>{html.escape(gender)}</strong></span>'
        f'<span><strong>题</strong>{html.escape(qno)}</span>'
        f'<span><strong>题型</strong>{html.escape(qtype)}</span>'
        f'<span><strong>难</strong>{html.escape(diff)}</span>'
        '</div>'
    )
    if points:
        points_html = " ".join(f"<code>{html.escape(p)}</code>" for p in points)
        meta += f'<p><strong>考点</strong>：{points_html}</p>'

    # 真题页路径 docs/student/exam/{学科}/{stem}.html → 仓库根需 4 级 ../
    current_subject = fm_get(fm, "学科")
    body_html = md_to_html(body, resolve, depth=2, relative_repo_prefix="../../../../",
                            current_subject=current_subject)
    content = f'<h1>{html.escape(title)}</h1>{meta}{body_html}'
    return render_page(title, content, depth=2)


def gen_subject_index(subject: str, atoms: list[tuple[Path, dict, int]],
                      thresholds: dict[str, int]) -> str:
    title = f"{subject} · 高频考点（吉林冲刺）"
    items = []
    for p, fm, w in atoms:
        cls = weight_class(w, thresholds)
        atom_title = fm_get(fm, "title", p.stem)
        jl = fm_get(fm, "吉林反链", "0")
        href = f"atoms/{html.escape(p.stem)}.html"
        items.append(
            f'<li class="{cls}" data-title="{html.escape(atom_title.lower())}">'
            f'<span class="badge {cls}">{w}</span>'
            f'<span class="title"><a href="{href}">{html.escape(atom_title)}</a></span>'
            f'<span class="meta">吉{jl}</span>'
            '</li>'
        )
    list_html = '<ul class="entry-list">' + "".join(items) + "</ul>"
    search = (
        '<input class="search" placeholder="筛词条标题（前端 JS 即时过滤）" '
        'oninput="filterEntries(this.value)">'
        '<script>function filterEntries(q){'
        'q=q.trim().toLowerCase();'
        'document.querySelectorAll(".entry-list li").forEach(li=>{'
        'li.style.display=q===""||li.dataset.title.includes(q)?"":"none";});}'
        '</script>'
    )
    content = (
        f'<h1>{html.escape(title)}</h1>'
        f'<p>共 {len(atoms)} 条，weight 降序。'
        '<span class="badge gold">金</span> top15%，'
        '<span class="badge red">红</span> 16-40%，'
        '<span class="badge blue">蓝</span> 余。</p>'
        f'{search}{list_html}'
    )
    return render_page(title, content, depth=0)


def gen_home(stats_by_sub: dict[str, int], total: int) -> str:
    content = (
        '<h1>吉林冲刺 · 学生重点 HTML</h1>'
        '<p>数物化生 4 科 weight ≥ 10 的核心词条，离线可读。'
        '<br>配置：<code>00-元/scripts/weight_config.yaml</code>；'
        '重生成：<code>python 00-元/scripts/gen_html.py --apply --threshold 10</code></p>'
        f'<p><strong>共 {total} 词条</strong></p>'
        '<ul>'
        f'<li>🔢 <a href="数学.html">数学 ({stats_by_sub["数学"]})</a></li>'
        f'<li>⚛️ <a href="物理.html">物理 ({stats_by_sub["物理"]})</a></li>'
        f'<li>🧪 <a href="化学.html">化学 ({stats_by_sub["化学"]})</a></li>'
        f'<li>🧬 <a href="生物.html">生物 ({stats_by_sub["生物"]})</a></li>'
        '<li>📊 <a href="总览.html">总览（跨 4 科 top 30）</a></li>'
        '</ul>'
        '<hr>'
        '<p style="font-size:0.85em;color:#888;">使用提示：</p>'
        '<ul style="font-size:0.85em;color:#888;">'
        '<li>词条间链接 <code>[[X]]</code> 自动跳转；未收录词条灰色</li>'
        '<li>真题截图在 <code>素材/真题截图/</code>；离线使用须把整个仓库（含 docs/ 与 素材/）拷贝到设备</li>'
        '<li>公式 $...$ / $$...$$ 由 KaTeX 离线渲染（<code>vendor/katex/</code>，~600KB，首次需联网 <code>--fetch-katex</code> 拉取）</li>'
        '<li>未生成的内容：英语词条、低 weight 词条、小学/初中、非吉林真题（保留位）</li>'
        '</ul>'
    )
    return render_page("吉林冲刺·学生 HTML", content, depth=0)


def gen_top_overview(all_atoms: list[tuple[Path, dict, int, str]]) -> str:
    top = sorted(all_atoms, key=lambda x: -x[2])[:30]
    items = []
    for p, fm, w, s in top:
        cls = weight_class(w, {"gold": 50, "red": 20})
        atom_title = fm_get(fm, "title", p.stem)
        jl = fm_get(fm, "吉林反链", "0")
        href = f"atoms/{html.escape(p.stem)}.html"
        items.append(
            f'<li class="{cls}">'
            f'<span class="badge {cls}">{w}</span>'
            f'<span class="title"><a href="{href}">{html.escape(atom_title)}</a> '
            f'<small style="color:#888;">({s})</small></span>'
            f'<span class="meta">吉{jl}</span>'
            '</li>'
        )
    content = (
        '<h1>总览 · 跨 4 科 top 30（吉林冲刺）</h1>'
        '<ul class="entry-list">' + "".join(items) + "</ul>"
    )
    return render_page("总览", content, depth=0)


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="写盘；否则仅扫描汇总")
    ap.add_argument("--threshold", type=int, default=10,
                    help="weight 阈值（默认 10）")
    ap.add_argument("--fetch-katex", action="store_true",
                    help="联网下载 KaTeX 全套到 vendor/katex/（一次性 ~250KB）")
    args = ap.parse_args()

    if args.fetch_katex:
        print("下载 KaTeX 0.16.11 离线包 ...")
        fetch_katex(OUT_DIR / "vendor")
        print("KaTeX 下载完成。后续 --apply 生成的页面会自动渲染公式。")
        if not args.apply:
            return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "atoms").mkdir(exist_ok=True)
    (OUT_DIR / "exam").mkdir(exist_ok=True)
    (OUT_DIR / "vendor").mkdir(exist_ok=True)

    # 1) 扫所有 4 科词条 + 取 weight ≥ threshold
    included: set[str] = set()
    atom_titles: dict[str, str] = {}     # alias / bare-name → stem
    by_subject: dict[str, list] = defaultdict(list)
    all_atoms: list = []
    for s in SUBJECTS:
        sd = REPO_ROOT / s
        if not sd.is_dir():
            continue
        for p in iter_entries(sd):
            fm = read_frontmatter(p)
            if not fm:
                continue
            w = int(fm_get(fm, "weight", "0") or 0)
            atom_titles[p.stem] = p.stem
            for a in parse_list(fm_get(fm, "aliases")):
                atom_titles.setdefault(a, p.stem)
            bare = re.sub(r"^\d+-", "", p.stem)
            atom_titles.setdefault(bare, p.stem)
            if w >= args.threshold:
                included.add(p.stem)
                by_subject[s].append((p, fm, w))
                all_atoms.append((p, fm, w, s))

    # 2) 扫 真题（吉林+黑龙江） (subject, stem) → path，做反链跳转目标
    #    用 (subject, stem) 复合键避免跨学科同 stem 互覆（如化学 vs 物理的
    #    2008-全国Ⅱ-04 是不同题）；resolve 时按 atom 学科消歧。
    exam_atom_map: dict[tuple[str, str], str] = {}
    for sub in iter_exam_dirs():
        if not (sub.name.startswith("吉林") or sub.name.startswith("黑龙江")):
            continue
        # 目录名 `吉林-化学` → 学科 = 化学
        parts = sub.name.split("-", 1)
        if len(parts) != 2:
            continue
        prov, subject_name = parts
        for p in sub.glob("*.md"):
            exam_atom_map[(subject_name, p.stem)] = str(p)

    resolve = build_link_resolver(included, atom_titles, exam_atom_map)
    thresholds = {"gold": 50, "red": 20}

    stats = {s: len(v) for s, v in by_subject.items()}
    total = sum(stats.values())
    print(f"扫描：4 科 / {total} 词条（weight ≥ {args.threshold}）", flush=True)
    for s in SUBJECTS:
        n = stats.get(s, 0)
        print(f"  {s}: {n}")

    if not args.apply:
        print("\n(dry-run) 加 --apply 写盘。")
        return 0

    # 3) 词条详情页
    n_atom = 0
    for s, lst in by_subject.items():
        lst.sort(key=lambda x: -x[2])
        for p, fm, w in lst:
            text = p.read_text(encoding="utf-8")
            body = FM_RE.sub("", text, count=1)
            html_out = gen_atom_page(p, fm, body, resolve)
            (OUT_DIR / "atoms" / f"{p.stem}.html").write_text(
                html_out, encoding="utf-8", newline="")
            n_atom += 1

    # 4) 真题题级页（仅子集中词条反链命中的题，按当前学科消歧 stem）
    #    referenced_by_subject: 学科 → set(stem)，因同 stem 跨学科是不同题
    referenced_by_subject: dict[str, set[str]] = defaultdict(set)
    for s, lst in by_subject.items():
        for p, fm, w in lst:
            text = p.read_text(encoding="utf-8")
            for m in BACKLINK_RE.finditer(text):
                for mm in re.finditer(r"\[\[([^\[\]|]+?)(?:\|[^\]]*)?\]\]", m.group(1)):
                    referenced_by_subject[s].add(mm.group(1).strip())
    n_exam = 0
    for sub in iter_exam_dirs():
        if not sub.name.startswith("吉林"):
            continue
        parts = sub.name.split("-", 1)
        if len(parts) != 2:
            continue
        subject_name = parts[1]
        ref_set = referenced_by_subject.get(subject_name, set())
        if not ref_set:
            continue
        subj_dir = OUT_DIR / "exam" / subject_name
        subj_dir.mkdir(parents=True, exist_ok=True)
        for p in sub.glob("*.md"):
            if p.stem not in ref_set:
                continue
            text = p.read_text(encoding="utf-8")
            fm = read_frontmatter(p)
            body = FM_RE.sub("", text, count=1)
            html_out = gen_exam_page(p, fm, body, resolve)
            (subj_dir / f"{p.stem}.html").write_text(
                html_out, encoding="utf-8", newline="")
            n_exam += 1

    # 5) 科目索引 + 总览 + 首页
    for s, lst in by_subject.items():
        page = gen_subject_index(s, lst, thresholds)
        (OUT_DIR / f"{s}.html").write_text(page, encoding="utf-8", newline="")
    (OUT_DIR / "总览.html").write_text(
        gen_top_overview(all_atoms), encoding="utf-8", newline="")
    (OUT_DIR / "index.html").write_text(
        gen_home(stats, total), encoding="utf-8", newline="")

    print(f"\n[APPLY] 词条 {n_atom} / 真题 {n_exam} / 索引 5 / 首页 1 → {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
