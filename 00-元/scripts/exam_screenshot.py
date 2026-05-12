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
    """根据题号+答案 anchor 算每题的截图区域。

    返回 {qno: {"q": region_or_None, "a": region_or_None}}
    region = {"x0": 0, "y0": float, "x1": page_width, "y1": float}

    策略:
    - 题面 region: y0=题号 y0, y1=该题对应 answer anchor 的 y0 (若有)，否则下一题题号 y0
    - 解析 region: y0=answer y0, y1=下一题题号 y0（若无下一题用 page_height）
    """
    sorted_qnos = sorted(q_anchors.keys())
    regions: dict[int, dict] = {}
    for i, qno in enumerate(sorted_qnos):
        q_y0 = q_anchors[qno]["y0"]
        next_q_y0 = (
            q_anchors[sorted_qnos[i + 1]]["y0"]
            if i + 1 < len(sorted_qnos)
            else page_height
        )
        # 找该题区间内第一个 answer anchor
        a_in_range = next(
            (a for a in a_anchors if q_y0 < a["y0"] < next_q_y0), None
        )
        if a_in_range:
            q_region = {"y0": q_y0, "y1": a_in_range["y0"]}
            a_region = {"y0": a_in_range["y0"], "y1": next_q_y0}
        else:
            q_region = {"y0": q_y0, "y1": next_q_y0}
            a_region = None
        regions[qno] = {"q": q_region, "a": a_region}
    return regions
