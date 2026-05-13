"""
词条关联性诊断。

扫描所有学科目录的 [[]] 双向链接，建立有向图，输出：

1. 总览（词条 / 链接 / 平均度数）
2. 孤岛词条（既无入链也无出链）
3. 断链（[[X]] 但找不到 X 也找不到它的 alias）
4. frontmatter bare-name alias 缺失（影响 [[]] 解析）
5. 跨学段连贯性（按学科：低学段→高学段是否互链）

用法
----
    python 00-元/scripts/analyze_links.py            # 总览 + top 50 列表
    python 00-元/scripts/analyze_links.py --full    # 全量列表
    python 00-元/scripts/analyze_links.py --json    # 机读 JSON
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import (  # noqa: E402
    REPO_ROOT, SUBJECT_DIRS, bare_name, iter_entries, iter_exam_dirs,
    read_frontmatter, setup_utf8,
)

LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
ALIASES_LINE_RE = re.compile(r"^aliases\s*:\s*\[(.*?)\]\s*$", re.MULTILINE)
ALIASES_BLOCK_RE = re.compile(
    r"^aliases\s*:\s*\n((?:[ \t]+-[ \t]+.+\n)+)", re.MULTILINE
)


def parse_aliases(fm_text: str) -> list[str]:
    """解析 frontmatter aliases，支持 inline 和 block 两种 YAML 格式。

    Inline: `aliases: [a, b, "x,y", ...]`
    Block:
        aliases:
          - a
          - b

    YAML 语义：`What's-the-matter` 中间的 `'` 是字面量，不是字符串边界。
    """
    # 先试 block 格式
    bm = ALIASES_BLOCK_RE.search(fm_text)
    if bm:
        out: list[str] = []
        for line in bm.group(1).splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                v = stripped[2:].strip()
                # 去掉外层引号
                if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                    v = v[1:-1]
                if v:
                    out.append(v)
        return out
    # fallback 到 inline 格式
    m = ALIASES_LINE_RE.search(fm_text)
    if not m:
        return []
    s = m.group(1)
    # split by 顶层逗号（忽略引号包裹值内的逗号）
    out: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    started = False  # 当前值是否已开始（用于决定引号是边界还是字面量）
    for ch in s:
        if quote:
            if ch == quote:
                quote = None
                # 引号闭合后，剩余字符直到逗号都是同值的一部分，但不再视为字符串
            else:
                buf.append(ch)
        elif not started and ch in ('"', "'"):
            quote = ch
            started = True
        elif ch == ",":
            v = "".join(buf).strip()
            if v:
                out.append(v)
            buf = []
            started = False
        elif ch.isspace() and not started:
            continue  # 跳过值起始前的空白
        else:
            buf.append(ch)
            started = True
    v = "".join(buf).strip()
    if v:
        out.append(v)
    return out


def collect_all() -> tuple[dict[str, Path], dict[str, str], dict[str, str]]:
    """返回 (bare → path, alias → bare, bare → 学科)"""
    files: dict[str, Path] = {}
    aliases: dict[str, str] = {}
    subject_of: dict[str, str] = {}
    fm_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    for s in SUBJECT_DIRS:
        d = REPO_ROOT / s
        if not d.is_dir():
            continue
        for p in iter_entries(d):
            bare = bare_name(p)
            if bare in files:
                # 跨学科同名：保留首个，但 alias 仍指向第一个
                continue
            files[bare] = p
            subject_of[bare] = s
            text = p.read_text(encoding="utf-8", errors="replace")
            m = fm_re.match(text)
            if not m:
                continue
            for a in parse_aliases(m.group(1)):
                aliases.setdefault(a, bare)
    # 真题词条也纳入图，避免反链被误判为断链
    for exam_dir in iter_exam_dirs():
        for p in iter_entries(exam_dir):
            bare = bare_name(p)
            if bare in files:
                continue
            files[bare] = p
            subject_of[bare] = exam_dir.name  # 例如 "吉林-数学"
            text = p.read_text(encoding="utf-8", errors="replace")
            m = fm_re.match(text)
            if not m:
                continue
            for a in parse_aliases(m.group(1)):
                aliases.setdefault(a, bare)
    # bare 自身也是 alias
    for b in files:
        aliases.setdefault(b, b)
    return files, aliases, subject_of


SKIP = "__SKIP__"  # 合法的非词条链接（教材/路径），不计入图也不算断链


def resolve(target: str, files: dict[str, Path], aliases: dict[str, str]) -> str | None:
    """[[target]] → bare-name / SKIP / None(=broken)。"""
    t = target.strip()
    if not t:
        return SKIP
    # 路径型链接（教材 / 学习路径 / 索引等）—— 合法但不计入词条图
    if "/" in t or "\\" in t:
        return SKIP
    if t in files:
        return t
    if t in aliases:
        return aliases[t]
    # 去前缀再试（[[16-加法]] → 加法）
    stripped = re.sub(r"^\d{2,4}-", "", t)
    if stripped in files:
        return stripped
    if stripped in aliases:
        return aliases[stripped]
    return None


def build_graph(
    files: dict[str, Path],
    aliases: dict[str, str],
) -> tuple[dict[str, set[str]], dict[str, set[str]], list[tuple[str, str]], list[str]]:
    """返回 (out_links, in_links, broken_links, missing_bare_alias)"""
    out_links: dict[str, set[str]] = defaultdict(set)
    in_links: dict[str, set[str]] = defaultdict(set)
    broken: list[tuple[str, str]] = []
    missing_alias: list[str] = []

    fm_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    for bare, p in files.items():
        text = p.read_text(encoding="utf-8", errors="replace")
        m = fm_re.match(text)
        if m:
            als = parse_aliases(m.group(1))
            # 真题词条 (真题/<省份>-<学科>/) 的 bare-name 是 `文-01` 这种切片名，
            # 没人会写 `[[文-01]]` 类链接，跳过该检查
            is_exam_atom = (
                p.parts[-3:-1] == ("真题",) + (p.parts[-2],) if len(p.parts) >= 3
                else False
            ) or "真题" in p.parts
            # 规则：aliases 必须包含 bare-name（不强制首位，以兼容消歧后缀词条）
            if not is_exam_atom and bare not in als:
                missing_alias.append(bare)
        for lm in LINK_RE.finditer(text):
            target = lm.group(1)
            resolved = resolve(target, files, aliases)
            if resolved is None:
                broken.append((bare, target))
            elif resolved == SKIP:
                continue
            elif resolved != bare:
                out_links[bare].add(resolved)
                in_links[resolved].add(bare)
    return out_links, in_links, broken, missing_alias


def report(
    files: dict[str, Path],
    subject_of: dict[str, str],
    out_links: dict[str, set[str]],
    in_links: dict[str, set[str]],
    broken: list[tuple[str, str]],
    missing_alias: list[str],
    full: bool,
) -> None:
    total = len(files)
    out_count = sum(len(v) for v in out_links.values())
    isolated = sorted(b for b in files if not out_links[b] and not in_links[b])
    no_out = sorted(b for b in files if not out_links[b] and in_links[b])
    no_in = sorted(b for b in files if out_links[b] and not in_links[b])

    print("=" * 60)
    print("词条关联性诊断")
    print("=" * 60)
    print(f"总词条:           {total}")
    print(f"总有效出链:       {out_count}")
    print(f"平均出度:         {out_count / total:.2f}")
    print(f"孤岛 (无入无出):   {len(isolated)}  ({len(isolated)/total*100:.1f}%)")
    print(f"无出链 (有入链):   {len(no_out)}")
    print(f"无入链 (有出链):   {len(no_in)}")
    print(f"断链:             {len(broken)}")
    print(f"缺 bare alias:     {len(missing_alias)}")

    by_subject: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "isolated": 0})
    for b, s in subject_of.items():
        by_subject[s]["total"] += 1
        if not out_links[b] and not in_links[b]:
            by_subject[s]["isolated"] += 1
    print()
    print("按学科孤岛分布:")
    print(f"  {'学科':<10} {'总数':>6} {'孤岛':>6} {'孤岛率':>8}")
    for s in sorted(by_subject, key=lambda x: -by_subject[x]["total"]):
        d = by_subject[s]
        rate = d["isolated"] / d["total"] * 100 if d["total"] else 0
        print(f"  {s:<10} {d['total']:>6} {d['isolated']:>6} {rate:>7.1f}%")

    cap = None if full else 30
    print()
    print(f"--- 孤岛词条 (前 {cap or len(isolated)}) ---")
    for b in isolated[:cap]:
        print(f"  {subject_of[b]:<8} {b}")

    print()
    print(f"--- 断链 (前 {cap or len(broken)}) ---")
    for src, tgt in broken[:cap]:
        print(f"  [{subject_of.get(src, '?')}] {src} -> [[{tgt}]]")

    print()
    print(f"--- 缺 bare-name alias (前 {cap or len(missing_alias)}) ---")
    for b in missing_alias[:cap]:
        print(f"  {subject_of[b]:<8} {b}")


def to_json(
    files, subject_of, out_links, in_links, broken, missing_alias,
) -> str:
    return json.dumps({
        "total": len(files),
        "isolated": sorted(b for b in files if not out_links[b] and not in_links[b]),
        "no_out": sorted(b for b in files if not out_links[b] and in_links[b]),
        "no_in": sorted(b for b in files if out_links[b] and not in_links[b]),
        "broken": [{"src": s, "target": t} for s, t in broken],
        "missing_bare_alias": missing_alias,
        "by_subject": {
            s: sum(1 for b in subject_of if subject_of[b] == s)
            for s in set(subject_of.values())
        },
    }, ensure_ascii=False, indent=2)


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="输出完整列表")
    ap.add_argument("--json", action="store_true", help="JSON 格式")
    args = ap.parse_args()

    files, aliases, subject_of = collect_all()
    out_links, in_links, broken, missing_alias = build_graph(files, aliases)

    if args.json:
        print(to_json(files, subject_of, out_links, in_links, broken, missing_alias))
    else:
        report(files, subject_of, out_links, in_links, broken, missing_alias, args.full)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
