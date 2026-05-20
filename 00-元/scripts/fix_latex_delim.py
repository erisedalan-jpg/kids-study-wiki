"""LaTeX 定界符迁 Obsidian：`\\( \\) \\[ \\]` → `$ $$`。

根因：v4-pro 用标准 LaTeX 定界符，Obsidian 默认 MathJax 只认 $ / $$，
故 `\\frac` `^2` `\\sqrt` `\\pi` 全按字面显示反斜杠/字符。

安全约束：
1. 范围严限 manifest（按 bare-title 匹配，绝不动旧词条）。默认 manifest
   `00-元/scripts/_llm_logs/北京缺口-{subject}.manifest.jsonl`；
   用 `--manifest-prefix` 指定其他批次（如 `湖南缺口`），用 `--subjects`
   限定学科子集。
2. 负向后顾 `(?<!\\\\)` 保护 `\\\\[4pt]` / `\\\\[6pt]` 等 LaTeX 换行符
   （正确 `$$` 块内的换行不受影响）。
3. 默认 dry-run；`--apply` 才写盘。
4. 奇数计数文件须手清未配对定界符（输出 ⚠RESID 提醒）。
"""
import sys, io, json, re, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOG = REPO / "00-元/scripts/_llm_logs"
DEFAULT_SUBJECTS = ["数学", "物理", "化学", "生物", "英语"]

# 单反斜杠定界符（前面不是另一个反斜杠 → 排除 `\\[4pt]` 换行）
SUBS = [
    (re.compile(r"(?<!\\)\\\["), "$$"),
    (re.compile(r"(?<!\\)\\\]"), "$$"),
    (re.compile(r"(?<!\\)\\\("), "$"),
    (re.compile(r"(?<!\\)\\\)"), "$"),
]
RESIDUAL = re.compile(r"(?<!\\)\\[\(\)\[\]]")


def manifest_titles(manifest_prefix: str, subject: str) -> set[str]:
    """读 manifest jsonl → bare-title 集合。"""
    mf = LOG / f"{manifest_prefix}-{subject}.manifest.jsonl"
    if not mf.exists():
        return set()
    titles = set()
    for ln in mf.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        j = json.loads(ln)
        for v in j.values():
            if isinstance(v, str) and v.endswith(".md"):
                titles.add(Path(v.replace("\\", "/")).stem)
                break
    return titles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--manifest-prefix", default="北京缺口",
                    help="manifest 文件名前缀（默认 北京缺口；对应 _llm_logs/<prefix>-<subject>.manifest.jsonl）")
    ap.add_argument("--subjects", nargs="+", default=DEFAULT_SUBJECTS,
                    help="学科子集（默认 数理化生英）")
    args = ap.parse_args()

    grand = 0
    changed = []
    for s in args.subjects:
        titles = manifest_titles(args.manifest_prefix, s)
        if not titles:
            print(f"[skip] {s}: manifest 不存在或为空 ({args.manifest_prefix}-{s}.manifest.jsonl)")
            continue
        for f in sorted((REPO / s).glob("*.md")):
            bare = re.sub(r"^\d+-", "", f.stem)
            if bare not in titles:
                continue
            txt = f.read_text(encoding="utf-8")
            n = sum(len(rx.findall(txt)) for rx, _ in SUBS)
            if n == 0:
                continue
            new = txt
            for rx, rep in SUBS:
                new = rx.sub(rep, new)
            resid = RESIDUAL.findall(new)
            grand += n
            changed.append((f.relative_to(REPO).as_posix(), n, len(resid)))
            if args.apply:
                f.write_text(new, encoding="utf-8", newline="")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] {len(changed)} 文件，{grand} 处定界符  (manifest-prefix={args.manifest_prefix})")
    for path, n, resid in changed:
        flag = f"  ⚠RESID={resid}" if resid else ""
        print(f"  {n:3d}  {path}{flag}")
    bad = [c for c in changed if c[2]]
    print(f"\n残留单反斜杠定界符的文件: {len(bad)}（应为 0）")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
