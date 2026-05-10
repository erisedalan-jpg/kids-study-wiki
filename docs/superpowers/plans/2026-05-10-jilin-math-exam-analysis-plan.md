# 吉林数学高考真题分析（试点）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地吉林 2015-2024 数学 19 套高考真题的端到端分析流水线，并沉淀省份+学科参数化的可复用脚本组件，产出 4 份索引 + 反链回填到现有 526 个数学词条。

**Architecture:** 5 个参数化脚本 + 1 份集中配置 + 中间 JSON 协议串联，PDF→题块→候选 tag→（外部 LLM 子代理终审）→真题原子词条→4 份索引 + 反链。脚本与省份/学科解耦，通过命令行参数与 yaml 配置切换。

**Tech Stack:** Python 3.12 + pyyaml + pdfplumber（PDF 提取）+ unittest（标准库测试）+ Markdown/Obsidian 双向链接 + sonnet 子代理（LLM 终审，不在脚本内）。

**Spec:** `docs/superpowers/specs/2026-05-10-jilin-math-exam-analysis-design.md`

---

## 文件结构总览

新建：
```
00-元/scripts/
  exam_pipeline_config.yaml          # 配置（省份/学科/卷别归一/题型正则/tag 池过滤）
  _exam_utils.py                     # 共享工具（yaml 加载、卷别归一、文件名构造、tag-pool 过滤）
  build_subject_lexicon.py           # 学科 → 白名单 JSON
  parse_exam_pdf.py                  # PDF → 题块 JSON
  tag_questions.py                   # 题块 + 白名单 → 候选 tag JSON（不调 LLM）
  render_exam_atoms.py               # 终审后 JSON → 真题词条 .md
  aggregate_exam_indices.py          # 真题词条 → 4 份索引 + 反链回填
  tests/
    __init__.py
    test_exam_utils.py
    test_build_subject_lexicon.py
    test_parse_exam_pdf.py
    test_tag_questions.py
    test_render_exam_atoms.py
    test_aggregate_exam_indices.py
    fixtures/
      mini_subject/                  # 假学科目录（3-5 个词条）
      mini_qa.json                   # 切分后 3 道假题 JSON
      mini_paper.pdf                 # 1 张实际真题（2024 新课标Ⅱ）软链
docs/superpowers/working/            # 中间产物（gitignore）
真题/吉林-数学/                       # 真题原子词条（最终）
索引/真题/                            # 4 份索引（最终）
```

修改：
- `CLAUDE.md`：新增 `<!-- AUTO-PROGRESS-START/END -->` 之外的"真题分析"章节
- `.gitignore`：加 `docs/superpowers/working/`、`00-元/scripts/_*_lexicon.json` 行
- 现有 `数学/<高频考点>.md`：末尾追加 `<!-- exam-backlinks-start/end -->` 区段（由 aggregate_exam_indices.py 自动维护）

---

## Task 1: 环境准备（依赖 + 目录 + gitignore + CLAUDE.md 锚点）

**Files:**
- Modify: `.gitignore`
- Modify: `CLAUDE.md`（添加章节锚点）
- Create: `docs/superpowers/working/.gitkeep`
- Create: `00-元/scripts/tests/__init__.py`
- Create: `00-元/scripts/tests/fixtures/.gitkeep`
- Create: `真题/.gitkeep`
- Create: `索引/真题/.gitkeep`

- [ ] **Step 1: 安装依赖**

```bash
pip install pyyaml pdfplumber
```

预期：两个包 install successful；不需要 sudo。

- [ ] **Step 2: 验证依赖**

```bash
python -c "import yaml, pdfplumber; print('yaml', yaml.__version__, 'pdfplumber', pdfplumber.__version__)"
```

预期：打印两个版本号，无 ImportError。

- [ ] **Step 3: 创建目录骨架**

```bash
mkdir -p "00-元/scripts/tests/fixtures" "docs/superpowers/working" "真题/吉林-数学" "索引/真题"
touch "00-元/scripts/tests/__init__.py" "00-元/scripts/tests/fixtures/.gitkeep" \
      "docs/superpowers/working/.gitkeep" "真题/.gitkeep" "索引/真题/.gitkeep"
```

- [ ] **Step 4: 修改 .gitignore**

在 `.gitignore` 末尾追加：
```
# 真题流水线中间产物
docs/superpowers/working/
00-元/scripts/_*_lexicon.json
```

- [ ] **Step 5: 在 CLAUDE.md 适当位置（"已完成进度"章节之后）加入章节锚点**

```markdown
## 真题分析进度

<!-- EXAM-PROGRESS-START -->
（暂未启动；由 aggregate_exam_indices.py 维护）
<!-- EXAM-PROGRESS-END -->
```

- [ ] **Step 6: Commit**

```bash
git add .gitignore CLAUDE.md "00-元/scripts/tests" "docs/superpowers/working" "真题" "索引/真题"
git commit -m "chore(真题): 环境准备 - 依赖/目录/gitignore/CLAUDE.md 锚点"
```

---

## Task 2: 配置文件 `exam_pipeline_config.yaml`

**Files:**
- Create: `00-元/scripts/exam_pipeline_config.yaml`

- [ ] **Step 1: 创建配置文件**

写入 `00-元/scripts/exam_pipeline_config.yaml`：

```yaml
# 真题流水线集中配置 —— 由所有 5 个脚本共享读取
# 修改后所有脚本下次运行自动生效

provinces:
  - 吉林
  - 北京
  - 黑龙江

subjects:
  - 数学
  - 语文
  - 英语
  - 物理
  - 化学
  - 生物
  - 历史
  - 政治
  - 地理

# 卷别归一：PDF 文件名子串 → 短简称（用于真题词条文件名）
# 顺序敏感：长 key 优先匹配（避免 "新课标Ⅱ" 被 "新课标" 抢匹配）
paper_aliases:
  - ["新课标Ⅱ卷", "新课标Ⅱ"]
  - ["新课标Ⅰ卷", "新课标Ⅰ"]
  - ["新课标Ⅱ", "新课标Ⅱ"]
  - ["新课标Ⅰ", "新课标Ⅰ"]
  - ["全国乙卷", "全国乙"]
  - ["全国甲卷", "全国甲"]
  - ["全国卷Ⅱ", "全国Ⅱ"]
  - ["全国卷Ⅰ", "全国Ⅰ"]
  - ["全国Ⅱ", "全国Ⅱ"]
  - ["新课标", "新课标"]
  - ["北京", "北京"]

# 文/理识别（PDF 文件名子串 → 文/理/不分）
gender_aliases:
  - ["（文）", "文"]
  - ["（理）", "理"]

# 题型识别正则（按学科）
question_patterns:
  数学:
    选择:
      - '^\s*(\d+)\s*[\.、]\s*[^\n]{10,}?[A-D]\s*[\.．、][^\n]+'
    填空:
      - '^\s*(\d+)\s*[\.、][^\n]+_{2,}'
    解答:
      - '^\s*(\d+)\s*[\.、]\s*\(本小题|^\s*(\d+)\s*[\.、][^\n]{0,20}（\s*\d+\s*分'

# tag 池过滤：仅参与"高频考点统计"的词条范围
tag_pool_filters:
  数学:
    序号范围: [265, 514]      # 高中数学
    额外纳入:                 # 初中关键概念（白名单内但序号 < 265，明确允许进统计）
      - 函数
      - 不等式
      - 三角函数
      - 数列
      - 向量
      - 导数
      - 概率
      - 统计
      - 立体几何
      - 解析几何
```

- [ ] **Step 2: Commit**

```bash
git add "00-元/scripts/exam_pipeline_config.yaml"
git commit -m "feat(真题): 添加流水线集中配置 exam_pipeline_config.yaml"
```

---

## Task 3: `_exam_utils.py` 共享工具

**Files:**
- Create: `00-元/scripts/_exam_utils.py`
- Create: `00-元/scripts/tests/test_exam_utils.py`

- [ ] **Step 1: 写 test 先**

写入 `00-元/scripts/tests/test_exam_utils.py`：

```python
"""测试 _exam_utils.py 公共工具的 4 个核心函数。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _exam_utils import (  # noqa: E402
    load_config,
    normalize_paper,
    normalize_gender,
    build_atom_filename,
    is_in_tag_pool,
)


class TestExamUtils(unittest.TestCase):
    def test_load_config_returns_dict_with_subjects(self):
        cfg = load_config()
        self.assertIn("subjects", cfg)
        self.assertIn("数学", cfg["subjects"])

    def test_normalize_paper_long_key_first(self):
        cfg = load_config()
        # "新课标Ⅱ卷" 必须命中"新课标Ⅱ"，不能被"新课标"抢
        self.assertEqual(normalize_paper("2024年高考数学试卷（新课标Ⅱ卷）（解析卷）.pdf", cfg), "新课标Ⅱ")
        self.assertEqual(normalize_paper("2021年高考数学试卷（理）（全国乙卷）（新课标Ⅰ）（解析卷）.pdf", cfg), "全国乙")
        self.assertEqual(normalize_paper("2010年高考数学试卷（文）（新课标）（解析卷）.pdf", cfg), "新课标")

    def test_normalize_gender(self):
        cfg = load_config()
        self.assertEqual(normalize_gender("2017年高考数学试卷（文）（新课标Ⅱ）.pdf", cfg), "文")
        self.assertEqual(normalize_gender("2017年高考数学试卷（理）（新课标Ⅱ）.pdf", cfg), "理")
        self.assertEqual(normalize_gender("2024年高考数学试卷（新课标Ⅱ卷）.pdf", cfg), "不分")

    def test_build_atom_filename(self):
        # 2017 文理分卷 → 2017-理-08
        self.assertEqual(build_atom_filename(2017, "理", "新课标Ⅱ", 8), "2017-理-08.md")
        # 2024 不分文理 → 2024-新课标Ⅱ-08
        self.assertEqual(build_atom_filename(2024, "不分", "新课标Ⅱ", 8), "2024-新课标Ⅱ-08.md")

    def test_is_in_tag_pool(self):
        cfg = load_config()
        # 高中数学序号范围内
        self.assertTrue(is_in_tag_pool("函数", 300, "数学", cfg))
        # 初中数学但在额外纳入清单
        self.assertTrue(is_in_tag_pool("数列", 100, "数学", cfg))
        # 小学数学，不在额外纳入清单
        self.assertFalse(is_in_tag_pool("加法", 16, "数学", cfg))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试看失败**

```bash
python -m unittest 00-元.scripts.tests.test_exam_utils -v
```

预期：FAIL，`ModuleNotFoundError: No module named '_exam_utils'`。

- [ ] **Step 3: 写实现**

写入 `00-元/scripts/_exam_utils.py`：

```python
"""真题流水线共享工具。

复用 _utils.py 的 setup_utf8 / REPO_ROOT。
本模块新增：
- load_config(): 读 exam_pipeline_config.yaml
- normalize_paper(): PDF 文件名 → 卷别短简称
- normalize_gender(): PDF 文件名 → 文/理/不分
- build_atom_filename(): 真题词条文件名构造
- is_in_tag_pool(): 判断 tag 是否进入高频统计池
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
    """PDF 文件名 → 卷别短简称。

    paper_aliases 列表已按长度从长到短排序（yaml 里维护），
    保证 "新课标Ⅱ卷" 命中 "新课标Ⅱ" 而非 "新课标"。
    """
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
    """真题词条文件名。

    - 2008-2022 文/理分卷：YYYY-<文|理>-NN.md
    - 2023+ 不分文理：YYYY-<卷别>-NN.md
    """
    nn = f"{qno:02d}"
    if gender in ("文", "理"):
        return f"{year}-{gender}-{nn}.md"
    return f"{year}-{paper}-{nn}.md"


def is_in_tag_pool(tag: str, entry_seq: int, subject: str, cfg: dict[str, Any]) -> bool:
    """tag 是否参与"高频考点"统计。

    - 在高中序号范围内 → True
    - 在"额外纳入"白名单 → True
    - 否则 False（不影响反链，仅影响高频榜单）
    """
    flt = cfg.get("tag_pool_filters", {}).get(subject)
    if not flt:
        return True  # 没配置过滤就全部纳入
    lo, hi = flt["序号范围"]
    if lo <= entry_seq <= hi:
        return True
    if tag in flt.get("额外纳入", []):
        return True
    return False
```

- [ ] **Step 4: 跑测试看通过**

```bash
python -m unittest 00-元.scripts.tests.test_exam_utils -v
```

预期：5 tests pass，0 failures。

- [ ] **Step 5: Commit**

```bash
git add "00-元/scripts/_exam_utils.py" "00-元/scripts/tests/test_exam_utils.py"
git commit -m "feat(真题): _exam_utils.py 共享工具 + 单元测试"
```

---

## Task 4: `build_subject_lexicon.py` 学科白名单生成

**Files:**
- Create: `00-元/scripts/build_subject_lexicon.py`
- Create: `00-元/scripts/tests/test_build_subject_lexicon.py`
- Create: `00-元/scripts/tests/fixtures/mini_subject/` 内 3 个假词条

- [ ] **Step 1: 准备 fixture**

```bash
mkdir -p "00-元/scripts/tests/fixtures/mini_subject"
```

写入 `00-元/scripts/tests/fixtures/mini_subject/265-函数.md`：
```markdown
---
title: 函数
aliases: [函数, function, 映射]
学科: 数学
学段: 高中
主题: 必修一
状态: 完成
英文术语: function
---

# 函数

（占位内容）
```

写入 `00-元/scripts/tests/fixtures/mini_subject/100-数列.md`：
```markdown
---
title: 数列
aliases: [数列, sequence]
学科: 数学
学段: 初中
主题: 九上
状态: 完成
英文术语: sequence
---

# 数列
```

写入 `00-元/scripts/tests/fixtures/mini_subject/016-加法.md`：
```markdown
---
title: 加法
aliases: [加法, addition, plus]
学科: 数学
学段: 小学
主题: 一上
状态: 完成
英文术语: addition
---

# 加法
```

- [ ] **Step 2: 写 test 先**

写入 `00-元/scripts/tests/test_build_subject_lexicon.py`：

```python
"""测试 build_subject_lexicon.py 对 mini_subject fixture 的白名单提取。"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_subject_lexicon import build_lexicon  # noqa: E402


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_subject"


class TestBuildSubjectLexicon(unittest.TestCase):
    def test_extracts_bare_name_and_aliases(self):
        lex = build_lexicon(FIXTURE_DIR)
        # 每个词条的 bare-name 与 alias 都应进入白名单
        # 白名单结构: {term: {"bare": <bare-name>, "seq": <int|None>}}
        self.assertIn("函数", lex)
        self.assertIn("function", lex)
        self.assertIn("映射", lex)
        self.assertEqual(lex["函数"]["bare"], "函数")
        self.assertEqual(lex["function"]["bare"], "函数")
        # alias 共指向 bare-name
        self.assertEqual(lex["映射"]["bare"], "函数")

    def test_seq_extracted_from_filename_prefix(self):
        lex = build_lexicon(FIXTURE_DIR)
        self.assertEqual(lex["函数"]["seq"], 265)
        self.assertEqual(lex["数列"]["seq"], 100)
        self.assertEqual(lex["加法"]["seq"], 16)

    def test_term_count_at_least_8(self):
        lex = build_lexicon(FIXTURE_DIR)
        # 3 词条 × (bare + 2-3 aliases) = 至少 8 个 term
        self.assertGreaterEqual(len(lex), 8)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 跑测试看失败**

```bash
python -m unittest 00-元.scripts.tests.test_build_subject_lexicon -v
```

预期：FAIL `ModuleNotFoundError: No module named 'build_subject_lexicon'`。

- [ ] **Step 4: 写实现**

写入 `00-元/scripts/build_subject_lexicon.py`：

```python
"""学科 → 白名单 JSON。

扫描 <repo>/<subject>/*.md 的 frontmatter `aliases`，提取所有
bare-name + alias，输出 _<subject>_lexicon.json。

输出 schema:
    {
      "<term>": {"bare": "<bare-name>", "seq": 265 | null},
      ...
    }

用法:
    python 00-元/scripts/build_subject_lexicon.py --subject 数学
    # 写出 00-元/scripts/_数学_lexicon.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, bare_name, iter_entries, setup_utf8  # noqa: E402
from analyze_links import parse_aliases  # noqa: E402

PREFIX_NUM_RE = re.compile(r"^(\d{2,4})-")
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _seq_of(path: Path) -> int | None:
    m = PREFIX_NUM_RE.match(path.name)
    return int(m.group(1)) if m else None


def build_lexicon(subject_dir: Path) -> dict[str, dict]:
    """扫描目录，返回 term → {bare, seq} 映射。"""
    lex: dict[str, dict] = {}
    for p in iter_entries(subject_dir):
        bare = bare_name(p)
        seq = _seq_of(p)
        text = p.read_text(encoding="utf-8", errors="replace")
        m = FM_RE.match(text)
        aliases = parse_aliases(m.group(1)) if m else []
        # bare 必入
        lex.setdefault(bare, {"bare": bare, "seq": seq})
        for a in aliases:
            lex.setdefault(a, {"bare": bare, "seq": seq})
    return lex


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True, help="学科名（如 数学）")
    ap.add_argument("--out", help="输出路径（默认 00-元/scripts/_<subject>_lexicon.json）")
    args = ap.parse_args()

    subject_dir = REPO_ROOT / args.subject
    if not subject_dir.is_dir():
        sys.exit(f"ERROR: 找不到学科目录 {subject_dir}")

    lex = build_lexicon(subject_dir)
    out = Path(args.out) if args.out else REPO_ROOT / "00-元" / "scripts" / f"_{args.subject}_lexicon.json"
    out.write_text(json.dumps(lex, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: 写出 {out}（{len(lex)} 个 term，覆盖学科={args.subject}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: 跑测试看通过**

```bash
python -m unittest 00-元.scripts.tests.test_build_subject_lexicon -v
```

预期：3 tests pass。

- [ ] **Step 6: 实跑数学全量验证**

```bash
python "00-元/scripts/build_subject_lexicon.py" --subject 数学
```

预期输出：`OK: 写出 ...\_数学_lexicon.json（≥1500 个 term，覆盖学科=数学）`。
打开生成的 JSON 抽查 5 个高中术语（如"函数"、"导数"、"等差数列"）有 seq 字段且在 [265, 514]。

- [ ] **Step 7: Commit**

```bash
git add "00-元/scripts/build_subject_lexicon.py" "00-元/scripts/tests/test_build_subject_lexicon.py" \
        "00-元/scripts/tests/fixtures/mini_subject"
git commit -m "feat(真题): build_subject_lexicon.py - 学科白名单生成 + 测试"
```

注意：`_数学_lexicon.json` 已在 .gitignore 中，不入库。

---

## Task 5: `parse_exam_pdf.py` PDF 切分为题块

**Files:**
- Create: `00-元/scripts/parse_exam_pdf.py`
- Create: `00-元/scripts/tests/test_parse_exam_pdf.py`

设计要点：
- 用 pdfplumber 提取整张卷文本
- 用 `question_patterns[学科]` 中的正则切分题号
- 解析卷里题目 + "【答案】" + "【解析】" 块按题号拼回
- 输出 `<working>/<paper-id>-questions.json`，schema：

```json
{
  "paper_id": "2024-不分-新课标Ⅱ",
  "year": 2024,
  "gender": "不分",
  "paper": "新课标Ⅱ",
  "subject": "数学",
  "province": "吉林",
  "source_pdf": "../../素材/真题/吉林/.../2024年....pdf",
  "questions": [
    {"qno": 1, "qtype": "选择", "score": 5, "stem": "...", "answer": "B", "solution": "..."},
    ...
  ]
}
```

- [ ] **Step 1: 写 test 先**

写入 `00-元/scripts/tests/test_parse_exam_pdf.py`：

```python
"""测试 parse_exam_pdf.py 对 2024 新课标Ⅱ 真题的题块切分。

注意: 此测试需要本地存在 2024 年吉林新课标Ⅱ 解析卷 PDF。
fixture 中放软链/相对路径，CI 跳过。
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parse_exam_pdf import parse_pdf  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
PDF = REPO / "素材" / "真题" / "吉林" / "2008-2024·（吉林）数学高考真题" / \
      "2024年高考数学试卷（新课标Ⅱ卷）（解析卷）.pdf"


@unittest.skipUnless(PDF.exists(), "需要 2024 新课标Ⅱ 解析卷 PDF")
class TestParseExamPdf(unittest.TestCase):
    def test_question_count_in_range(self):
        result = parse_pdf(PDF, subject="数学", province="吉林", year=2024)
        # 高考数学卷题数典型 19-22
        self.assertGreaterEqual(len(result["questions"]), 18)
        self.assertLessEqual(len(result["questions"]), 23)

    def test_question_fields_present(self):
        result = parse_pdf(PDF, subject="数学", province="吉林", year=2024)
        first = result["questions"][0]
        self.assertEqual(first["qno"], 1)
        self.assertIn("stem", first)
        self.assertIn("qtype", first)
        self.assertGreater(len(first["stem"]), 5)

    def test_paper_id_format(self):
        result = parse_pdf(PDF, subject="数学", province="吉林", year=2024)
        self.assertEqual(result["paper_id"], "2024-不分-新课标Ⅱ")
        self.assertEqual(result["paper"], "新课标Ⅱ")
        self.assertEqual(result["gender"], "不分")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试看失败**

```bash
python -m unittest 00-元.scripts.tests.test_parse_exam_pdf -v
```

预期：FAIL `No module named 'parse_exam_pdf'`。

- [ ] **Step 3: 写实现**

写入 `00-元/scripts/parse_exam_pdf.py`：

```python
"""PDF 解析卷 → 题块 JSON。

策略:
1. pdfplumber 提取全文（保留行序）
2. 用 question_patterns[学科] 切分题号边界
3. 解析卷的"【答案】"/"【解析】"段附在对应题块上

输出: <working_dir>/<paper_id>-questions.json

用法:
    python 00-元/scripts/parse_exam_pdf.py \
        --pdf "<.../2024年高考数学试卷（新课标Ⅱ卷）（解析卷）.pdf>" \
        --subject 数学 --province 吉林 --year 2024 \
        --out docs/superpowers/working/
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
from _utils import REPO_ROOT, setup_utf8  # noqa: E402
from _exam_utils import build_atom_filename, load_config, normalize_gender, normalize_paper  # noqa: E402

# 题号边界识别（不区分学科的通用版）
QNO_RE = re.compile(r"^\s*(\d{1,2})\s*[\.、．]\s*", re.MULTILINE)
ANSWER_TAG_RE = re.compile(r"【答案】([^\n【]*)")
SOLUTION_TAG_RE = re.compile(r"【解析】([^【]+)")


def _classify_qtype(stem: str) -> str:
    """启发式题型分类。"""
    if re.search(r"[A-D]\s*[\.．、]", stem) and len(stem) < 600:
        return "选择"
    if re.search(r"_{2,}", stem):
        return "填空"
    return "解答"


def _classify_score(qno: int, qtype: str) -> int:
    """高考数学典型分值。"""
    if qtype == "选择":
        return 5
    if qtype == "填空":
        return 5
    if qno >= 17:  # 解答题倒数几道
        return 12 if qno < 22 else 17
    return 12


def _split_questions(full_text: str) -> list[tuple[int, str]]:
    """按题号边界把全文切成 [(qno, body)] 列表。"""
    matches = list(QNO_RE.finditer(full_text))
    out: list[tuple[int, str]] = []
    for i, m in enumerate(matches):
        qno = int(m.group(1))
        # 顺序约束：题号必须递增（避免段中数字误识别）
        if out and qno != out[-1][0] + 1:
            continue
        if not out and qno != 1:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        out.append((qno, full_text[start:end].strip()))
    return out


def parse_pdf(pdf_path: Path, *, subject: str, province: str, year: int) -> dict[str, Any]:
    cfg = load_config()
    fname = pdf_path.name
    paper = normalize_paper(fname, cfg)
    gender = normalize_gender(fname, cfg)
    paper_id = f"{year}-{gender}-{paper}"

    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join((page.extract_text() or "") for page in pdf.pages)

    raw = _split_questions(text)
    questions: list[dict[str, Any]] = []
    for qno, body in raw:
        # 拆题面 vs 答案 vs 解析
        ans_m = ANSWER_TAG_RE.search(body)
        sol_m = SOLUTION_TAG_RE.search(body)
        stem_end = min(
            ans_m.start() if ans_m else len(body),
            sol_m.start() if sol_m else len(body),
        )
        stem = body[:stem_end].strip()
        if not stem or len(stem) < 5:
            continue
        qtype = _classify_qtype(stem)
        questions.append({
            "qno": qno,
            "qtype": qtype,
            "score": _classify_score(qno, qtype),
            "stem": stem,
            "answer": ans_m.group(1).strip() if ans_m else "",
            "solution": sol_m.group(1).strip() if sol_m else "",
        })

    rel_pdf = pdf_path.relative_to(REPO_ROOT) if pdf_path.is_relative_to(REPO_ROOT) else pdf_path
    return {
        "paper_id": paper_id,
        "year": year,
        "gender": gender,
        "paper": paper,
        "subject": subject,
        "province": province,
        "source_pdf": str(rel_pdf).replace("\\", "/"),
        "questions": questions,
    }


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--province", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--out", default="docs/superpowers/working/")
    args = ap.parse_args()

    result = parse_pdf(Path(args.pdf), subject=args.subject, province=args.province, year=args.year)
    out_dir = REPO_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.province}-{args.subject}-{result['paper_id']}-questions.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: 切分 {len(result['questions'])} 题 → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试看通过**

```bash
python -m unittest 00-元.scripts.tests.test_parse_exam_pdf -v
```

预期：3 tests pass。

- [ ] **Step 5: 实跑 2024 新课标Ⅱ 验证**

```bash
python "00-元/scripts/parse_exam_pdf.py" \
  --pdf "素材/真题/吉林/2008-2024·（吉林）数学高考真题/2024年高考数学试卷（新课标Ⅱ卷）（解析卷）.pdf" \
  --subject 数学 --province 吉林 --year 2024
```

预期：`OK: 切分 19-22 题 → docs/superpowers/working/吉林-数学-2024-不分-新课标Ⅱ-questions.json`。

人工抽查：打开 JSON 看第 1 题 stem 是否完整、qtype 是否合理。若有 ≥ 5 道题面失真严重 → 触发 spec § 8 风险回退条款。

- [ ] **Step 6: Commit**

```bash
git add "00-元/scripts/parse_exam_pdf.py" "00-元/scripts/tests/test_parse_exam_pdf.py"
git commit -m "feat(真题): parse_exam_pdf.py - PDF 切分题块 + 测试"
```

---

## Task 6: `tag_questions.py` 候选 tag 生成器（不调 LLM）

**Files:**
- Create: `00-元/scripts/tag_questions.py`
- Create: `00-元/scripts/tests/test_tag_questions.py`
- Create: `00-元/scripts/tests/fixtures/mini_qa.json`
- Create: `00-元/scripts/tests/fixtures/mini_lexicon.json`

设计要点：
- 输入：题块 JSON（Task 5 输出） + 白名单 JSON（Task 4 输出）
- 输出：每题加 `tag_candidates: [...]`（命中的所有白名单词，按出现频次排序），不做 LLM 终审。
- LLM 终审是另一步骤：主会话起 sonnet 子代理，读题块 JSON + 候选，输出最终 `tags: [...]` 字段，写回同一个 JSON。
- 此脚本只负责"客观可重现的关键词命中"。

- [ ] **Step 1: 准备 fixture**

写入 `00-元/scripts/tests/fixtures/mini_qa.json`：

```json
{
  "paper_id": "fixture-test",
  "year": 2024,
  "gender": "不分",
  "paper": "test",
  "subject": "数学",
  "province": "fixture",
  "source_pdf": "fixture",
  "questions": [
    {"qno": 1, "qtype": "选择", "score": 5,
     "stem": "已知函数 f(x) = x^2 在区间上单调递增，求...",
     "answer": "B", "solution": "由导数判断单调性。"},
    {"qno": 2, "qtype": "选择", "score": 5,
     "stem": "数列 {a_n} 是等差数列，求 a_5。",
     "answer": "C", "solution": "等差数列通项公式。"}
  ]
}
```

写入 `00-元/scripts/tests/fixtures/mini_lexicon.json`：

```json
{
  "函数": {"bare": "函数", "seq": 265},
  "导数": {"bare": "导数", "seq": 280},
  "单调性": {"bare": "单调性", "seq": 285},
  "数列": {"bare": "数列", "seq": 100},
  "等差数列": {"bare": "等差数列", "seq": 290},
  "加法": {"bare": "加法", "seq": 16}
}
```

- [ ] **Step 2: 写 test 先**

写入 `00-元/scripts/tests/test_tag_questions.py`：

```python
"""测试 tag_questions.py 候选 tag 生成。"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tag_questions import tag_paper  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


class TestTagQuestions(unittest.TestCase):
    def setUp(self):
        self.qa = json.loads((FIX / "mini_qa.json").read_text(encoding="utf-8"))
        self.lex = json.loads((FIX / "mini_lexicon.json").read_text(encoding="utf-8"))

    def test_q1_hits_function_and_monotonicity(self):
        result = tag_paper(self.qa, self.lex)
        q1 = result["questions"][0]
        self.assertIn("函数", q1["tag_candidates"])
        self.assertIn("单调性", q1["tag_candidates"])
        self.assertIn("导数", q1["tag_candidates"])

    def test_q2_hits_sequence(self):
        result = tag_paper(self.qa, self.lex)
        q2 = result["questions"][1]
        self.assertIn("数列", q2["tag_candidates"])
        self.assertIn("等差数列", q2["tag_candidates"])

    def test_no_false_positive_addition(self):
        # "加法" 在白名单里但题面无明显出现 → 不应误命中
        result = tag_paper(self.qa, self.lex)
        for q in result["questions"]:
            self.assertNotIn("加法", q["tag_candidates"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 跑测试看失败**

```bash
python -m unittest 00-元.scripts.tests.test_tag_questions -v
```

预期：FAIL `No module named 'tag_questions'`。

- [ ] **Step 4: 写实现**

写入 `00-元/scripts/tag_questions.py`：

```python
"""候选 tag 生成器（不调用 LLM）。

输入: 题块 JSON + 白名单 JSON
输出: 给每题加 tag_candidates: [...] 字段，按命中频次降序

LLM 终审在 plan Task 9 由 sonnet 子代理完成（独立步骤），
本脚本仅产出客观可重现的关键词命中候选。

用法:
    python 00-元/scripts/tag_questions.py \
        --questions docs/superpowers/working/吉林-数学-2024-不分-新课标Ⅱ-questions.json \
        --lexicon  00-元/scripts/_数学_lexicon.json
    # 写回输入 JSON（原地修改）
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _utils import setup_utf8  # noqa: E402


def _hit_counts(text: str, lex: dict[str, dict]) -> Counter[str]:
    """统计 text 中每个白名单 term 出现次数（聚合到 bare-name）。"""
    cnt: Counter[str] = Counter()
    for term, meta in lex.items():
        if len(term) < 2:  # 单字 term 误命中率高，跳过
            continue
        n = text.count(term)
        if n > 0:
            cnt[meta["bare"]] += n
    return cnt


def tag_paper(qa: dict[str, Any], lex: dict[str, dict]) -> dict[str, Any]:
    """在 qa["questions"] 每题上加 tag_candidates 字段。"""
    for q in qa["questions"]:
        text = "\n".join([q.get("stem", ""), q.get("answer", ""), q.get("solution", "")])
        cnt = _hit_counts(text, lex)
        # 按命中次数降序，取前 8 个候选交给 LLM 终审
        q["tag_candidates"] = [t for t, _ in cnt.most_common(8)]
    return qa


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    ap.add_argument("--lexicon", required=True)
    args = ap.parse_args()

    qa = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    lex = json.loads(Path(args.lexicon).read_text(encoding="utf-8"))
    tag_paper(qa, lex)
    Path(args.questions).write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(q["tag_candidates"]) for q in qa["questions"])
    print(f"OK: 候选写回 {args.questions}（{len(qa['questions'])} 题，共 {total} 个候选 tag）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: 跑测试看通过**

```bash
python -m unittest 00-元.scripts.tests.test_tag_questions -v
```

预期：3 tests pass。

- [ ] **Step 6: Commit**

```bash
git add "00-元/scripts/tag_questions.py" "00-元/scripts/tests/test_tag_questions.py" \
        "00-元/scripts/tests/fixtures/mini_qa.json" "00-元/scripts/tests/fixtures/mini_lexicon.json"
git commit -m "feat(真题): tag_questions.py - 白名单候选 tag 生成 + 测试"
```

---

## Task 7: `render_exam_atoms.py` 渲染真题原子词条

**Files:**
- Create: `00-元/scripts/render_exam_atoms.py`
- Create: `00-元/scripts/tests/test_render_exam_atoms.py`

输入约定：题块 JSON 含 `tags: [...]`（LLM 终审后的最终 tag）和 `gap_terms: [...]`（白名单缺口候选）。
输出：`真题/<省份>-<学科>/YYYY-<gender|paper>-NN.md`。

- [ ] **Step 1: 写 test 先**

写入 `00-元/scripts/tests/test_render_exam_atoms.py`：

```python
"""测试 render_exam_atoms.py 渲染真题词条。"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from render_exam_atoms import render_paper  # noqa: E402


SAMPLE = {
    "paper_id": "2024-不分-新课标Ⅱ",
    "year": 2024,
    "gender": "不分",
    "paper": "新课标Ⅱ",
    "subject": "数学",
    "province": "吉林",
    "source_pdf": "素材/真题/吉林/.../2024年.pdf",
    "questions": [
        {"qno": 8, "qtype": "选择", "score": 5,
         "stem": "已知 f(x)=x^2，求 f(2)。", "answer": "B",
         "solution": "代入 x=2 得 4。",
         "tags": ["函数"], "gap_terms": [], "difficulty": "易"},
    ],
}


class TestRenderExamAtoms(unittest.TestCase):
    def test_creates_atom_file_with_correct_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            files = render_paper(SAMPLE, output_root=tmp_path)
            self.assertEqual(len(files), 1)
            expected = tmp_path / "吉林-数学" / "2024-新课标Ⅱ-08.md"
            self.assertTrue(expected.exists())

    def test_atom_frontmatter_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            files = render_paper(SAMPLE, output_root=tmp_path)
            text = files[0].read_text(encoding="utf-8")
            self.assertIn("title: 2024-新课标Ⅱ-08", text)
            self.assertIn("年份: 2024", text)
            self.assertIn("题号: 8", text)
            self.assertIn("考点: [函数]", text)
            self.assertIn("录入状态: 已入库", text)
            self.assertIn("[[函数]]", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试看失败**

```bash
python -m unittest 00-元.scripts.tests.test_render_exam_atoms -v
```

预期：FAIL `No module named 'render_exam_atoms'`。

- [ ] **Step 3: 写实现**

写入 `00-元/scripts/render_exam_atoms.py`：

```python
"""真题词条渲染器。

输入: 题块 JSON（包含 LLM 终审后的 tags / gap_terms / difficulty 字段）
输出: 真题/<省份>-<学科>/YYYY-*-NN.md

用法:
    python 00-元/scripts/render_exam_atoms.py \
        --questions docs/superpowers/working/吉林-数学-2024-不分-新课标Ⅱ-questions.json
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


def _atom_text(qa_meta: dict[str, Any], q: dict[str, Any]) -> str:
    """单题词条 markdown 文本。"""
    year = qa_meta["year"]
    gender = qa_meta["gender"]
    paper = qa_meta["paper"]
    qno = q["qno"]
    nn = f"{qno:02d}"
    title = build_atom_filename(year, gender, paper, qno).removesuffix(".md")
    aliases = [
        title,
        f"{year}{qa_meta['province']}{qa_meta['subject']}{paper}-{nn}",
        f"{year}年{paper}{qa_meta['subject']}第{qno}题",
    ]
    tags = q.get("tags", [])
    state = "已入库" if tags else "待人工核对"
    body_lines = [
        "---",
        f"title: {title}",
        f"aliases: [{', '.join(aliases)}]",
        f"学科: {qa_meta['subject']}",
        "学段: 高考",
        f"省份: {qa_meta['province']}",
        f"年份: {year}",
        f"卷别: {paper}",
        f"文理: {gender}",
        f"题号: {qno}",
        f"题型: {q['qtype']}",
        f"分值: {q['score']}",
        f"考点: [{', '.join(tags)}]",
        f"难度: {q.get('difficulty', '中')}",
        f"录入状态: {state}",
        f"来源PDF: {qa_meta['source_pdf']}",
        "---",
        "",
        "## 题面",
        "",
        q["stem"],
        "",
        "## 标准解答",
        "",
        f"**答案**: {q.get('answer', '（待补）')}",
        "",
        q.get("solution", "（待补）"),
        "",
        "## 关联知识点",
        "",
    ]
    for t in tags:
        body_lines.append(f"- [[{t}]]")
    if q.get("gap_terms"):
        body_lines += ["", "## 白名单缺口（待考虑建词条）"]
        for g in q["gap_terms"]:
            body_lines.append(f"- {g}")
    body_lines.append("")
    return "\n".join(body_lines)


def render_paper(qa: dict[str, Any], output_root: Path) -> list[Path]:
    """渲染整张卷为真题词条 .md 文件列表。"""
    out_dir = output_root / f"{qa['province']}-{qa['subject']}"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for q in qa["questions"]:
        fname = build_atom_filename(qa["year"], qa["gender"], qa["paper"], q["qno"])
        path = out_dir / fname
        path.write_text(_atom_text(qa, q), encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    ap.add_argument("--output-root", default="真题/")
    args = ap.parse_args()

    qa = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    out_root = REPO_ROOT / args.output_root
    files = render_paper(qa, out_root)
    print(f"OK: 渲染 {len(files)} 个真题词条到 {out_root}/{qa['province']}-{qa['subject']}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试看通过**

```bash
python -m unittest 00-元.scripts.tests.test_render_exam_atoms -v
```

预期：2 tests pass。

- [ ] **Step 5: Commit**

```bash
git add "00-元/scripts/render_exam_atoms.py" "00-元/scripts/tests/test_render_exam_atoms.py"
git commit -m "feat(真题): render_exam_atoms.py - 真题词条渲染 + 测试"
```

---

## Task 8: `aggregate_exam_indices.py` 聚合 4 份索引 + 反链回填

**Files:**
- Create: `00-元/scripts/aggregate_exam_indices.py`
- Create: `00-元/scripts/tests/test_aggregate_exam_indices.py`

输出 4 份索引：
1. `索引/真题/<省份><学科>-高频考点.md` — tag 频次榜（按 tag_pool_filters 过滤）
2. `索引/真题/<省份><学科>-题型×考点交叉表.md` — 选择/填空/解答 × tag 矩阵
3. `索引/真题/<省份><学科>-缺口词条清单.md` — 真题词条 frontmatter 中收集 gap_terms
4. `索引/真题/<省份><学科>-试卷地图.md` — 每张卷的题数/题型分布概览

副作用：在每个被命中且属于 tag_pool 的现有词条末尾幂等维护 `<!-- exam-backlinks-start --> ... <!-- exam-backlinks-end -->` 区段（最多 5 道，按年份倒序）。

- [ ] **Step 1: 写 test 先**

写入 `00-元/scripts/tests/test_aggregate_exam_indices.py`：

```python
"""测试 aggregate_exam_indices.py 聚合 4 份索引 + 反链回填。"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aggregate_exam_indices import aggregate  # noqa: E402


def _write_atom(d: Path, name: str, year: int, qno: int, qtype: str, tags: list[str], gaps: list[str] | None = None):
    fm = dedent(f"""\
        ---
        title: {name.removesuffix('.md')}
        aliases: [{name.removesuffix('.md')}]
        学科: 数学
        学段: 高考
        省份: 吉林
        年份: {year}
        卷别: 新课标Ⅱ
        文理: 不分
        题号: {qno}
        题型: {qtype}
        分值: 5
        考点: [{', '.join(tags)}]
        难度: 中
        录入状态: 已入库
        来源PDF: dummy
        ---

        ## 题面
        dummy
    """)
    body = fm
    if gaps:
        body += "\n## 白名单缺口（待考虑建词条）\n" + "\n".join(f"- {g}" for g in gaps) + "\n"
    (d / name).write_text(body, encoding="utf-8")


class TestAggregateExamIndices(unittest.TestCase):
    def test_creates_four_indices_and_backlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            atom_dir = tmp_path / "真题" / "吉林-数学"
            atom_dir.mkdir(parents=True)
            subject_dir = tmp_path / "数学"
            subject_dir.mkdir()
            # 现有词条
            (subject_dir / "265-函数.md").write_text(
                "---\ntitle: 函数\naliases: [函数]\n学科: 数学\n学段: 高中\n主题: 必修一\n状态: 完成\n英文术语: function\n---\n\n# 函数\n",
                encoding="utf-8",
            )
            # 真题原子
            _write_atom(atom_dir, "2024-新课标Ⅱ-08.md", 2024, 8, "选择", ["函数"])
            _write_atom(atom_dir, "2023-新课标Ⅱ-11.md", 2023, 11, "选择", ["函数"], gaps=["微分方程"])

            indices_dir = tmp_path / "索引" / "真题"
            indices_dir.mkdir(parents=True)

            aggregate(
                province="吉林", subject="数学",
                atom_root=tmp_path / "真题",
                indices_root=indices_dir,
                subject_root=tmp_path,
                tag_pool=lambda t, seq: True,  # 测试时全部纳入
                seq_lookup=lambda t: 265,
            )

            self.assertTrue((indices_dir / "吉林数学-高频考点.md").exists())
            self.assertTrue((indices_dir / "吉林数学-题型×考点交叉表.md").exists())
            self.assertTrue((indices_dir / "吉林数学-缺口词条清单.md").exists())
            self.assertTrue((indices_dir / "吉林数学-试卷地图.md").exists())

            # 反链回填
            text = (subject_dir / "265-函数.md").read_text(encoding="utf-8")
            self.assertIn("<!-- exam-backlinks-start -->", text)
            self.assertIn("[[2024-新课标Ⅱ-08]]", text)
            self.assertIn("[[2023-新课标Ⅱ-11]]", text)

            # 缺口清单含 微分方程
            gap_text = (indices_dir / "吉林数学-缺口词条清单.md").read_text(encoding="utf-8")
            self.assertIn("微分方程", gap_text)

    def test_backlink_idempotent(self):
        """连续跑两次反链应保持不变（幂等）。"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            atom_dir = tmp_path / "真题" / "吉林-数学"
            atom_dir.mkdir(parents=True)
            subject_dir = tmp_path / "数学"
            subject_dir.mkdir()
            (subject_dir / "265-函数.md").write_text(
                "---\ntitle: 函数\naliases: [函数]\n---\n\n# 函数\n",
                encoding="utf-8",
            )
            _write_atom(atom_dir, "2024-新课标Ⅱ-08.md", 2024, 8, "选择", ["函数"])

            indices_dir = tmp_path / "索引" / "真题"
            indices_dir.mkdir(parents=True)

            kwargs = dict(
                province="吉林", subject="数学",
                atom_root=tmp_path / "真题",
                indices_root=indices_dir,
                subject_root=tmp_path,
                tag_pool=lambda t, seq: True,
                seq_lookup=lambda t: 265,
            )
            aggregate(**kwargs)
            after_first = (subject_dir / "265-函数.md").read_text(encoding="utf-8")
            aggregate(**kwargs)
            after_second = (subject_dir / "265-函数.md").read_text(encoding="utf-8")
            self.assertEqual(after_first, after_second)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试看失败**

```bash
python -m unittest 00-元.scripts.tests.test_aggregate_exam_indices -v
```

预期：FAIL `No module named 'aggregate_exam_indices'`。

- [ ] **Step 3: 写实现**

写入 `00-元/scripts/aggregate_exam_indices.py`：

```python
"""真题原子词条 → 4 份索引 + 反链回填到现有词条。

4 份索引:
1. <province><subject>-高频考点.md
2. <province><subject>-题型×考点交叉表.md
3. <province><subject>-缺口词条清单.md
4. <province><subject>-试卷地图.md

反链区段定界:
    <!-- exam-backlinks-start -->
    ## 高考真题命中
    - [[YYYY-...]]
    ...
    <!-- exam-backlinks-end -->

幂等：重跑覆盖整段。

用法:
    python 00-元/scripts/aggregate_exam_indices.py --province 吉林 --subject 数学
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).parent))
from _exam_utils import is_in_tag_pool, load_config  # noqa: E402
from _utils import REPO_ROOT, bare_name, iter_entries, read_frontmatter, setup_utf8  # noqa: E402

BL_START = "<!-- exam-backlinks-start -->"
BL_END = "<!-- exam-backlinks-end -->"
BL_RE = re.compile(re.escape(BL_START) + r".*?" + re.escape(BL_END), re.DOTALL)
PREFIX_NUM_RE = re.compile(r"^(\d{2,4})-")


def _read_atom(p: Path) -> dict[str, Any]:
    fm = read_frontmatter(p)
    text = p.read_text(encoding="utf-8", errors="replace")
    # 缺口段
    gaps: list[str] = []
    gap_m = re.search(r"##\s*白名单缺口[^\n]*\n((?:- [^\n]+\n)+)", text)
    if gap_m:
        gaps = [line[2:].strip() for line in gap_m.group(1).splitlines() if line.startswith("- ")]
    # 考点解析
    tags_raw = fm.get("考点", "")
    tags = []
    tm = re.match(r"\[(.*)\]", tags_raw.strip())
    if tm:
        tags = [t.strip() for t in tm.group(1).split(",") if t.strip()]
    return {
        "title": fm.get("title", p.stem),
        "year": int(fm.get("年份", 0) or 0),
        "qtype": fm.get("题型", ""),
        "paper": fm.get("卷别", ""),
        "tags": tags,
        "gaps": gaps,
        "path": p,
    }


def _frequency_index(atoms: list[dict], tag_pool: Callable[[str, int], bool], seq_lookup: Callable[[str], int]) -> str:
    cnt: Counter[str] = Counter()
    years_of: dict[str, set[int]] = defaultdict(set)
    for a in atoms:
        for t in a["tags"]:
            seq = seq_lookup(t) or 0
            if not tag_pool(t, seq):
                continue
            cnt[t] += 1
            years_of[t].add(a["year"])
    lines = ["# 高频考点", "", "| 排名 | 考点 | 命中题数 | 命中年份 |", "|---:|---|---:|---|"]
    for i, (t, n) in enumerate(cnt.most_common(), 1):
        ys = ", ".join(str(y) for y in sorted(years_of[t], reverse=True))
        lines.append(f"| {i} | [[{t}]] | {n} | {ys} |")
    lines.append("")
    return "\n".join(lines)


def _qtype_x_tag_index(atoms: list[dict], tag_pool: Callable[[str, int], bool], seq_lookup: Callable[[str], int]) -> str:
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    for a in atoms:
        for t in a["tags"]:
            seq = seq_lookup(t) or 0
            if not tag_pool(t, seq):
                continue
            matrix[t][a["qtype"]] += 1
    lines = ["# 题型 × 考点交叉表", "", "| 考点 | 选择 | 填空 | 解答 | 总计 |", "|---|---:|---:|---:|---:|"]
    for t in sorted(matrix, key=lambda x: -sum(matrix[x].values())):
        c = matrix[t]
        total = sum(c.values())
        lines.append(f"| [[{t}]] | {c.get('选择',0)} | {c.get('填空',0)} | {c.get('解答',0)} | {total} |")
    lines.append("")
    return "\n".join(lines)


def _gap_index(atoms: list[dict]) -> str:
    cnt: Counter[str] = Counter()
    sources: dict[str, set[str]] = defaultdict(set)
    for a in atoms:
        for g in a["gaps"]:
            cnt[g] += 1
            sources[g].add(a["title"])
    lines = ["# 白名单缺口词条清单", "", "下列概念在真题中出现但现有学科目录无对应词条，建议补建：", "",
             "| 概念 | 出现题数 | 来源 |", "|---|---:|---|"]
    for t, n in cnt.most_common():
        srcs = ", ".join(f"[[{s}]]" for s in sorted(sources[t]))
        lines.append(f"| {t} | {n} | {srcs} |")
    lines.append("")
    return "\n".join(lines)


def _paper_map_index(atoms: list[dict]) -> str:
    by_paper: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for a in atoms:
        by_paper[(a["year"], a["paper"])].append(a)
    lines = ["# 试卷地图", "", "| 年份 | 卷别 | 题数 | 选择 | 填空 | 解答 |", "|---:|---|---:|---:|---:|---:|"]
    for (year, paper) in sorted(by_paper.keys()):
        atoms_p = by_paper[(year, paper)]
        c = Counter(a["qtype"] for a in atoms_p)
        lines.append(f"| {year} | {paper} | {len(atoms_p)} | {c.get('选择',0)} | {c.get('填空',0)} | {c.get('解答',0)} |")
    lines.append("")
    return "\n".join(lines)


def _write_backlinks(atoms: list[dict], subject: str, subject_root: Path, tag_pool, seq_lookup):
    """在每个被命中且 in pool 的现有词条末尾维护反链区段。

    subject_root 通常传仓库根；函数扫 <subject_root>/<subject>/*.md。
    """
    by_tag: dict[str, list[dict]] = defaultdict(list)
    for a in atoms:
        for t in a["tags"]:
            seq = seq_lookup(t) or 0
            if not tag_pool(t, seq):
                continue
            by_tag[t].append(a)

    # 通过 bare-name 反向查找现有词条文件（仅扫当前学科目录）
    name_to_path: dict[str, Path] = {}
    target_dir = subject_root / subject
    if target_dir.is_dir():
        for p in iter_entries(target_dir):
            name_to_path[bare_name(p)] = p

    for tag, hits in by_tag.items():
        path = name_to_path.get(tag)
        if not path:
            continue
        hits_sorted = sorted(hits, key=lambda a: -a["year"])[:5]
        section = "\n".join([
            BL_START,
            "## 高考真题命中",
            *(f"- [[{a['title']}]]" for a in hits_sorted),
            BL_END,
        ])
        text = path.read_text(encoding="utf-8")
        if BL_RE.search(text):
            new = BL_RE.sub(section, text)
        else:
            sep = "\n\n" if not text.endswith("\n") else "\n"
            new = text + sep + section + "\n"
        if new != text:
            path.write_text(new, encoding="utf-8")


def aggregate(*, province: str, subject: str,
              atom_root: Path, indices_root: Path, subject_root: Path,
              tag_pool: Callable[[str, int], bool],
              seq_lookup: Callable[[str], int]):
    atom_dir = atom_root / f"{province}-{subject}"
    atoms = [_read_atom(p) for p in atom_dir.glob("*.md")]
    indices_root.mkdir(parents=True, exist_ok=True)
    (indices_root / f"{province}{subject}-高频考点.md").write_text(_frequency_index(atoms, tag_pool, seq_lookup), encoding="utf-8")
    (indices_root / f"{province}{subject}-题型×考点交叉表.md").write_text(_qtype_x_tag_index(atoms, tag_pool, seq_lookup), encoding="utf-8")
    (indices_root / f"{province}{subject}-缺口词条清单.md").write_text(_gap_index(atoms), encoding="utf-8")
    (indices_root / f"{province}{subject}-试卷地图.md").write_text(_paper_map_index(atoms), encoding="utf-8")
    _write_backlinks(atoms, subject, subject_root, tag_pool, seq_lookup)


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--province", required=True)
    ap.add_argument("--subject", required=True)
    args = ap.parse_args()

    cfg = load_config()
    lex_path = REPO_ROOT / "00-元" / "scripts" / f"_{args.subject}_lexicon.json"
    lex = json.loads(lex_path.read_text(encoding="utf-8")) if lex_path.exists() else {}

    def tag_pool(t: str, seq: int) -> bool:
        return is_in_tag_pool(t, seq, args.subject, cfg)

    def seq_lookup(t: str) -> int:
        meta = lex.get(t)
        return (meta or {}).get("seq") or 0

    aggregate(
        province=args.province, subject=args.subject,
        atom_root=REPO_ROOT / "真题",
        indices_root=REPO_ROOT / "索引" / "真题",
        subject_root=REPO_ROOT,
        tag_pool=tag_pool, seq_lookup=seq_lookup,
    )
    print(f"OK: 4 份索引 + 反链回填完成（{args.province}-{args.subject}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试看通过**

```bash
python -m unittest 00-元.scripts.tests.test_aggregate_exam_indices -v
```

预期：2 tests pass。

- [ ] **Step 5: 跑全量测试**

```bash
python -m unittest discover -s "00-元/scripts/tests" -v
```

预期：所有 6 个测试模块全部 pass。

- [ ] **Step 6: Commit**

```bash
git add "00-元/scripts/aggregate_exam_indices.py" "00-元/scripts/tests/test_aggregate_exam_indices.py"
git commit -m "feat(真题): aggregate_exam_indices.py - 4 份索引聚合 + 反链回填 + 测试"
```

---

## Task 9: P1 Pilot — 跑通 2024 新课标Ⅱ 端到端

**Files:**
- Create: `真题/吉林-数学/2024-新课标Ⅱ-*.md`（19-22 个词条）
- Create: `索引/真题/吉林数学-*.md`（4 份）
- Modify: `数学/<被命中词条>.md`（追加反链区段）

- [ ] **Step 1: 生成数学白名单（若未生成）**

```bash
python "00-元/scripts/build_subject_lexicon.py" --subject 数学
```

预期：`OK: 写出 ...\_数学_lexicon.json（≥1500 个 term）`。

- [ ] **Step 2: PDF 切分**

```bash
python "00-元/scripts/parse_exam_pdf.py" \
  --pdf "素材/真题/吉林/2008-2024·（吉林）数学高考真题/2024年高考数学试卷（新课标Ⅱ卷）（解析卷）.pdf" \
  --subject 数学 --province 吉林 --year 2024
```

预期：`docs/superpowers/working/吉林-数学-2024-不分-新课标Ⅱ-questions.json` 含 19-22 题。

人工抽查 JSON：第 1、5、12、19 题的 `stem` 是否完整、`qtype` 合理。
若 ≥ 5 题 stem < 20 字符或包含明显乱码 → STOP，触发 spec § 8 风险回退。

- [ ] **Step 3: 候选 tag 生成**

```bash
python "00-元/scripts/tag_questions.py" \
  --questions "docs/superpowers/working/吉林-数学-2024-不分-新课标Ⅱ-questions.json" \
  --lexicon "00-元/scripts/_数学_lexicon.json"
```

预期：`OK: 候选写回 ...（19-22 题，共 80-150 个候选 tag）`。

- [ ] **Step 4: LLM 终审（sonnet 子代理）**

启动一个 sonnet 子代理，prompt 模板：

> 你是高考数学考点标注员。我会给你一张 2024 新课标Ⅱ 数学卷的题块 JSON，每题已带 `tag_candidates`（白名单关键词命中候选）。你的任务：
>
> 1. 对每题，从 `tag_candidates` 中选出 2-4 个最贴合该题考点的 term 作为最终 `tags`，必须从候选中选，不能创造新词。
> 2. 若题面里出现重要数学概念但不在候选里（白名单缺口），加入 `gap_terms: [...]`（最多 3 个）。
> 3. 给一个难度判断 `difficulty`：易/中/难（启发式：选择 1-6 题/填空 13-14=易；解答倒数 2 道=难；其他=中）。
> 4. 输出 JSON 同 schema，仅在每题增加 `tags`/`gap_terms`/`difficulty` 三个字段。
>
> 输入 JSON 路径：`docs/superpowers/working/吉林-数学-2024-不分-新课标Ⅱ-questions.json`
> 输出：原地写回（保留所有原字段，加新字段）。

预期：子代理完成后，JSON 每题都有 `tags` (2-4 个) / `gap_terms` (0-3 个) / `difficulty` 字段。

- [ ] **Step 5: 渲染真题原子词条**

```bash
python "00-元/scripts/render_exam_atoms.py" \
  --questions "docs/superpowers/working/吉林-数学-2024-不分-新课标Ⅱ-questions.json"
```

预期：`真题/吉林-数学/2024-新课标Ⅱ-01.md ... 2024-新课标Ⅱ-22.md` 创建。

- [ ] **Step 6: 聚合索引 + 反链回填**

```bash
python "00-元/scripts/aggregate_exam_indices.py" --province 吉林 --subject 数学
```

预期：
- `索引/真题/吉林数学-高频考点.md`
- `索引/真题/吉林数学-题型×考点交叉表.md`
- `索引/真题/吉林数学-缺口词条清单.md`
- `索引/真题/吉林数学-试卷地图.md`
- 至少 5 个 `数学/<词条>.md` 末尾出现 `<!-- exam-backlinks-start -->` 区段

- [ ] **Step 7: P1 Pilot 验收**

人工逐项验收（spec § 7.1）：
- [ ] 19-22 个 .md 词条 frontmatter 字段齐全
- [ ] 用 `python -c "import yaml; from pathlib import Path; [yaml.safe_load(open(p,encoding='utf-8').read().split('---')[1]) for p in Path('真题/吉林-数学').glob('2024-*.md')]"` 验证 yaml 可解析
- [ ] tag 全部能在 `_数学_lexicon.json` 命中（用 `aggregate_exam_indices.py` 已隐含校验，缺口在缺口清单里）
- [ ] 在 Obsidian 里打开 `数学/265-函数.md`（或任一被命中词条），能点击跳到真题词条
- [ ] 缺口词条清单非空
- [ ] OCR/公式失真题数 ≤ 2（人工抽查）

任一不通过 → 修复后重跑此 Task。

- [ ] **Step 8: Commit Pilot**

```bash
git add "真题/吉林-数学" "索引/真题" "数学"
git commit -m "feat(真题): P1 Pilot - 吉林 2024 新课标Ⅱ 数学端到端跑通"
```

---

## Task 10: P2 扩量 — 2020-2024 共 9 套卷

吉林 2020-2024 数学共 9 张卷：
- 2020 文 + 理（新课标Ⅱ）
- 2021 文 + 理（全国乙=新课标Ⅰ）
- 2022 文 + 理（全国乙）
- 2023（新课标Ⅱ，不分）
- 2024（新课标Ⅱ，不分）

合计 9 套（注意 2021 解析卷有重名带 (1) 后缀的副本，跳过）。

- [ ] **Step 1: 准备运行清单**

```bash
ls "素材/真题/吉林/2008-2024·（吉林）数学高考真题/" | grep "解析卷.pdf$" | grep -E "^(202[0-4])" | grep -v "(1)" | sort -u
```

预期：列出 9 个 PDF 文件名。把这个列表保存到 `docs/superpowers/working/p2-papers.txt`。

- [ ] **Step 2: 批量步骤 ①②③（PDF 切分 + 候选 tag）**

对 p2-papers.txt 中每个 PDF（脚本可分别手动调，也可写 shell 循环）：

```bash
for f in $(cat docs/superpowers/working/p2-papers.txt); do
  YEAR=$(echo "$f" | grep -oE '^[0-9]{4}')
  python "00-元/scripts/parse_exam_pdf.py" \
    --pdf "素材/真题/吉林/2008-2024·（吉林）数学高考真题/$f" \
    --subject 数学 --province 吉林 --year $YEAR
done

for j in docs/superpowers/working/吉林-数学-202*.json; do
  python "00-元/scripts/tag_questions.py" \
    --questions "$j" \
    --lexicon "00-元/scripts/_数学_lexicon.json"
done
```

预期：9 个题块 JSON 文件，每个含 `tag_candidates`。

- [ ] **Step 3: 批量步骤 ④（LLM 终审）—— 4 个并行子代理**

并行 dispatch 4 个 sonnet 子代理，每个领 2-3 张卷，prompt 同 Task 9 Step 4。
分组：
- 子代理 A：2020 文 + 2020 理 + 2021 文
- 子代理 B：2021 理 + 2022 文 + 2022 理
- 子代理 C：2023
- 子代理 D：2024（已 Pilot 完，跳过）

实际并行 3 个（子代理 A / B / C），D 已完成。

预期：所有未完成的 JSON 文件都新增 tags/gap_terms/difficulty 字段。

- [ ] **Step 4: 批量步骤 ⑤（渲染原子词条）**

```bash
for j in docs/superpowers/working/吉林-数学-202[0-3]-*.json; do
  python "00-元/scripts/render_exam_atoms.py" --questions "$j"
done
```

预期：`真题/吉林-数学/` 下新增 ~180 个原子词条（不含已有 2024 的 22 个）。

- [ ] **Step 5: 重跑聚合**

```bash
python "00-元/scripts/aggregate_exam_indices.py" --province 吉林 --subject 数学
```

预期：4 份索引重写为 9 套卷的全量数据；反链回填范围扩大。

- [ ] **Step 6: P2 验收**

- [ ] `真题/吉林-数学/` 词条数 ≈ 200（19+ 题/卷 × 9 卷 - 重叠的 2024 22 题）
- [ ] 高频考点表榜首 3 项符合直觉（典型为：函数、导数应用、立体几何/解析几何）
- [ ] 至少 20 个现有词条获得了反链区段

- [ ] **Step 7: Commit P2**

```bash
git add "真题/吉林-数学" "索引/真题" "数学"
git commit -m "feat(真题): P2 扩量 - 吉林 2020-2024 共 9 套卷入库"
```

---

## Task 11: P3 扩量 — 2015-2019 共 10 套卷

吉林 2015-2019 数学共 10 张卷（5 年 × 文/理 = 10）。

- [ ] **Step 1: 准备运行清单**

```bash
ls "素材/真题/吉林/2008-2024·（吉林）数学高考真题/" | grep "解析卷.pdf$" | grep -E "^201[5-9]" | sort -u > docs/superpowers/working/p3-papers.txt
wc -l docs/superpowers/working/p3-papers.txt
```

预期：10 行。

- [ ] **Step 2: 批量切分 + 候选**

```bash
for f in $(cat docs/superpowers/working/p3-papers.txt); do
  YEAR=$(echo "$f" | grep -oE '^[0-9]{4}')
  python "00-元/scripts/parse_exam_pdf.py" \
    --pdf "素材/真题/吉林/2008-2024·（吉林）数学高考真题/$f" \
    --subject 数学 --province 吉林 --year $YEAR
done

for j in docs/superpowers/working/吉林-数学-201[5-9]-*.json; do
  python "00-元/scripts/tag_questions.py" --questions "$j" --lexicon "00-元/scripts/_数学_lexicon.json"
done
```

- [ ] **Step 3: LLM 终审 5 个并行子代理**

5 组（每组 2 张卷，分别为同年文+理）：
- 子代理 E：2015 文+理
- 子代理 F：2016 文+理
- 子代理 G：2017 文+理
- 子代理 H：2018 文+理
- 子代理 I：2019 文+理

并行 dispatch（建议每次 4 个，分两批）。

- [ ] **Step 4: 渲染**

```bash
for j in docs/superpowers/working/吉林-数学-201[5-9]-*.json; do
  python "00-元/scripts/render_exam_atoms.py" --questions "$j"
done
```

预期：`真题/吉林-数学/` 总词条数达 ~420。

- [ ] **Step 5: 终聚合**

```bash
python "00-元/scripts/aggregate_exam_indices.py" --province 吉林 --subject 数学
```

- [ ] **Step 6: P3 验收**

- [ ] `真题/吉林-数学/` 总词条数 ≥ 380（容许少量 OCR 失真跳过题）
- [ ] 4 份索引内容覆盖 2015-2024 全部数据
- [ ] 缺口清单去重后 ≥ 5 个候选概念

- [ ] **Step 7: Commit P3**

```bash
git add "真题/吉林-数学" "索引/真题" "数学"
git commit -m "feat(真题): P3 扩量 - 吉林 2015-2019 共 10 套卷入库；近 10 年全量完成"
```

---

## Task 12: 终验 + CLAUDE.md 进度更新

- [ ] **Step 1: 跑全量测试**

```bash
python -m unittest discover -s "00-元/scripts/tests" -v
```

预期：所有测试 pass。

- [ ] **Step 2: 扩展 `analyze_links.py` 让它扫真题目录**

否则现有词条末尾追加的 `[[2024-新课标Ⅱ-08]]` 反链会被误判为断链。

修改 `00-元/scripts/_utils.py`，在 `SUBJECT_DIRS` 之后追加：

```python
# 真题词条根（区别于 SUBJECT_DIRS 的学科目录）
# 子目录命名: <省份>-<学科>，如 真题/吉林-数学/
EXAM_BASE_DIR = "真题"


def iter_exam_dirs() -> Iterator[Path]:
    """遍历 真题/<省份>-<学科>/ 子目录。"""
    base = REPO_ROOT / EXAM_BASE_DIR
    if not base.is_dir():
        return
    for sub in sorted(base.iterdir()):
        if sub.is_dir() and not sub.name.startswith("."):
            yield sub
```

修改 `00-元/scripts/analyze_links.py` 的 `collect_all()` 函数，在 SUBJECT_DIRS 循环之后追加：

```python
    # 真题词条也纳入图
    from _utils import iter_exam_dirs
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
```

- [ ] **Step 3: 跑词条关联性诊断**

```bash
python "00-元/scripts/analyze_links.py" | head -40
```

预期：总词条数 ≈ 946（原 526 + 真题 ~420）；断链数不应高于试点前。
新出现的"学科"行 `吉林-数学` 应有 ~420 词条，孤岛率应较低（每题至少有 2-4 个出链 + 现有词条反向入链）。

- [ ] **Step 4: 跑 stats.py**

```bash
python "00-元/scripts/stats.py" --check
```

如果显示 STALE：

```bash
python "00-元/scripts/stats.py" --write
```

预期：CLAUDE.md 顶部进度表更新，数学词条数变化。

- [ ] **Step 5: 更新 CLAUDE.md "真题分析进度" 章节**

替换 `<!-- EXAM-PROGRESS-START -->` ... `<!-- EXAM-PROGRESS-END -->` 之间的占位为：

```markdown
<!-- EXAM-PROGRESS-START -->

| 省份-学科 | 年份范围 | 卷数 | 题词条数 | 索引文件 | 状态 |
|---|---|---:|---:|---|---|
| 吉林-数学 | 2015-2024 | 19 | ~420 | 4 份 | ✅ 已完成 |

**4 份索引**（位于 `索引/真题/`）：
- `吉林数学-高频考点.md` — 按 tag 频次排序，pool 过滤后只看高中数学
- `吉林数学-题型×考点交叉表.md` — 选择/填空/解答 × 考点矩阵
- `吉林数学-缺口词条清单.md` — 真题命中但现有词条未覆盖的概念
- `吉林数学-试卷地图.md` — 每张卷题数/题型分布概览

**反链回填**：被命中的现有数学词条末尾自动维护 `<!-- exam-backlinks-start/end -->` 区段。

**可复用流水线**（5 个参数化脚本 + 1 yaml 配置）：
后续接 北京/黑龙江/其他学科 仅需重新跑 5 步即可，详见 `docs/superpowers/specs/2026-05-10-jilin-math-exam-analysis-design.md`。

<!-- EXAM-PROGRESS-END -->
```

- [ ] **Step 6: 最终 commit**

```bash
git add CLAUDE.md
git commit -m "docs(真题): 吉林数学高考真题分析试点完成 - 19 卷 ~420 题入库 + 4 份索引"
```

---

## 验收标准（整体）

整个计划完成后必须全部满足：
- [ ] `00-元/scripts/` 下 5 个新脚本 + 1 份配置 + 1 份共享工具 + 6 份测试，全测试通过
- [ ] `真题/吉林-数学/` 词条数 ≥ 380（约 420 - OCR 失真容差）
- [ ] `索引/真题/` 下 4 份索引文件齐全且非空
- [ ] 至少 30 个 `数学/*.md` 词条末尾有 `<!-- exam-backlinks-start -->` 反链区段
- [ ] CLAUDE.md "真题分析进度" 章节更新
- [ ] 跑 `python "00-元/scripts/analyze_links.py"` 后断链数不应高于试点前
- [ ] Spec § 7.1 P1 Pilot 验收清单全部勾选；Spec § 7 表中 P0/P1/P2/P3 里程碑全部完成
