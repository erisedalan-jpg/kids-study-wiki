"""v2 词条渲染（Step 4）。

输入: questions.json (含 enrich 后的全部字段)
输出: 真题/<省份>-<学科>/*.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _exam_utils import build_atom_filename  # noqa: E402
from _utils import REPO_ROOT, setup_utf8  # noqa: E402


def _as_list(v: Any) -> list[str]:
    """兼容 题面图/解析图 字段为 str (旧) 或 list (新)。"""
    if not v:
        return []
    if isinstance(v, str):
        return [v]
    return [s for s in v if s]


def _fm_list(v: Any) -> str:
    """frontmatter 输出 list 形式 `[a, b]`，空时输出 `[]`。"""
    items = _as_list(v)
    return "[" + ", ".join(items) + "]"


# 题型按题号 + 总题数启发式（沿用 v1）
def classify_qtype(qno: int, total: int) -> str:
    if total <= 20:
        if qno <= 11:
            return "选择"
        if qno <= 14:
            return "填空"
        return "解答"
    if qno <= 12:
        return "选择"
    if qno <= 16:
        return "填空"
    return "解答"


def classify_score(qno: int, qtype: str, year: int, total: int) -> int:
    """分值按年份+总题数表查（沿用 v1 修复）。"""
    if qtype in ("选择", "填空"):
        return 5
    if total == 19 and qno == 19:
        return 17
    if total == 23 and qno >= 22:
        return 10  # 2022 全国乙 选做题
    return 12


def render_atom(qa_meta: dict[str, Any], q: dict[str, Any]) -> str:
    """渲染单题 markdown。"""
    year = qa_meta["year"]
    gender = qa_meta["gender"]
    paper = qa_meta["paper"]
    subject = qa_meta["subject"]
    province = qa_meta["province"]
    qno = q["qno"]
    nn = f"{qno:02d}"
    total_q = qa_meta.get("total_q", 23)

    title = build_atom_filename(year, gender, paper, qno).removesuffix(".md")
    aliases = [
        title,
        f"{year}{province}{subject}{paper}-{nn}",
        f"{year}年{paper}{subject}第{qno}题",
    ]
    qtype = classify_qtype(qno, total_q)
    score = classify_score(qno, qtype, year, total_q)

    tags = q.get("tags", [])
    state = "已入库" if tags else "待人工核对"

    fm_lines = [
        "---",
        f"title: {title}",
        f"aliases: [{', '.join(aliases)}]",
        f"学科: {subject}",
        "学段: 高考",
        f"省份: {province}",
        f"年份: {year}",
        f"卷别: {paper}",
        f"文理: {gender}",
        f"题号: {qno}",
        f"题型: {qtype}",
        f"分值: {score}",
        f"考点: [{', '.join(tags)}]",
        f"难度: {q.get('difficulty', '中')}",
        f"PDF: {qa_meta['source_pdf']}",
        f"PDF页码: {q.get('page', 0)}",
        f"题面图: {_fm_list(q.get('题面图'))}",
        f"解析图: {_fm_list(q.get('解析图'))}",
        f"答案: {q.get('answer', '')}",
        f"录入状态: {state}",
        "---",
        "",
    ]

    # 截图路径用相对路径（从 真题/<province>-<subject>/ 到 素材/...，两级 ../）
    q_imgs = _as_list(q.get("题面图"))
    a_imgs = _as_list(q.get("解析图"))

    body_lines = ["## 题面", ""]
    for rel in q_imgs:
        body_lines.append(f"![](../../{rel})")
    body_lines += [
        "",
        "## 摘要",
        "",
        q.get("summary", "（待补）"),
        "",
        "## 关联考点",
        "",
    ]
    for tag in tags:
        body_lines.append(f"- [[{tag}]]")
    body_lines += ["", "## 答案与解析", ""]
    for rel in a_imgs:
        body_lines.append(f"![](../../{rel})")
    if a_imgs:
        body_lines.append("")
    body_lines += [
        f"> 📄 原 PDF 第 {q.get('page', 0)} 页：`{qa_meta['source_pdf']}`",
        "",
    ]
    return "\n".join(fm_lines + body_lines)


def render_paper(qa: dict[str, Any]) -> list[Path]:
    """渲染整张卷的所有题。"""
    out_dir = REPO_ROOT / "真题" / f"{qa['province']}-{qa['subject']}"
    out_dir.mkdir(parents=True, exist_ok=True)
    qa_meta = dict(qa)
    qa_meta["total_q"] = len(qa["questions"])

    written: list[Path] = []
    for q in qa["questions"]:
        fname = build_atom_filename(qa["year"], qa["gender"], qa["paper"], q["qno"])
        path = out_dir / fname
        path.write_text(render_atom(qa_meta, q), encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    args = ap.parse_args()

    qa = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    files = render_paper(qa)
    print(f"OK: 渲染 {len(files)} 题词条到 真题/{qa['province']}-{qa['subject']}/")
    # 规范化新生成词条中的 [[X]] 链接（Obsidian 跳转兼容，详见 fix_wikilinks.py）
    from fix_wikilinks import canonicalize_files
    fixed, unresolved = canonicalize_files(files)
    if fixed:
        uniq = len(set(unresolved))
        print(f"📎 规范化 {fixed} 条 wikilinks（unresolved: {uniq} 唯一 tag）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
