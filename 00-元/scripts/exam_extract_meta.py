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
QNO_RE = re.compile(r"^\s*([1-9]\d?)\s*[\.、．](?!\d)\s*", re.MULTILINE)
# 答案标签兼容 "【答案】" 和 "【 答 案 】"
ANSWER_TAG_RE = re.compile(r"【\s*答\s*案\s*】([^\n【]*)")
# 解析段
SOLUTION_TAG_RE = re.compile(r"【\s*解\s*析\s*】(.+)", re.DOTALL)


def split_by_question(md_text: str) -> dict[int, str]:
    """按题号切分 markdown，返回 {qno: chunk}。

    题号递增约束：从 1 开始，跳号忽略。
    """
    matches = list(QNO_RE.finditer(md_text))
    chunks: dict[int, str] = {}
    accepted_qnos: list[int] = []
    for i, m in enumerate(matches):
        qno = int(m.group(1))
        if accepted_qnos and qno != accepted_qnos[-1] + 1:
            continue
        if not accepted_qnos and qno != 1:
            continue
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        chunks[qno] = md_text[body_start:body_end].strip()
        accepted_qnos.append(qno)
    return chunks


def extract_answer(chunk: str, max_len: int = 50) -> str:
    """从题 chunk 抽答案，截断到 max_len 字符。"""
    m = ANSWER_TAG_RE.search(chunk)
    if not m:
        return ""
    return m.group(1).strip()[:max_len]


def extract_solution_text(chunk: str) -> str:
    """抽 chunk 中 【解析】之后的全部文本（含【分析】【详解】【小问】等）。"""
    m = SOLUTION_TAG_RE.search(chunk)
    if not m:
        return ""
    return m.group(1).strip()


def extract_meta(pdf_path: Path) -> dict[int, dict[str, str]]:
    """主入口：PDF → {qno: {"answer", "solution_text"}}"""
    md = MarkItDown()
    result = md.convert(str(pdf_path))
    text = result.text_content
    chunks = split_by_question(text)
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
    pdf_path = REPO_ROOT / qa["source_pdf"]
    meta = extract_meta(pdf_path)

    # 合并到 questions.json
    for q in qa["questions"]:
        m = meta.get(q["qno"], {})
        q["answer"] = m.get("answer", "")
        q["solution_text"] = m.get("solution_text", "")

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
