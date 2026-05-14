"""v4-pro 摘要 + 考点 + 难度抽取（v2 Step 3）。

输入: questions.json (含 solution_text)
输出: 每题加 summary / tags / difficulty 字段

LLM prompt 设计（按多模型工作流 v3）：v4-pro + system message + t=0.3
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _llm_router import LLMError, Task, call  # noqa: E402
from _utils import setup_utf8  # noqa: E402


def _make_system(subject: str) -> str:
    return (
        f"你是高考{subject}题考点标注员。"
        "回答必须简短直接，不展开推理过程，严格按指定格式输出。"
        "禁止输出 '无' / '非XX题' / '无XX考点' 等无意义占位 tag — "
        "若解析文本不足以判断考点，输出空。"
    )


def _make_prompt(subject: str, solution_text: str) -> str:
    return f"""任务：阅读高考{subject}题的解析文本，输出该题的摘要 + 考点 + 难度。

[解析文本]
{solution_text}

按下面三行格式输出，不要额外内容:
第一行: 1-2 句话简述该题考查内容（不超过 50 字）
第二行: 逗号分隔的 2-4 个核心{subject}考点术语（禁止 '无' / '非XX' / '无XX考点' 等占位）
第三行: 易 或 中 或 难
"""


# 兼容老代码 (test_exam_enrich 用)
SYSTEM_PROMPT = _make_system("数学")
PROMPT_TEMPLATE = """任务：阅读高考数学题的解析文本，输出该题的摘要 + 考点 + 难度。

[解析文本]
{solution_text}

按下面三行格式输出，不要额外内容:
第一行: 1-2 句话简述该题考查内容（不超过 50 字）
第二行: 逗号分隔的 2-4 个核心数学考点术语
第三行: 易 或 中 或 难
"""

VALID_DIFFICULTY = {"易", "中", "难"}


def parse_llm_output(text: str) -> dict:
    if not text or not text.strip():
        return {"parse_error": "LLM 返回空内容"}
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) < 3:
        return {"parse_error": f"LLM 输出行数 {len(lines)} < 3"}

    # 容忍前缀 "摘要:" / "考点:" / "难度:"
    def strip_prefix(s: str) -> str:
        if ":" in s or "：" in s:
            return re.split(r"[:：]", s, maxsplit=1)[-1].strip()
        return s

    summary = strip_prefix(lines[0])
    tag_line = strip_prefix(lines[1])
    diff_line = strip_prefix(lines[2])

    tags = [t.strip() for t in re.split(r"[,，、；;]", tag_line) if t.strip()]
    difficulty = "中"
    for d in VALID_DIFFICULTY:
        if d in diff_line:
            difficulty = d
            break

    return {
        "summary": summary[:80],
        "tags": tags[:6],  # 最多 6 个
        "difficulty": difficulty,
    }


BAD_TAGS = {"无", "无考点", "非数学题", "无数学考点", "无对应考点", "无可识别考点"}


def _clean_bad_tags(tags: list[str], subject: str) -> list[str]:
    """过滤无意义占位 tag。"""
    out = []
    for t in tags:
        t = t.strip()
        if not t or t in BAD_TAGS:
            continue
        # "无<学科>考点" / "非<学科>题"
        if t.startswith("无") and t.endswith("考点"):
            continue
        if t.startswith("非") and t.endswith("题"):
            continue
        out.append(t)
    return out


def enrich_question(q: dict, subject: str = "数学") -> dict:
    """单题调 v4-pro，按 subject 定制 prompt。"""
    sol = q.get("solution_text", "")[:2000]
    # solution 文本过短跳过（避免 v4-pro 凭空乱猜占位 tag）
    if len(sol.strip()) < 20:
        return {"parse_error": f"solution_text 过短 ({len(sol)}<20)，跳过 enrich"}

    system = _make_system(subject)
    prompt = _make_prompt(subject, sol)
    try:
        result = call(
            prompt, task=Task.COMPLEX, system=system,
            temperature=0.3, max_tokens=400,
        )
        parsed = parse_llm_output(result.text)
        if "parse_error" in parsed:
            result = call(
                prompt, task=Task.COMPLEX, system=system,
                temperature=0.5, max_tokens=600,
            )
            parsed = parse_llm_output(result.text)
        if "tags" in parsed:
            parsed["tags"] = _clean_bad_tags(parsed["tags"], subject)
            if not parsed["tags"]:
                return {"parse_error": "LLM 输出全为占位 tag"}
        return parsed
    except LLMError as e:
        return {"parse_error": str(e)[:200]}


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    ap.add_argument(
        "--force-clean", action="store_true",
        help="清洗已有 tags 中的占位 (无/非XX题/无XX考点)，并 redo 这些题",
    )
    args = ap.parse_args()

    qa_path = Path(args.questions)
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    subject = qa.get("subject", "数学")

    failed = 0
    for q in qa["questions"]:
        if args.force_clean and q.get("tags"):
            cleaned = _clean_bad_tags(q["tags"], subject)
            if len(cleaned) != len(q["tags"]):
                q["tags"] = cleaned
            if not cleaned:
                # 全是占位，清空触发 redo
                q.pop("tags", None)
                q.pop("summary", None)

        if q.get("summary") and q.get("tags"):
            continue  # 已富化过则跳过
        result = enrich_question(q, subject=subject)
        if "parse_error" in result:
            failed += 1
            q["enrich_error"] = result["parse_error"]
            continue
        q["summary"] = result["summary"]
        q["tags"] = result["tags"]
        q["difficulty"] = result["difficulty"]
        q.pop("enrich_error", None)
        print(f"[ok] Q{q['qno']}: {len(result['tags'])} tags, {result['difficulty']}")

    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完成: {len(qa['questions']) - failed}/{len(qa['questions'])} 题 enrich 成功")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
