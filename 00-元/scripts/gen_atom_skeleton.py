"""
批量调用 DeepSeek 生成词条骨架（家庭学习 Wiki 多模型异构流水线 · 生成阶段）

从一份 topics.jsonl（或 --names "x,y,z"）读入待生成的词条清单，
对每条调用 DeepSeek（默认 deepseek-v4-pro，可降级到 flash），
写入对应学科目录下的 Markdown 文件，并把元数据追加到 manifest.jsonl
供下游 review_dispatch.py 按 10/40/50 分桶复检。

用法
----
    # 从 JSONL（推荐，可携带 topic / english_term 等字段）
    python 00-元/scripts/gen_atom_skeleton.py \
        --topics-file topics.jsonl \
        --model complex \
        --out-manifest 00-元/scripts/_llm_logs/政治-批次1.manifest.jsonl

    # 快速命令行清单（字段从 --subject/--stage/--semester 取默认）
    python 00-元/scripts/gen_atom_skeleton.py \
        --names "联合国,世界贸易组织,二十国集团" \
        --subject 政治 --stage 初中 --semester 九上 \
        --model complex

输入 JSONL 行格式
----------------
    {"title": "联合国", "subject": "政治", "stage": "初中", "semester": "九上",
     "topic": "国际组织", "english_term": "United Nations"}

输出
----
    1) 每条词条 → <学科>/<bare-name>.md（写入前检查冲突，已存在则跳过）
    2) manifest.jsonl 每行：
       {"id": "...", "title": "...", "file": "...", "model": "...",
        "status": "ok|skipped|routed_to_opus|failed", "ts": "..."}

退出码
------
    0  全部成功或路由
    1  有失败项（manifest 中 status=failed）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _llm_router import LLMError, Task, call  # noqa: E402
from _utils import REPO_ROOT, setup_utf8  # noqa: E402


_PROMPTS_DIR = Path(__file__).parent / "_prompts"
DEFAULT_PROMPT = _PROMPTS_DIR / "atom_skeleton.md"

ROUTE_MARKER = "__ROUTE_TO_OPUS__"


def render_prompt(item: dict, *, today: str, model_tag: str, template: str) -> str:
    """把 prompt 模板中的 {placeholder} 替换为本条参数。"""
    fields = {
        "title": item["title"],
        "subject": item["subject"],
        "stage": item["stage"],
        "semester": item.get("semester", ""),
        "topic": item.get("topic", ""),
        "english_term": item.get("english_term", ""),
        "today": today,
        "model_tag": model_tag,
    }
    out = template
    for k, v in fields.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def load_items(args: argparse.Namespace) -> list[dict]:
    if args.topics_file:
        items = []
        for line in Path(args.topics_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                items.append(json.loads(line))
        return items
    if args.names:
        names = [n.strip() for n in args.names.split(",") if n.strip()]
        return [
            {
                "title": n,
                "subject": args.subject,
                "stage": args.stage,
                "semester": args.semester or "",
                "topic": args.topic or "",
                "english_term": "",
            }
            for n in names
        ]
    sys.exit("ERROR: 必须提供 --topics-file 或 --names")


def target_path(item: dict) -> Path:
    """词条文件目标路径。不加序号前缀——后续走 renumber.py 统一编号。"""
    safe = re.sub(r'[\\/:*?"<>|]', "_", item["title"])
    return REPO_ROOT / item["subject"] / f"{safe}.md"


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--topics-file", help="JSONL 文件路径")
    ap.add_argument("--names", help="逗号分隔词条名（与 --topics-file 二选一）")
    ap.add_argument("--subject", help="--names 模式下的学科")
    ap.add_argument("--stage", help="--names 模式下的学段")
    ap.add_argument("--semester", help="--names 模式下的学期")
    ap.add_argument("--topic", help="--names 模式下的主题")
    ap.add_argument(
        "--model",
        choices=["simple", "complex"],
        default="complex",
        help="路由 Task：simple→v4-flash / complex→v4-pro",
    )
    ap.add_argument("--out-manifest", required=True, help="输出 manifest.jsonl 路径")
    ap.add_argument(
        "--prompt-file",
        help="自定义 prompt 模板路径（默认 _prompts/atom_skeleton.md）。"
        "真题缺口考点词条用 _prompts/exam_lexicon.md",
    )
    ap.add_argument("--dry-run", action="store_true", help="只渲染 prompt 不调 API")
    ap.add_argument("--overwrite", action="store_true", help="覆盖已存在的词条文件")
    args = ap.parse_args()

    prompt_path = Path(args.prompt_file) if args.prompt_file else DEFAULT_PROMPT
    if not prompt_path.is_absolute():
        prompt_path = (REPO_ROOT / prompt_path) if not prompt_path.exists() else prompt_path
    prompt_template = prompt_path.read_text(encoding="utf-8")

    items = load_items(args)
    task_enum = {"simple": Task.SIMPLE, "complex": Task.COMPLEX}[args.model]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    model_tag = f"DeepSeek-{args.model}"

    manifest_path = Path(args.out_manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    failed = 0
    written_paths: list[Path] = []
    with manifest_path.open("a", encoding="utf-8") as mf:
        for item in items:
            tgt = target_path(item)
            entry = {
                "id": uuid.uuid4().hex[:12],
                "title": item["title"],
                "subject": item["subject"],
                "file": str(tgt.relative_to(REPO_ROOT)),
                "model": model_tag,
                "ts": datetime.now(timezone.utc).isoformat(),
            }

            if tgt.exists() and not args.overwrite:
                entry["status"] = "skipped"
                entry["reason"] = "file_exists"
                mf.write(json.dumps(entry, ensure_ascii=False) + "\n")
                print(f"[skip] {tgt.relative_to(REPO_ROOT)} 已存在", file=sys.stderr)
                continue

            prompt = render_prompt(
                item, today=today, model_tag=model_tag, template=prompt_template
            )
            if args.dry_run:
                print(f"--- DRY RUN · {item['title']} ---\n{prompt[:500]}...\n", file=sys.stderr)
                entry["status"] = "dry_run"
                mf.write(json.dumps(entry, ensure_ascii=False) + "\n")
                continue

            try:
                result = call(prompt, task=task_enum, temperature=0.3, max_tokens=4000)
            except LLMError as e:
                entry["status"] = "failed"
                entry["error"] = str(e)
                failed += 1
                mf.write(json.dumps(entry, ensure_ascii=False) + "\n")
                print(f"[fail] {item['title']}: {e}", file=sys.stderr)
                continue

            if result.text.lstrip().startswith(ROUTE_MARKER):
                entry["status"] = "routed_to_opus"
                entry["route_reason"] = result.text.strip()
                mf.write(json.dumps(entry, ensure_ascii=False) + "\n")
                print(f"[route] {item['title']} → 主会话: {result.text.strip()}", file=sys.stderr)
                continue

            tgt.parent.mkdir(parents=True, exist_ok=True)
            tgt.write_text(result.text, encoding="utf-8")
            entry["status"] = "ok"
            entry["tokens"] = result.usage.total_tokens
            mf.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"[ok]   {item['title']} → {tgt.relative_to(REPO_ROOT)} ({result.usage.total_tokens} tok)")
            written_paths.append(tgt)

    # 规范化新生成词条中的 [[X]] 链接（Obsidian 跳转兼容）
    if written_paths:
        from fix_wikilinks import canonicalize_files
        fixed, unresolved = canonicalize_files(written_paths)
        if fixed:
            uniq = len(set(unresolved))
            print(f"📎 规范化 {fixed} 条 wikilinks（unresolved: {uniq} 唯一 tag）")

    if failed:
        print(f"\n失败 {failed} 条，详见 {manifest_path}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
