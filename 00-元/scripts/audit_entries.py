"""词条有效性体检：frontmatter / 正文层 / 教材引用 / 链接 / 公式定界符。

产出每词条记分卡 + 不合规清单。CLI:
  python 00-元/scripts/audit_entries.py --dir 数学 --grade 小学
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, iter_entries, read_frontmatter, setup_utf8  # noqa: E402

REQUIRED_FM = ["title", "aliases", "学科", "学段", "主题", "状态", "英文术语"]
SKELETON_MARK = "🚧"


def _parse_aliases(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if raw.startswith("[") and raw.endswith("]"):
        return [x.strip() for x in raw[1:-1].split(",") if x.strip()]
    return [raw] if raw else []


def check_frontmatter(fm: dict, stem: str) -> list[str]:
    issues = []
    for k in REQUIRED_FM:
        if not str(fm.get(k, "")).strip():
            issues.append(f"frontmatter 缺字段：{k}")
    bare = re.sub(r"^\d{2,4}-", "", stem)
    aliases = _parse_aliases(str(fm.get("aliases", "")))
    if aliases and aliases[0] != bare:
        issues.append(f"aliases 首位非 bare-name（应为 {bare}）")
    return issues


def _section(text: str, header_kw: str) -> str | None:
    """取 `## ...header_kw...` 到下一 `## ` 前的正文。"""
    m = re.search(rf"^##[^\n]*{re.escape(header_kw)}[^\n]*$", text, re.MULTILINE)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(r"^##\s", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def check_body_layers(text: str, grade: str = "小学") -> list[str]:
    issues = []
    if _section(text, "🧒") is not None:
        issues.append("仍含 🧒3-6 层（小学应已清，跑 strip_kid_layer.py）")
    if "高中" in grade:
        # 高中单层模板：仅要求存在一个 🎓 段（表头可为「考点精讲」或自由式）
        gao = _section(text, "🎓")
        if gao is None:
            issues.append("缺 🎓 层")
        elif SKELETON_MARK in gao or not gao.strip():
            issues.append("🎓 层仍是骨架（🚧/空）")
        return issues
    # 小学/初中两层模板
    for kw, name in [("📚 给 6-12", "📚"), ("🎓 给 12+", "🎓")]:
        body = _section(text, kw)
        if body is None:
            issues.append(f"缺 {name} 层")
        elif SKELETON_MARK in body or not body.strip():
            issues.append(f"{name} 层仍是骨架（🚧/空）")
    return issues


def check_textbook_ref(text: str) -> list[str]:
    # 兼容两种出处标题：「## 📑 出处与参考资料」与精简版「## 📑 出处」
    body = _section(text, "出处")
    if body is None:
        return ["缺 📑 出处 段"]
    m = re.search(r"-\s*\*\*教材\*\*：(.*)", body)
    if not m or not m.group(1).strip():
        return ["📑 教材引用为空"]
    line = m.group(1)
    issues = []
    if "ChinaTextbook" not in line:
        issues.append("📑 教材行未指向本地 ChinaTextbook PDF")
    if not re.search(r"(第.+[单元章节课册讲]|《.+》|准备课|总复习|[Pp]\.?\s*\d|页)", line):
        issues.append("📑 教材行缺具体章节/页码")
    return issues


def check_wikilinks(text: str) -> list[str]:
    """检测无管线裸链 [[X]]（应规范化为 [[NNN-X|X]]）。"""
    issues = []
    for m in re.finditer(r"\[\[([^\[\]|#]+?)\]\]", text):
        tgt = m.group(1).strip()
        if "/" in tgt:  # 路径型（教材/学习路径）放过
            continue
        if not re.match(r"^\d{2,4}-", tgt):
            issues.append(f"未规范化裸链 [[{tgt}]]")
    return issues


def check_math_delim(text: str) -> list[str]:
    issues = []
    if re.search(r"(?<!\\)\\\(", text) or re.search(r"(?<!\\)\\\[", text):
        issues.append("含 LaTeX \\( 或 \\[ 定界符（应改 $ / $$）")
    return issues


def audit_one(path: Path, fm: dict, text: str) -> list[str]:
    stem = path.stem
    grade = "高中" if "高中" in str(fm.get("学段", "")) else "小学"
    return (
        check_frontmatter(fm, stem)
        + check_body_layers(text, grade)
        + check_textbook_ref(text)
        + check_wikilinks(text)
        + check_math_delim(text)
    )


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--grade", default="小学")
    args = ap.parse_args()

    base = REPO_ROOT / args.dir
    total = clean = 0
    bad: list[tuple[str, list[str]]] = []
    for p in iter_entries(base):
        fm = read_frontmatter(p)
        if not fm or args.grade not in str(fm.get("学段", "")):
            continue
        total += 1
        text = p.read_text(encoding="utf-8")
        issues = audit_one(p, fm, text)
        if issues:
            bad.append((str(p.relative_to(REPO_ROOT)), issues))
        else:
            clean += 1
    print(f"体检 {total} 词条：合规 {clean} / 不合规 {len(bad)}\n")
    for rel, issues in bad:
        print(f"✗ {rel}")
        for i in issues:
            print(f"    - {i}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
