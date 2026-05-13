# 真题分析 v2 设计 · 截图 + 摘要 + 指针 + 三层复审

- **日期**：2026-05-12
- **状态**：design（待 user approve → writing-plans）
- **替代**：v1（已清空，备份 zip 在 `素材/backup/2026-05-12/exam-pre-migrate.zip`）
- **关联**：[多模型工作流 v3](../plans/2026-05-12-multi-model-workflow-v3.md)

## 0. 背景与决策动机

### v1 痛点（驱动 v2 重新设计）

| # | 痛点 | 根因 |
|---|---|---|
| 1 | stem 字符级 bug 大量残留（√/分数/上下标在 PDF 里是字形不是 unicode） | pdfplumber/PyMuPDF/pdfminer 三库实测均不可救（task #15） |
| 2 | tags 错配率 ~35%（实数→复数题、面积→线性回归 等） | v4-pro 抽考点未复审就直接入库 |
| 3 | 9 题"待人工核对"长期未处理 | 缺自动断言强制非空 |
| 4 | markdown 词条人工审定质量"较低" | 1+2 累积，孩子看不懂题面 |

### 用户主场景（决定一切设计）

按 [Q1] 用户选定 **1 + 3 + 4 三类场景**（不含 2）:
1. **孩子复习用** — 需完整题面 / 答案 / 解析，按考点检索
3. **考点频次统计分析** — 看高频考点指导学习路径优先级
4. **考点知识图谱** — 概念关联图供未来快速查看

**未选 2（家长备课）** → 不需要为家长设计特定路径

### 核心矛盾解决（截图替代文本）

场景 1 要求"完整题面"，但 v1 证明任何文本提取库都救不了字符级 bug。**v2 采用截图 + 摘要 + 指针三件套**：

- **截图**：保证题面 / 解析 100% 视觉保真
- **摘要**：1-2 句自然语言，用于 Obsidian 全文检索
- **指针**：链回原 PDF 特定页，可手动跳转

---

## 1. 数据模型

### 1.1 单题词条结构（v2 模板）

```markdown
---
title: 2022-文-01
aliases: [2022-文-01, 2022吉林数学全国乙-01]
学科: 数学
学段: 高考
省份: 吉林
年份: 2022
卷别: 全国乙
文理: 文
题号: 1
题型: 选择
分值: 5
考点: [集合的运算, 并集]
难度: 易
PDF: 素材/真题/吉林/.../2022年高考数学试卷（文）.pdf
PDF页码: 1
题面图: 素材/真题截图/吉林-数学/2022-文-01.q.png
解析图: 素材/真题截图/吉林-数学/2022-文-01.a.png
答案: A
录入状态: 已入库
---

## 题面

![](../../素材/真题截图/吉林-数学/2022-文-01.q.png)

## 摘要

考察集合的交集运算。已知 M、N 两个集合，求 M ∩ N。简单计算题。

## 关联考点

- [[314-集合的运算|集合的运算]]
- [[并集]]

## 答案与解析

![](../../素材/真题截图/吉林-数学/2022-文-01.a.png)

> 📄 原 PDF 第 1 页：`素材/真题/吉林/.../2022年高考数学试卷（文）.pdf`
```

### 1.2 frontmatter 字段定义

| 字段 | 类型 | 来源 | 必填 |
|---|---|---|---|
| `title` | str | 文件名同名 | ✓ |
| `aliases` | list[str] | 模板：title / `<year><province><subject><paper>-<qno>` 等 | ✓ |
| `学科 / 学段 / 省份 / 年份 / 卷别 / 文理` | str | CLI 参数 | ✓ |
| `题号` | int | 切分得 | ✓ |
| `题型` | str | 启发式（按 qno + total_q） | ✓ |
| `分值` | int | 按 year + total_q 表查 | ✓ |
| `考点` | list[str] | **v4-pro 抽 → sonnet 复验**（L2） | ✓ ≥ 1 项（典型 2-4） |
| `难度` | str | v4-pro 启发式估（易/中/难） | ✓ |
| `PDF` | str | 相对路径 | ✓ |
| `PDF页码` | int | bbox 定位 | ✓ |
| `题面图` | str | 相对路径 | ✓ |
| `解析图` | str | 相对路径 | ✓ |
| `答案` | str | markitdown 抓【答案】后段（限长 50 字符） | ✓ |
| `录入状态` | enum | 已入库 / 仲裁中 / 待人工核对 | ✓ |

### 1.3 目录组织

```
真题/吉林-数学/                            ← 词条 (~23/卷 × 19 卷 ≈ 400+)
  ├── 2022-文-01.md
  ├── 2022-文-02.md
  └── ...

素材/真题截图/吉林-数学/                   ← 截图（每题 2 张）
  ├── 2022-文-01.q.png                    ← 题面截图
  ├── 2022-文-01.a.png                    ← 答案/解析截图
  └── ...

索引/真题/                                  ← 索引（与 v1 形式相同）
  ├── 吉林数学-高频考点.md
  ├── 吉林数学-题型×考点交叉表.md
  ├── 吉林数学-缺口词条清单.md
  └── 吉林数学-试卷地图.md

数学/<词条>.md                              ← 概念词条末尾追加反链段（与 v1 同机制）
```

### 1.4 与 v1 的关键差异

| 维度 | v1 | v2 |
|---|---|---|
| stem 形式 | 纯文本（字符级 bug 重灾区） | **截图**（PNG，保真） |
| 答案/解析 | 文本字段（公式碎） | **截图**（PNG，保真） |
| 答案字段 | 多行文本 | 仅选项字母 / 简短数值 |
| 摘要 | 无 | 1-2 句自然语言（**新增**） |
| tags 复审 | 无（v4-pro 直接上线） | **三层复审**（自动断言 + sonnet 看图 + Opus 抽检） |
| 文件数 | 87 .md | 87 .md + 174 PNG |

---

## 2. 工作流（含三层复审）

### 2.1 6 步主流程

```text
INPUT: 一张 PDF（如 2022 全国乙文）

Step 1【脚本 · PyMuPDF】题边界识别 + 截图生成
  - 用 page.get_text("words") 拿题号 "N." 的 bbox
  - 题面区域 = 题号 N → 【答案】之前
  - 解析区域 = 【答案】→ 题号 N+1 之前（含跨页处理）
  - 用 page.get_pixmap(clip=area, dpi=200) 渲染 PNG
  - 输出：N × 2 PNG + questions.json（含 qno / 题型 / 分值 / 截图路径 / PDF页码）
  ─── L1 自动断言 ───
  ✓ 题数 = 卷期望题数（2022 文 = 23）
  ✓ 每张截图宽高比 ∈ [0.5, 4.0]
  ✓ 截图文件 > 10 KB
  ✓ 跨页题 flag 警告

Step 2【脚本 · markitdown】元数据提取
  - markitdown 转 PDF → md（含【答案】【解析】段）
  - 正则抽每题：答案文本 / 解析关键文本
  - 输出：questions.json 更新（+answer +solution_text）
  ─── L1 自动断言 ───
  ✓ 每题 answer 非空
  ✓ 解析文本长度 > 30 字符
  ✓ 答案文本长度 < 50（防答案块整体串入）

Step 3【DeepSeek v4-pro】摘要 + 考点抽取
  - 输入：每题 solution_text（中文为主，公式碎可忽略）
  - prompt：「输出 1-2 句考点描述 + 2-4 个考点术语」
  - 输出：questions.json 更新（+summary +tags +difficulty）

Step 3b【Sonnet subagent · L2 看截图复验】★ v2 新增关键机制
  - 起 ⌈N/10⌉ 个 sonnet subagent（每个领 10 题）
  - 输入：题面截图 + v4-pro 抽出的 tags + summary
  - prompt：「看截图判断 v4-pro 抽的考点和摘要是否吻合实际题面。
             输出：吻合 / 部分偏差（指出哪些 tag 错配）/ 严重偏差」
  - 输出：verdict.jsonl，每题一行
  - 不吻合项进 Opus 仲裁队列

Step 4【脚本】渲染词条 .md
  - 用 v2 模板渲染 N 个真题/吉林-数学/*.md
  - tags 用 Step 3b 校准后版本

Step 5【脚本】4 份索引 + 反链回填
  - 高频考点 / 题型×考点 / 缺口词条 / 试卷地图
  - 数学概念词条末尾追加 <!-- exam-backlinks-start/end -->

Step 6【Opus · L3 终审】
  - 优先处理 Step 3b 的 Opus 仲裁队列（不吻合 tags）
  - 抽 10% 看截图 + 核验 frontmatter 完整性
  - 跨页题人工核对（Step 1 flag）
  - 通过 → 入库；否则回退某步重跑
```

### 2.2 三层复审设计

| 层 | 工具 | 覆盖率 | 抓什么 bug | 防 v1 的哪个痛点 |
|---|---|---|---|---|
| L1 自动复审 | 脚本断言 | **100%** | 截图边界异常 / 元数据字段缺失 / 答案文本超长 | v1 没有自动断言，bug 上线才发现 |
| L2 Sonnet 看图复验 | sonnet subagent + 视觉 | **100%** | tags 错配、摘要不准、截图边界偏差 | v1 没复审 → tags 错配 35% |
| L3 Opus 终审 | 主会话 | 10% 抽样 + 100% 仲裁队列 | L2 标记的不吻合项 + 跨学段一致性 | v1 没系统终审 |

### 2.3 资源测算（每卷 23 题）

| 操作 | 频次 | 单次成本 |
|---|---|---|
| Step 3 v4-pro API | 23 次 | ~¥0.05 |
| **Step 3b Sonnet subagent** | **3 个** subagent × 10 题 | sonnet quota（视觉看图） |
| Step 6 Opus 抽检 | 2-3 题 | 主会话 token |
| **预期不吻合率** | **< 5%**（vs v1 35%） | Opus 处理 ~1 题/卷 |

---

## 3. 脚本设计

### 3.1 6 脚本 + 2 配置

```
00-元/scripts/
├── exam_pipeline_config.yaml      [配置] 省份/学科/卷别归一/tag 池过滤
├── _exam_utils.py                 [工具] paper_id 构造 / filename 模板 / config load
│
├── exam_screenshot.py             [Step 1] PyMuPDF 截图生成 + bbox 定位
├── exam_extract_meta.py           [Step 2] markitdown 抽 answer + 解析文本
├── exam_enrich.py                 [Step 3] v4-pro 摘要 + 考点
├── exam_verify.py                 [Step 3b] sonnet 复验队列（prepare/ingest 两步法）
├── exam_render.py                 [Step 4] 渲染 .md 词条
└── exam_index.py                  [Step 5] 4 份索引 + 反链回填
```

### 3.2 CLI 接口

| 脚本 | CLI | 输入 | 输出 |
|---|---|---|---|
| `exam_screenshot.py` | `--pdf <p> --province --subject --year` | 1 张 PDF | `素材/真题截图/<province>-<subject>/*.png` + `questions.json` |
| `exam_extract_meta.py` | `--questions <p>` | questions.json + PDF | json 更新（+answer +solution_text） |
| `exam_enrich.py` | `--questions <p>` | questions.json | json 更新（+summary +tags +difficulty） |
| `exam_verify.py` | `--questions <p> --mode prepare\|ingest` | json + 截图 | `verdicts/` prompt 队列 → ingest 后 +verdict 字段 |
| `exam_render.py` | `--questions <p>` | questions.json | `真题/<province>-<subject>/*.md` |
| `exam_index.py` | `--province --subject` | 真题 .md 目录 | `索引/真题/*.md` + 数学词条反链段 |

### 3.3 单测策略

| 脚本 | 单测重点 | 目标数 |
|---|---|---|
| `_exam_utils` | filename 模板 / paper_id 构造 / config load | 4 |
| `exam_screenshot` | 题号 bbox 定位准确性（fixture 验已知坐标）/ 跨页题边界 | 6 |
| `exam_extract_meta` | answer 正则 / 解析段截取 / 字段长度限制 | 5 |
| `exam_enrich` | mock LLM 返回 + 解析逻辑 / 解析失败兜底 | 5 |
| `exam_verify` | prompt 渲染 / verdict 解析 / prepare-ingest 幂等 | 6 |
| `exam_render` | frontmatter 字段完整性 / 截图 link 路径正确 / 反链段 | 5 |
| `exam_index` | 高频统计 / 反链回填幂等性 | 4 |
| **合计** | | **~35** |

---

## 4. 验收标准与数据迁移

### 4.1 Pilot 验收 gate（首张卷 = 23 题）

| 指标 | 要求 |
|---|---|
| 截图完整性 | 23 × 2 = 46 PNG 全部生成，宽高比 ∈ [0.5, 4.0] |
| 元数据完整性 | 100% answer / summary / tags 非空（tags ≥ 1，典型 2-4） |
| L2 sonnet 复验 | ≥ 90% "吻合"，仲裁队列 ≤ 3 题 |
| Opus 抽检 | 3 题（~13%）全部通过 |
| 索引产出 | 4 份索引正常生成，反链回填幂等 |
| 端到端时间 | ≤ 1 小时（含 sonnet quota 等待） |
| 单测 | ~35 个全部通过 |

**任何指标不达标 → 不进入 Phase 2，先修脚本/调 prompt**

### 4.2 数据迁移与备份

- **v1 zip 备份保留**：`素材/backup/2026-05-12/exam-pre-migrate.zip` 不动
- **v1 数据已清空** 87 词条 + 索引 + 反链已删
- **v1 脚本已删** 不复用，从头写
- **v2 从零** pilot 验证 → Phase 2 续跑

### 4.3 CLAUDE.md 真题节恢复

Pilot 通过后，将当前"已清空 v1"占位替换为：

```markdown
## 真题分析

<!-- EXAM-PROGRESS-START -->

| 省份-学科 | 年份范围 | 卷数 | 题词条数 | 索引 | 状态 |
|---|---|---:|---:|---|---|
| 吉林-数学 | 2022-2024 | <N>/19 | <M> | 4 份 | ⏳/✅ |

**v2 脚手架** ✅（6 脚本 + yaml + ~35 单测）

**v2 关键设计**:
- 题面 + 解析 用截图保真（PNG），彻底回避 v1 字符级 bug
- L1 自动断言 + L2 sonnet 看图复验 + L3 Opus 抽检 三层复审
- 每题双图：<id>.q.png + <id>.a.png

**已知限制**：
- 跨页题需 Opus 人工核对（脚本自动 flag）
- 题号坐标定位偶有偏差（PyMuPDF + bbox 启发式，~5% 抽样修正）

详见 `docs/superpowers/specs/2026-05-12-jilin-math-exam-v2-design.md` 与对应 plan。

<!-- EXAM-PROGRESS-END -->
```

---

## 5. 实施分阶段

### 5.1 Phase 1 · Pilot（半天）

1. **脚手架搭建** ~3 小时
   - 写 6 脚本骨架 + yaml 配置 + 共享工具
   - 写 ~35 单测，全部通过
2. **首张卷端到端** ~1 小时
   - 选 2022 文 = 23 题（v1 跑过，可对比效果）
   - 走完整 Step 1-6
   - Opus 仲裁 + 验收 gate

**Phase 1 出口**：23 题入库 + 4 份索引 + 全部验收 gate 通过

### 5.2 Phase 2 · 续跑剩余 18 卷（5/15 sonnet quota 恢复后）

- 2022 理 / 2023 / 2024 = 3 卷
- 2020 / 2021 文+理 = 4 卷
- 2008-2019 = 12 卷（部分年份可能只有文或只有理）
- 一次 `dispatching-parallel-agents` 起 5 个 sonnet subagent 并行 L2 复验
- 预计总耗时：~3-4 小时（含 Opus 仲裁）

**Phase 2 出口**：吉林数学 19 卷全部入库 ≈ 400+ 题词条

### 5.3 Phase 3 · 扩省份 / 学科

- yaml 零代码改动平移：北京 / 黑龙江 + 物理 / 化学 / 生物
- 每省份首批开 `--cross-check 10`（参照工作流 v3 交叉复检规则）

**Phase 3 出口**：2+ 省份样本入库，pipeline 验证可扩展

---

## 6. 防御与已知风险

### 6.1 v2 防御措施 vs v1 已知失败

| v1 失败 | v2 防御 |
|---|---|
| 9 题 tags 空 → "待人工核对" 拖延 | L1 自动断言：tags 空就 fail，不入库 |
| 30+ 题 tag 错配 | L2 sonnet 每题必看截图复验 |
| 跨年同名 bare 冲突 | 文件名 `<year>-<paper>-<qno>` 设计已规避 |
| stem 字符级 bug | 截图替代文本，根除 |
| solution 字段大量空 | 截图替代，无此字段 |
| 答案块串入 stem | 截图边界由 bbox 定位 + L1 断言 |

### 6.2 v2 新风险

| 风险 | 缓解 |
|---|---|
| 题号 bbox 定位偏差（题号被表格化等） | L1 断言宽高比 + L2 sonnet 抽样验证 + L3 跨页题人工核对 |
| sonnet quota 不足（每卷 3 subagent × 19 卷 = 57） | 5/15 后跑 + 仲裁队列降级到 Opus 主会话 |
| markitdown 提取的解析文本质量参差 | 用作 v4-pro 输入素材，最终结论由 L2 看截图复核 |
| 截图体积大（每题 2 PNG，19 卷 × ~50 题 × 2 ≈ 2000 PNG） | dpi=200 平衡清晰度与体积，估算总 < 200 MB |

---

## 7. 关联文档

- 多模型工作流 v3：`docs/superpowers/plans/2026-05-12-multi-model-workflow-v3.md`
- v1 历史备份：`素材/backup/2026-05-12/exam-pre-migrate.zip`（清空前快照）
- CLAUDE.md「真题分析」节：待 Phase 1 通过后恢复

## 8. 后续步骤

本 spec 通过后由 `superpowers:writing-plans` 转写实施计划：`docs/superpowers/plans/2026-05-12-jilin-math-exam-v2-plan.md`
