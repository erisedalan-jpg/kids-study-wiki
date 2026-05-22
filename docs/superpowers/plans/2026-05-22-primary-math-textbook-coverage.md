# 小学数学教材覆盖重设计 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以学习路径为基准，把小学数学（一上→六下）教材内容完整落为知识词条，梳理现有 81 词条有效性，并沿概念 strand 建纵向「前置/延伸」双向链。

**Architecture:** 新增 3 个可复用脚本（`strip_kid_layer.py` 清 🧒 层 / `audit_entries.py` 有效性体检 / `coverage_matrix.py` 覆盖 diff / `gen_ladder_links.py` 纵向链注入），全部 TDD，复用现有 `_utils`、`fix_wikilinks.collect_targets`、`gen_atom_skeleton`。执行按 spec 五阶段：抽检→梳理→覆盖→扩容→链接→验收。

**Tech Stack:** Python 3.11 + pytest + PyYAML；现有 `00-元/scripts/` 工具箱；DeepSeek v4-pro（批量补条）；pdf/markitdown skill（抽检）。

设计稿：`docs/superpowers/specs/2026-05-22-primary-math-textbook-coverage-design.md`

---

## File Structure

| 文件 | 职责 | 新建/改 |
|---|---|---|
| `00-元/scripts/strip_kid_layer.py` | 删词条 `## 🧒 给 3-6 岁（共读版）` 整段 | 新建 |
| `00-元/scripts/audit_entries.py` | 词条有效性记分卡（fm/层/教材引用/链接/公式） | 新建 |
| `00-元/scripts/coverage_matrix.py` | 学习路径知识点 vs 词条覆盖 diff + 缺口清单 | 新建 |
| `00-元/scripts/gen_ladder_links.py` | 按 strand_map 注入前置/延伸双向链 | 新建 |
| `00-元/scripts/strand_map_数学小学.yaml` | 词条→strand+前置+延伸 声明 | 新建（数据） |
| `00-元/scripts/tests/test_strip_kid_layer.py` | — | 新建 |
| `00-元/scripts/tests/test_audit_entries.py` | — | 新建 |
| `00-元/scripts/tests/test_coverage_matrix.py` | — | 新建 |
| `00-元/scripts/tests/test_gen_ladder_links.py` | — | 新建 |
| `00-元/模板/词条模板-小学.md` | 两层正文模板（去 🧒） | 新建 |
| `数学/*.md`（小学段） | 清 🧒 / 补缺口 / 注入链 | 改（执行阶段） |
| `CLAUDE.md` | 进度与落地备注 | 改 |
| `docs/superpowers/working/` | 抽检报告 / 覆盖矩阵 / 记分卡产物 | 产物 |

约定：所有脚本 `sys.path.insert` + `from _utils import REPO_ROOT, setup_utf8, ...`；CLI 带 `--dry`/`--apply`（默认 dry）；`setup_utf8()` 在 `main()` 内调用（不在 import 期，避免破坏单测，见 `fix_stale_links` 教训）。

---

## Task 1: `strip_kid_layer.py` — 删 🧒3-6 层

**Files:**
- Create: `00-元/scripts/strip_kid_layer.py`
- Test: `00-元/scripts/tests/test_strip_kid_layer.py`

- [ ] **Step 1: 写失败测试**

```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestStripKidSection(unittest.TestCase):
    def setUp(self):
        from strip_kid_layer import strip_kid_section
        self.strip = strip_kid_section

    def test_removes_kid_section_keeps_others(self):
        text = (
            "# 加法\n\n## 🧒 给 3-6 岁（共读版）\n\n两个苹果合起来。\n\n"
            "## 📚 给 6-12 岁（自读版）\n\n加法是合并。\n\n"
            "## 🎓 给 12+（进阶版）\n\n加法群。\n"
        )
        out, changed = self.strip(text)
        self.assertTrue(changed)
        self.assertNotIn("🧒", out)
        self.assertNotIn("两个苹果", out)
        self.assertIn("## 📚 给 6-12 岁（自读版）", out)
        self.assertIn("加法是合并", out)
        self.assertIn("## 🎓 给 12+（进阶版）", out)

    def test_no_kid_section_unchanged(self):
        text = "# 加法\n\n## 📚 给 6-12 岁（自读版）\n\n加法是合并。\n"
        out, changed = self.strip(text)
        self.assertFalse(changed)
        self.assertEqual(out, text)

    def test_kid_section_bounded_by_hr(self):
        text = (
            "# X\n\n## 🧒 给 3-6 岁（共读版）\n\n童语。\n\n---\n\n## 🌐 中英对照\n"
        )
        out, changed = self.strip(text)
        self.assertTrue(changed)
        self.assertNotIn("童语", out)
        self.assertIn("## 🌐 中英对照", out)
        self.assertIn("---", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest "00-元/scripts/tests/test_strip_kid_layer.py" -v`
Expected: FAIL — `ModuleNotFoundError` / `cannot import name 'strip_kid_section'`

- [ ] **Step 3: 写实现**

```python
"""删词条 `## 🧒 给 3-6 岁（共读版）` 整段（小学起不再要学前层）。

删除范围：从 `## 🧒 给 3-6 岁` 标题行 起，到下一个 `## ` 标题 或 `---` 分隔线
（不含）止；保留其后内容。仅删该段，不动 📚 / 🎓。

CLI:
  python 00-元/scripts/strip_kid_layer.py --dir 数学 --grade 小学 --dry
  python 00-元/scripts/strip_kid_layer.py --dir 数学 --grade 小学 --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, iter_entries, read_frontmatter, setup_utf8  # noqa: E402

KID_HEADER = re.compile(r"^##\s*🧒\s*给\s*3-6\s*岁.*$", re.MULTILINE)


def strip_kid_section(text: str) -> tuple[str, bool]:
    """删 🧒3-6 段，返回 (新文本, 是否改动)。"""
    m = KID_HEADER.search(text)
    if not m:
        return text, False
    start = m.start()
    # 找该段终点：下一个 `## ` 或 `---` 行的行首
    rest = text[m.end():]
    end_rel = len(rest)
    for stop in re.finditer(r"^(##\s|---\s*$)", rest, re.MULTILINE):
        end_rel = stop.start()
        break
    end = m.end() + end_rel
    new = text[:start] + text[end:]
    # 收敛多余空行
    new = re.sub(r"\n{3,}", "\n\n", new)
    return new, True


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="学科目录，如 数学")
    ap.add_argument("--grade", default="小学", help="仅处理 学段 含此值的词条")
    ap.add_argument("--apply", action="store_true", help="写盘；否则 dry-run")
    args = ap.parse_args()

    base = REPO_ROOT / args.dir
    n_hit = n_write = 0
    for p in iter_entries(base):
        fm = read_frontmatter(p)
        if not fm or args.grade not in str(fm.get("学段", "")):
            continue
        text = p.read_text(encoding="utf-8")
        new, changed = strip_kid_section(text)
        if changed:
            n_hit += 1
            print(f"  🧒 {p.relative_to(REPO_ROOT)}")
            if args.apply:
                p.write_text(new, encoding="utf-8", newline="")
                n_write += 1
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n[{mode}] 含 🧒 段词条 {n_hit} / 写盘 {n_write}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest "00-元/scripts/tests/test_strip_kid_layer.py" -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add "00-元/scripts/strip_kid_layer.py" "00-元/scripts/tests/test_strip_kid_layer.py"
git commit -m "feat: add strip_kid_layer.py 删小学词条 🧒3-6 层"
```

---

## Task 2: `audit_entries.py` — 有效性体检

**Files:**
- Create: `00-元/scripts/audit_entries.py`
- Test: `00-元/scripts/tests/test_audit_entries.py`

- [ ] **Step 1: 写失败测试**

```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestAuditChecks(unittest.TestCase):
    def setUp(self):
        import audit_entries as ae
        self.ae = ae

    def _good_fm(self):
        return {
            "title": "加法", "aliases": "[加法, addition, plus]",
            "学科": "数学", "学段": "[小学]", "主题": "[数与运算]",
            "状态": "已完成", "英文术语": "addition",
        }

    def test_fm_ok(self):
        self.assertEqual(self.ae.check_frontmatter(self._good_fm(), "016-加法"), [])

    def test_fm_missing_field(self):
        fm = self._good_fm(); del fm["英文术语"]
        issues = self.ae.check_frontmatter(fm, "016-加法")
        self.assertTrue(any("英文术语" in i for i in issues))

    def test_fm_bare_not_first_alias(self):
        fm = self._good_fm(); fm["aliases"] = "[addition, 加法]"
        issues = self.ae.check_frontmatter(fm, "016-加法")
        self.assertTrue(any("bare" in i for i in issues))

    def test_body_layers_skeleton(self):
        text = "## 📚 给 6-12 岁（自读版）\n\n🚧\n\n## 🎓 给 12+（进阶版）\n\n实数。\n"
        issues = self.ae.check_body_layers(text)
        self.assertTrue(any("📚" in i and "骨架" in i for i in issues))

    def test_body_kid_layer_flagged(self):
        text = "## 🧒 给 3-6 岁（共读版）\n\n童语。\n\n## 📚 给 6-12 岁（自读版）\n\n合并。\n## 🎓 给 12+（进阶版）\n\n群。\n"
        issues = self.ae.check_body_layers(text)
        self.assertTrue(any("🧒" in i for i in issues))

    def test_textbook_ref_missing(self):
        text = "## 📑 出处与参考资料\n\n- **教材**：\n- **课标**：x\n"
        issues = self.ae.check_textbook_ref(text)
        self.assertTrue(any("教材" in i for i in issues))

    def test_textbook_ref_ok(self):
        text = ("## 📑 出处与参考资料\n\n- **教材**："
                "[[素材/教材/ChinaTextbook/小学/数学/人教版/x.pdf]] 第三单元\n")
        self.assertEqual(self.ae.check_textbook_ref(text), [])

    def test_unnormalized_wikilink(self):
        text = "见 [[减法]] 与 [[017-减法|减法]]"
        issues = self.ae.check_wikilinks(text)
        self.assertTrue(any("减法" in i for i in issues))

    def test_latex_delim_flagged(self):
        text = r"公式 \(x+1\) 与 \[y\]"
        issues = self.ae.check_math_delim(text)
        self.assertTrue(len(issues) >= 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest "00-元/scripts/tests/test_audit_entries.py" -v`
Expected: FAIL — `ModuleNotFoundError: audit_entries`

- [ ] **Step 3: 写实现**

```python
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
    elif not aliases:
        issues.append("aliases 为空（缺 bare-name）")
    return issues


def _section(text: str, header_kw: str) -> str | None:
    """取 `## ...header_kw...` 到下一 `## ` 前的正文。"""
    m = re.search(rf"^##[^\n]*{re.escape(header_kw)}[^\n]*$", text, re.MULTILINE)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(r"^##\s", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def check_body_layers(text: str) -> list[str]:
    issues = []
    if _section(text, "🧒") is not None:
        issues.append("仍含 🧒3-6 层（小学应已清，跑 strip_kid_layer.py）")
    for kw, name in [("📚 给 6-12", "📚"), ("🎓 给 12+", "🎓")]:
        body = _section(text, kw)
        if body is None:
            issues.append(f"缺 {name} 层")
        elif SKELETON_MARK in body or not body.strip():
            issues.append(f"{name} 层仍是骨架（🚧/空）")
    return issues


def check_textbook_ref(text: str) -> list[str]:
    body = _section(text, "出处与参考资料")
    if body is None:
        return ["缺 📑 出处与参考资料 段"]
    m = re.search(r"-\s*\*\*教材\*\*：(.*)", body)
    if not m or not m.group(1).strip():
        return ["📑 教材引用为空"]
    line = m.group(1)
    issues = []
    if "ChinaTextbook" not in line:
        issues.append("📑 教材行未指向本地 ChinaTextbook PDF")
    if not re.search(r"(第.+[单元章节课]|[Pp]\.?\s*\d|页)", line):
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
    return (
        check_frontmatter(fm, stem)
        + check_body_layers(text)
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest "00-元/scripts/tests/test_audit_entries.py" -v`
Expected: PASS（9 passed）

- [ ] **Step 5: 提交**

```bash
git add "00-元/scripts/audit_entries.py" "00-元/scripts/tests/test_audit_entries.py"
git commit -m "feat: add audit_entries.py 词条有效性体检"
```

---

## Task 3: `coverage_matrix.py` — 覆盖 diff

**Files:**
- Create: `00-元/scripts/coverage_matrix.py`
- Test: `00-元/scripts/tests/test_coverage_matrix.py`

- [ ] **Step 1: 写失败测试**

```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestExtractConcepts(unittest.TestCase):
    def setUp(self):
        from coverage_matrix import extract_concepts
        self.extract = extract_concepts

    def test_pulls_link_targets_and_bold_terms(self):
        doc = (
            "# 学习路径\n\n### 阶段 1\n"
            "- 数一数 → [[001-数数|数数]] [[003-1-10|1-10]]\n"
            "- 上下前后左右 → [[015-位置|位置]] (新)\n\n"
            "## 重点知识点全单\n\n"
            "1. **凑十法**: 9+5\n"
            "2. **数位**: 个/十位\n"
        )
        got = self.extract(doc)
        # 链接目标取裸名（去序号前缀）
        self.assertIn("数数", got)
        self.assertIn("1-10", got)
        self.assertIn("位置", got)
        # 知识点全单的加粗术语
        self.assertIn("凑十法", got)
        self.assertIn("数位", got)

    def test_dedup(self):
        doc = "- a → [[016-加法|加法]] [[016-加法|加法]]\n## 重点知识点全单\n1. **加法**: x\n"
        got = self.extract(doc)
        self.assertEqual(got.count("加法"), 1)


class TestClassify(unittest.TestCase):
    def test_gap_when_unresolved(self):
        from coverage_matrix import classify_concept
        targets = {"加法": "016-加法"}  # bare -> stem
        self.assertEqual(classify_concept("加法", targets), ("covered", "016-加法"))
        self.assertEqual(classify_concept("微积分", targets), ("GAP", ""))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest "00-元/scripts/tests/test_coverage_matrix.py" -v`
Expected: FAIL — `cannot import name 'extract_concepts'`

- [ ] **Step 3: 写实现**

```python
"""学习路径知识点 vs 现有词条 覆盖 diff。

期望知识点 = 路径文档内 [[链接目标]]（裸名）∪「重点知识点全单」加粗术语。
经 alias-aware 解析（复用 analyze_links.collect_all）映射到现有词条；
未命中 = GAP。

CLI:
  python 00-元/scripts/coverage_matrix.py --paths 00-元/学习路径/小学/数学 --dir 数学
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402

LINK_RE = re.compile(r"\[\[([^\[\]|#]+?)(?:\|[^\]]*)?\]\]")
BOLD_RE = re.compile(r"\*\*([^*]+?)\*\*")
SECTION_RE = re.compile(r"##\s*重点知识点全单(.*?)(?:\n##\s|\Z)", re.DOTALL)


def extract_concepts(doc: str) -> list[str]:
    """返回去重、保序的期望知识点裸名清单。"""
    out: list[str] = []
    seen: set[str] = set()

    def add(name: str):
        n = re.sub(r"^\d{2,4}-", "", name.strip())
        if n and n not in seen:
            seen.add(n)
            out.append(n)

    for m in LINK_RE.finditer(doc):
        tgt = m.group(1).strip()
        if "/" in tgt:  # 路径型链接（教材）跳过
            continue
        add(tgt)
    sec = SECTION_RE.search(doc)
    if sec:
        for bm in BOLD_RE.finditer(sec.group(1)):
            add(bm.group(1))
    return out


def classify_concept(name: str, targets: dict[str, str]) -> tuple[str, str]:
    """name → ('covered', stem) | ('GAP', '')。targets: bare/alias -> stem。"""
    stem = targets.get(name)
    return ("covered", stem) if stem else ("GAP", "")


def _build_targets() -> dict[str, str]:
    """裸名/alias -> 词条 stem（复用 analyze_links）。"""
    import analyze_links as al
    files, aliases, _ = al.collect_all()
    targets: dict[str, str] = {}
    for bare in files:
        targets[bare] = bare
    for alias, bare in aliases.items():
        targets.setdefault(alias, bare)
    return targets


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", required=True, help="学习路径目录")
    ap.add_argument("--dir", required=True, help="学科目录（仅用于报告标题）")
    args = ap.parse_args()

    targets = _build_targets()
    paths_dir = REPO_ROOT / args.paths
    rows: list[tuple[str, str, str, str]] = []  # (册, 知识点, 状态, stem)
    gap_n = cov_n = 0
    for p in sorted(paths_dir.glob("*.md")):
        doc = p.read_text(encoding="utf-8")
        for concept in extract_concepts(doc):
            status, stem = classify_concept(concept, targets)
            rows.append((p.stem, concept, status, stem))
            if status == "GAP":
                gap_n += 1
            else:
                cov_n += 1

    print(f"覆盖矩阵 [{args.dir}]：已覆盖 {cov_n} / 缺口 {gap_n}\n")
    print("== 缺口清单（GAP）==")
    for ce, concept, status, _ in rows:
        if status == "GAP":
            print(f"  [{ce}] {concept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest "00-元/scripts/tests/test_coverage_matrix.py" -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add "00-元/scripts/coverage_matrix.py" "00-元/scripts/tests/test_coverage_matrix.py"
git commit -m "feat: add coverage_matrix.py 学习路径覆盖 diff"
```

---

## Task 4: `gen_ladder_links.py` — 纵向链注入

**Files:**
- Create: `00-元/scripts/gen_ladder_links.py`
- Test: `00-元/scripts/tests/test_gen_ladder_links.py`

- [ ] **Step 1: 写失败测试**

```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestInject(unittest.TestCase):
    def setUp(self):
        from gen_ladder_links import inject_links, build_reciprocal
        self.inject = inject_links
        self.recip = build_reciprocal

    def test_inject_into_existing_section(self):
        text = "# 乘法\n\n## 🔗 相关词条\n\n🚧\n\n## 📚 素材\n\n🚧\n"
        out = self.inject(text, 前置=[("016-加法", "加法")], 延伸=[("050-乘方", "乘方")])
        self.assertIn("**前置**", out)
        self.assertIn("[[016-加法|加法]]", out)
        self.assertIn("**延伸**", out)
        self.assertIn("[[050-乘方|乘方]]", out)
        self.assertNotIn("🚧\n\n## 📚 素材", out)  # 🔗 段的 🚧 被替换
        self.assertIn("## 📚 素材", out)            # 后续段保留

    def test_inject_creates_section_if_missing(self):
        text = "# 乘法\n\n## 🎓 给 12+（进阶版）\n\n群。\n"
        out = self.inject(text, 前置=[("016-加法", "加法")], 延伸=[])
        self.assertIn("## 🔗 相关词条", out)
        self.assertIn("[[016-加法|加法]]", out)

    def test_build_reciprocal(self):
        # 加法 延伸→乘法，则乘法应得 前置←加法
        edges = {"016-加法": {"延伸": ["030-乘法"], "前置": []}}
        recip = self.recip(edges)
        self.assertIn("030-乘法", recip)
        self.assertIn("016-加法", recip["030-乘法"]["前置"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest "00-元/scripts/tests/test_gen_ladder_links.py" -v`
Expected: FAIL — `cannot import name 'inject_links'`

- [ ] **Step 3: 写实现**

```python
"""按 strand_map YAML 向词条 `## 🔗 相关词条` 段注入「前置/延伸」双向链。

YAML schema（strand_map_数学小学.yaml）:
  edges:
    "016-加法":   {strand: 数与运算, 前置: [], 延伸: ["030-乘法"]}
    "030-乘法":   {strand: 数与运算, 前置: ["016-加法"], 延伸: ["050-乘方"]}
显式声明的 延伸 会自动在目标处回填对应 前置（build_reciprocal）。

CLI:
  python 00-元/scripts/gen_ladder_links.py --map strand_map_数学小学.yaml --dir 数学 --dry
  python 00-元/scripts/gen_ladder_links.py --map strand_map_数学小学.yaml --dir 数学 --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402

SECTION_HEADER = "## 🔗 相关词条"


def _bare(stem: str) -> str:
    return re.sub(r"^\d{2,4}-", "", stem)


def _fmt(items: list[tuple[str, str]]) -> str:
    return " ".join(f"[[{stem}|{disp}]]" for stem, disp in items)


def build_reciprocal(edges: dict[str, dict]) -> dict[str, dict]:
    """据每条 延伸 边回填目标的 前置；返回补全后的 edges（含新键）。"""
    out: dict[str, dict] = {
        s: {"前置": list(v.get("前置", [])), "延伸": list(v.get("延伸", []))}
        for s, v in edges.items()
    }
    for src, v in edges.items():
        for dst in v.get("延伸", []):
            out.setdefault(dst, {"前置": [], "延伸": []})
            if src not in out[dst]["前置"]:
                out[dst]["前置"].append(src)
        for dst in v.get("前置", []):
            out.setdefault(dst, {"前置": [], "延伸": []})
            if src not in out[dst]["延伸"]:
                out[dst]["延伸"].append(src)
    return out


def _block(前置: list[tuple[str, str]], 延伸: list[tuple[str, str]]) -> str:
    lines = [SECTION_HEADER, ""]
    if 前置:
        lines.append(f"- **前置**：{_fmt(前置)}")
    if 延伸:
        lines.append(f"- **延伸**：{_fmt(延伸)}")
    if not 前置 and not 延伸:
        lines.append("🚧")
    lines.append("")
    return "\n".join(lines)


def inject_links(
    text: str,
    前置: list[tuple[str, str]],
    延伸: list[tuple[str, str]],
) -> str:
    """替换/新建 🔗 相关词条 段。"""
    block = _block(前置, 延伸)
    m = re.search(re.escape(SECTION_HEADER), text)
    if m:
        rest = text[m.end():]
        nxt = re.search(r"^##\s", rest, re.MULTILINE)
        end = m.end() + (nxt.start() if nxt else len(rest))
        return text[: m.start()] + block + ("\n" if not text[end:].startswith("\n") else "") + text[end:]
    # 段不存在：追加到文末
    sep = "" if text.endswith("\n") else "\n"
    return text + sep + "\n" + block


def _resolve_disp(edges_norm: dict, stem_to_path: dict[str, Path]) -> dict[str, str]:
    return {stem: _bare(stem) for stem in edges_norm}


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True, help="strand_map YAML 文件名（位于 scripts/）")
    ap.add_argument("--dir", required=True, help="学科目录")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    map_path = Path(__file__).parent / args.map
    cfg = yaml.safe_load(map_path.read_text(encoding="utf-8"))
    edges = build_reciprocal(cfg.get("edges", {}))

    base = REPO_ROOT / args.dir
    stem_to_path = {p.stem: p for p in base.glob("*.md")}
    disp = {stem: _bare(stem) for stem in stem_to_path}

    n_write = 0
    for stem, v in edges.items():
        p = stem_to_path.get(stem)
        if not p:
            print(f"  ⚠ map 中 {stem} 无对应词条文件，跳过")
            continue
        前置 = [(s, disp.get(s, _bare(s))) for s in v["前置"]]
        延伸 = [(s, disp.get(s, _bare(s))) for s in v["延伸"]]
        text = p.read_text(encoding="utf-8")
        new = inject_links(text, 前置, 延伸)
        if new != text:
            print(f"  🔗 {p.name}: 前置{len(前置)} 延伸{len(延伸)}")
            if args.apply:
                p.write_text(new, encoding="utf-8", newline="")
                n_write += 1
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n[{mode}] 注入 {len(edges)} 词条 / 写盘 {n_write}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest "00-元/scripts/tests/test_gen_ladder_links.py" -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 全量单测回归**

Run: `python -m pytest "00-元/scripts/tests/" -q`
Expected: 原 96 + 新 18 = 全过（无回归）

- [ ] **Step 6: 提交**

```bash
git add "00-元/scripts/gen_ladder_links.py" "00-元/scripts/tests/test_gen_ladder_links.py"
git commit -m "feat: add gen_ladder_links.py 纵向前置/延伸双向链注入"
```

---

## Task 5: 小学词条模板（去 🧒）

**Files:**
- Create: `00-元/模板/词条模板-小学.md`

- [ ] **Step 1: 写模板**

复制 `00-元/模板/词条模板.md`，删 `## 🧒 给 3-6 岁（共读版）` 段，正文仅留 📚 + 🎓。文件内容：

```markdown
---
title: 
aliases: []
学科: 
学段: []
主题: []
状态: 骨架
英文术语: 
首次共读: <% tp.date.now("YYYY-MM-DD") %>
最近共读: 
---

# {{title}}

> **一句话**：
> **English**: 

---

## 📚 给 6-12 岁（自读版）

🚧

## 🎓 给 12+（进阶版）

🚧

---

## 🌐 中英对照

### 词汇

| 中文 | English | 词性 | 例句 |
|------|---------|------|------|
|      |         |      |      |

### 例句（可朗读对照）

| 中文 | English |
|------|---------|
|      |         |

## 📖 相关绘本

- 🚧

## 🗣️ 家长讲解话术

- 孩子可能问 **"……"** → 
- **共读小活动**：

## 📺 讲解版（开屏对孩子讲时用）

🚧 占位。需要时用触发短语 6️⃣（轻量）或 7️⃣（精装）让 Claude 填充。

## 📑 出处与参考资料

- **教材**：
- **课标**：
- **百科**：
- **拓展阅读**：
- **生成校对**：Claude 生成于 YYYY-MM-DD，由家长核对

## 🔗 相关词条

🚧

## 📚 素材

🚧
```

- [ ] **Step 2: 提交**

```bash
git add "00-元/模板/词条模板-小学.md"
git commit -m "feat: add 小学词条模板（去 🧒3-6 层）"
```

---

## Task 6: Phase 0 — 抽检对照教材（执行）

**Files:** Create: `docs/superpowers/working/phase0-小学数学-抽检.md`

- [ ] **Step 1: 抽 3 册教材目录**

对 `素材/教材/ChinaTextbook/小学/数学/人教版/` 的 一上 / 三下 / 六上 三册 PDF，用 pdf 或 markitdown skill 抽目录页（前 5 页）与各单元标题。
Run（示例）：用 markitdown skill 转 PDF 目录页为 markdown，记录单元清单。

- [ ] **Step 2: 比对学习路径**

逐册把教材实际单元/黑体知识点 与 `00-元/学习路径/小学/数学/{01-一上,06-三下,11-六上}.md` 的「单元构成」「重点知识点全单」对照。

- [ ] **Step 3: 写抽检报告**

在 `docs/superpowers/working/phase0-小学数学-抽检.md` 记录：每册逐单元「教材有 / 路径有」对照表 + 结论（路径忠实 ✅ / 系统性漏 ⚠️ + 修正规则）。
路由：本步用 Opus/Sonnet 亲做（字符级判断），不调 v4-pro。

- [ ] **Step 4: 决策门**

若 ✅ 忠实 → 路径定为基准，进 Task 7。
若 ⚠️ 有系统性漏 → 先按修正规则回补对应学习路径文档（补「重点知识点全单」遗漏项），再进 Task 7。

- [ ] **Step 5: 提交**

```bash
git add "docs/superpowers/working/phase0-小学数学-抽检.md"
git commit -m "docs: Phase0 小学数学抽检对照教材报告"
```

---

## Task 7: Phase 1 — 有效性梳理（执行）

**Files:** Modify: `数学/*.md`（小学段，含 🧒 清理）；Create: `docs/superpowers/working/phase1-小学数学-记分卡.md`

- [ ] **Step 1: 清 🧒 层（先 dry）**

Run: `python "00-元/scripts/strip_kid_layer.py" --dir 数学 --grade 小学 --dry`
Expected: 列出含 🧒 段的小学数学词条（约 ≤81 条），人工抽看 2 条预览无误删。

- [ ] **Step 2: 清 🧒 层（apply）**

Run: `python "00-元/scripts/strip_kid_layer.py" --dir 数学 --grade 小学 --apply`
Expected: `[APPLY] ... 写盘 N`

- [ ] **Step 3: 跑有效性体检**

Run: `python "00-元/scripts/audit_entries.py" --dir 数学 --grade 小学 > "docs/superpowers/working/phase1-小学数学-记分卡.md"`
Expected: 生成记分卡，列不合规项。

- [ ] **Step 4: 自动可修项修复**

Run:
```bash
python "00-元/scripts/fix_wikilinks.py" --apply
python "00-元/scripts/fix_latex_delim.py" --apply
python "00-元/scripts/fix_stale_links.py" --apply
```
Expected: 裸链/LaTeX/stale 号链修复。

- [ ] **Step 5: 需人工项处理**

对记分卡剩余「缺教材引用 / 骨架层 / 缺 fm 字段」项，逐条人工补（教材引用查 `00-元/教材索引.md`）。复跑 Step 3 直至记分卡全绿。

- [ ] **Step 6: 提交**

```bash
git add "数学/" "docs/superpowers/working/phase1-小学数学-记分卡.md"
git commit -m "chore: Phase1 小学数学有效性梳理（清 🧒 + 修链 + 补引用）"
```

---

## Task 8: Phase 2 — 覆盖矩阵（执行）

**Files:** Create: `docs/superpowers/working/phase2-小学数学-覆盖矩阵.md`

- [ ] **Step 1: 生成覆盖矩阵**

Run: `python "00-元/scripts/coverage_matrix.py" --paths "00-元/学习路径/小学/数学" --dir 数学 > "docs/superpowers/working/phase2-小学数学-覆盖矩阵.md"`
Expected: 报告「已覆盖 N / 缺口 M」+ 缺口清单。

- [ ] **Step 2: 人工校缺口**

过缺口清单，剔除「同义已存在但 alias 没收」的伪缺口（这类回到 Task 7 给现有词条补 alias，不新建）；保留真缺口知识点。

- [ ] **Step 3: 提交**

```bash
git add "docs/superpowers/working/phase2-小学数学-覆盖矩阵.md"
git commit -m "docs: Phase2 小学数学覆盖矩阵 + 缺口清单"
```

---

## Task 9: Phase 3 — 扩容生成（执行）

**Files:** Create: `数学/NNN-*.md`（缺口新词条）

- [ ] **Step 1: 备 topics 清单**

把 Task 8 真缺口知识点整理为 `gen_atom_skeleton.py` 输入（每条含：知识点名 / 学期 / 教材 PDF 路径+单元 / strand）。教材路径查 `00-元/教材索引.md`。

- [ ] **Step 2: 批量生成骨架**

Run: `python "00-元/scripts/gen_atom_skeleton.py"`（按其 CLI 传 topics；用小学模板两层；route 批量走 v4-pro + 50% 自检）
Expected: 生成新词条 md，带学期序号前缀 + bare-name alias + 教材引用。

- [ ] **Step 3: 规范化**

Run:
```bash
python "00-元/scripts/fix_wikilinks.py" --apply
python "00-元/scripts/fix_latex_delim.py" --apply
```

- [ ] **Step 4: 新词条过体检**

Run: `python "00-元/scripts/audit_entries.py" --dir 数学 --grade 小学`
Expected: 新词条合规（不合规项回 Step 2/手工补）。

- [ ] **Step 5: 提交**

```bash
git add "数学/"
git commit -m "feat: Phase3 小学数学教材缺口扩容（新增 N 词条）"
```

---

## Task 10: Phase 4 — 纵向链接（执行）

**Files:** Create: `00-元/scripts/strand_map_数学小学.yaml`；Modify: `数学/*.md`

- [ ] **Step 1: 编写 strand_map**

据 spec §4 四领域，把小学数学全部词条（含新补）按 strand 排序并声明前后位。文件 `00-元/scripts/strand_map_数学小学.yaml`，schema：

```yaml
edges:
  "001-数数":   {strand: 数与代数, 前置: [], 延伸: ["003-1-10"]}
  "003-1-10":  {strand: 数与代数, 前置: ["001-数数"], 延伸: ["016-加法"]}
  "016-加法":   {strand: 数与代数, 前置: ["003-1-10"], 延伸: ["030-乘法"]}
  # ... 四 strand 全词条逐条
```
（仅需声明 延伸 即可，前置 由 build_reciprocal 自动回填；显式写双边亦可。）

- [ ] **Step 2: dry 预览注入**

Run: `python "00-元/scripts/gen_ladder_links.py" --map strand_map_数学小学.yaml --dir 数学 --dry`
Expected: 列各词条 前置/延伸 计数，无 ⚠ 缺文件（有则修 map 序号）。

- [ ] **Step 3: apply 注入**

Run: `python "00-元/scripts/gen_ladder_links.py" --map strand_map_数学小学.yaml --dir 数学 --apply`
Expected: `[APPLY] ... 写盘 N`

- [ ] **Step 4: 规范化 + 体检**

Run:
```bash
python "00-元/scripts/fix_wikilinks.py" --apply
python "00-元/scripts/audit_entries.py" --dir 数学 --grade 小学
```
Expected: 链接规范、体检全绿。

- [ ] **Step 5: 提交**

```bash
git add "00-元/scripts/strand_map_数学小学.yaml" "数学/"
git commit -m "feat: Phase4 小学数学纵向 strand 前置/延伸双向链"
```

---

## Task 11: Phase 5 — 验收 + 收尾

**Files:** Modify: `CLAUDE.md`

- [ ] **Step 1: 链接体检**

Run: `python "00-元/scripts/analyze_links.py"`
Expected: 对比试点前基线，小学数学段 断链↓、无入链↓；前置/延伸双向连通（抽查 3 条 strand 链首尾）。

- [ ] **Step 2: 覆盖复核**

Run: `python "00-元/scripts/coverage_matrix.py" --paths "00-元/学习路径/小学/数学" --dir 数学`
Expected: 缺口 = 0（或仅留人工判定的非词条项）。

- [ ] **Step 3: 进度刷新**

Run: `python "00-元/scripts/stats.py --write"`
Expected: CLAUDE.md 进度表更新。

- [ ] **Step 4: 全量单测**

Run: `python -m pytest "00-元/scripts/tests/" -q`
Expected: 全过。

- [ ] **Step 5: CLAUDE.md 落地备注**

在 CLAUDE.md「已完成进度」加：小学数学教材覆盖重设计试点完成（清 🧒 / 体检 / 覆盖 100% / 纵向链）；记录 3 个新工具 + strand_map 入工具箱清单。

- [ ] **Step 6: 提交**

```bash
git add "CLAUDE.md"
git commit -m "docs: 小学数学教材覆盖重设计试点验收 + CLAUDE.md 更新"
```

---

## Self-Review 结论

- **Spec 覆盖**：§3 基准→Task6；§4 strand→Task4/10；§5 模板去🧒→Task1/5；§6 五阶段→Task6-11；§7 三工具→Task1-4；§9 验收→Task11。无遗漏。
- **占位扫描**：无 TBD；执行类步骤（Phase0/3）给了具体命令与决策门，topics 内容依赖 Phase2 真实产出（合理，非占位）。
- **类型一致**：`extract_concepts`/`classify_concept`/`inject_links`/`build_reciprocal`/`strip_kid_section`/`check_*`/`audit_one` 跨任务签名一致；strand_map `edges` schema 与 `build_reciprocal` 入参一致。
