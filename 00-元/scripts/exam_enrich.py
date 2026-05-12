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


SYSTEM_PROMPT = (
    "你是高考数学题考点标注员。"
    "回答必须简短直接，不展开推理过程，严格按指定格式输出。"
)

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


def enrich_question(q: dict) -> dict:
    """单题调 v4-pro。"""
    prompt = PROMPT_TEMPLATE.format(solution_text=q.get("solution_text", "")[:2000])
    try:
        result = call(
            prompt,
            task=Task.COMPLEX,
            system=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=400,
        )
        parsed = parse_llm_output(result.text)
        if "parse_error" in parsed:
            # 重试一次（t=0.5）
            result = call(
                prompt,
                task=Task.COMPLEX,
                system=SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=600,
            )
            parsed = parse_llm_output(result.text)
        return parsed
    except LLMError as e:
        return {"parse_error": str(e)[:200]}


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    args = ap.parse_args()

    qa_path = Path(args.questions)
    qa = json.loads(qa_path.read_text(encoding="utf-8"))

    failed = 0
    for q in qa["questions"]:
        if q.get("summary") and q.get("tags"):
            continue  # 已富化过则跳过
        result = enrich_question(q)
        if "parse_error" in result:
            failed += 1
            q["enrich_error"] = result["parse_error"]
            continue
        q["summary"] = result["summary"]
        q["tags"] = result["tags"]
        q["difficulty"] = result["difficulty"]
        print(f"[ok] Q{q['qno']}: {len(result['tags'])} tags, {result['difficulty']}")

    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完成: {len(qa['questions']) - failed}/{len(qa['questions'])} 题 enrich 成功")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
