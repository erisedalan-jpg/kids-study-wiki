# CLAUDE.md

家庭学习 Wiki：为两个孩子（5 岁、3 岁，学前→高中）共建的知识库。Obsidian + Claude Code 协作；参考 [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 思想，原子化文章 + 双向链接组网 + 增量积累。

## 沟通

- 始终用**简体中文**回复用户；代码、命令、术语、文件名保留原文
- Windows 11 + Obsidian + Claude Code；bash 与 PowerShell 均可用，优先 bash（正斜杠路径）
- Obsidian Git 插件每 30 分钟自动备份到私有 GitHub（commit message: `vault backup: ...`）
- 5.4 GB 教材库 `素材/教材/ChinaTextbook/` 已 gitignore，不上传

## 目录结构

```
00-元/                    元规则：模板/命名/工作流/教材索引/学习路径
00-元/学习路径/小学/<学科>/  10 学科 × 12 册学习路径文档（已加序号 01-12）
00-元/scripts/            工具脚本（含 exam_* 真题管线 + 通用工具 + tests/）
数学/ 语文/ 英语/        小学→高中三段词条，3 位序号前缀（具体计数见下方 stats 表）
物理/ 化学/ 生物/        初中+高中两段词条，3 位序号前缀
生活与社会/ 历史/ 地理/ 政治/   其他学科词条（部分骨架，部分已升级）
真题/{省}-{科}/          高考真题题级 md（北京/吉林/湖南 × 5 科）
索引/                     Dataview 视图 + 真题 4 索引/省·科
素材/讲解PPT/             家长讲解 PPT（轻量 / 精装）
素材/教材/                本地 PDF 教材库（gitignore）
素材/真题/                高考真题 PDF 源
docs/superpowers/         设计稿/实施计划/working 草稿与一次性脚本
```

## 词条创建规范

**模板**：`00-元/模板/词条模板.md`
- frontmatter 7 字段：title / aliases / 学科 / 学段 / 主题 / 状态 / 英文术语
- 三层正文：🧒 3-6 岁共读版 / 📚 6-12 岁自读版 / 🎓 12+ 进阶版
- 中英对照（词汇表 + 例句表）
- 相关绘本 + 家长讲解话术 + 共读小活动
- 📺 讲解版占位（用触发短语 6/7 填充）
- 📑 出处：课标(2022) + **本地教材 PDF 链接** + 百科 + 拓展阅读 + 生成校对

**命名**（详见 `00-元/命名规则.md`）：
- 学科目录词条按"首次出现学期"加 2 位序号前缀，如 `16-加法.md`、`73-圆周率.md`
- frontmatter `aliases` 数组**首位必含 bare-name**（如 `aliases: [加法, addition, plus]`），保持 `[[加法]]` 链接通过 alias 解析有效

**工作流**（详见 `00-元/工作流.md`）：7 条触发短语（新增/升级骨架/批量/共读/找漏链/PPT 轻量/PPT 精装）+ 7 条红线：
- 教材引用必引本地 ChinaTextbook PDF
- 学科目录词条必加序号前缀 + bare-name alias
- **wikilinks 必须规范化**：Obsidian `[[X]]` 只看文件名，必须写 `[[017-减法|减法]]` 形式；4 个内置生成脚本（`gen_atom_skeleton.py` / `exam_render.py` / `exam_index.py` / `backfill_author_links.py`）已自动 hook；手动编辑后跑 `python 00-元/scripts/fix_wikilinks.py --apply`
- **数学公式必须用 Obsidian 定界符**：行内 `$...$` / 块级 `$$...$$`。DeepSeek/v4-pro 生成的二三级词条（尤数学/物理）惯用 LaTeX `\(\)\[\]`，Obsidian 默认 MathJax 不渲染（字面显示反斜杠/`^2`/`\sqrt`/`\pi`）。缺口词条已植入 `_prompts/exam_lexicon.md` 红线 8 防复发；存量批量后跑 `python 00-元/scripts/fix_latex_delim.py --apply`（按 manifest 严限范围 + 负向后顾保护 `\\[Npt]` 行距；奇数计数文件须手清未配对定界符）
- **renumber 后必跑 `fix_stale_links.py`**：`fix_wikilinks.LINK_RE` 故意只处理无管线 `[[X]]`，跳过 `[[X|Y]]`；而 `exam_render` / `exam_index` 产出恒带管线 `[[旧号-裸名|显示]]`，renumber 后变 stale 无人修。批量改号 → `python 00-元/scripts/fix_stale_links.py --apply`（按裸名→当前号唯一映射改写；0/多候选保守不动）
- **反链回填走 alias-aware**：`exam_index.backfill_backlinks` 已复用 `fix_wikilinks.collect_targets()`，tag 是 alias（如「余弦定理」→ `126-定理.md`）也能命中；跨省运行用并集合并（避免按省覆盖只剩末次省份）

## 已完成进度

<!-- AUTO-PROGRESS-START -->

_由 `00-元/scripts/stats.py` 生成，共 5375 词条 / 7 学科。_

| 学科 | 词条数 |
|---|---:|
| 数学 | 1223 |
| 语文 | 634 |
| 英语 | 992 |
| 物理 | 782 |
| 化学 | 902 |
| 生物 | 816 |
| 生活与社会 | 26 |
| **合计** | **5375** |

<!-- AUTO-PROGRESS-END -->

（上方表格由 `00-元/scripts/stats.py --write` 自动维护；下方为人工记录的细节备注。）

- ✅ 60 词条骨架 + 设计稿与模板
- ✅ Obsidian Git 自动备份到私有仓库
- ✅ 5.4 GB ChinaTextbook 本地教材库
- ✅ 102 学习路径文档（10 学科 × 12 册，已序号 01-12）
- ✅ 数学 81 词条全龄完成（学前→六下，已序号 01-81）
  - 01-14 学前 · 15-24 一上 · 25-26 一下
  - 27-31 二上 · 32-37 二下 · 38-42 三上 · 43-45 三下
  - 46-51 四上 · 52-56 四下 · 57-63 五上 · 64-69 五下
  - 70-77 六上 · 78-81 六下
- ✅ 语文 240 词条全龄完成（学前→六下，已序号 001-240，3 位前缀）
  - 每学期内顺序：概念 → 古诗 → 课文
  - 一上 38 (001-038)：23 概念 + 5 古诗 + 10 课文
  - 一下 18 (039-056) · 二上 21 (057-077) · 二下 23 (078-100)
  - 三上 23 (101-123) · 三下 19 (124-142)
  - 四上 19 (143-161) · 四下 18 (162-179)
  - 五上 16 (180-195) · 五下 15 (196-210)
  - 六上 15 (211-225) · 六下 15 (226-240)
- ✅ 英语 65 词条骨架/共读完成（已序号 01-65）
- ✅ 初中 42 学习路径文档（9 学科 七上→九下，已序号）
  - 政治 6 / 地理 4 / 化学 2 / 历史 6 / 生物 4
  - 数学 6 / 物理 3 / 英语 5 / 语文 6
- ✅ 初中 Phase 2 数学/语文/英语 完成（~610 词条，已序号化）
  - 数学 264 词条 (001-264)：001-081 小学 + 082-264 初中（七上→九下，每学期 30）
  - 语文 421 词条 (001-421)：001-240 小学 + 241-421 初中（七上→九下，每学期 ~30）
  - 英语 333 词条 (001-333)：001-065 小学 + 066-333 初中（七上→九年级全一，~50/学期）
  - 全部加 3 位前缀（小学语文 001-240 不变；其余 2 位升 3 位）+ bare-name alias 校验
- ⏳ 小学其他学科词条补缺：~60 道法 / ~50 科学 / ~30 美术 / ~40 艺术 / ~30 音乐 / ~25 书法 / ~25 体育
- ⏳ 初中 Phase 2 剩余 6 学科：政治 ~120 / 地理 ~200 / 化学 ~150 / 历史 ~250 / 生物 ~200 / 物理 ~200 (~1120 词条)
- ✅ 高中 33 学习路径文档（6 学科 必修 + 选择性必修，已序号）
  - 物理 6（必修 1-3 + 选必 1-3）/ 化学 5（必修 1-2 + 选必 1-3）/ 生物 5（必修 1-2 + 选必 1-3）
  - 数学 5（必修 1-2 + 选必 1-3，必修第一册 PDF 已从 GitHub 补齐）
  - 英语 7（必修 1-3 + 选必 1-4）/ 语文 5（必修上下 + 选必上中下）
- ✅ 高中 Phase 2 数学/语文/英语 完成（~692 词条，已序号化）
  - 数学 514 词条 (001-514)：001-264 小学+初中 + 265-514 高中 250
  - 语文 571 词条 (001-571)：001-421 小学+初中 + 422-571 高中 150（含 37 篇补齐古文/现代文学）
  - 英语 613 词条 (001-613)：001-333 小学+初中 + 334-613 高中 280
  - 高中按学期（必修上下/必一二三/选必上中下/选必一二三四）顺序加 3 位前缀
  - 模板：单层正文（仅 🎓 12+ 进阶版）
  - 语文跳过部分(必上 5 + 必下 14 + 选必中 8 + 选必下 9 = 36 篇古文/现代文学) 已由主会话直接补齐
- ✅ 物理初中+高中 完成（450 词条，已序号化 001-450）
  - 初中 200：八上50（001-050）+ 八下70（051-120）+ 九年级全一80（121-200）
  - 高中 250：必一45（201-245）+ 必二45（246-290）+ 必三45（291-335）
    + 选必一40（336-375）+ 选必二40（376-415）+ 选必三35（416-450）
  - 模板：初中两层正文（📚 6-12 + 🎓 12+）/ 高中单层 🎓
- ✅ 化学初中+高中 完成（520 词条，已序号化 001-520）
  - 初中 150：九上80（001-080）+ 九下70（081-150）
  - 高中 370：必一80（151-230）+ 必二70（231-300）+ 选必一75（301-375）
    + 选必二70（376-445）+ 选必三75（446-520）
  - 模板：初中两层正文（📚 6-12 + 🎓 12+）/ 高中单层 🎓
- ✅ 生物初中+高中 完成（457 词条，已序号化 001-457）
  - 初中 203：七上50（001-050）+ 七下53（051-103）+ 八上50（104-153）+ 八下50（154-203）
  - 高中 254：必一60（204-263）+ 必二49（264-312）+ 选必一50（313-362）
    + 选必二45（363-407）+ 选必三50（408-457）
  - 模板：初中两层正文（📚 6-12 + 🎓 12+）/ 高中单层 🎓
  - 备注：sonnet 子代理 quota 耗尽（重置 2026-05-15）后由主会话直接补齐 49 条

## 真题分析

<!-- EXAM-PROGRESS-START -->

v2 架构：截图 + 摘要 + 指针 + 三层复审（L1 自动断言 / L2 看图复验 / L3 Opus 仲裁）。设计稿 `docs/superpowers/specs/2026-05-12-jilin-math-exam-v2-design.md`，实施计划 `docs/superpowers/plans/2026-05-12-jilin-math-exam-v2-plan.md`。v1 zip 备份保留于 `素材/backup/2026-05-12/exam-pre-migrate.zip`。

**数理化生管线**（`00-元/scripts/exam_*.py`，62 单测全过）：

1. `exam_screenshot.py` — PyMuPDF 找题号/答案锚点 + 渲染 PNG（含跨页 running counter，命名 `{year}-{paper}-{NN}.q.png`）
2. `exam_extract_meta.py` — markitdown 抽答案/解析（最长上升序列容错表格题号）；北京公式碎片走 `split_by_answer_tag` 降级
3. `exam_enrich.py` — DeepSeek v4-pro 抽 摘要/考点/难度（含 retry + LLMError 路径）
4. `exam_verify.py` — L2 复验两步法（prepare 写 prompt 队列 / ingest 收 verdict）
5. `exam_render.py` — 渲染题级 .md（frontmatter + 截图 + 摘要 + tags 反链 + PDF 指针）
6. `exam_index.py` — 4 索引 + 反链回填学科词条（alias-aware 解析 + 跨省并集合并）

**英语篇章管线**（`exam_eng_*.py`，无 enrich 步）：

1. `exam_eng_screenshot.py` — 按【答案】锚分篇章块，渲染 PNG（**遗留：裸号命名 `{NN}.q.png` 跨卷碰撞，待修**）
2. `exam_eng_extract.py` — `SUBSTANTIVE` 正向谓词 (`raw_sol` 含 `【导语】` 或 `【N题详解】`) 判要不要 render；`infer_qtype` 单字母 ≥10 = 完形填空（先于阅读理解规则）
3. `exam_eng_render.py` — `skip_render` 跳过听力/纯版式块

**全量结论**（2026-05-19）：北京/吉林/湖南 × 5 科 = 15 组全量入库；数理化生 ~1000 题，英语 45 篇章。湖南为独立卷（与吉林 ratio 0.07-0.29，非同卷）；黑龙江与吉林 ratio=1.0000 全同卷，**新增词条 = 0**，详见 `索引/真题/黑龙江-同卷说明.md`。`paper_aliases` 已加新高考Ⅰ / 全国卷Ⅰ / 湖南。

**Pilot 已知问题**（待后续扩省份/年份前修）：
- markitdown 在多列 PDF 上偶发漏题（Q15/Q19 缺解析），需在 `enrich_question` 中加截图回退分支或改用 fitz region 切片
- `analyze_links.py` 的 bare-name alias 检查对真题路径不适用（误报 23 题缺 alias）
- Q14 答案字段抓到 markdown 表格残片（已手动 patch；需在 `extract_answer` 加管道符清洗）
- **英语截图裸号命名**（`素材/真题截图/{省}-英语/{NN}.q.png`）跨卷碰撞覆盖，需统一为 `{year}-{paper}-E{NN}.q.png`

**扩省份规则**：必先跑 `python 00-元/scripts/pdf_content_diff.py`（fitz 提文本 → 归一化 → SequenceMatcher.ratio）判同卷，**不要看文件名**。ratio=1.0 → 不建镜像，仅写同卷说明；ratio < 0.5 → 独立卷，进 5 步管线。

<!-- EXAM-PROGRESS-END -->

## 工作模式提示

- **工具箱**（`00-元/scripts/` 通用；`docs/superpowers/working/` 一次性修补）—— **不要再为每个学科一次性写脚本**：
  - 进度：`stats.py`（含 `--write` 同步 CLAUDE.md 表）
  - 命名/链接：`renumber.py` / `check_naming_conflicts.py` / `check_missing.py` / `analyze_links.py` / `fix_aliases.py`
  - 链接修复：`fix_wikilinks.py`（规范化 `[[X]] → [[NN-X|X]]`）/ `fix_stale_links.py`（修 renumber 致 stale 号链）/ `fix_latex_delim.py`（`\(\)\[\] → $$`）
  - 词条生成：`gen_atom_skeleton.py`（v4-pro 批量骨架）/ `review_dispatch.py`（复检派发）/ `backfill_author_links.py`（古诗作者反链）
  - 真题：`exam_*.py` 数理化生 5 步 + `exam_eng_*.py` 英语 3 步；`pdf_content_diff.py` 扩省份判同卷
- 用户可能开启 `caveman mode`：进入后回复必须简洁压缩，保留技术准确性
- 词条与学习路径分离：路径在 `00-元/学习路径/<学段>/<学科>/`，词条在 `<学科>/`
- 风格参考：`数学/16-加法.md`（标准 A 模式全龄完成）、`数学/18-长方体.md`（含教材链接的几何类）

## 常用命令

```bash
# 进度刷新（同时改 CLAUDE.md 进度表）
python 00-元/scripts/stats.py --write

# 单测（62 用例全过为基线）
pytest 00-元/scripts/tests/
pytest 00-元/scripts/tests/test_exam_index.py        # 单文件

# 链接体检与修复
python 00-元/scripts/analyze_links.py                # 报告漏 alias / 死链
python 00-元/scripts/fix_wikilinks.py --apply        # 规范化无管线 [[X]]
python 00-元/scripts/fix_stale_links.py --apply  # 修 renumber 致 stale 号链（必跑）
python 00-元/scripts/fix_latex_delim.py --apply  # \(\)\[\] → $$

# 真题数理化生（5 步串行，单 {省}-{科}）
python 00-元/scripts/exam_screenshot.py    --province 湖南 --subject 数学
python 00-元/scripts/exam_extract_meta.py  --province 湖南 --subject 数学
python 00-元/scripts/exam_enrich.py        --province 湖南 --subject 数学
python 00-元/scripts/exam_render.py        --province 湖南 --subject 数学
python 00-元/scripts/exam_index.py         --province 湖南 --subject 数学

# 真题英语（3 步，无 enrich）
python 00-元/scripts/exam_eng_screenshot.py --province 湖南
python 00-元/scripts/exam_eng_extract.py    --province 湖南
python 00-元/scripts/exam_eng_render.py     --province 湖南

# 扩省份前必跑：判同卷
python 00-元/scripts/pdf_content_diff.py
```

## 多模型工作流 v3 路由

详见 `docs/superpowers/plans/2026-05-12-multi-model-workflow-v3.md`。核心规则：

- **Opus 主会话** = 核心 / 编排 / 终审 / 古文 / 古诗 / 敏感议题亲自写 / **字符级编码审查**
- **Sonnet subagent** = 并行复检 / 抽 topics / 扩省份 checklist / **字符级 OCR 判断（替代 v4-pro 在这类任务上的噪声）**（不再做主体生成）
- **DeepSeek v4-pro** = 批量生成（**含小批量**）+ 50% 自检 + lexicon 概念抽取（取代已弃用的 deepseek-reasoner）。**禁用场景：字符级编码审查 / 细粒度 OCR 判断**（噪声率 > 信号率）
- **DeepSeek v4-flash** = OCR 抽样 / 短文本清洗（注意：长解答题字符审查仍噪声大，必要时升 sonnet/opus）
- 词条生成统一走工作流 A（无批量阈值）；古文/敏感议题在 topics.jsonl 打 `route: opus` 跳过 v4-pro
- 复检比例 `10/40/50`（Opus / Sonnet / v4-pro）；过渡期 5/12–5/15 用 `30,0,70`
- 交叉复检按场景触发：新学科 / 新配置 10%，稳定期 5% 或 0%

## 已启用插件（来自全局 `~/.claude/CLAUDE.md`）

superpowers / skill-creator / github / claude-md-management
