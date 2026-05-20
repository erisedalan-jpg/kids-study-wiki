"""英语真题截图（专用管线，篇章/大题级）。

英语结构性不同于数理化：【答案】按大题分组聚合（一篇阅读 5 小题共一块
【答案】），篇章共享题干。故锚点用【答案】块而非题号。

切分（交错式结构 [篇章+小题]→【答案】【解析】【导语】→下一大题）：
- 块 i 题面区 = ans[i-1] 末 → ans[i] 前（本大题篇章+小题；块0从正文起）
- 块 i 解析区 = ans[i] → ans[i+1] 前（本块【答案】+【解析】+【导语】）
每块 = 1 篇章单元 → 1 md。qno_range 从块内 `N.` 题号推断。

CLI:
    python 00-元/scripts/exam_eng_screenshot.py \\
        --pdf "素材/真题/北京/...英语...解析卷.pdf" \\
        --province 北京 --year 2024
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402
from _exam_utils import load_config, normalize_paper  # noqa: E402

# 仅锚【答案】（不含【解析】，块内【解析】不作块边界）
ANS_RE = re.compile(r"【\s*答\s*案\s*】")
# 块内题号（行内 N. / N． / N、），用于推断 qno_range
QNO_IN = re.compile(r"(?<!\d)(\d{1,2})\s*[\.．、]")
# 页眉页脚噪声行（截图 y 过滤无关，仅文本推断时剔除）
NOISE_LINE = re.compile(r"第\s*\d+\s*页|共\s*\d+\s*页|学科网|股份有限公司")


def collect_answer_anchors(doc) -> list[tuple[int, float]]:
    """跨页收集所有【答案】位置，按 (page, y0) 排序。"""
    anchors: list[tuple[int, float]] = []
    for pno, page in enumerate(doc):
        for w in page.get_text("words"):
            if ANS_RE.match(w[4].strip()):
                anchors.append((pno, w[1]))
    anchors.sort()
    return anchors


def page_text_between(doc, p0, y0, p1, y1) -> str:
    """提取 (p0,y0)→(p1,y1) 区间文本（用于推断 qno_range / 题型）。"""
    out = []
    for p in range(p0, p1 + 1):
        page = doc[p]
        clip_y0 = y0 if p == p0 else 0.0
        clip_y1 = y1 if p == p1 else page.rect.height
        if clip_y1 - clip_y0 < 2:
            continue
        rect = fitz.Rect(0, clip_y0, page.rect.width, clip_y1)
        out.append(page.get_text("text", clip=rect))
    return "\n".join(out)


def render_clip_series(doc, pages, out_dir, province, year, paper, block_no, kind, dpi):
    """pages: list[(p, y0, y1)] → 渲染 PNG 多图，返回相对路径列表。

    命名 `{year}-{paper}-E{NN}.{kind}[.pN].png`：含年份+卷别防多年份块号互覆
    （原裸号 `{NN}.{kind}.png` 末次写盘覆盖前次，致 md 图片无法展示）。
    """
    rels: list[str] = []
    paper_safe = paper.replace("/", "_").replace("\\", "_") or "未知"
    for idx, (p, y0, y1) in enumerate(pages):
        if y1 - y0 < 5:
            continue
        suffix = "" if idx == 0 else f".p{idx + 1}"
        fname = f"{year}-{paper_safe}-E{block_no:02d}.{kind}{suffix}.png"
        out_path = out_dir / fname
        clip = fitz.Rect(0, y0, doc[p].rect.width, y1)
        doc[p].get_pixmap(clip=clip, dpi=dpi).save(str(out_path))
        rels.append(f"素材/真题截图/{province}-英语/{fname}")
    return rels


def span_pages(p0, y0, p1, y1, per_h) -> list[tuple[int, float, float]]:
    """把 (p0,y0)→(p1,y1) 拆成逐页 [(p,y0,y1)]。"""
    if p0 == p1:
        return [(p0, y0, y1)]
    out = [(p0, y0, per_h[p0])]
    for p in range(p0 + 1, p1):
        out.append((p, 0.0, per_h[p]))
    if y1 > 0:
        out.append((p1, 0.0, y1))
    return out


def build(pdf_path: Path, province: str, year: int, dpi: int = 200) -> dict[str, Any]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 不存在: {pdf_path}")
    cfg = load_config()
    paper = normalize_paper(pdf_path.name, cfg)
    doc = fitz.open(str(pdf_path))
    try:
        per_h = {p: doc[p].rect.height for p in range(len(doc))}
        anchors = collect_answer_anchors(doc)
        if not anchors:
            raise ValueError(
                f"未找到任何【答案】锚点: {pdf_path.name}（非标准解析卷？）"
            )
        out_dir = REPO_ROOT / "素材" / "真题截图" / f"{province}-英语"
        out_dir.mkdir(parents=True, exist_ok=True)

        n = len(anchors)
        blocks: list[dict[str, Any]] = []
        for i in range(n):
            a_p, a_y = anchors[i]
            # 题面区: 上块【答案】末 → 本块【答案】前（块0 从正文首页起）
            if i == 0:
                q_p0, q_y0 = 0, 0.0
            else:
                q_p0, q_y0 = anchors[i - 1]
            q_p1, q_y1 = a_p, a_y
            # 解析区: 本块【答案】 → 下块【答案】前（末块到 PDF 尾）
            if i + 1 < n:
                s_p1, s_y1 = anchors[i + 1]
            else:
                s_p1, s_y1 = len(doc) - 1, per_h[len(doc) - 1]

            q_pages = span_pages(q_p0, q_y0, q_p1, q_y1, per_h)
            s_pages = span_pages(a_p, a_y, s_p1, s_y1, per_h)

            block_no = i + 1
            q_imgs = render_clip_series(doc, q_pages, out_dir, province, year, paper, block_no, "q", dpi)
            s_imgs = render_clip_series(doc, s_pages, out_dir, province, year, paper, block_no, "a", dpi)

            # qno_range：仅取【答案】→ 块内首个【解析】前的纯聚合答案区
            # （整解析区会含下块篇章题面致题号串入，必须截断在【解析】）
            sol_txt = page_text_between(doc, a_p, a_y, s_p1, s_y1)
            ans_only = re.split(r"【\s*解\s*析\s*】", sol_txt, maxsplit=1)[0]
            qnos = [
                int(m.group(1)) for ln in ans_only.splitlines()
                if not NOISE_LINE.search(ln)
                for m in QNO_IN.finditer(ln.strip())
                if 1 <= int(m.group(1)) <= 60
            ]
            qnos = sorted(set(qnos))
            qrange = f"{qnos[0]}-{qnos[-1]}" if len(qnos) >= 2 else (
                str(qnos[0]) if qnos else "")

            sol_parts = re.split(r"【\s*解\s*析\s*】", sol_txt, maxsplit=1)
            raw_ans = sol_parts[0].strip()
            raw_sol = sol_parts[1].strip() if len(sol_parts) > 1 else ""
            blocks.append({
                "block_no": block_no,
                "qno_range": qrange,
                "qnos": qnos,
                "题面图": q_imgs,
                "解析图": s_imgs,
                "page": a_p + 1,
                "raw_ans": raw_ans[:1200],
                "raw_sol": raw_sol[:2500],
            })
    finally:
        doc.close()

    rel_pdf = (pdf_path.relative_to(REPO_ROOT)
               if pdf_path.is_relative_to(REPO_ROOT) else pdf_path)
    return {
        "paper_id": f"{year}-不分-{paper}",
        "year": year,
        "gender": "不分",
        "paper": paper,
        "subject": "英语",
        "province": province,
        "source_pdf": str(rel_pdf).replace("\\", "/"),
        "blocks": blocks,
    }


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--province", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out", default="docs/superpowers/working/")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.is_absolute():
        pdf_path = REPO_ROOT / pdf_path
    qa = build(pdf_path, args.province, args.year, args.dpi)
    out_dir = REPO_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.province}-英语-{qa['paper_id']}-blocks.json"
    out_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(qa['blocks'])} 块截图 + blocks.json → {out_path}")
    for b in qa["blocks"]:
        print(f"  块{b['block_no']:>2} qno={b['qno_range']:<8} "
              f"q图={len(b['题面图'])} a图={len(b['解析图'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
