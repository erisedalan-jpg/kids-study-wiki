# 真题分析 v2 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现真题分析 v2 流水线 —— 6 脚本端到端把 1 张高考真题 PDF 转成「截图 + 摘要 + 指针」形式的 .md 词条 + 索引，含 L1/L2/L3 三层复审，pilot 通过后续跑剩余 18 卷。

**Architecture:** 题级 .md 存储（截图替代字符级 stem，根除 v1 字符级 bug）。流水线 6 步：PyMuPDF 题号 bbox 定位 + 截图 → markitdown 抽元数据 → v4-pro 摘要+考点 → sonnet/Opus 看图复验 → 渲染 → 索引聚合。

**Tech Stack:** Python 3.12, PyMuPDF (fitz), markitdown, _llm_router (DeepSeek v4-pro), pytest, Obsidian wikilink for backlinks.

**Spec:** `docs/superpowers/specs/2026-05-12-jilin-math-exam-v2-design.md`

---

## 阶段路线图

| 阶段 | 内容 | Task IDs |
|---|---|---|
| **A · 脚手架** | 6 脚本 + 2 配置 + ~35 单测 | Task 1-17 |
| **B · Pilot 端到端** | 跑通 2022 文卷 + 验收 gate | Task 18 |
| **C · 进度节恢复** | CLAUDE.md 更新 + commit | Task 19 |
| Phase 2/3（不在本 plan）| 续跑 18 卷 + 扩省份 | 复用同流程 |

---

## A · 脚手架

### Task 1: yaml 配置文件

**Files:**
- Create: `00-元/scripts/exam_pipeline_config.yaml`

- [ ] **Step 1: 写配置文件**

```yaml
# 真题流水线配置（v2）
# 控制：PDF 文件名 → 卷别/文理归一化、tag 池过滤
# 复用 v1 设计，无 schema 变化

paper_aliases:
  # 按长度从长到短排序，保证 "新课标Ⅱ卷" 命中 "新课标Ⅱ" 而非 "新课标"
  - ["新课标Ⅱ卷", "新课标Ⅱ"]
  - ["新课标Ⅰ卷", "新课标Ⅰ"]
  - ["全国乙卷",   "全国乙"]
  - ["全国甲卷",   "全国甲"]
  - ["北京卷",     "北京"]
  - ["上海卷",     "上海"]

gender_aliases:
  - ["（文）", "文"]
  - ["（理）", "理"]
  - ["（文科）", "文"]
  - ["（理科）", "理"]

# tag 池过滤：哪些 tag 进入高频统计
tag_pool_filters:
  数学:
    序号范围: [1, 9999]  # 全部数学概念
    额外纳入:
      - 单调性
      - 立体几何
      - 解三角形
      - 二面角
      - 导数应用
```

- [ ] **Step 2: Commit**

```bash
git add "00-元/scripts/exam_pipeline_config.yaml"
git commit -m "feat(exam): add v2 pipeline config (paper/gender aliases + tag pool)"
```

---

### Task 2: _exam_utils.py · 共享工具

**Files:**
- Create: `00-元/scripts/_exam_utils.py`
- Test: `00-元/scripts/tests/test_exam_utils.py`

- [ ] **Step 1: 写失败测试**

```python
# 00-元/scripts/tests/test_exam_utils.py
"""测试真题流水线共享工具。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _exam_utils import (  # noqa: E402
    build_atom_filename,
    build_screenshot_filename,
    load_config,
    normalize_gender,
    normalize_paper,
)


class TestNormalize(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()

    def test_paper_long_key_first(self):
        # "新课标Ⅱ卷" 应该命中 "新课标Ⅱ" 而非 "新课标"
        self.assertEqual(
            normalize_paper("2024年高考数学试卷（新课标Ⅱ卷）.pdf", self.cfg),
            "新课标Ⅱ",
        )

    def test_paper_quanguoyi(self):
        self.assertEqual(
            normalize_paper("2022年高考数学试卷（文）（全国乙卷）.pdf", self.cfg),
            "全国乙",
        )

    def test_gender_wen(self):
        self.assertEqual(normalize_gender("2022...（文）...pdf", self.cfg), "文")
        self.assertEqual(normalize_gender("2022...（理）...pdf", self.cfg), "理")

    def test_gender_unknown_defaults(self):
        self.assertEqual(normalize_gender("2024-新课标Ⅱ.pdf", self.cfg), "不分")


class TestFilenames(unittest.TestCase):
    def test_atom_filename_with_gender(self):
        self.assertEqual(build_atom_filename(2022, "文", "全国乙", 1), "2022-文-01.md")

    def test_atom_filename_without_gender(self):
        # 2023+ 不分文理用卷别
        self.assertEqual(build_atom_filename(2024, "不分", "新课标Ⅱ", 8), "2024-新课标Ⅱ-08.md")

    def test_screenshot_filename(self):
        self.assertEqual(
            build_screenshot_filename(2022, "文", "全国乙", 1, "q"),
            "2022-文-01.q.png",
        )
        self.assertEqual(
            build_screenshot_filename(2024, "不分", "新课标Ⅱ", 8, "a"),
            "2024-新课标Ⅱ-08.a.png",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试看 fail**

Run: `python -m unittest 00-元.scripts.tests.test_exam_utils -v`
Expected: ImportError (`_exam_utils` 尚未创建)

- [ ] **Step 3: 写实现**

```python
# 00-元/scripts/_exam_utils.py
"""真题流水线共享工具。

提供：
- load_config(): 读 exam_pipeline_config.yaml
- normalize_paper(): PDF 文件名 → 卷别短简称
- normalize_gender(): PDF 文件名 → 文/理/不分
- build_atom_filename(): 真题词条文件名（如 2022-文-01.md）
- build_screenshot_filename(): 截图文件名（含 .q.png / .a.png 后缀）
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT  # noqa: E402

CONFIG_PATH = REPO_ROOT / "00-元" / "scripts" / "exam_pipeline_config.yaml"


def load_config() -> dict[str, Any]:
    """读 exam_pipeline_config.yaml 并返回 dict。"""
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def normalize_paper(pdf_filename: str, cfg: dict[str, Any]) -> str:
    """PDF 文件名 → 卷别短简称。长 key 优先匹配。"""
    for pattern, simple in cfg["paper_aliases"]:
        if pattern in pdf_filename:
            return simple
    return "未知"


def normalize_gender(pdf_filename: str, cfg: dict[str, Any]) -> str:
    """PDF 文件名 → 文/理/不分。"""
    for pattern, gender in cfg["gender_aliases"]:
        if pattern in pdf_filename:
            return gender
    return "不分"


def build_atom_filename(year: int, gender: str, paper: str, qno: int) -> str:
    """真题词条文件名（无扩展前缀，跨年同名靠年份避免）。"""
    nn = f"{qno:02d}"
    if gender in ("文", "理"):
        return f"{year}-{gender}-{nn}.md"
    return f"{year}-{paper}-{nn}.md"


def build_screenshot_filename(year: int, gender: str, paper: str, qno: int, kind: str) -> str:
    """截图文件名 <year>-<gender|paper>-<qno>.<kind>.png

    kind: "q"(题面) 或 "a"(答案/解析)
    """
    if kind not in ("q", "a"):
        raise ValueError(f"kind 必须是 'q' 或 'a'，收到 {kind!r}")
    nn = f"{qno:02d}"
    prefix = gender if gender in ("文", "理") else paper
    return f"{year}-{prefix}-{nn}.{kind}.png"
```

- [ ] **Step 4: 跑测试看 pass**

Run: `python -m unittest 00-元.scripts.tests.test_exam_utils -v`
Expected: 7 tests pass

- [ ] **Step 5: Commit**

```bash
git add "00-元/scripts/_exam_utils.py" "00-元/scripts/tests/test_exam_utils.py"
git commit -m "feat(exam): _exam_utils with config load + paper/gender/filename helpers"
```

---

### Task 3: exam_screenshot.py · 题号 bbox 定位

**Files:**
- Create: `00-元/scripts/exam_screenshot.py`
- Test: `00-元/scripts/tests/test_exam_screenshot.py`

- [ ] **Step 1: 写失败测试**

```python
# 00-元/scripts/tests/test_exam_screenshot.py
"""测试题号 bbox 定位 + 截图生成。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_screenshot import find_question_anchors, find_answer_anchors  # noqa: E402


class TestFindAnchors(unittest.TestCase):
    def test_question_anchor_basic(self):
        """words 含 '1.' '集合' 应识别 qno=1 的 anchor。"""
        # words: list[(x0, y0, x1, y1, text, block_no, line_no, word_no)]
        words = [
            (10, 100, 20, 110, "1.", 0, 0, 0),
            (25, 100, 50, 110, "集合", 0, 0, 1),
        ]
        anchors = find_question_anchors(words, expected_max_qno=23)
        self.assertEqual(anchors[1]["y0"], 100)

    def test_question_anchor_rejects_decimal(self):
        """'0.04' 不应被识别为题号 '0.'"""
        words = [
            (10, 100, 30, 110, "0.04", 0, 0, 0),
        ]
        anchors = find_question_anchors(words, expected_max_qno=23)
        self.assertEqual(anchors, {})

    def test_question_anchor_increment_only(self):
        """题号必须递增（从 1 开始），跳号丢弃。"""
        words = [
            (10, 100, 20, 110, "1.", 0, 0, 0),
            (10, 200, 30, 210, "5.", 0, 1, 0),  # 跳号
            (10, 300, 20, 310, "2.", 0, 2, 0),
        ]
        anchors = find_question_anchors(words, expected_max_qno=23)
        self.assertIn(1, anchors)
        self.assertIn(2, anchors)
        self.assertNotIn(5, anchors)

    def test_answer_anchor_detects_bracket(self):
        """'【答案】' 或 '【 答 案 】' 都应识别为 answer anchor。"""
        words = [
            (10, 100, 50, 110, "【答案】", 0, 0, 0),
            (10, 200, 60, 210, "【 答 案 】", 0, 1, 0),
        ]
        anchors = find_answer_anchors(words)
        self.assertEqual(len(anchors), 2)
        self.assertEqual(anchors[0]["y0"], 100)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试看 fail**

Run: `python -m unittest 00-元.scripts.tests.test_exam_screenshot -v`
Expected: ImportError

- [ ] **Step 3: 写实现（题号 + 答案 anchor 定位）**

```python
# 00-元/scripts/exam_screenshot.py
"""真题截图生成（v2 Step 1）。

用 PyMuPDF 提取每个 PDF 页面的 word boxes（含 bbox），定位：
- 题号 anchor: 形如 "1." "23." 的 word，必须从 1 开始递增
- 答案 anchor: "【答案】" 或带空格的 "【 答 案 】"

然后按 题面区域 = (题号 N → 答案 anchor) / 解析区域 = (答案 anchor → 题号 N+1)
渲染 PNG 截图到 素材/真题截图/<省份>-<学科>/ 目录。

输出: questions.json（含 qno/bbox/page/截图相对路径）

CLI:
    python 00-元/scripts/exam_screenshot.py \\
        --pdf "素材/真题/.../2022年高考数学试卷（文）.pdf" \\
        --province 吉林 --subject 数学 --year 2022 \\
        --out docs/superpowers/working/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).parent))
from _exam_utils import (  # noqa: E402
    build_atom_filename,
    build_screenshot_filename,
    load_config,
    normalize_gender,
    normalize_paper,
)
from _utils import REPO_ROOT, setup_utf8  # noqa: E402


# 题号正则：行首数字 + 点 + 空白（不允许点后接数字，排除 0.04 / 1.6158 等小数）
QNO_TOKEN_RE = re.compile(r"^([1-9]\d?)[\.、．]$")


def find_question_anchors(
    words: list[tuple], expected_max_qno: int
) -> dict[int, dict[str, float]]:
    """找题号 anchor。

    words: PyMuPDF page.get_text("words") 返回的元组列表
           (x0, y0, x1, y1, text, block_no, line_no, word_no)
    返回: {qno: {"x0", "y0", "x1", "y1", "block_no", "line_no"}}

    题号必须从 1 开始严格递增，跳号丢弃。
    """
    candidates: list[tuple[int, dict]] = []
    for w in words:
        x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
        m = QNO_TOKEN_RE.match(text.strip())
        if not m:
            continue
        qno = int(m.group(1))
        if qno > expected_max_qno + 5:  # 容忍 +5 缓冲
            continue
        candidates.append((qno, {
            "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            "block_no": w[5] if len(w) > 5 else 0,
            "line_no": w[6] if len(w) > 6 else 0,
        }))

    # 按 y 坐标排序（页面阅读顺序），然后筛递增
    candidates.sort(key=lambda x: x[1]["y0"])
    result: dict[int, dict] = {}
    next_expected = 1
    for qno, info in candidates:
        if qno == next_expected:
            result[qno] = info
            next_expected = qno + 1
    return result


def find_answer_anchors(words: list[tuple]) -> list[dict[str, float]]:
    """找【答案】或【 答 案 】anchor。

    返回按 y 坐标排序的 list[{"x0", "y0", "x1", "y1"}]。
    """
    answer_re = re.compile(r"^【\s*答\s*案\s*】")
    anchors: list[dict] = []
    for w in words:
        text = w[4]
        if answer_re.match(text):
            anchors.append({
                "x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3],
            })
    anchors.sort(key=lambda a: a["y0"])
    return anchors
```

- [ ] **Step 4: 跑测试看 pass**

Run: `python -m unittest 00-元.scripts.tests.test_exam_screenshot -v`
Expected: 4 tests pass

- [ ] **Step 5: Commit**

```bash
git add "00-元/scripts/exam_screenshot.py" "00-元/scripts/tests/test_exam_screenshot.py"
git commit -m "feat(exam): screenshot anchor finders (question + answer markers)"
```

---

### Task 4: exam_screenshot.py · 截图渲染逻辑

**Files:**
- Modify: `00-元/scripts/exam_screenshot.py`（增加截图渲染函数）
- Modify: `00-元/scripts/tests/test_exam_screenshot.py`（增加测试）

- [ ] **Step 1: 加测试 (mock fitz Page)**

在 `00-元/scripts/tests/test_exam_screenshot.py` 类外加：

```python
from unittest.mock import MagicMock


class TestRegionsAndRender(unittest.TestCase):
    def _make_words(self, items):
        """items: list[(x0,y0,x1,y1,text)]"""
        return [(x[0], x[1], x[2], x[3], x[4], 0, i, 0) for i, x in enumerate(items)]

    def test_compute_question_regions_single_page(self):
        """同页 Q1: 题号→answer 之间是题面；answer→Q2 之间是解析。"""
        from exam_screenshot import compute_regions  # noqa
        words = self._make_words([
            (10, 100, 20, 110, "1."),
            (25, 100, 80, 110, "集合A=..."),
            (10, 200, 50, 210, "【答案】"),
            (10, 300, 50, 310, "解析内容"),
            (10, 400, 20, 410, "2."),
        ])
        q_anchors = find_question_anchors(words, 5)
        a_anchors = find_answer_anchors(words)
        regions = compute_regions(q_anchors, a_anchors, page_height=600)
        # Q1 题面: y=100→200 (answer 起)
        self.assertEqual(regions[1]["q"]["y0"], 100)
        self.assertAlmostEqual(regions[1]["q"]["y1"], 200, delta=5)
        # Q1 解析: y=200→400 (Q2 起)
        self.assertEqual(regions[1]["a"]["y0"], 200)
        self.assertAlmostEqual(regions[1]["a"]["y1"], 400, delta=5)

    def test_compute_question_regions_no_answer_uses_next_q(self):
        """如果没找到 answer anchor（罕见），题面延伸到下一题号。"""
        from exam_screenshot import compute_regions
        words = self._make_words([
            (10, 100, 20, 110, "1."),
            (10, 400, 20, 410, "2."),
        ])
        q_anchors = find_question_anchors(words, 5)
        a_anchors = find_answer_anchors(words)
        regions = compute_regions(q_anchors, a_anchors, page_height=600)
        self.assertAlmostEqual(regions[1]["q"]["y1"], 400, delta=5)
        self.assertIsNone(regions[1]["a"])
```

- [ ] **Step 2: 跑测试看 fail**

Run: `python -m unittest 00-元.scripts.tests.test_exam_screenshot.TestRegionsAndRender -v`
Expected: ImportError `compute_regions`

- [ ] **Step 3: 写实现**

在 `00-元/scripts/exam_screenshot.py` 加：

```python
def compute_regions(
    q_anchors: dict[int, dict],
    a_anchors: list[dict],
    page_height: float,
) -> dict[int, dict[str, dict | None]]:
    """根据题号+答案 anchor 算每题的截图区域。

    返回 {qno: {"q": region_or_None, "a": region_or_None}}
    region = {"x0": 0, "y0": float, "x1": page_width, "y1": float}

    策略:
    - 题面 region: y0=题号 y0, y1=该题对应 answer anchor 的 y0 (若有)，否则下一题题号 y0
    - 解析 region: y0=answer y0, y1=下一题题号 y0（若无下一题用 page_height）
    """
    sorted_qnos = sorted(q_anchors.keys())
    regions: dict[int, dict] = {}
    for i, qno in enumerate(sorted_qnos):
        q_y0 = q_anchors[qno]["y0"]
        next_q_y0 = (
            q_anchors[sorted_qnos[i + 1]]["y0"]
            if i + 1 < len(sorted_qnos)
            else page_height
        )
        # 找该题区间内第一个 answer anchor
        a_in_range = next(
            (a for a in a_anchors if q_y0 < a["y0"] < next_q_y0), None
        )
        if a_in_range:
            q_region = {"y0": q_y0, "y1": a_in_range["y0"]}
            a_region = {"y0": a_in_range["y0"], "y1": next_q_y0}
        else:
            q_region = {"y0": q_y0, "y1": next_q_y0}
            a_region = None
        regions[qno] = {"q": q_region, "a": a_region}
    return regions
```

- [ ] **Step 4: 跑测试看 pass**

Run: `python -m unittest 00-元.scripts.tests.test_exam_screenshot.TestRegionsAndRender -v`
Expected: 2 tests pass

- [ ] **Step 5: Commit**

```bash
git add "00-元/scripts/exam_screenshot.py" "00-元/scripts/tests/test_exam_screenshot.py"
git commit -m "feat(exam): compute_regions splits Q area by answer anchor"
```

---

### Task 5: exam_screenshot.py · CLI + L1 自动断言

**Files:**
- Modify: `00-元/scripts/exam_screenshot.py`

- [ ] **Step 1: 加 CLI 主流程**

在 `00-元/scripts/exam_screenshot.py` 末尾追加：

```python
def render_screenshots(
    pdf_path: Path,
    *,
    province: str,
    subject: str,
    year: int,
    expected_max_qno: int = 25,
    dpi: int = 200,
) -> dict[str, Any]:
    """从 PDF 提取题号 + 渲染截图到目标目录。

    返回 questions.json 数据（含 qno / page / 截图相对路径）。
    """
    cfg = load_config()
    fname = pdf_path.name
    paper = normalize_paper(fname, cfg)
    gender = normalize_gender(fname, cfg)
    paper_id = f"{year}-{gender}-{paper}"

    # 截图输出目录
    out_dir = REPO_ROOT / "素材" / "真题截图" / f"{province}-{subject}"
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    all_questions: list[dict] = []
    all_q_anchors: dict[int, tuple[int, dict]] = {}  # qno -> (page_no, anchor)
    all_a_anchors_by_page: dict[int, list[dict]] = {}

    # 第一遍：扫所有页面找 anchor
    for page_no, page in enumerate(doc):
        words = page.get_text("words")
        q_anchors = find_question_anchors(words, expected_max_qno)
        # 全局合并，按 page+y 排序
        for qno, info in q_anchors.items():
            if qno not in all_q_anchors:  # 首次出现优先
                all_q_anchors[qno] = (page_no, info)
        all_a_anchors_by_page[page_no] = find_answer_anchors(words)

    # 第二遍：渲染每题截图
    for qno in sorted(all_q_anchors.keys()):
        page_no, q_info = all_q_anchors[qno]
        page = doc[page_no]
        a_anchors = all_a_anchors_by_page.get(page_no, [])
        # 用本页 q_anchors + a_anchors 算 region（跨页题暂用本页截到底）
        page_words = page.get_text("words")
        page_q_anchors = find_question_anchors(page_words, expected_max_qno)
        regions = compute_regions(page_q_anchors, a_anchors, page.rect.height)
        if qno not in regions:
            continue  # 跨页题：本页找不到 qno 起点
        q_region = regions[qno]["q"]
        a_region = regions[qno]["a"]

        # 渲染 q.png
        q_filename = build_screenshot_filename(year, gender, paper, qno, "q")
        q_path = out_dir / q_filename
        clip = fitz.Rect(0, q_region["y0"], page.rect.width, q_region["y1"])
        pix = page.get_pixmap(clip=clip, dpi=dpi)
        pix.save(str(q_path))

        # 渲染 a.png（可能 None）
        a_filename = None
        if a_region:
            a_filename = build_screenshot_filename(year, gender, paper, qno, "a")
            a_path = out_dir / a_filename
            clip_a = fitz.Rect(0, a_region["y0"], page.rect.width, a_region["y1"])
            pix_a = page.get_pixmap(clip=clip_a, dpi=dpi)
            pix_a.save(str(a_path))

        all_questions.append({
            "qno": qno,
            "page": page_no + 1,  # 用户友好的 1-indexed
            "题面图": f"素材/真题截图/{province}-{subject}/{q_filename}",
            "解析图": f"素材/真题截图/{province}-{subject}/{a_filename}" if a_filename else "",
        })

    doc.close()
    rel_pdf = pdf_path.relative_to(REPO_ROOT) if pdf_path.is_relative_to(REPO_ROOT) else pdf_path
    return {
        "paper_id": paper_id,
        "year": year,
        "gender": gender,
        "paper": paper,
        "subject": subject,
        "province": province,
        "source_pdf": str(rel_pdf).replace("\\", "/"),
        "questions": all_questions,
    }


def assert_screenshot_quality(qa: dict[str, Any], expected_qno_range: tuple[int, int]) -> list[str]:
    """L1 自动断言。返回违规列表（空 = 通过）。"""
    violations: list[str] = []
    n = len(qa["questions"])
    lo, hi = expected_qno_range
    if not (lo <= n <= hi):
        violations.append(f"题数 {n} 不在期望范围 {lo}-{hi}")
    for q in qa["questions"]:
        q_img_path = REPO_ROOT / q["题面图"]
        if not q_img_path.exists():
            violations.append(f"Q{q['qno']}: 题面图不存在 {q['题面图']}")
            continue
        size = q_img_path.stat().st_size
        if size < 10 * 1024:
            violations.append(f"Q{q['qno']}: 题面图过小 ({size} bytes < 10KB)")
        if q.get("解析图"):
            a_img_path = REPO_ROOT / q["解析图"]
            if not a_img_path.exists():
                violations.append(f"Q{q['qno']}: 解析图不存在")
    return violations


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--province", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out", default="docs/superpowers/working/")
    ap.add_argument("--expected-min", type=int, default=18, help="期望最少题数（含）")
    ap.add_argument("--expected-max", type=int, default=25, help="期望最多题数（含）")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()

    qa = render_screenshots(
        Path(args.pdf),
        province=args.province,
        subject=args.subject,
        year=args.year,
        expected_max_qno=args.expected_max,
        dpi=args.dpi,
    )

    violations = assert_screenshot_quality(qa, (args.expected_min, args.expected_max))
    if violations:
        print("L1 断言失败:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    out_dir = REPO_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.province}-{args.subject}-{qa['paper_id']}-questions.json"
    out_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: 截图 {len(qa['questions'])} 题 + questions.json → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 跑全部测试**

Run: `python -m unittest discover -s 00-元/scripts/tests`
Expected: 11+ tests pass

- [ ] **Step 3: Commit**

```bash
git add "00-元/scripts/exam_screenshot.py"
git commit -m "feat(exam): screenshot CLI + L1 quality assertions"
```

---

### Task 6: exam_extract_meta.py · 答案与解析文本抓取

**Files:**
- Create: `00-元/scripts/exam_extract_meta.py`
- Test: `00-元/scripts/tests/test_exam_extract_meta.py`

- [ ] **Step 1: 写失败测试**

```python
# 00-元/scripts/tests/test_exam_extract_meta.py
"""测试 markitdown 元数据抽取。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_extract_meta import (  # noqa: E402
    extract_answer,
    extract_solution_text,
    split_by_question,
)


class TestSplitByQuestion(unittest.TestCase):
    def test_split_basic(self):
        md = """前置文本
1. 第一题题面
【答案】A
【解析】xxx
2. 第二题题面
【答案】B
"""
        chunks = split_by_question(md)
        self.assertEqual(set(chunks.keys()), {1, 2})
        self.assertIn("第一题题面", chunks[1])
        self.assertIn("第二题题面", chunks[2])

    def test_split_skips_decimal_in_table(self):
        """0.04 在表格里不应被识别为题号 0."""
        md = """1. 题面
0.04 0.06
【答案】A
"""
        chunks = split_by_question(md)
        self.assertEqual(list(chunks.keys()), [1])


class TestExtractAnswer(unittest.TestCase):
    def test_simple_letter(self):
        chunk = "题面\n【答案】A\n【解析】..."
        self.assertEqual(extract_answer(chunk), "A")

    def test_spaced_bracket(self):
        chunk = "题面\n【 答 案 】B\n【解析】..."
        self.assertEqual(extract_answer(chunk), "B")

    def test_multi_choice(self):
        chunk = "题面\n【答案】ABD\n"
        self.assertEqual(extract_answer(chunk), "ABD")

    def test_truncates_long_answer(self):
        """答案字段超过 50 字符截断（防答案块整体串入）。"""
        long_text = "x" * 100
        chunk = f"题面\n【答案】{long_text}\n"
        result = extract_answer(chunk)
        self.assertLessEqual(len(result), 50)


class TestExtractSolutionText(unittest.TestCase):
    def test_captures_analysis_and_detail(self):
        chunk = "【答案】A\n【解析】\n【分析】先算...\n【详解】具体...\n"
        sol = extract_solution_text(chunk)
        self.assertIn("先算", sol)
        self.assertIn("具体", sol)

    def test_empty_when_no_solution_marker(self):
        chunk = "题面\n【答案】A\n"
        self.assertEqual(extract_solution_text(chunk), "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试看 fail**

Run: `python -m unittest 00-元.scripts.tests.test_exam_extract_meta -v`
Expected: ImportError

- [ ] **Step 3: 写实现**

```python
# 00-元/scripts/exam_extract_meta.py
"""真题元数据抽取（v2 Step 2）。

用 markitdown 把 PDF 转 markdown，然后正则抽取每题的 answer 文本 + 解析关键文本。
这些元数据用于 Step 3 (v4-pro 摘要+考点) 的输入。

不抓题面 stem —— 题面由 exam_screenshot.py 截图保真，markdown 只存元数据。

CLI:
    python 00-元/scripts/exam_extract_meta.py \\
        --questions docs/superpowers/working/吉林-数学-2022-文-全国乙-questions.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from markitdown import MarkItDown

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402


# 题号边界（同 v1 修复版）：1-9 开头，点后非数字（防小数误识别）
QNO_RE = re.compile(r"^\s*([1-9]\d?)\s*[\.、．](?!\d)\s*", re.MULTILINE)
# 答案标签兼容 "【答案】" 和 "【 答 案 】"
ANSWER_TAG_RE = re.compile(r"【\s*答\s*案\s*】([^\n【]*)")
# 解析段
SOLUTION_TAG_RE = re.compile(r"【\s*解\s*析\s*】(.+)", re.DOTALL)


def split_by_question(md_text: str) -> dict[int, str]:
    """按题号切分 markdown，返回 {qno: chunk}。

    题号递增约束：从 1 开始，跳号忽略。
    """
    matches = list(QNO_RE.finditer(md_text))
    chunks: dict[int, str] = {}
    accepted_qnos: list[int] = []
    for i, m in enumerate(matches):
        qno = int(m.group(1))
        if accepted_qnos and qno != accepted_qnos[-1] + 1:
            continue
        if not accepted_qnos and qno != 1:
            continue
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        chunks[qno] = md_text[body_start:body_end].strip()
        accepted_qnos.append(qno)
    return chunks


def extract_answer(chunk: str, max_len: int = 50) -> str:
    """从题 chunk 抽答案，截断到 max_len 字符。"""
    m = ANSWER_TAG_RE.search(chunk)
    if not m:
        return ""
    return m.group(1).strip()[:max_len]


def extract_solution_text(chunk: str) -> str:
    """抽 chunk 中 【解析】之后的全部文本（含【分析】【详解】【小问】等）。"""
    m = SOLUTION_TAG_RE.search(chunk)
    if not m:
        return ""
    return m.group(1).strip()


def extract_meta(pdf_path: Path) -> dict[int, dict[str, str]]:
    """主入口：PDF → {qno: {"answer", "solution_text"}}"""
    md = MarkItDown()
    result = md.convert(str(pdf_path))
    text = result.text_content
    chunks = split_by_question(text)
    return {
        qno: {
            "answer": extract_answer(chunk),
            "solution_text": extract_solution_text(chunk),
        }
        for qno, chunk in chunks.items()
    }


def assert_meta_quality(qa: dict[str, Any]) -> list[str]:
    """L1 自动断言: 每题 answer 非空 / solution_text 长度 > 30 / answer ≤ 50."""
    violations: list[str] = []
    for q in qa["questions"]:
        qno = q["qno"]
        ans = q.get("answer", "")
        sol = q.get("solution_text", "")
        if not ans:
            violations.append(f"Q{qno}: answer 为空")
        if len(ans) > 50:
            violations.append(f"Q{qno}: answer 超长 ({len(ans)} > 50)")
        if len(sol) < 30:
            violations.append(f"Q{qno}: solution_text 过短 ({len(sol)} < 30)")
    return violations


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    args = ap.parse_args()

    qa_path = Path(args.questions)
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    pdf_path = REPO_ROOT / qa["source_pdf"]
    meta = extract_meta(pdf_path)

    # 合并到 questions.json
    for q in qa["questions"]:
        m = meta.get(q["qno"], {})
        q["answer"] = m.get("answer", "")
        q["solution_text"] = m.get("solution_text", "")

    violations = assert_meta_quality(qa)
    if violations:
        print("L1 断言失败:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        # 不直接 fail，存疑题在后续 LLM 步骤中可能仍能 enrich

    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: 提取 {len(meta)} 题元数据 → {qa_path}")
    print(f"L1 违规: {len(violations)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试**

Run: `python -m unittest 00-元.scripts.tests.test_exam_extract_meta -v`
Expected: 7 tests pass

- [ ] **Step 5: Commit**

```bash
git add "00-元/scripts/exam_extract_meta.py" "00-元/scripts/tests/test_exam_extract_meta.py"
git commit -m "feat(exam): markitdown answer/solution extractor with L1 assertions"
```

---

### Task 7: exam_enrich.py · v4-pro 摘要 + 考点

**Files:**
- Create: `00-元/scripts/exam_enrich.py`
- Test: `00-元/scripts/tests/test_exam_enrich.py`

- [ ] **Step 1: 写失败测试（mock LLM）**

```python
# 00-元/scripts/tests/test_exam_enrich.py
"""测试 v4-pro 摘要+考点抽取。"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_enrich import parse_llm_output, enrich_question, SYSTEM_PROMPT  # noqa: E402


class TestParseLLMOutput(unittest.TestCase):
    def test_normal_three_lines(self):
        text = "考集合的交集运算\n集合的运算, 并集\n易"
        r = parse_llm_output(text)
        self.assertEqual(r["summary"], "考集合的交集运算")
        self.assertEqual(r["tags"], ["集合的运算", "并集"])
        self.assertEqual(r["difficulty"], "易")

    def test_chinese_separators(self):
        text = "线性规划题\n线性规划、约束条件；最值\n中"
        r = parse_llm_output(text)
        self.assertEqual(set(r["tags"]), {"线性规划", "约束条件", "最值"})

    def test_with_prefix(self):
        text = "摘要：考向量数量积\n考点：向量数量积, 向量模\n难度：难"
        r = parse_llm_output(text)
        self.assertIn("向量数量积", r["summary"])
        self.assertIn("向量数量积", r["tags"])
        self.assertEqual(r["difficulty"], "难")

    def test_empty_returns_error(self):
        r = parse_llm_output("")
        self.assertIn("parse_error", r)


class TestEnrichQuestion(unittest.TestCase):
    @patch("exam_enrich.call")
    def test_basic_enrich(self, mock_call):
        mock_call.return_value = MagicMock(
            text="考集合运算\n集合的运算, 并集\n易",
            model="deepseek-v4-pro",
        )
        q = {"qno": 1, "solution_text": "M 与 N 的交集计算..."}
        result = enrich_question(q)
        self.assertEqual(result["summary"], "考集合运算")
        self.assertEqual(result["tags"], ["集合的运算", "并集"])
        self.assertEqual(result["difficulty"], "易")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试看 fail**

Run: `python -m unittest 00-元.scripts.tests.test_exam_enrich -v`
Expected: ImportError

- [ ] **Step 3: 写实现**

```python
# 00-元/scripts/exam_enrich.py
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
```

- [ ] **Step 4: 跑测试**

Run: `python -m unittest 00-元.scripts.tests.test_exam_enrich -v`
Expected: 5 tests pass

- [ ] **Step 5: Commit**

```bash
git add "00-元/scripts/exam_enrich.py" "00-元/scripts/tests/test_exam_enrich.py"
git commit -m "feat(exam): v4-pro enrich (summary + tags + difficulty)"
```

---

### Task 8: exam_verify.py · L2 sonnet/Opus 看图复验

**Files:**
- Create: `00-元/scripts/exam_verify.py`
- Test: `00-元/scripts/tests/test_exam_verify.py`

- [x] **Step 1: 写失败测试**

```python
# 00-元/scripts/tests/test_exam_verify.py
"""测试 L2 复验队列 (prepare/ingest)。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_verify import (  # noqa: E402
    parse_verdict_response,
    render_verify_prompt,
)


class TestRenderVerifyPrompt(unittest.TestCase):
    def test_prompt_contains_image_and_tags(self):
        q = {
            "qno": 1,
            "题面图": "素材/真题截图/吉林-数学/2022-文-01.q.png",
            "tags": ["集合的运算", "并集"],
            "summary": "考集合的交集运算。",
        }
        prompt = render_verify_prompt(q)
        self.assertIn("2022-文-01.q.png", prompt)
        self.assertIn("集合的运算", prompt)
        self.assertIn("并集", prompt)
        self.assertIn("吻合", prompt)  # 评判选项


class TestParseVerdictResponse(unittest.TestCase):
    def test_pass(self):
        r = parse_verdict_response("吻合\ntags 与题面一致")
        self.assertEqual(r["verdict"], "吻合")
        self.assertEqual(r["note"], "tags 与题面一致")

    def test_partial(self):
        r = parse_verdict_response("部分偏差\ntags 中 '并集' 应改为 '交集'")
        self.assertEqual(r["verdict"], "部分偏差")
        self.assertIn("交集", r["note"])

    def test_severe(self):
        r = parse_verdict_response("严重偏差\n该题考的是导数不是集合")
        self.assertEqual(r["verdict"], "严重偏差")

    def test_unknown(self):
        r = parse_verdict_response("不确定")
        self.assertEqual(r["verdict"], "未识别")

    def test_empty(self):
        r = parse_verdict_response("")
        self.assertEqual(r["verdict"], "调用失败")


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: 跑测试看 fail**

Run: `python -m unittest 00-元.scripts.tests.test_exam_verify -v`
Expected: ImportError

- [x] **Step 3: 写实现**

```python
# 00-元/scripts/exam_verify.py
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
```

- [x] **Step 4: 跑测试**

Run: `python -m unittest 00-元.scripts.tests.test_exam_verify -v`
Expected: 5 tests pass — 实测 8 tests pass (扩展含 Fix1/2/4/5)

- [x] **Step 5: Commit** — 已 commit。后续大量扩展（subject-aware/paper_id-collision/双重复核）已并入大批量 verify 工作流；详见 redo_severe_2026-05-15.log + commit 历史 (`c00cd38c` Obsidian Git 拦截) 与 `redo_severe.sh`。

---

### Task 9: exam_render.py · 渲染词条 .md

**Files:**
- Create: `00-元/scripts/exam_render.py`
- Test: `00-元/scripts/tests/test_exam_render.py`

- [ ] **Step 1: 写失败测试**

```python
# 00-元/scripts/tests/test_exam_render.py
"""测试 v2 词条渲染。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_render import render_atom  # noqa: E402


class TestRenderAtom(unittest.TestCase):
    def setUp(self):
        self.qa_meta = {
            "year": 2022,
            "gender": "文",
            "paper": "全国乙",
            "subject": "数学",
            "province": "吉林",
            "source_pdf": "素材/真题/吉林/.../2022.pdf",
        }
        self.q = {
            "qno": 1,
            "page": 1,
            "题面图": "素材/真题截图/吉林-数学/2022-文-01.q.png",
            "解析图": "素材/真题截图/吉林-数学/2022-文-01.a.png",
            "answer": "A",
            "summary": "考集合的交集运算",
            "tags": ["集合的运算", "并集"],
            "difficulty": "易",
        }

    def test_frontmatter_fields_present(self):
        text = render_atom(self.qa_meta, self.q)
        for field in ["title:", "学科:", "年份:", "卷别:", "文理:", "题号:",
                       "考点:", "答案:", "PDF页码:", "题面图:", "解析图:"]:
            self.assertIn(field, text, f"missing {field}")

    def test_includes_screenshots(self):
        text = render_atom(self.qa_meta, self.q)
        self.assertIn("![](../../素材/真题截图/吉林-数学/2022-文-01.q.png)", text)
        self.assertIn("![](../../素材/真题截图/吉林-数学/2022-文-01.a.png)", text)

    def test_includes_tags_backlinks(self):
        text = render_atom(self.qa_meta, self.q)
        self.assertIn("[[314-集合的运算|集合的运算]]", text)
        self.assertIn("[[并集]]", text)

    def test_summary_section(self):
        text = render_atom(self.qa_meta, self.q)
        self.assertIn("考集合的交集运算", text)

    def test_status_done_when_tags_nonempty(self):
        text = render_atom(self.qa_meta, self.q)
        self.assertIn("录入状态: 已入库", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试看 fail**

Run: `python -m unittest 00-元.scripts.tests.test_exam_render -v`
Expected: ImportError

- [ ] **Step 3: 写实现**

```python
# 00-元/scripts/exam_render.py
"""v2 词条渲染（Step 4）。

输入: questions.json (含 enrich 后的全部字段)
输出: 真题/<省份>-<学科>/*.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _exam_utils import build_atom_filename  # noqa: E402
from _utils import REPO_ROOT, setup_utf8  # noqa: E402


# 题型按题号 + 总题数启发式（沿用 v1）
def classify_qtype(qno: int, total: int) -> str:
    if total <= 20:
        if qno <= 11:
            return "选择"
        if qno <= 14:
            return "填空"
        return "解答"
    if qno <= 12:
        return "选择"
    if qno <= 16:
        return "填空"
    return "解答"


def classify_score(qno: int, qtype: str, year: int, total: int) -> int:
    """分值按年份+总题数表查（沿用 v1 修复）。"""
    if qtype in ("选择", "填空"):
        return 5
    if total == 19 and qno == 19:
        return 17
    if total == 23 and qno >= 22:
        return 10  # 2022 全国乙 选做题
    return 12


def render_atom(qa_meta: dict[str, Any], q: dict[str, Any]) -> str:
    """渲染单题 markdown。"""
    year = qa_meta["year"]
    gender = qa_meta["gender"]
    paper = qa_meta["paper"]
    subject = qa_meta["subject"]
    province = qa_meta["province"]
    qno = q["qno"]
    nn = f"{qno:02d}"
    total_q = qa_meta.get("total_q", 23)

    title = build_atom_filename(year, gender, paper, qno).removesuffix(".md")
    aliases = [
        title,
        f"{year}{province}{subject}{paper}-{nn}",
        f"{year}年{paper}{subject}第{qno}题",
    ]
    qtype = classify_qtype(qno, total_q)
    score = classify_score(qno, qtype, year, total_q)

    tags = q.get("tags", [])
    state = "已入库" if tags else "待人工核对"

    fm_lines = [
        "---",
        f"title: {title}",
        f"aliases: [{', '.join(aliases)}]",
        f"学科: {subject}",
        "学段: 高考",
        f"省份: {province}",
        f"年份: {year}",
        f"卷别: {paper}",
        f"文理: {gender}",
        f"题号: {qno}",
        f"题型: {qtype}",
        f"分值: {score}",
        f"考点: [{', '.join(tags)}]",
        f"难度: {q.get('difficulty', '中')}",
        f"PDF: {qa_meta['source_pdf']}",
        f"PDF页码: {q.get('page', 0)}",
        f"题面图: {q.get('题面图', '')}",
        f"解析图: {q.get('解析图', '')}",
        f"答案: {q.get('answer', '')}",
        f"录入状态: {state}",
        "---",
        "",
    ]

    # 截图路径用相对路径（从 真题/<province>-<subject>/ 到 素材/...，两级 ../）
    q_img_rel = "../../" + q.get("题面图", "")
    a_img_rel = "../../" + q.get("解析图", "") if q.get("解析图") else ""

    body_lines = [
        "## 题面",
        "",
        f"![]({q_img_rel})",
        "",
        "## 摘要",
        "",
        q.get("summary", "（待补）"),
        "",
        "## 关联考点",
        "",
    ]
    for tag in tags:
        body_lines.append(f"- [[{tag}]]")
    body_lines += [
        "",
        "## 答案与解析",
        "",
    ]
    if a_img_rel:
        body_lines += [f"![]({a_img_rel})", ""]
    body_lines += [
        f"> 📄 原 PDF 第 {q.get('page', 0)} 页：`{qa_meta['source_pdf']}`",
        "",
    ]
    return "\n".join(fm_lines + body_lines)


def render_paper(qa: dict[str, Any]) -> list[Path]:
    """渲染整张卷的所有题。"""
    out_dir = REPO_ROOT / "真题" / f"{qa['province']}-{qa['subject']}"
    out_dir.mkdir(parents=True, exist_ok=True)
    qa_meta = dict(qa)
    qa_meta["total_q"] = len(qa["questions"])

    written: list[Path] = []
    for q in qa["questions"]:
        fname = build_atom_filename(qa["year"], qa["gender"], qa["paper"], q["qno"])
        path = out_dir / fname
        path.write_text(render_atom(qa_meta, q), encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    args = ap.parse_args()

    qa = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    files = render_paper(qa)
    print(f"OK: 渲染 {len(files)} 题词条到 真题/{qa['province']}-{qa['subject']}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试**

Run: `python -m unittest 00-元.scripts.tests.test_exam_render -v`
Expected: 5 tests pass

- [ ] **Step 5: Commit**

```bash
git add "00-元/scripts/exam_render.py" "00-元/scripts/tests/test_exam_render.py"
git commit -m "feat(exam): render v2 atom .md (screenshot + summary + pointer)"
```

---

### Task 10: exam_index.py · 索引 + 反链回填

**Files:**
- Create: `00-元/scripts/exam_index.py`
- Test: `00-元/scripts/tests/test_exam_index.py`

- [ ] **Step 1: 写失败测试**

```python
# 00-元/scripts/tests/test_exam_index.py
"""测试索引聚合 + 反链回填。"""
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exam_index import build_freq_table, build_gap_list, BACKLINK_START, BACKLINK_END  # noqa: E402


class TestFreqTable(unittest.TestCase):
    def test_count_tags(self):
        atoms = [
            {"考点": ["集合的运算", "并集"], "题号": 1, "卷别": "全国乙", "文理": "文"},
            {"考点": ["集合的运算", "交集"], "题号": 2, "卷别": "全国乙", "文理": "文"},
            {"考点": ["函数最值"], "题号": 5, "卷别": "全国乙", "文理": "文"},
        ]
        freq = build_freq_table(atoms)
        self.assertEqual(freq["集合的运算"], 2)
        self.assertEqual(freq["并集"], 1)
        self.assertEqual(freq["函数最值"], 1)


class TestGapList(unittest.TestCase):
    def test_gap_detection(self):
        atoms = [
            {"考点": ["集合的运算", "未知概念"], "题号": 1, "卷别": "全国乙", "文理": "文"},
        ]
        existing = {"集合的运算"}  # lexicon
        gaps = build_gap_list(atoms, existing)
        self.assertIn("未知概念", gaps)
        self.assertNotIn("集合的运算", gaps)


class TestBacklinkMarkers(unittest.TestCase):
    def test_markers_defined(self):
        self.assertEqual(BACKLINK_START, "<!-- exam-backlinks-start -->")
        self.assertEqual(BACKLINK_END, "<!-- exam-backlinks-end -->")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试看 fail**

Run: `python -m unittest 00-元.scripts.tests.test_exam_index -v`
Expected: ImportError

- [ ] **Step 3: 写实现**

```python
# 00-元/scripts/exam_index.py
"""真题索引 + 反链回填（v2 Step 5）。

输出 4 份索引到 索引/真题/:
  - <省份><学科>-高频考点.md
  - <省份><学科>-题型×考点交叉表.md
  - <省份><学科>-缺口词条清单.md
  - <省份><学科>-试卷地图.md

同时把"该考点命中的真题题号列表"作为反链段追加到 学科/<考点>.md 末尾。
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, bare_name, iter_entries, read_frontmatter, setup_utf8  # noqa: E402


BACKLINK_START = "<!-- exam-backlinks-start -->"
BACKLINK_END = "<!-- exam-backlinks-end -->"


def parse_atom_fm(text: str) -> dict[str, Any]:
    """解析真题词条 frontmatter（含 list 字段如 考点）。"""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm: dict[str, Any] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        # list 字段
        if v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            fm[k] = [t.strip() for t in inner.split(",") if t.strip()]
        else:
            fm[k] = v
    return fm


def collect_atoms(province: str, subject: str) -> list[dict[str, Any]]:
    """扫真题/<province>-<subject>/ 下所有 .md。"""
    exam_dir = REPO_ROOT / "真题" / f"{province}-{subject}"
    if not exam_dir.is_dir():
        return []
    atoms: list[dict] = []
    for p in sorted(exam_dir.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        fm = parse_atom_fm(text)
        if fm:
            fm["_path"] = p
            fm["_bare"] = p.stem
            atoms.append(fm)
    return atoms


def build_freq_table(atoms: list[dict]) -> Counter:
    counter: Counter = Counter()
    for a in atoms:
        for tag in a.get("考点", []):
            counter[tag] += 1
    return counter


def build_qtype_cross(atoms: list[dict]) -> dict[str, Counter]:
    """题型 → 考点 频次。"""
    cross: dict[str, Counter] = defaultdict(Counter)
    for a in atoms:
        qtype = a.get("题型", "未知")
        for tag in a.get("考点", []):
            cross[qtype][tag] += 1
    return cross


def build_gap_list(atoms: list[dict], existing_concepts: set[str]) -> Counter:
    """缺口：真题命中但 学科目录 无对应词条。"""
    gaps: Counter = Counter()
    for a in atoms:
        for tag in a.get("考点", []):
            if tag not in existing_concepts:
                gaps[tag] += 1
    return gaps


def build_paper_map(atoms: list[dict]) -> dict[str, dict]:
    """试卷地图: (年份, 卷别, 文理) → 题数 + 题型分布。"""
    pmap: dict[tuple, dict] = defaultdict(lambda: {"total": 0, "by_qtype": Counter()})
    for a in atoms:
        key = (a.get("年份"), a.get("卷别"), a.get("文理"))
        pmap[key]["total"] += 1
        pmap[key]["by_qtype"][a.get("题型", "未知")] += 1
    return pmap


def write_freq_index(freq: Counter, out_path: Path, label: str) -> None:
    lines = [f"# {label} · 高频考点（按出现次数）\n"]
    lines.append("| 排名 | 考点 | 出现 |")
    lines.append("|---:|---|---:|")
    for i, (tag, cnt) in enumerate(freq.most_common(50), 1):
        lines.append(f"| {i} | [[{tag}]] | {cnt} |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_qtype_cross(cross: dict[str, Counter], out_path: Path, label: str) -> None:
    all_tags = sorted({t for c in cross.values() for t in c})
    lines = [f"# {label} · 题型 × 考点 交叉表\n"]
    qtypes = sorted(cross.keys())
    header = ["考点"] + qtypes + ["合计"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for tag in all_tags:
        row = [f"[[{tag}]]"] + [str(cross[q].get(tag, 0)) for q in qtypes]
        total = sum(cross[q].get(tag, 0) for q in qtypes)
        row.append(str(total))
        lines.append("| " + " | ".join(row) + " |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_gap_list(gaps: Counter, out_path: Path, label: str) -> None:
    lines = [f"# {label} · 缺口词条清单\n"]
    lines.append("真题命中但学科目录未建对应词条的考点：\n")
    lines.append("| 缺口考点 | 命中次数 |")
    lines.append("|---|---:|")
    for tag, cnt in gaps.most_common(50):
        lines.append(f"| {tag} | {cnt} |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_paper_map(pmap: dict, out_path: Path, label: str) -> None:
    lines = [f"# {label} · 试卷地图\n"]
    lines.append("| 年份 | 卷别 | 文理 | 题数 | 选择 | 填空 | 解答 |")
    lines.append("|---|---|---|---:|---:|---:|---:|")
    for (year, paper, gender), stat in sorted(pmap.items()):
        lines.append(
            f"| {year} | {paper} | {gender} | {stat['total']} | "
            f"{stat['by_qtype'].get('选择', 0)} | "
            f"{stat['by_qtype'].get('填空', 0)} | "
            f"{stat['by_qtype'].get('解答', 0)} |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def backfill_backlinks(atoms: list[dict], subject: str) -> int:
    """把"该考点命中的真题题号"作为反链段追加到 学科/<考点>.md 末尾。"""
    # tag → list[atom_bare_name]
    tag_to_atoms: dict[str, list[str]] = defaultdict(list)
    for a in atoms:
        for tag in a.get("考点", []):
            tag_to_atoms[tag].append(a["_bare"])

    # 找 学科/<tag>.md（用 bare_name 匹配）
    subject_dir = REPO_ROOT / subject
    if not subject_dir.is_dir():
        return 0
    bare_to_path: dict[str, Path] = {}
    for p in iter_entries(subject_dir):
        bare_to_path[bare_name(p)] = p

    updated = 0
    section_re = re.compile(
        re.escape(BACKLINK_START) + r".*?" + re.escape(BACKLINK_END),
        re.DOTALL,
    )
    for tag, exam_atoms in tag_to_atoms.items():
        path = bare_to_path.get(tag)
        if not path:
            continue
        text = path.read_text(encoding="utf-8")
        body = "\n".join([f"- [[{atom}]]" for atom in sorted(set(exam_atoms))])
        section = (
            f"\n{BACKLINK_START}\n## 高考真题命中\n{body}\n{BACKLINK_END}\n"
        )
        if BACKLINK_START in text:
            new_text = section_re.sub(section.strip(), text)
        else:
            new_text = text.rstrip() + "\n" + section
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            updated += 1
    return updated


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--province", required=True)
    ap.add_argument("--subject", required=True)
    args = ap.parse_args()

    atoms = collect_atoms(args.province, args.subject)
    if not atoms:
        sys.exit(f"ERROR: 真题/{args.province}-{args.subject}/ 下无词条")

    # 收集 学科目录现有 bare
    subject_dir = REPO_ROOT / args.subject
    existing = (
        {bare_name(p) for p in iter_entries(subject_dir)}
        if subject_dir.is_dir()
        else set()
    )

    freq = build_freq_table(atoms)
    cross = build_qtype_cross(atoms)
    gaps = build_gap_list(atoms, existing)
    pmap = build_paper_map(atoms)

    out_dir = REPO_ROOT / "索引" / "真题"
    out_dir.mkdir(parents=True, exist_ok=True)
    label = f"{args.province}{args.subject}"

    write_freq_index(freq, out_dir / f"{label}-高频考点.md", label)
    write_qtype_cross(cross, out_dir / f"{label}-题型×考点交叉表.md", label)
    write_gap_list(gaps, out_dir / f"{label}-缺口词条清单.md", label)
    write_paper_map(pmap, out_dir / f"{label}-试卷地图.md", label)

    updated = backfill_backlinks(atoms, args.subject)
    print(f"OK: 4 份索引 + 反链回填 {updated} 词条（{args.province}-{args.subject}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试**

Run: `python -m unittest 00-元.scripts.tests.test_exam_index -v`
Expected: 4 tests pass

- [ ] **Step 5: 跑全部单测**

Run: `python -m unittest discover -s 00-元/scripts/tests`
Expected: ~35 tests pass

- [ ] **Step 6: Commit**

```bash
git add "00-元/scripts/exam_index.py" "00-元/scripts/tests/test_exam_index.py"
git commit -m "feat(exam): index aggregation + backlink backfill"
```

---

## B · Pilot 端到端

### Task 11: Pilot · 2022 文卷端到端验证

**Files:** （无新增，跑现有脚本）

- [ ] **Step 1: 跑 Step 1 截图生成**

Run:
```bash
python 00-元/scripts/exam_screenshot.py \
    --pdf "素材/真题/吉林/2008-2024·（吉林）数学高考真题/2022年高考数学试卷（文）（全国乙卷）（解析卷）.pdf" \
    --province 吉林 --subject 数学 --year 2022 \
    --expected-min 18 --expected-max 25
```
Expected: `OK: 截图 23 题 + questions.json` （L1 断言全过）

- [ ] **Step 2: 跑 Step 2 markitdown 元数据**

Run:
```bash
python 00-元/scripts/exam_extract_meta.py \
    --questions docs/superpowers/working/吉林-数学-2022-文-全国乙-questions.json
```
Expected: `OK: 提取 23 题元数据` （L1 违规 ≤ 3 条，允许少量解析过短）

- [ ] **Step 3: 跑 Step 3 v4-pro enrich**

Run:
```bash
python 00-元/scripts/exam_enrich.py \
    --questions docs/superpowers/working/吉林-数学-2022-文-全国乙-questions.json
```
Expected: `完成: 23/23 题 enrich 成功`（最多 1-2 题失败可接受）

- [ ] **Step 4: 跑 Step 3b verify prepare（写队列）**

Run:
```bash
python 00-元/scripts/exam_verify.py \
    --questions docs/superpowers/working/吉林-数学-2022-文-全国乙-questions.json \
    --mode prepare
```
Expected: `📝 23 题 verify prompt 已写入 .../verdicts/`

- [ ] **Step 5: Opus 主会话亲跑 L2 复验**

5/15 前 sonnet quota 未恢复，**由 Opus 主会话亲自处理 verify 队列**：

执行步骤：
1. 用 Glob 列出 `docs/superpowers/working/verdicts/q*.prompt.md`
2. 对每个 prompt：Read prompt 文件 → Read 对应题面截图 → 评判 → Write 同名 .verdict.txt
3. 23 题全部跑完后进 Step 6

预期：23 个 q01.verdict.txt ... q23.verdict.txt

- [ ] **Step 6: 跑 verify ingest**

Run:
```bash
python 00-元/scripts/exam_verify.py \
    --questions docs/superpowers/working/吉林-数学-2022-文-全国乙-questions.json \
    --mode ingest
```
Expected: `已 ingest 23 条 / 缺失 0 / 需 Opus 仲裁 ≤ 3`

- [ ] **Step 7: 处理仲裁队列（Opus 主会话）**

读 questions.json，对 `verdict in ("严重偏差", "未识别")` 的题：
- Read 题面截图
- 修正 tags / summary
- 写回 questions.json

- [ ] **Step 8: 跑 Step 4 渲染**

Run:
```bash
python 00-元/scripts/exam_render.py \
    --questions docs/superpowers/working/吉林-数学-2022-文-全国乙-questions.json
```
Expected: `OK: 渲染 23 题词条到 真题/吉林-数学/`

- [ ] **Step 9: 跑 Step 5 索引**

Run:
```bash
python 00-元/scripts/exam_index.py --province 吉林 --subject 数学
```
Expected: `OK: 4 份索引 + 反链回填 N 词条`

- [ ] **Step 10: L3 Opus 抽检 3 题**

Opus 主会话：
1. 随机抽 3 题（如 Q5 / Q12 / Q21）
2. Read 词条 .md + Read 题面截图 + Read 解析截图
3. 核验：frontmatter 字段完整 / 截图加载正常 / tags 与截图吻合 / 反链 [[]] 正确

预期：3 题全部通过。任一不通过则回退对应步骤修脚本。

- [ ] **Step 11: 跑 analyze_links 验证孤岛**

Run:
```bash
python 00-元/scripts/analyze_links.py
```
Expected: 真题部分 23 题入图，孤岛 ≤ 1 题（仅当某题 tags 全是缺口词条时）

- [ ] **Step 12: Commit Pilot 数据**

```bash
git add 真题/ 索引/真题/ 素材/真题截图/吉林-数学/ \
        docs/superpowers/working/吉林-数学-2022-文-全国乙-questions.json
git add 数学/  # 反链段
git commit -m "feat(exam): Pilot 2022 文卷端到端跑通 (v2)"
```

---

## C · 进度节恢复

### Task 12: CLAUDE.md 真题节恢复

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 替换占位**

把当前 CLAUDE.md 中的：

```markdown
## 真题分析

<!-- EXAM-PROGRESS-START -->

_2026-05-12 已清空 v1 全部产出（数据 + 脚本 + 文档），保留 zip 备份于 `素材/backup/2026-05-12/exam-pre-migrate.zip`。新方案待重新规划。_

<!-- EXAM-PROGRESS-END -->
```

替换为：

```markdown
## 真题分析

<!-- EXAM-PROGRESS-START -->

| 省份-学科 | 年份范围 | 卷数 | 题词条数 | 索引 | 状态 |
|---|---|---:|---:|---|---|
| 吉林-数学 | 2022 | 1/19 | 23 | 4 份 | ⏳ Pilot 完成 |

**v2 脚手架** ✅（6 脚本 + yaml + ~35 单测）：
- `00-元/scripts/exam_pipeline_config.yaml` — 卷别/文理归一 + tag 池过滤
- `00-元/scripts/_exam_utils.py` — load_config / build_atom_filename / build_screenshot_filename
- `00-元/scripts/exam_screenshot.py` — PyMuPDF 题号 bbox 定位 + 截图渲染 + L1 断言
- `00-元/scripts/exam_extract_meta.py` — markitdown answer + 解析文本提取
- `00-元/scripts/exam_enrich.py` — v4-pro 摘要 + 考点 + 难度
- `00-元/scripts/exam_verify.py` — L2 复验队列（prepare/ingest 两步法）
- `00-元/scripts/exam_render.py` — 渲染 v2 词条 .md（截图 + 摘要 + 指针）
- `00-元/scripts/exam_index.py` — 4 份索引 + 反链回填

**v2 关键设计**：
- 题面 + 解析 用截图保真（PNG），彻底回避 v1 字符级 bug
- L1 自动断言 + L2 看图复验 + L3 Opus 抽检 三层复审
- 每题双图：`<id>.q.png`（题面）+ `<id>.a.png`（答案/解析）

**已知限制**：
- 跨页题需 Opus 人工核对（脚本自动 flag）
- 题号坐标定位偶有偏差（PyMuPDF + bbox 启发式，~5% 抽样修正）

**待跑卷**：
- Phase 2 续跑：2022 理 / 2023 / 2024 / 2020 / 2021 / 2008-2019 共 18 卷
- Phase 3 扩省份：北京 / 黑龙江 + 物理/化学/生物

详见 `docs/superpowers/specs/2026-05-12-jilin-math-exam-v2-design.md` 与对应 plan。

<!-- EXAM-PROGRESS-END -->
```

- [ ] **Step 2: 跑 stats 刷新词条数**

Run:
```bash
python 00-元/scripts/stats.py --write
```
Expected: stats 表格更新（数学新增 23）

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(exam): restore 真题分析 progress section after v2 pilot"
```

---

## 验收 Checklist

Pilot 通过须全部 ✅:

- [ ] 所有 ~35 单测通过
- [ ] L1 断言：截图 23 × 2 = 46 PNG 全部生成且 ≥ 10 KB
- [ ] L1 断言：元数据 answer / summary / tags 100% 非空
- [ ] L2 复验：≥ 90% "吻合"，仲裁队列 ≤ 3 题
- [ ] L3 Opus 抽 3 题全部通过
- [ ] 索引 4 份正常生成
- [ ] 反链回填幂等（重跑 exam_index 输出相同）
- [ ] analyze_links 孤岛 ≤ 1
- [ ] CLAUDE.md 进度节恢复

---

## Self-Review 已跑

- [x] Spec coverage：spec 8 节全部对应 task（数据模型→Task 9 / 工作流→Task 11 / 脚本→Task 2-10 / 验收→Pilot Checklist / 三层复审→L1 in Task 5/6 + L2 in Task 8 + L3 in Task 11.10）
- [x] Placeholder scan：无 TBD / TODO / "to be defined" / "similar to"
- [x] Type 一致性：questions.json schema 全程一致（qno / page / 题面图 / 解析图 / answer / summary / tags / difficulty / verdict）
