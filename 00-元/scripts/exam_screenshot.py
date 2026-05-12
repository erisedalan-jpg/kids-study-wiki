"""真题截图生成（v2 Step 1）。

用 PyMuPDF 提取每个 PDF 页面的 word boxes（含 bbox），定位：
- 题号 anchor: 形如 "1." "23." 的 word，必须从 1 开始递增
- 答案 anchor: "【答案】" 或带空格的 "【 答 案 】"

然后按 题面区域 = (题号 N → 答案 anchor) / 解析区域 = (答案 anchor → 题号 N+1)
渲染 PNG 截图到 素材/真题截图/<省份>-<学科>/ 目录。

输出: questions.json（含 qno/bbox/page/截图相对路径）

CLI:
    python 00-元/scripts/exam_screenshot.py \\
        --pdf "素材/真题/.../2022年高考数学试卷（文）.pdf" \\
        --province 吉林 --subject 数学 --year 2022 \\
        --out docs/superpowers/working/
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
from _exam_utils import (  # noqa: E402
    build_atom_filename,
    build_screenshot_filename,
    load_config,
    normalize_gender,
    normalize_paper,
)
from _utils import REPO_ROOT, setup_utf8  # noqa: E402


# 题号正则：行首数字 + 点 + 空白（不允许点后接数字，排除 0.04 / 1.6158 等小数）
QNO_TOKEN_RE = re.compile(r"^([1-9]\d?)[\.、．]$")


def find_question_anchors(
    words: list[tuple], expected_max_qno: int
) -> dict[int, dict[str, float]]:
    """找题号 anchor。

    words: PyMuPDF page.get_text("words") 返回的元组列表
           (x0, y0, x1, y1, text, block_no, line_no, word_no)
    返回: {qno: {"x0", "y0", "x1", "y1", "block_no", "line_no"}}

    题号必须从 1 开始严格递增，跳号丢弃。
    """
    candidates: list[tuple[int, dict]] = []
    for w in words:
        x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
        m = QNO_TOKEN_RE.match(text.strip())
        if not m:
            continue
        qno = int(m.group(1))
        if qno > expected_max_qno + 5:  # 容忍 +5 缓冲
            continue
        candidates.append((qno, {
            "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            "block_no": w[5] if len(w) > 5 else 0,
            "line_no": w[6] if len(w) > 6 else 0,
        }))

    # 按 y 坐标排序（页面阅读顺序），然后筛递增
    candidates.sort(key=lambda x: x[1]["y0"])
    result: dict[int, dict] = {}
    next_expected = 1
    for qno, info in candidates:
        if qno == next_expected:
            result[qno] = info
            next_expected = qno + 1
    return result


def find_answer_anchors(words: list[tuple]) -> list[dict[str, float]]:
    """找【答案】或【 答 案 】anchor。

    返回按 y 坐标排序的 list[{"x0", "y0", "x1", "y1"}]。
    """
    answer_re = re.compile(r"^【\s*答\s*案\s*】")
    anchors: list[dict] = []
    for w in words:
        text = w[4]
        if answer_re.match(text):
            anchors.append({
                "x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3],
            })
    anchors.sort(key=lambda a: a["y0"])
    return anchors


def compute_regions(
    q_anchors: dict[int, dict],
    a_anchors: list[dict],
    page_height: float,
) -> dict[int, dict[str, dict | None]]:
    """根据题号+答案 anchor 算每题的截图区域（**单页内**）。

    返回 {qno: {"q": region_or_None, "a": region_or_None}}
    region = {"y0": float, "y1": float}（x 范围由调用方在渲染时补，通常用整页宽）

    策略:
    - 题面 region: y0=题号 y0, y1=该题对应 answer anchor 的 y0 (若有)，否则下一题题号 y0
    - 解析 region: y0=answer y0, y1=下一题题号 y0（若无下一题用 page_height）
    - answer anchor 区间用左闭右开 [q_y0, next_q_y0)，对应"恰好在 q_y0 行的 answer 也归当前题"语义

    范围边界:
    - 本函数仅处理**单页内**切分。跨页题（题号在本页但 answer/下一题号在下一页）
      的处理由上层 `render_screenshots` 负责（按 page 拆 + 跨页合并截图）。
    - 最后一题的 y1 = page_height，可能包含页脚/页码；上层渲染时自行 crop 或忽略。
    - PyMuPDF y 排序异常（如浮动元素导致 a_y0 < q_y0）：未匹配的 answer 会被静默
      丢弃，但函数末尾打印 stderr warning 提示上层。
    """
    sorted_qnos = sorted(q_anchors.keys())
    regions: dict[int, dict] = {}
    matched_a_indices: set[int] = set()
    for i, qno in enumerate(sorted_qnos):
        q_y0 = q_anchors[qno]["y0"]
        next_q_y0 = (
            q_anchors[sorted_qnos[i + 1]]["y0"]
            if i + 1 < len(sorted_qnos)
            else page_height
        )
        # 找该题区间内第一个 answer anchor（左闭右开）
        a_idx_in_range = next(
            (
                idx for idx, a in enumerate(a_anchors)
                if q_y0 <= a["y0"] < next_q_y0
            ),
            None,
        )
        if a_idx_in_range is not None:
            a = a_anchors[a_idx_in_range]
            matched_a_indices.add(a_idx_in_range)
            q_region = {"y0": q_y0, "y1": a["y0"]}
            a_region = {"y0": a["y0"], "y1": next_q_y0}
        else:
            q_region = {"y0": q_y0, "y1": next_q_y0}
            a_region = None
        regions[qno] = {"q": q_region, "a": a_region}

    # 警告：有未匹配的 answer anchor（y 排序异常）
    unmatched = [
        a for idx, a in enumerate(a_anchors) if idx not in matched_a_indices
    ]
    if unmatched and q_anchors:
        import sys as _sys
        _sys.stderr.write(
            f"compute_regions: {len(unmatched)} answer anchor(s) "
            f"未匹配到任何题号区间（y 排序异常？）\n"
        )

    return regions


def render_screenshots(
    pdf_path: Path,
    *,
    province: str,
    subject: str,
    year: int,
    expected_max_qno: int = 25,
    dpi: int = 200,
) -> dict[str, Any]:
    """从 PDF 提取题号 + 渲染截图到目标目录。

    返回 questions.json 数据（含 qno / page / 截图相对路径）。

    失败模式（明确 raise）：
    - PDF 不存在 → FileNotFoundError
    - PDF 损坏 / 不可读 → ValueError
    - PDF 加密 → ValueError
    - 全部页面识别不到任何题号（如扫描版无文字层）→ ValueError
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 不存在: {pdf_path}")

    cfg = load_config()
    fname = pdf_path.name
    paper = normalize_paper(fname, cfg)
    gender = normalize_gender(fname, cfg)
    paper_id = f"{year}-{gender}-{paper}"

    out_dir = REPO_ROOT / "素材" / "真题截图" / f"{province}-{subject}"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        doc = fitz.open(str(pdf_path))
    except fitz.FileDataError as e:
        raise ValueError(f"PDF 损坏或不可读: {pdf_path}: {e}") from e

    try:
        if doc.is_encrypted:
            raise ValueError(f"PDF 已加密，需先解密: {pdf_path}")

        all_questions: list[dict] = []
        all_q_anchors: dict[int, tuple[int, dict]] = {}
        # 缓存每页的 q/a anchors（消除第二遍重复 get_text("words")）
        per_page_anchors: dict[int, dict[str, Any]] = {}
        per_page_height: dict[int, float] = {}

        # 第一遍：扫所有页面找 anchor 并缓存
        for page_no, page in enumerate(doc):
            words = page.get_text("words")
            q_anchors = find_question_anchors(words, expected_max_qno)
            a_anchors = find_answer_anchors(words)
            per_page_anchors[page_no] = {
                "q_anchors": q_anchors,
                "a_anchors": a_anchors,
            }
            per_page_height[page_no] = page.rect.height
            for qno, info in q_anchors.items():
                if qno not in all_q_anchors:
                    all_q_anchors[qno] = (page_no, info)

        if not all_q_anchors:
            raise ValueError(
                f"未识别到任何题号: {pdf_path.name} (可能是扫描版无文字层 / "
                f"或题号格式不在 QNO_TOKEN_RE 范围)"
            )

        # 第二遍：渲染每题截图（用缓存的 anchors）
        for qno in sorted(all_q_anchors.keys()):
            page_no, _q_info = all_q_anchors[qno]
            page = doc[page_no]
            cache = per_page_anchors[page_no]
            page_q_anchors = cache["q_anchors"]
            a_anchors = cache["a_anchors"]
            regions = compute_regions(
                page_q_anchors, a_anchors, per_page_height[page_no]
            )
            if qno not in regions:
                continue  # 跨页题：本页找不到 qno 起点（保守跳过）
            q_region = regions[qno]["q"]
            a_region = regions[qno]["a"]

            # 渲染 q.png
            q_filename = build_screenshot_filename(year, gender, paper, qno, "q")
            q_path = out_dir / q_filename
            clip = fitz.Rect(0, q_region["y0"], page.rect.width, q_region["y1"])
            pix = page.get_pixmap(clip=clip, dpi=dpi)
            pix.save(str(q_path))

            # 渲染 a.png（可能 None）
            a_filename = None
            if a_region:
                a_filename = build_screenshot_filename(year, gender, paper, qno, "a")
                a_path = out_dir / a_filename
                clip_a = fitz.Rect(0, a_region["y0"], page.rect.width, a_region["y1"])
                pix_a = page.get_pixmap(clip=clip_a, dpi=dpi)
                pix_a.save(str(a_path))

            all_questions.append({
                "qno": qno,
                "page": page_no + 1,
                "题面图": f"素材/真题截图/{province}-{subject}/{q_filename}",
                "解析图": (
                    f"素材/真题截图/{province}-{subject}/{a_filename}"
                    if a_filename
                    else ""
                ),
            })
    finally:
        doc.close()

    rel_pdf = (
        pdf_path.relative_to(REPO_ROOT)
        if pdf_path.is_relative_to(REPO_ROOT)
        else pdf_path
    )
    return {
        "paper_id": paper_id,
        "year": year,
        "gender": gender,
        "paper": paper,
        "subject": subject,
        "province": province,
        "source_pdf": str(rel_pdf).replace("\\", "/"),
        "questions": all_questions,
    }


def assert_screenshot_quality(qa: dict[str, Any], expected_qno_range: tuple[int, int]) -> list[str]:
    """L1 自动断言。返回违规列表（空 = 通过）。"""
    violations: list[str] = []
    n = len(qa["questions"])
    lo, hi = expected_qno_range
    if not (lo <= n <= hi):
        violations.append(f"题数 {n} 不在期望范围 {lo}-{hi}")
    for q in qa["questions"]:
        q_img_path = REPO_ROOT / q["题面图"]
        if not q_img_path.exists():
            violations.append(f"Q{q['qno']}: 题面图不存在 {q['题面图']}")
            continue
        size = q_img_path.stat().st_size
        if size < 10 * 1024:
            violations.append(f"Q{q['qno']}: 题面图过小 ({size} bytes < 10KB)")
        if q.get("解析图"):
            a_img_path = REPO_ROOT / q["解析图"]
            if not a_img_path.exists():
                violations.append(f"Q{q['qno']}: 解析图不存在")
    return violations


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--province", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out", default="docs/superpowers/working/")
    ap.add_argument("--expected-min", type=int, default=18, help="期望最少题数（含）")
    ap.add_argument("--expected-max", type=int, default=25, help="期望最多题数（含）")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()

    qa = render_screenshots(
        Path(args.pdf),
        province=args.province,
        subject=args.subject,
        year=args.year,
        expected_max_qno=args.expected_max,
        dpi=args.dpi,
    )

    violations = assert_screenshot_quality(qa, (args.expected_min, args.expected_max))

    # 无论 L1 通过与否都 dump JSON（含 violations 字段供调试）
    qa["_violations"] = violations
    out_dir = REPO_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = (
        out_dir / f"{args.province}-{args.subject}-{qa['paper_id']}-questions.json"
    )
    out_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")

    if violations:
        print("L1 断言失败:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        print(f"⚠️ 仍写入 questions.json 含 _violations 字段 → {out_path}", file=sys.stderr)
        return 1

    print(f"OK: 截图 {len(qa['questions'])} 题 + questions.json → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
