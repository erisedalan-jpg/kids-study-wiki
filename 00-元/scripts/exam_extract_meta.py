"""真题元数据抽取（v2 Step 2）。

用 markitdown 把 PDF 转 markdown，然后正则抽取每题的 answer 文本 + 解析关键文本。
这些元数据用于 Step 3 (v4-pro 摘要+考点) 的输入。

不抓题面 stem —— 题面由 exam_screenshot.py 截图保真，markdown 只存元数据。

CLI:
    python 00-元/scripts/exam_extract_meta.py \\
        --questions docs/superpowers/working/吉林-数学-2022-文-全国乙-questions.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from markitdown import MarkItDown

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402


# 题号边界（同 v1 修复版）：1-9 开头，点后非数字（防小数误识别）
# 行首 或 紧跟 markdown 表格分隔符 `|`（markitdown 会把多列 PDF 题号包进 `| N. ...|`）
QNO_RE = re.compile(
    r"(?:^|\|)\s*([1-9]\d?)\s*[\.、．](?!\d)\s*",
    re.MULTILINE,
)
# 答案标签兼容 "【答案】" 和 "【 答 案 】"
ANSWER_TAG_RE = re.compile(r"【\s*答\s*案\s*】([^\n【]*)")
# 解析段
SOLUTION_TAG_RE = re.compile(r"【\s*解\s*析\s*】(.+)", re.DOTALL)

# 仅当 QNO marker 后 _ANSWER_LOOKAHEAD 字符内存在 【答案】 才视为真题（过滤说明节中的 "1. 答卷前..." 等）
_ANSWER_LOOKAHEAD = 1500


def split_by_question(md_text: str) -> dict[int, str]:
    """按题号切分 markdown，返回 {qno: chunk}。

    策略：
    1. 用 QNO_RE 收集所有 QNO 候选（含 `^N.` 与 ` |N.` 两种形态）。
    2. 仅保留后续 _ANSWER_LOOKAHEAD 字符内有 `【答案】` 的 QNO（过滤说明节伪题号）。
    3. 在文档顺序内找**最长严格上升子序列**（连续 slice），跳号容忍。
       这样可以越过顶部说明区的 [1,2,3] 残段，从真题区域 [1,2,3,...,N] 开始切。
    """
    matches = list(QNO_RE.finditer(md_text))
    ans_positions = [m.start() for m in ANSWER_TAG_RE.finditer(md_text)]

    valid: list = []
    for m in matches:
        pos = m.end()
        if any(pos <= a < pos + _ANSWER_LOOKAHEAD for a in ans_positions):
            valid.append(m)

    if not valid:
        return {}

    qnos = [int(m.group(1)) for m in valid]
    n = len(qnos)
    # 找最长 contiguous slice [i, j) 使 qnos[i..j-1] 严格上升
    best_start, best_end = 0, 1
    cur_start = 0
    for i in range(1, n):
        if qnos[i] > qnos[i - 1]:
            if i + 1 - cur_start > best_end - best_start:
                best_start, best_end = cur_start, i + 1
        else:
            cur_start = i
    selected = valid[best_start:best_end]
    selected_qnos = qnos[best_start:best_end]

    chunks: dict[int, str] = {}
    for k, (qno, m) in enumerate(zip(selected_qnos, selected)):
        body_start = m.end()
        body_end = (
            selected[k + 1].start() if k + 1 < len(selected) else len(md_text)
        )
        chunks[qno] = md_text[body_start:body_end].strip()
    return chunks


def extract_answer(chunk: str, max_len: int = 50) -> str:
    """从题 chunk 抽答案，截断到 max_len 字符。

    清洗 markdown 表格残片：当 markitdown 把答案塞进 `| ##0.3 | | | ... |`
    形式的表格时，去掉前导 `|`、`##`、以及尾部 `|     |     |`。
    """
    m = ANSWER_TAG_RE.search(chunk)
    if not m:
        return ""
    raw = m.group(1).strip()
    # 1) 去掉所有 markdown 表格分隔符 `|`
    if "|" in raw:
        cells = [c.strip() for c in raw.split("|") if c.strip()]
        # 取第一个非空 cell 作为答案候选
        raw = cells[0] if cells else ""
    # 2) 去掉 markitdown 偶发前缀 `##` (来自 heading marker 误转)
    raw = re.sub(r"^#+\s*", "", raw).strip()
    return raw[:max_len]


def extract_solution_text(chunk: str) -> str:
    """抽 chunk 中 【解析】之后的全部文本（含【分析】【详解】【小问】等）。"""
    m = SOLUTION_TAG_RE.search(chunk)
    if not m:
        return ""
    return m.group(1).strip()


def fallback_from_pdf_region(
    pdf_path: Path, missing_qnos: list[int], expected_max_qno: int = 25
) -> dict[int, str]:
    """markitdown 漏题降级：用 PyMuPDF 切片该题区域抽 raw text。

    可能含 CJK glyph 编码乱码（PDF 自定义字体导致），但至少给 v4-pro 一些
    上下文。返回 {qno: raw_text}（按 missing_qnos 子集）。
    """
    import fitz  # type: ignore
    from exam_screenshot import find_question_anchors  # noqa: E402

    if not missing_qnos:
        return {}
    out: dict[int, str] = {}
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        sys.stderr.write(f"⚠️  fallback fitz.open 失败: {e}\n")
        return {}
    try:
        # 跨页 running counter 找全部题号 anchor
        all_anchors: dict[int, tuple[int, dict]] = {}
        per_page_height: dict[int, float] = {}
        running = 1
        for pno, page in enumerate(doc):
            words = page.get_text("words")
            q_anchors = find_question_anchors(
                words, expected_max_qno, start_qno=running
            )
            per_page_height[pno] = page.rect.height
            for qno, info in q_anchors.items():
                all_anchors.setdefault(qno, (pno, info))
            if q_anchors:
                running = max(q_anchors.keys()) + 1

        sorted_qnos = sorted(all_anchors.keys())
        for i, qno in enumerate(sorted_qnos):
            if qno not in missing_qnos:
                continue
            pno, info = all_anchors[qno]
            page = doc[pno]
            y0 = info["y0"]
            # 下一题 y0 同页：到下一题；不同页/无下一题：到本页底部
            y1 = per_page_height[pno]
            if i + 1 < len(sorted_qnos):
                next_qno = sorted_qnos[i + 1]
                next_pno, next_info = all_anchors[next_qno]
                if next_pno == pno:
                    y1 = next_info["y0"]
            clip = fitz.Rect(0, y0, page.rect.width, y1)
            raw = page.get_text("text", clip=clip).strip()
            if raw:
                out[qno] = raw
    finally:
        doc.close()
    return out


def extract_meta(pdf_path: Path) -> dict[int, dict[str, str]]:
    """主入口：PDF → {qno: {"answer", "solution_text"}}"""
    md = MarkItDown()
    result = md.convert(str(pdf_path))
    text = result.text_content
    chunks = split_by_question(text)
    if chunks:
        max_qno = max(chunks.keys())
        if max_qno > len(chunks):
            missing = sorted(set(range(1, max_qno + 1)) - set(chunks.keys()))
            sys.stderr.write(
                f"⚠️  split_by_question: 题号不连续/丢弃 {len(missing)} 题: {missing[:20]}\n"
            )
    else:
        sys.stderr.write(
            f"⚠️  split_by_question: 未识别到任何题号（首题非 1 或全部不递增？）\n"
        )
    return {
        qno: {
            "answer": extract_answer(chunk),
            "solution_text": extract_solution_text(chunk),
        }
        for qno, chunk in chunks.items()
    }


def assert_meta_quality(qa: dict[str, Any]) -> list[str]:
    """L1 自动断言: 每题 answer 非空 / solution_text 长度 > 30 / answer ≤ 50."""
    violations: list[str] = []
    for q in qa["questions"]:
        qno = q["qno"]
        ans = q.get("answer", "")
        sol = q.get("solution_text", "")
        if not ans:
            violations.append(f"Q{qno}: answer 为空")
        if len(ans) > 50:
            violations.append(f"Q{qno}: answer 超长 ({len(ans)} > 50)")
        if len(sol) < 30:
            violations.append(f"Q{qno}: solution_text 过短 ({len(sol)} < 30)")
    return violations


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    args = ap.parse_args()

    qa_path = Path(args.questions)
    qa = json.loads(qa_path.read_text(encoding="utf-8"))

    # 校验 source_pdf 字段
    if "source_pdf" not in qa:
        print(
            f"ERROR: questions.json 缺 source_pdf 字段: {qa_path}",
            file=sys.stderr,
        )
        return 1

    pdf_path = REPO_ROOT / qa["source_pdf"]
    if not pdf_path.exists():
        print(f"ERROR: PDF 不存在: {pdf_path}", file=sys.stderr)
        return 1

    # markitdown 转换可能抛 FileNotFoundError / 解析异常等
    try:
        meta = extract_meta(pdf_path)
    except Exception as e:
        print(
            f"ERROR: markitdown 转换失败 {pdf_path.name}: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 1

    # 合并到 questions.json
    for q in qa["questions"]:
        m = meta.get(q["qno"], {})
        q["answer"] = m.get("answer", "")
        q["solution_text"] = m.get("solution_text", "")

    # 降级：markitdown 漏题用 fitz 切片该题区域作 solution_text 兜底
    missing_qnos = [
        q["qno"] for q in qa["questions"]
        if not q.get("solution_text") or len(q.get("solution_text", "")) < 30
    ]
    if missing_qnos:
        print(
            f"⚠️  markitdown 漏 {len(missing_qnos)} 题，尝试 fitz fallback: "
            f"{missing_qnos[:10]}{'...' if len(missing_qnos) > 10 else ''}",
            file=sys.stderr,
        )
        fallback = fallback_from_pdf_region(pdf_path, missing_qnos)
        for q in qa["questions"]:
            if q["qno"] in fallback:
                q["solution_text"] = fallback[q["qno"]]
        recovered = sum(1 for qno in missing_qnos if qno in fallback)
        print(
            f"   fitz fallback 找回 {recovered}/{len(missing_qnos)} 题 raw text",
            file=sys.stderr,
        )

    violations = assert_meta_quality(qa)
    if violations:
        print("L1 断言失败:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        # 不直接 fail，存疑题在后续 LLM 步骤中可能仍能 enrich

    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: 提取 {len(meta)} 题元数据 → {qa_path}")
    print(f"L1 违规: {len(violations)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
