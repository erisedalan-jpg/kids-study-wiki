"""真题词条渲染器。

输入: 题块 JSON（包含 LLM 终审后的 tags / gap_terms / difficulty 字段）
输出: 真题/<省份>-<学科>/YYYY-*-NN.md

用法:
    python 00-元/scripts/render_exam_atoms.py \
        --questions docs/superpowers/working/吉林-数学-2024-不分-新课标Ⅱ-questions.json
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


def _atom_text(qa_meta: dict[str, Any], q: dict[str, Any]) -> str:
    """单题词条 markdown 文本。"""
    year = qa_meta["year"]
    gender = qa_meta["gender"]
    paper = qa_meta["paper"]
    qno = q["qno"]
    nn = f"{qno:02d}"
    title = build_atom_filename(year, gender, paper, qno).removesuffix(".md")
    aliases = [
        title,
        f"{year}{qa_meta['province']}{qa_meta['subject']}{paper}-{nn}",
        f"{year}年{paper}{qa_meta['subject']}第{qno}题",
    ]
    tags = q.get("tags", [])
    state = "已入库" if tags else "待人工核对"
    body_lines = [
        "---",
        f"title: {title}",
        f"aliases: [{', '.join(aliases)}]",
        f"学科: {qa_meta['subject']}",
        "学段: 高考",
        f"省份: {qa_meta['province']}",
        f"年份: {year}",
        f"卷别: {paper}",
        f"文理: {gender}",
        f"题号: {qno}",
        f"题型: {q['qtype']}",
        f"分值: {q['score']}",
        f"考点: [{', '.join(tags)}]",
        f"难度: {q.get('difficulty', '中')}",
        f"录入状态: {state}",
        f"来源PDF: {qa_meta['source_pdf']}",
        "---",
        "",
        "## 题面",
        "",
        q["stem"],
        "",
        "## 标准解答",
        "",
        f"**答案**: {q.get('answer', '（待补）')}",
        "",
        q.get("solution", "（待补）"),
        "",
        "## 关联知识点",
        "",
    ]
    for t in tags:
        body_lines.append(f"- [[{t}]]")
    if q.get("gap_terms"):
        body_lines += ["", "## 白名单缺口（待考虑建词条）"]
        for g in q["gap_terms"]:
            body_lines.append(f"- {g}")
    body_lines.append("")
    return "\n".join(body_lines)


def render_paper(qa: dict[str, Any], output_root: Path) -> list[Path]:
    """渲染整张卷为真题词条 .md 文件列表。"""
    out_dir = output_root / f"{qa['province']}-{qa['subject']}"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for q in qa["questions"]:
        fname = build_atom_filename(qa["year"], qa["gender"], qa["paper"], q["qno"])
        path = out_dir / fname
        path.write_text(_atom_text(qa, q), encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    ap.add_argument("--output-root", default="真题/")
    args = ap.parse_args()

    qa = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    out_root = REPO_ROOT / args.output_root
    files = render_paper(qa, out_root)
    print(f"OK: 渲染 {len(files)} 个真题词条到 {out_root}/{qa['province']}-{qa['subject']}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
