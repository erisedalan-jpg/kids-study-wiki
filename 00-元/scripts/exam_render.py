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
        f"题面图: {q.get('题面图', '')}",
        f"解析图: {q.get('解析图', '')}",
        f"答案: {q.get('answer', '')}",
        f"录入状态: {state}",
        "---",
        "",
    ]

    # 截图路径用相对路径（从 真题/<province>-<subject>/ 到 素材/...，两级 ../）
    q_img_rel = "../../" + q.get("题面图", "")
    a_img_rel = "../../" + q.get("解析图", "") if q.get("解析图") else ""

    body_lines = [
        "## 题面",
        "",
        f"![]({q_img_rel})",
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
    body_lines += [
        "",
        "## 答案与解析",
        "",
    ]
    if a_img_rel:
        body_lines += [f"![]({a_img_rel})", ""]
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
