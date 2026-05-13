"""L2 复验队列 (v2 Step 3b)。

两步法：
  Step A: --mode prepare  → 写 prompt 队列到 <manifest_dir>/verdicts/<id>.prompt.md
                             同时写 _pending.jsonl 跟踪状态
  Step B: 用户在 Opus 主会话（5/15 前）或 sonnet subagent（5/15 后）跑每个 prompt
          把 verdict 文本保存为 <id>.verdict.txt
  Step C: --mode ingest   → 读 verdict.txt，解析回 questions.json (+ verdict 字段)

prompt 设计：把题面截图路径告诉 LLM，让它看图判断 v4-pro 抽的 tags + summary 是否吻合。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402


PROMPT_TEMPLATE = """请打开题面截图 (用 Read 工具或视觉能力查看)：
`{image_abs_path}`

v4-pro 抽出的元数据：
- 摘要: {summary}
- 考点 tags: {tags}

任务：看截图判断 v4-pro 抽的考点和摘要是否吻合实际题面。

按下面两行格式输出，不要额外内容:
第一行: 吻合 / 部分偏差 / 严重偏差
第二行: 一句话说明理由（≤ 40 字；部分偏差时说明建议改哪些 tag）
"""

VALID_VERDICTS = {"吻合", "部分偏差", "严重偏差"}


def render_verify_prompt(q: dict) -> str:
    """生成单题 verify prompt。image 路径用绝对路径方便 Opus/sonnet 找到。"""
    image_path = REPO_ROOT / q["题面图"]
    tags_str = ", ".join(q.get("tags", []))
    return PROMPT_TEMPLATE.format(
        image_abs_path=str(image_path).replace("\\", "/"),
        summary=q.get("summary", "(无)"),
        tags=tags_str,
    )


def parse_verdict_response(text: str) -> dict[str, str]:
    """解析 LLM 输出的两行 verdict + note。"""
    if not text or not text.strip():
        return {"verdict": "调用失败", "note": "LLM 返回空"}
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return {"verdict": "调用失败", "note": "空行"}
    first = lines[0]
    if ":" in first or "：" in first:
        first = re.split(r"[:：]", first, maxsplit=1)[-1].strip()
    verdict = "未识别"
    for v in VALID_VERDICTS:
        if v in first:
            verdict = v
            break
    note = lines[1] if len(lines) >= 2 else first
    return {"verdict": verdict, "note": note[:80]}


def run_prepare(qa_path: Path) -> int:
    """写 verify prompt 队列。"""
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    queue_dir = qa_path.parent / "verdicts"
    queue_dir.mkdir(parents=True, exist_ok=True)
    pending_log = queue_dir / "_pending.jsonl"

    queued = 0
    with pending_log.open("a", encoding="utf-8") as f:
        for q in qa["questions"]:
            if q.get("verdict"):
                continue  # 已 ingest 过
            prompt = render_verify_prompt(q)
            prompt_file = queue_dir / f"q{q['qno']:02d}.prompt.md"
            prompt_file.write_text(prompt, encoding="utf-8")
            record = {
                "qno": q["qno"],
                "prompt_file": str(prompt_file.relative_to(qa_path.parent)),
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            queued += 1
            print(f"[queued] Q{q['qno']} → {prompt_file.name}")

    print(f"\n📝 {queued} 题 verify prompt 已写入 {queue_dir}")
    print("   下一步: Opus 主会话或 sonnet subagent 跑每个 prompt，把 verdict")
    print(f"   保存为 q01.verdict.txt / q02.verdict.txt 等到同目录")
    print(f"   完成后用 --mode ingest 收回")
    return 0


def run_ingest(qa_path: Path) -> int:
    """读 verdict.txt 回写 questions.json。"""
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    queue_dir = qa_path.parent / "verdicts"
    if not queue_dir.exists():
        sys.exit(f"ERROR: verdicts 目录不存在: {queue_dir}")

    ingested = 0
    missing = 0
    severe = 0
    for q in qa["questions"]:
        if q.get("verdict"):
            continue
        verdict_file = queue_dir / f"q{q['qno']:02d}.verdict.txt"
        if not verdict_file.exists():
            missing += 1
            continue
        text = verdict_file.read_text(encoding="utf-8")
        result = parse_verdict_response(text)
        q["verdict"] = result["verdict"]
        q["verdict_note"] = result["note"]
        ingested += 1
        if result["verdict"] in ("严重偏差", "未识别", "调用失败"):
            severe += 1
        print(f"[{result['verdict']}] Q{q['qno']}: {result['note'][:50]}")

    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已 ingest {ingested} 条 / 缺失 {missing} / 需 Opus 仲裁 {severe}")
    return 1 if (missing or severe) else 0


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    ap.add_argument("--mode", required=True, choices=["prepare", "ingest"])
    args = ap.parse_args()

    qa_path = Path(args.questions)
    if args.mode == "prepare":
        return run_prepare(qa_path)
    return run_ingest(qa_path)


if __name__ == "__main__":
    raise SystemExit(main())
