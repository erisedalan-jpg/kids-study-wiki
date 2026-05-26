# CLAUDE.md

家庭学习 Wiki：为两个孩子（5 岁、3 岁，学前→高中）共建的知识库。Obsidian + Claude Code 协作；参考 [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 思想，原子化文章 + 双向链接组网 + 增量积累。

> **本文件是精简操作手册**（怎么干 / 规矩 / 东西在哪）。「做了什么」以 git log + 词条本身 + `stats.py` 为真相源，明细见下方各「→ 文档」指针，不在此复刻。

## 沟通与环境

- 始终用**简体中文**回复用户；代码、命令、术语、文件名保留原文
- Windows 11 + Obsidian + Claude Code；bash 与 PowerShell 均可用，优先 bash（正斜杠路径）
- Obsidian Git 插件每 30 分钟自动备份到私有 GitHub（commit message: `vault backup: ...`）；一般无需手动提交
- 5.4 GB 教材库 `素材/教材/ChinaTextbook/` 已 gitignore，不上传
- 用户可能开启 `caveman mode`：回复必须简洁压缩，保留技术准确性

## 目录结构

```
00-元/                    元规则：模板/命名/工作流/教材索引/学习路径
00-元/scripts/            工具脚本（含 exam_* 真题管线 + 通用工具 + tests/）；命令速查见 COMMANDS.md
00-元/scripts/_prompts/   提示词 + subject_build_runbook.md（学科建库标准流程）
数学/ 语文/ 英语/        小学→高中三段词条，3 位序号前缀（计数见下方 stats 表）
物理/ 化学/ 生物/        初中+高中两段词条
政治/ 历史/ 地理/        初中+高中两段词条（2026-05 完成）
科学/                     小学全程；生活与社会/ 部分骨架
真题/{省}-{科}/          高考真题题级 md（北京/吉林/湖南 × 5 科）
索引/                     Dataview 视图 + 真题索引 + 各科纵向总览
素材/教材/(gitignore) · 素材/真题/ · 素材/讲解PPT/
docs/                     progress-log.md / 真题管线.md / 学生视图.md / superpowers(设计稿·计划·working)
```

## 词条创建规范

**模板**：`00-元/模板/词条模板.md`（小学起用两层模板 `词条模板-小学.md`：📚6-12 + 🎓12+；高中单层 🎓）
- frontmatter 7 字段：title / aliases / 学科 / 学段 / 主题 / 状态 / 英文术语
- 三层正文：🧒 3-6 岁共读版 / 📚 6-12 岁自读版 / 🎓 12+ 进阶版（小学两层、高中单层）
- 中英对照（词汇表 + 例句表）+ 相关绘本 + 家长讲解话术 + 共读小活动
- 📺 讲解版占位（触发短语 6/7 填充）
- 📑 出处：课标 + **本地教材 PDF 链接** + 百科 + 拓展阅读 + 生成校对

**命名**（详见 `00-元/命名规则.md`）：
- 学科目录词条按"首次出现学期"加序号前缀（≤99 两位、>99 三位），如 `16-加法.md`
- frontmatter `aliases` 数组**首位必含 bare-name**（如 `aliases: [加法, addition, plus]`），保持 `[[加法]]` 经 alias 解析有效

**工作流**（详见 `00-元/工作流.md`）：7 条触发短语（新增/升级骨架/批量/共读/找漏链/PPT 轻量/PPT 精装）。

### 🚫 红线（防复发硬约束，一字不动）

- 教材引用必引本地 ChinaTextbook PDF
- 学科目录词条必加序号前缀 + bare-name alias
- **wikilinks 必须规范化**：Obsidian `[[X]]` 只看文件名，必须写 `[[017-减法|减法]]` 形式；4 个内置生成脚本（`gen_atom_skeleton.py` / `exam_render.py` / `exam_index.py` / `backfill_author_links.py`）已自动 hook；手动编辑后跑 `python 00-元/scripts/fix_wikilinks.py --apply`
- **数学公式必须用 Obsidian 定界符**：行内 `$...$` / 块级 `$$...$$`。DeepSeek/v4-pro 生成的二三级词条（尤数学/物理）惯用 LaTeX `\(\)\[\]`，Obsidian 默认 MathJax 不渲染（字面显示反斜杠/`^2`/`\sqrt`/`\pi`）。缺口词条已植入 `_prompts/exam_lexicon.md` 红线 8 防复发；存量批量后跑 `python 00-元/scripts/fix_latex_delim.py --apply`（按 manifest 严限范围 + 负向后顾保护 `\\[Npt]` 行距；奇数计数文件须手清未配对定界符）
- **renumber 后必跑 `fix_stale_links.py`**：`fix_wikilinks.LINK_RE` 故意只处理无管线 `[[X]]`，跳过 `[[X|Y]]`；而 `exam_render` / `exam_index` 产出恒带管线 `[[旧号-裸名|显示]]`，renumber 后变 stale 无人修。批量改号 → `python 00-元/scripts/fix_stale_links.py --apply`（按裸名→当前号唯一映射改写；0/多候选保守不动）
- **反链回填走 alias-aware**：`exam_index.backfill_backlinks` 已复用 `fix_wikilinks.collect_targets()`，tag 是 alias（如「余弦定理」→ `126-定理.md`）也能命中；跨省运行用并集合并（避免按省覆盖只剩末次省份）
- **批量生成后、renumber 前必跑 `validate_gen.py`**：拦 v4-pro 5 类故障（代码围栏/提示模板吐出/缺字段/学期带括号/跨段裸名碰撞），不过不准进后处理

## 工作模式 + 工具箱

- **学科建库标准流程**：`00-元/scripts/_prompts/subject_build_runbook.md`（topics→gen→体检门→学期→renumber→教材/英文术语回填→链接→audit→stats；含 v4-pro 故障速查）
- **工具箱**（`00-元/scripts/` 通用；`docs/superpowers/working/` 一次性修补）—— **不要再为每个学科一次性写脚本**：
  - 进度/命名/链接：`stats.py`（`--write` 同步进度表）/ `renumber.py` / `analyze_links.py` / `fix_aliases.py` / `check_*.py`
  - 链接修复：`fix_wikilinks.py` / `fix_stale_links.py` / `fix_latex_delim.py`
  - 词条生成：`gen_atom_skeleton.py`（v4-pro 骨架）/ `validate_gen.py`（⭐体检门）/ `add_semester.py`（注入学期，空值守卫+块式感知）/ `review_dispatch.py` / `backfill_author_links.py`
  - 真题：`exam_*.py`（5 步）+ `exam_eng_*.py`（3 步）+ `pdf_content_diff.py`（扩省份判同卷）
- 词条与学习路径分离：路径在 `00-元/学习路径/<学段>/<学科>/`，词条在 `<学科>/`
- 风格参考：`数学/16-加法.md`（标准全龄）、`数学/18-长方体.md`（含教材链接几何类）
- 命令速查：`00-元/scripts/COMMANDS.md`

## 多模型路由（详见 `docs/superpowers/plans/2026-05-12-multi-model-workflow-v3.md`）

- **Opus 主会话** = 核心/编排/终审/古文古诗/敏感议题亲写/字符级编码审查
- **Sonnet subagent** = 并行复检/抽 topics/字符级 OCR 判断（不做主体生成）
- **DeepSeek v4-pro** = 批量生成（含小批量）+ 50% 自检 + lexicon 抽取；**禁用**：字符级编码审查/细粒度 OCR（噪声 > 信号）
- **v4-flash** = OCR 抽样/短文本清洗
- 古文/敏感议题在 topics.jsonl 打 `route: opus` 跳过 v4-pro（gen 也会自动路由敏感议题给 Opus）

## 已完成进度

<!-- AUTO-PROGRESS-START -->

_由 `00-元/scripts/stats.py` 生成，共 6694 词条 / 11 学科。_

| 学科 | 词条数 |
|---|---:|
| 数学 | 1325 |
| 语文 | 634 |
| 英语 | 1032 |
| 物理 | 850 |
| 化学 | 992 |
| 生物 | 914 |
| 政治 | 236 |
| 地理 | 197 |
| 历史 | 445 |
| 科学 | 43 |
| 生活与社会 | 26 |
| **合计** | **6694** |

<!-- AUTO-PROGRESS-END -->

**覆盖矩阵**（✅ 完成 / ⏳ 待办）：

| 学科 | 小学 | 初中 | 高中 |
|---|---|---|---|
| 数学·语文·英语 | ✅ | ✅ | ✅ |
| 物理·化学·生物 | — | ✅ | ✅ |
| 政治·历史·地理 | — | ✅ | ✅ |
| 科学 | ✅ | — | — |

- ⏳ **待办**：小学 道法/美术/音乐/书法/体育/艺术（~210 词条，科学已完成）；生活与社会（26 骨架待升级）
- ⏸ **不建**：高中各科考点前沿概念（题型变体，建词条有害无益，列 backlog）
- 📜 **完整进度史 + 踩坑教训 → `docs/progress-log.md`**

## 专题文档（按需载入）

- 真题分析管线 → `docs/真题管线.md`（架构 + 6 步 + 扩省份规则；**扩省份前必跑** `pdf_content_diff.py` 判同卷，不看文件名）
- 学生复习视图（吉林理科高中权重/仪表盘/HTML 站）→ `docs/学生视图.md`
- 学科整理 SOP → `docs/superpowers/specs/2026-05-23-学科整理SOP.md`
- 命令速查 → `00-元/scripts/COMMANDS.md`

## 已启用插件（来自全局 `~/.claude/CLAUDE.md`）

superpowers / skill-creator / github / claude-md-management
