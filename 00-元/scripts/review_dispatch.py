"""
按 10/40/50 比例分桶复检 DeepSeek 生成的词条骨架

读 gen_atom_skeleton.py 产出的 manifest.jsonl，对每条 status=ok 的词条
按用户指定比例分配复检角色：
- 10% → Opus 4.7   （主会话人工抽检，写 prompt 队列）
- 40% → Sonnet 4.6 （subagent 复审，写 prompt 队列）
- 50% → DeepSeek    自检（v4-pro 二次过审，自动调 API）

⚠️ opus/sonnet 两档走 Claude Code 订阅，不调外部 API，改为两步流程：

    Step 1: `--prepare` (默认)
        - DeepSeek-self 仍直接调 API，结果即时写回 manifest
        - opus/sonnet 各写一份 prompt 到 <manifest_dir>/reviews/<id>__<role>.prompt.md
        - 同时把 entry 快照写到 <manifest_dir>/reviews/_pending.jsonl

    Step 2: 主会话人工跑
        - 你在 Claude Code 里逐个（或批量）打开 prompt.md，让对应模型出 verdict
        - 把 verdict JSON 保存为 <id>__<role>.verdict.json（与 prompt 同目录）

    Step 3: `--ingest`
        - 重新跑本脚本带 --ingest，把已就绪的 verdict 收回 manifest
        - 缺失的 verdict 会列出来提示

verdict JSON 结构（与 deepseek-self 自检产物对齐）：
    {
      "verdict": "pass|fix_minor|fix_major|reroute_to_opus",
      "issues": [{"item": <int>, "level": "FAIL|WARN|INFO", "msg": "..."}],
      "fix_suggestions": ["..."]
    }

用法
----
    # Step 1: 分桶 + 跑 deepseek-self + 写 opus/sonnet 队列
    python 00-元/scripts/review_dispatch.py \
        --manifest 00-元/scripts/_llm_logs/政治-批次1.manifest.jsonl

    # 自定义比例（必须加起来 = 100）
    python 00-元/scripts/review_dispatch.py --manifest ... --ratio 20,30,50

    # 只分配不调用 LLM（dry-run）
    python 00-元/scripts/review_dispatch.py --manifest ... --dry-run

    # Step 3: 把主会话产出的 verdict.json 收回 manifest
    python 00-元/scripts/review_dispatch.py --manifest ... --ingest

输出
----
    原 manifest 文件追加 N 行：每行是原 entry 加上 "review" 字段：
    {
      ...原字段,
      "review": {
        "reviewer": "opus|sonnet|deepseek-self",
        "verdict": "pass|fix_minor|fix_major|reroute_to_opus",
        "issues": [...],
        "fix_suggestions": [...],
        "ts": "..."
      }
    }

退出码
------
    0  全部复检完成（或队列已写好等待人工处理，且无缺失 ingest）
    1  存在 verdict=fix_major / reroute_to_opus，或 --ingest 时仍有缺失
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _llm_router import LLMError, Task, call  # noqa: E402
from _utils import REPO_ROOT, setup_utf8  # noqa: E402


REVIEW_PROMPT = (Path(__file__).parent / "_prompts" / "review_atom.md").read_text(encoding="utf-8")

# 仅 deepseek-self 走 API；opus/sonnet 改为写 prompt 队列由主会话处理
DEEPSEEK_SELF_TASK = Task.COMPLEX
CLAUDE_REVIEWERS = ("opus", "sonnet")


def assign_reviewers(n: int, ratios: tuple[int, int, int], seed: int = 42) -> list[str]:
    """按比例稳定分配。10/40/50 → ['opus' n*0.1, 'sonnet' n*0.4, 'deepseek-self' n*0.5]，再 shuffle。"""
    opus_n = round(n * ratios[0] / 100)
    sonnet_n = round(n * ratios[1] / 100)
    ds_n = n - opus_n - sonnet_n
    assignments = ["opus"] * opus_n + ["sonnet"] * sonnet_n + ["deepseek-self"] * ds_n
    rng = random.Random(seed)
    rng.shuffle(assignments)
    return assignments


def parse_review(text: str) -> dict:
    """解析 LLM 返回的 JSON。容忍前后包裹 ```json 代码块。"""
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].lstrip()
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        return {"verdict": "fix_major", "issues": [{"item": 0, "level": "FAIL", "msg": f"复检结果非合法 JSON: {e}"}]}


def render_review_prompt(reviewer: str, entry: dict, atom_text: str) -> str:
    return (
        REVIEW_PROMPT.replace("{atom_markdown}", atom_text)
        .replace("{subject}", entry.get("subject", ""))
        .replace("{stage}", entry.get("stage", ""))
        .replace("{semester}", entry.get("semester", ""))
        .replace("{model_tag}", entry.get("model", ""))
        .replace("{reviewer_role}", reviewer)
    )


def queue_dir_for(manifest_path: Path) -> Path:
    d = manifest_path.parent / "reviews"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_pending(reviewer: str, entry: dict, atom_text: str, queue_dir: Path) -> Path:
    """把 opus/sonnet 复检任务写到队列，返回 prompt 文件路径。"""
    prompt_text = render_review_prompt(reviewer, entry, atom_text)
    prompt_file = queue_dir / f"{entry['id']}__{reviewer}.prompt.md"
    header = (
        f"<!-- review-queue entry_id={entry['id']} reviewer={reviewer} -->\n"
        f"<!-- 完成后请把 verdict JSON 保存为 {entry['id']}__{reviewer}.verdict.json，"
        f"然后重跑：python 00-元/scripts/review_dispatch.py --manifest <manifest> --ingest -->\n\n"
    )
    prompt_file.write_text(header + prompt_text, encoding="utf-8")

    pending_log = queue_dir / "_pending.jsonl"
    record = {
        "entry_id": entry["id"],
        "reviewer": reviewer,
        "prompt_file": str(prompt_file.relative_to(queue_dir.parent)),
        "entry": entry,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    with pending_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return prompt_file


def run_prepare(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.exists():
        sys.exit(f"ERROR: manifest 不存在: {manifest_path}")

    ratios = tuple(int(x) for x in args.ratio.split(","))
    if len(ratios) != 3 or sum(ratios) != 100:
        sys.exit(f"ERROR: --ratio 必须是 3 个数字加起来 = 100, 收到 {ratios}")

    entries = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok_entries = [e for e in entries if e.get("status") == "ok"]
    if not ok_entries:
        print("manifest 中无 status=ok 的词条，跳过", file=sys.stderr)
        return 0

    reviewers = assign_reviewers(len(ok_entries), ratios, seed=args.seed)
    print(
        f"分桶完成（seed={args.seed}）: "
        f"opus {reviewers.count('opus')} / sonnet {reviewers.count('sonnet')} / "
        f"deepseek-self {reviewers.count('deepseek-self')}",
        file=sys.stderr,
    )

    queue_dir = queue_dir_for(manifest_path)
    need_attention = 0
    queued = 0
    with manifest_path.open("a", encoding="utf-8") as mf:
        for entry, reviewer in zip(ok_entries, reviewers, strict=True):
            file_path = REPO_ROOT / entry["file"]
            if not file_path.exists():
                print(f"[skip] 文件已不存在: {entry['file']}", file=sys.stderr)
                continue

            if args.dry_run:
                review = {"reviewer": reviewer, "verdict": "dry_run"}
                _append_review(mf, entry, review)
                print(f"[{reviewer}] {entry['title']} → dry_run")
                continue

            atom = file_path.read_text(encoding="utf-8")

            if reviewer in CLAUDE_REVIEWERS:
                prompt_file = write_pending(reviewer, entry, atom, queue_dir)
                queued += 1
                print(f"[{reviewer}] {entry['title']} → 队列 {prompt_file.relative_to(REPO_ROOT)}")
                continue

            # deepseek-self
            prompt = render_review_prompt(reviewer, entry, atom)
            try:
                result = call(prompt, task=DEEPSEEK_SELF_TASK, temperature=0.0, max_tokens=2000)
                review = parse_review(result.text)
                review["reviewer"] = reviewer
                review["model"] = result.model
            except LLMError as e:
                review = {"reviewer": reviewer, "verdict": "fix_major", "error": str(e)}

            _append_review(mf, entry, review)
            verdict = review.get("verdict", "")
            if verdict in ("fix_major", "reroute_to_opus"):
                need_attention += 1
            print(f"[{reviewer}] {entry['title']} → {verdict}")

    if queued:
        print(
            f"\n📝 {queued} 条 opus/sonnet 复检 prompt 已写入 {queue_dir.relative_to(REPO_ROOT)}/",
            file=sys.stderr,
        )
        print(
            "   下一步：在 Claude Code 主会话里逐个/批量跑这些 prompt，把 verdict JSON "
            "保存为同名 .verdict.json，然后用 --ingest 收回。",
            file=sys.stderr,
        )
    if need_attention:
        print(f"\n⚠️  {need_attention} 条 deepseek-self 复检需主会话介入（fix_major / reroute_to_opus）", file=sys.stderr)
        return 1
    return 0


def run_ingest(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.exists():
        sys.exit(f"ERROR: manifest 不存在: {manifest_path}")

    queue_dir = manifest_path.parent / "reviews"
    pending_log = queue_dir / "_pending.jsonl"
    if not pending_log.exists():
        print("无 pending 记录，跳过", file=sys.stderr)
        return 0

    pendings = [json.loads(l) for l in pending_log.read_text(encoding="utf-8").splitlines() if l.strip()]
    # 已 ingest 过的记入 _ingested.jsonl，避免重跑重复写 manifest
    ingested_log = queue_dir / "_ingested.jsonl"
    already: set[tuple[str, str]] = set()
    if ingested_log.exists():
        for line in ingested_log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            already.add((r["entry_id"], r["reviewer"]))

    ingested = 0
    missing: list[str] = []
    bad_json: list[str] = []
    need_attention = 0
    with manifest_path.open("a", encoding="utf-8") as mf, ingested_log.open("a", encoding="utf-8") as il:
        for p in pendings:
            key = (p["entry_id"], p["reviewer"])
            if key in already:
                continue
            verdict_file = queue_dir / f"{p['entry_id']}__{p['reviewer']}.verdict.json"
            if not verdict_file.exists():
                missing.append(verdict_file.name)
                continue
            try:
                verdict = json.loads(verdict_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                verdict = {"verdict": "fix_major", "error": f"verdict JSON 解析失败: {e}"}
                bad_json.append(verdict_file.name)
            verdict.setdefault("reviewer", p["reviewer"])
            verdict["ts"] = datetime.now(timezone.utc).isoformat()
            _append_review(mf, p["entry"], verdict)
            il.write(json.dumps({"entry_id": p["entry_id"], "reviewer": p["reviewer"], "ts": verdict["ts"]}, ensure_ascii=False) + "\n")
            ingested += 1
            verdict_val = verdict.get("verdict", "")
            if verdict_val in ("fix_major", "reroute_to_opus"):
                need_attention += 1
            print(f"[{p['reviewer']}] {p['entry'].get('title', p['entry_id'])} → {verdict_val}")

    print(
        f"\n已 ingest: {ingested} 条 / 缺失 verdict: {len(missing)} / 解析失败: {len(bad_json)}",
        file=sys.stderr,
    )
    if missing:
        for m in missing[:10]:
            print(f"  缺: {m}", file=sys.stderr)
        if len(missing) > 10:
            print(f"  ... 还有 {len(missing) - 10} 条", file=sys.stderr)
    if need_attention:
        print(f"⚠️  {need_attention} 条需主会话介入（fix_major / reroute_to_opus）", file=sys.stderr)
    return 1 if (missing or need_attention) else 0


def _append_review(mf, entry: dict, review: dict) -> None:
    review.setdefault("ts", datetime.now(timezone.utc).isoformat())
    out = dict(entry)
    out["phase"] = "review"
    out["review"] = review
    mf.write(json.dumps(out, ensure_ascii=False) + "\n")


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--manifest", required=True, help="gen_atom_skeleton.py 产出的 manifest.jsonl")
    ap.add_argument("--ratio", default="10,40,50", help="opus,sonnet,deepseek 三档百分比")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true", help="只分配 reviewer，不调用 LLM / 不写队列")
    ap.add_argument("--ingest", action="store_true", help="收回主会话产出的 verdict.json，写回 manifest")
    args = ap.parse_args()

    if args.ingest:
        return run_ingest(args)
    return run_prepare(args)


if __name__ == "__main__":
    sys.exit(main())
