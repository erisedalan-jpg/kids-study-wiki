"""英语真题渲染（专用，篇章/大题级 md）。

读 exam_eng_extract.py 结构化后的 blocks.json，每块渲一篇章级 .md
→ 真题/<省>-英语/{year}-{paper}-E{NN}.md。

英语大题考点规整，按 qtype+genre 规则派生 tag（无需 LLM enrich）。
摘要取【导语】主旨句。末尾跑 fix_wikilinks 规范化（同其他生成脚本）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402

# qtype → 固定技能考点（英语大题考点规整）
QTYPE_TAGS = {
    "完形填空": ["完形填空", "词义辨析", "语境理解"],
    "语篇填空": ["语篇填空", "语法填空"],
    "阅读理解": ["阅读理解", "细节理解", "推理判断"],
    "七选五": ["七选五", "篇章结构"],
    "阅读表达": ["阅读表达", "信息归纳"],
    "书面表达": ["书面表达", "应用文写作"],
}
DETAIL_SPLIT = re.compile(r"【\s*\d*\s*题?\s*详解\s*】|【\s*详解\s*】")


def derive_tags(qtype: str, genre: str) -> list[str]:
    tags = list(QTYPE_TAGS.get(qtype, [qtype]))
    if genre and genre not in ("", "应用文/书面表达"):
        if genre not in tags:
            tags.append(genre)
    return tags


def summary_of(solution_text: str) -> str:
    """取【导语】主旨句（到首个【N题详解】前）。"""
    head = DETAIL_SPLIT.split(solution_text, maxsplit=1)[0]
    head = re.sub(r"【\s*导\s*语\s*】", "", head).strip()
    head = re.sub(r"\s+", " ", head)
    return head[:200] if head else "（待补）"


def render_block(qa: dict[str, Any], b: dict[str, Any]) -> str:
    year = qa["year"]
    paper = qa["paper"]
    province = qa["province"]
    bn = b["block_no"]
    nn = f"{bn:02d}"
    title = f"{year}-{paper}-E{nn}"
    qrange = b.get("qno_range", "")
    qtype = b.get("qtype", "")
    genre = b.get("genre", "")
    aliases = [
        title,
        f"{year}{province}英语{paper}-E{nn}",
        f"{year}年{paper}英语第{bn}大题",
    ]
    if qrange:
        aliases.append(f"{year}年{paper}英语{qtype}{qrange}")
    tags = derive_tags(qtype, genre)
    summary = summary_of(b.get("solution_text", ""))

    q_imgs = b.get("题面图", []) or []
    a_imgs = b.get("解析图", []) or []

    fm = [
        "---",
        f"title: {title}",
        f"aliases: [{', '.join(aliases)}]",
        "学科: 英语",
        "学段: 高考",
        f"省份: {province}",
        f"年份: {year}",
        f"卷别: {paper}",
        "文理: 不分",
        f"大题号: {bn}",
        f"题号范围: {qrange}",
        f"题型: {qtype}",
        f"文体: {genre}",
        f"考点: [{', '.join(tags)}]",
        "难度: 中",
        f"PDF: {qa['source_pdf']}",
        f"PDF页码: {b.get('page', 0)}",
        f"题面图: [{', '.join(q_imgs)}]",
        f"解析图: [{', '.join(a_imgs)}]",
        f"答案: {b.get('answer', '')[:120]}",
        "录入状态: 已入库",
        "---",
        "",
    ]
    body = ["## 篇章题面", ""]
    for rel in q_imgs:
        body.append(f"![](../../{rel})")
    body += ["", "## 摘要", "", summary, "", "## 关联考点", ""]
    for t in tags:
        body.append(f"- [[{t}]]")
    body += ["", "## 答案", "", f"`{b.get('answer', '')[:300]}`",
             "", "## 解析", ""]
    for rel in a_imgs:
        body.append(f"![](../../{rel})")
    body += ["", f"> 📄 原 PDF 第 {b.get('page', 0)} 页：`{qa['source_pdf']}`", ""]
    return "\n".join(fm + body)


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", required=True)
    args = ap.parse_args()
    qa = json.loads(Path(args.blocks).read_text(encoding="utf-8"))

    out_dir = REPO_ROOT / "真题" / f"{qa['province']}-英语"
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    skipped = 0
    for b in qa["blocks"]:
        if b.get("skip_render"):
            skipped += 1
            continue
        nn = f"{b['block_no']:02d}"
        fp = out_dir / f"{qa['year']}-{qa['paper']}-E{nn}.md"
        fp.write_text(render_block(qa, b), encoding="utf-8")
        files.append(fp)
    print(f"OK: 渲染 {len(files)} 篇章词条到 真题/{qa['province']}-英语/"
          f"（跳过听力块 {skipped}）")

    from fix_wikilinks import canonicalize_files
    fixed, unresolved = canonicalize_files(files)
    if fixed:
        print(f"📎 规范化 {fixed} 条 wikilinks（unresolved: "
              f"{len(set(unresolved))} 唯一 tag）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
