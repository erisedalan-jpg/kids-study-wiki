"""真题 考点 词表标准化迁移：按变体映射改写 frontmatter 考点 字段（保守）。

只动 frontmatter `考点:` 行；只写真正变更的文件；幂等。
--apply 前要求 git 工作树干净（基线可回退）。

CLI:
  python 00-元/scripts/normalize_kaodian_source.py                               # dry-run：吉林-数学（默认）
  python 00-元/scripts/normalize_kaodian_source.py --apply                       # 写盘（需 git 干净）
  python 00-元/scripts/normalize_kaodian_source.py --province 北京 --subject 数学 # dry-run：北京-数学
  python 00-元/scripts/normalize_kaodian_source.py --province 北京 --subject 数学 --apply
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402

SCRIPT_DIR = Path(__file__).parent

FM_RE = re.compile(r"^(---\s*\n)(.*?)(\n---\s*\n)", re.DOTALL)
KAO_RE = re.compile(r"^(考点:[ \t]*)(.*)$", re.MULTILINE)


def exam_dir_for(province: str, subject: str) -> Path:
    return REPO_ROOT / "真题" / f"{province}-{subject}"


def canon_path_for(subject: str) -> Path:
    return SCRIPT_DIR / f"canonical_考点_{subject}.yaml"


def load_canonical(path: Path | None = None) -> dict[str, str]:
    if path is None:
        path = canon_path_for("数学")
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {str(k): str(v) for k, v in data.items()}


def _parse_list(v: str) -> list[str]:
    v = (v or "").strip()
    if v.startswith("[") and v.endswith("]"):
        return [x.strip() for x in v[1:-1].split(",") if x.strip()]
    return [v] if v else []


def map_tags(tags: list[str], cmap: dict[str, str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for t in tags:
        c = cmap.get(t, t)
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def rewrite_text(text: str, cmap: dict[str, str]) -> tuple[str, list[str], list[str]]:
    """改写首个 frontmatter 内的 考点 行。返回 (新文本, before, after)。无变更则原样返回。"""
    fm = FM_RE.match(text)
    if not fm:
        return text, [], []
    head, fm_body, tail = fm.group(1), fm.group(2), fm.group(3)
    captured: dict[str, list[str]] = {"before": [], "after": []}

    def repl(km: "re.Match[str]") -> str:
        prefix, val = km.group(1), km.group(2)
        before = _parse_list(val)
        after = map_tags(before, cmap)
        captured["before"] = before
        captured["after"] = after
        return f"{prefix}[{', '.join(after)}]"

    new_body = KAO_RE.sub(repl, fm_body, count=1)
    before, after = captured["before"], captured["after"]
    if before == after:
        return text, before, after
    new_text = text[:fm.start()] + head + new_body + tail + text[fm.end():]
    return new_text, before, after


def git_clean() -> bool:
    r = subprocess.run(["git", "status", "--porcelain"],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == ""


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--province", default="吉林")
    ap.add_argument("--subject", default="数学")
    ap.add_argument("--apply", action="store_true", help="写盘（需 git 干净）")
    args = ap.parse_args()

    exam_dir = exam_dir_for(args.province, args.subject)
    canon_path = canon_path_for(args.subject)
    cmap = load_canonical(canon_path)
    if not cmap:
        print(f"映射表空或不存在：{canon_path}")
        return 1
    if not exam_dir.is_dir():
        print(f"真题目录不存在：{exam_dir}")
        return 1
    if args.apply and not git_clean():
        print("拒绝：git 工作树不干净，先提交/暂存以保基线。")
        return 1

    changed = 0
    for p in sorted(exam_dir.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        new, before, after = rewrite_text(text, cmap)
        if new == text:
            continue
        changed += 1
        print(f"{p.name}: {before} → {after}")
        if args.apply:
            p.write_text(new, encoding="utf-8", newline="")
    print(f"\n{'[APPLY] 已改写' if args.apply else '[dry-run] 将改写'} {changed} 文件（{exam_dir.name}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
