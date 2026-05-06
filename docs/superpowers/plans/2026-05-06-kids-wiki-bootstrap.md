# 家庭学习 Wiki 奠基与首批骨架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `study/` 目录搭出 Karpathy 风格的家庭学习 wiki 骨架（目录、模板、索引、Obsidian 配置），并生成 60 篇学前阶段词条骨架打底，使整个 wiki 进入"按需生长"的可用状态。

**Architecture:** 单一 Obsidian vault；**物理文件夹按学科扁平**（10 个学科 + 元/索引/杂物间/素材），学段/主题/状态等元信息全部走每篇文章的 YAML frontmatter；Dataview 查询代码块手写一次后自动生成索引视图；词条采用"单页分层"模板（同一概念学前/小学/初中/高中分段共存于一文件内）。git 从第 1 个任务起就承担版本控制。

**Tech Stack:** Obsidian (vault) · Markdown + YAML frontmatter · Dataview 插件 · Templater 插件 · Obsidian Git 插件 · Slides 核心插件 · git · Claude Code

**Spec:** `study/docs/superpowers/specs/2026-05-06-kids-wiki-design.md`

**范围说明：** 本 plan 覆盖 spec 第 6 节"实施路线图"的**阶段 0（奠基）+ 阶段 1（首批骨架）**。阶段 2/3/4 不在本 plan 范围内（属于日常使用与长期维护，不是一次性实施任务）。

---

## File Structure

任务执行后将创建/修改的文件：

| 路径 | 责任 |
|---|---|
| `study/.gitignore` | 排除 Obsidian 工作区缓存、临时索引等 |
| `study/README.md` | 一页说明 vault 用途与使用方式 |
| `study/00-元/模板/词条模板.md` | 唯一权威模板，所有新词条从此派生 |
| `study/00-元/命名规则.md` | 文件名/链接/aliases 的约定 |
| `study/00-元/工作流.md` | 7 条触发短语备忘 |
| `study/索引/状态-未完成.md` | Dataview：列骨架待写 |
| `study/索引/按学段-学前.md` | Dataview：可读的学前词条 |
| `study/索引/按学段-小学.md` | Dataview：可读的小学词条 |
| `study/索引/最近共读.md` | Dataview：按 `最近共读` 字段倒序 |
| `study/索引/待家长核对.md` | Dataview：含"生成校对"提示的词条 |
| `study/数学/*.md` | 学前数学启蒙骨架（20 篇） |
| `study/英语/*.md` | 学前英语启蒙骨架（15 篇） |
| `study/生活与社会/*.md` | 学前生活场景骨架（25 篇） |
| `study/.obsidian/community-plugins.json` | （手动）记录已装的社区插件 |

---

## Task 1: Git 初始化与基础排除规则

**Files:**
- Create: `study/.gitignore`
- Create: `study/README.md`
- Modify (init): `study/.git/`

- [ ] **Step 1: 检查 study 目录是否已经是 git 仓库**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git rev-parse --is-inside-work-tree 2>&1 || echo "NOT A REPO"
```
Expected: `NOT A REPO`（如返回 `true`，跳过 Step 2）

- [ ] **Step 2: 初始化 git**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git init -b main
```
Expected: `Initialized empty Git repository in .../study/.git/`

- [ ] **Step 3: 写 .gitignore**

Create `study/.gitignore`:
```
# Obsidian 工作区状态（机器相关）
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/workspaces.json

# Obsidian 临时缓存
.trash/

# 操作系统
.DS_Store
Thumbs.db
desktop.ini

# 编辑器临时
.vscode/
*.swp
*~

# 大文件保护：素材子目录建议交给 Git LFS 或外部存储；
# 当前规模可不忽略，将来再调
```

- [ ] **Step 4: 写一页 README**

Create `study/README.md`:
````markdown
# 家庭学习 Wiki

一个为孩子（学前 → 高中）准备的、用 Obsidian + Claude Code 共建的知识库。

参考 [Karpathy LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 思想：
原子化文章 + 双向链接组网 + 增量积累。

## 怎么用

打开 `00-元/工作流.md` 看 7 条触发短语；
新建词条直接说 "新增词条：X，所属 Y，学段 Z"。

## 设计稿

`docs/superpowers/specs/2026-05-06-kids-wiki-design.md`
````

- [ ] **Step 5: 首次提交**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add .gitignore README.md docs/superpowers/specs/2026-05-06-kids-wiki-design.md docs/superpowers/plans/2026-05-06-kids-wiki-bootstrap.md && git status
```
Expected: 4 个 new file。

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git commit -m "chore: bootstrap kids-study wiki vault with spec and plan"
```
Expected: `[main (root-commit) ...]` 4 files changed.

---

## Task 2: 顶层文件夹骨架

**Files:** 创建 14 个目录 + 各放一个 `.gitkeep` 让 git 跟踪空目录。

- [ ] **Step 1: 一次性建出所有顶层文件夹**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && mkdir -p \
  00-元/模板 \
  数学 英语 语文 物理 化学 生物 历史 地理 政治 \
  生活与社会 \
  索引 \
  杂物间/共读日记 \
  素材/教材 素材/绘本 素材/图片 素材/音视频 素材/讲解PPT
```

- [ ] **Step 2: 验证目录全部就位**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && ls -d */ 00-元/模板/ 杂物间/共读日记/ 素材/*/
```
Expected: 11 个一级目录 + 模板/共读日记/5 个素材子目录都列出。

- [ ] **Step 3: 给每个空目录放 .gitkeep（git 不追踪空目录）**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && for d in 00-元/模板 数学 英语 语文 物理 化学 生物 历史 地理 政治 生活与社会 索引 杂物间/共读日记 素材/教材 素材/绘本 素材/图片 素材/音视频 素材/讲解PPT; do touch "$d/.gitkeep"; done
```

- [ ] **Step 4: 验证 .gitkeep 数量**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && find . -name '.gitkeep' -not -path './.git/*' | wc -l
```
Expected: `18`

- [ ] **Step 5: 提交目录骨架**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add -A && git commit -m "feat: scaffold top-level wiki folders (10 subjects + 元/索引/杂物间/素材)"
```

---

## Task 3: 词条模板（spec 第 2 节的权威落地）

**Files:**
- Create: `study/00-元/模板/词条模板.md`

- [ ] **Step 1: 写模板文件**

Create `study/00-元/模板/词条模板.md`（注意 Templater 占位符 `<%  %>` 和 wiki frontmatter 不冲突；先用纯 frontmatter，Templater 在 Task 8 配置时再加变量）:

````markdown
---
title: 
aliases: []
学科: 
学段: []
主题: []
状态: 骨架
英文术语: 
首次共读: 
最近共读: 
---

# {{title}}

> **一句话**：
> **English**: 

---

## 🧒 给 3-6 岁（共读版）

🚧

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
- **绘本对应**：见上文"相关绘本"区块
- **课标**：
- **百科**：
- **拓展阅读**：
- **生成校对**：Claude 生成于 YYYY-MM-DD，由家长核对

## 🔗 相关词条

🚧

## 📚 素材

🚧
````

- [ ] **Step 2: 验证 frontmatter 合法**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && head -12 "00-元/模板/词条模板.md"
```
Expected: 第 1 行和第 12 行都是 `---`，中间 10 个键。

- [ ] **Step 3: 删 .gitkeep（已有真实文件）+ 提交**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && rm "00-元/模板/.gitkeep" && git add -A && git commit -m "feat: add canonical entry template with 三层正文/中英对照/讲解版/出处"
```

---

## Task 4: 命名规则文档

**Files:**
- Create: `study/00-元/命名规则.md`

- [ ] **Step 1: 写命名规则**

Create `study/00-元/命名规则.md`:

````markdown
# 命名规则

## 文件名

- 文件名 = 中文概念名，如 `光.md`、`凑十法.md`、`红绿灯.md`
- 不要带学段前缀（"学前-数数.md" ❌；"数数.md" ✅）
- 不要带空格、标点；纯中文 + 必要的阿拉伯数字

## 别名（aliases）

frontmatter `aliases` 字段挂英文与同义中文，便于 `[[light]]` 也能跳到《光》。

```yaml
aliases: [light, 光线]
```

## 跨学科归属

- 同时涉及多学科的概念（"光"既是物理也是诗词意象），**主学科归位 + 在其它学科建短链词条**
- 短链词条只含 frontmatter + 一句话 + `[[主词条]]` 跳转，不重复正文

## 跨学段归属

- 跨学段的概念（"光"涵盖学前→初中）**只放一份**在主学科文件夹内
- frontmatter `学段: [学前, 小学, 初中]` 让多个学段索引都能查到

## 小学"科学"特例

不单建"科学/"文件夹；按主题拆：
- 光、声、力、电 → `物理/`
- 植物、动物、人体 → `生物/`
- 岩石、土壤、天气 → `地理/`
- 水、空气、燃烧 → `化学/`
````

- [ ] **Step 2: 提交**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add "00-元/命名规则.md" && git commit -m "docs: add naming rules"
```

---

## Task 5: 工作流文档（7 条触发短语）

**Files:**
- Create: `study/00-元/工作流.md`

- [ ] **Step 1: 写工作流文档**

Create `study/00-元/工作流.md`:

````markdown
# 工作流：7 条触发短语

家长只需记这 7 条。每条都给具体例子。

## 1️⃣ 新增词条
> "新增词条：**[概念名]**，所属学科 **[学科]**，学段 **[学段]**"

例：`新增词条：彩虹，所属物理，学段 学前 小学`

→ Claude 检查重名 → 按模板生成完整内容（三层正文、中英对照、绘本、出处）→ 自动建立到相关词条的双向链接 → 给我审阅。

## 2️⃣ 把骨架填完整
> "把 **[词条名]** 从骨架升级到 **共读版完成 / 全龄完成**"

例：`把 红绿灯 升级到 共读版完成`

## 3️⃣ 批量骨架
> "为 **[学科]** 学段 **[学段]** 生成 **[主题]** 骨架，一批 10 篇"

例：`为 英语 学段 学前 生成 颜色和动物 骨架，一批 10 篇`

## 4️⃣ 共读回填
> "今天和孩子共读了 **[词条1] [词条2]**"

→ 更新 `最近共读` 字段；在 `杂物间/共读日记/YYYY-MM-DD.md` 写一条简记。

## 5️⃣ 找漏链
> "扫一遍 **[词条名 / 文件夹]**，看有没有该互链但没链上的"

## 6️⃣ 生成讲解 PPT（轻量版）
> "把 **[词条名]** 生成讲解 PPT（轻量）"

→ 调 `pptx` skill；纯文字 + 简单 emoji；输出 `素材/讲解PPT/[名]-轻量.pptx`

## 7️⃣ 生成讲解 PPT（精装版）
> "把 **[词条名]** 生成讲解 PPT（精装）"

→ 调 `nanobanana-ppt-skills`；含 AI 配图、设计感强；输出 `素材/讲解PPT/[名]-精装.pptx`

---

## 内容生成红线（每次新增/填充时遵守）

1. 涉及具体数据/原理 → 必须写"待家长核对"，并填 `📑 出处` 的"生成校对"行
2. 价值观题不下结论
3. 避免性别/地域刻板
4. 找不到来源就明说，不能编 URL 或书名
````

- [ ] **Step 2: 提交**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add "00-元/工作流.md" && git commit -m "docs: add workflow (7 trigger phrases) and content red lines"
```

---

## Task 6: Dataview 索引视图（5 个）

**Files:**
- Create: `study/索引/状态-未完成.md`
- Create: `study/索引/按学段-学前.md`
- Create: `study/索引/按学段-小学.md`
- Create: `study/索引/最近共读.md`
- Create: `study/索引/待家长核对.md`

- [ ] **Step 1: 状态-未完成**

Create `study/索引/状态-未完成.md`:
````markdown
# 状态-未完成

## 骨架待写

```dataview
TABLE 学科 as 学科, 学段 as 学段
FROM ""
WHERE 状态 = "骨架"
SORT file.mtime DESC
```

## 仅共读版完成（待写自读/进阶）

```dataview
TABLE 学科 as 学科, 学段 as 学段
FROM ""
WHERE 状态 = "共读版完成"
SORT file.mtime DESC
```
````

- [ ] **Step 2: 按学段-学前**

Create `study/索引/按学段-学前.md`:
````markdown
# 学前可读

```dataview
TABLE 学科 as 学科, 状态 as 状态
FROM ""
WHERE contains(学段, "学前") AND 状态 != "骨架"
SORT 学科, file.name
```

## 学前阶段全量（含骨架）

```dataview
TABLE 学科 as 学科, 状态 as 状态
FROM ""
WHERE contains(学段, "学前")
SORT 学科, file.name
```
````

- [ ] **Step 3: 按学段-小学**

Create `study/索引/按学段-小学.md`:
````markdown
# 小学可读

```dataview
TABLE 学科 as 学科, 状态 as 状态
FROM ""
WHERE contains(学段, "小学") AND 状态 != "骨架"
SORT 学科, file.name
```
````

- [ ] **Step 4: 最近共读**

Create `study/索引/最近共读.md`:
````markdown
# 最近共读（30 天内）

```dataview
TABLE 学科 as 学科, 最近共读 as 上次共读
FROM ""
WHERE 最近共读 != null AND date(最近共读) >= date(today) - dur(30 days)
SORT 最近共读 DESC
```
````

- [ ] **Step 5: 待家长核对**

Create `study/索引/待家长核对.md`:
````markdown
# 待家长核对

含"待家长核对"提示但未完成校对的词条：

```dataview
TABLE 学科 as 学科, 状态 as 状态
FROM ""
WHERE contains(file.content, "待家长核对")
SORT file.mtime DESC
```
````

- [ ] **Step 6: 删占位 + 提交**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && rm "索引/.gitkeep" && git add 索引/ && git commit -m "feat: add 5 dataview index views"
```

---

## Task 7: Obsidian 插件安装（用户手动 + 验证）

> ⚠️ **此任务由用户在 Obsidian 客户端手动完成**。Claude 仅提供精确指令清单与验证方法。

**Files:**（Obsidian 自动写入）
- Modify: `study/.obsidian/community-plugins.json`
- Modify: `study/.obsidian/core-plugins.json`

- [ ] **Step 1: 启用 Slides 核心插件**

Obsidian → Settings (⚙️) → Core plugins → 找到 **Slides** → 打开开关。

- [ ] **Step 2: 开启社区插件并安装 4 个**

Obsidian → Settings → Community plugins → **Turn on community plugins**（首次需信任）。

依次搜索安装并启用（**Install** → **Enable**）：
1. **Dataview**（作者：Michael Brenan / blacksmithgu）
2. **Templater**（作者：SilentVoid）
3. **Obsidian Git**（作者：Vinzent03）
4. **Various Complements**（作者：tadashi-aikawa）

- [ ] **Step 3: 验证**

打开任意 .md 文件，按 `Ctrl+P` 搜：
- 出现 `Dataview: ` 命令 → ✅
- 出现 `Templater: Open Insert Template modal` → ✅
- 出现 `Obsidian Git: Commit all changes` → ✅
- 出现 `Various Complements: Toggle Various Complements` → ✅

四项全部出现才算通过。

- [ ] **Step 4: 把 .obsidian 中要追踪的文件加到 git**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add .obsidian/community-plugins.json .obsidian/core-plugins.json 2>&1
```

如有 `.obsidian/plugins/` 子目录（被插件创建），不要 add（太大、和机器相关）。如果想忽略：
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && echo ".obsidian/plugins/" >> .gitignore
```

Commit：
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add .gitignore && git commit -m "chore: enable obsidian core/community plugins (slides + dataview + templater + git + complements)"
```

---

## Task 8: 配置 Templater 让"新建笔记"默认套词条模板

> ⚠️ **手动 + Claude 配合**。

**Files:**
- Modify: `study/.obsidian/plugins/templater-obsidian/data.json`（Templater 写入）

- [ ] **Step 1: 在 Templater 里指定模板文件夹**

Obsidian → Settings → Community plugins → Templater → **Settings**：
- **Template folder location**: `00-元/模板`
- **Trigger Templater on new file creation**: ON
- **Folder Templates**: 添加一行：
  - Folder: `数学`
  - Template: `00-元/模板/词条模板.md`
- 同样为 `英语`、`语文`、`物理`、`化学`、`生物`、`历史`、`地理`、`政治`、`生活与社会` 各加一行（10 行）

- [ ] **Step 2: 给词条模板加一个最小动态字段**

修改 `study/00-元/模板/词条模板.md` 的 frontmatter，让 `首次共读` 自动写入今天日期：

把：
```yaml
首次共读: 
```
改为：
```yaml
首次共读: <% tp.date.now("YYYY-MM-DD") %>
```

- [ ] **Step 3: 端到端测试**

在 Obsidian 中：在 `数学/` 文件夹右键 → New note → 命名 `测试-数数`。

期望：
- 文件自动套用模板
- frontmatter `首次共读` 字段被填成今天日期
- 三层正文区块都是 `🚧` 占位

- [ ] **Step 4: 删除测试文件**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && rm 数学/测试-数数.md && git status
```
Expected: working tree clean（测试文件未提交则不影响）。

- [ ] **Step 5: 提交模板更新**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add "00-元/模板/词条模板.md" && git commit -m "feat: wire templater with 首次共读 auto-fill and 10 folder bindings"
```

---

## Task 9: 端到端冒烟测试 — 完整跑通一条词条

> 这是阶段 0 的验证关。**所有触发短语必须在这一条上跑通**，再进入批量骨架。

**Files:**
- Create: `study/生活与社会/红绿灯.md`（测试用）
- Create: `study/素材/讲解PPT/红绿灯-轻量.pptx`（如执行 6️⃣）
- Create: `study/杂物间/共读日记/2026-05-06.md`

- [ ] **Step 1: 触发短语 1️⃣（新增完整词条）**

家长说：`新增词条：红绿灯，所属生活与社会，学段 学前 小学`

→ Claude 按模板生成完整《红绿灯》词条（三层正文、中英对照、绘本、家长讲解话术、📺 讲解版区块占位、出处含"生成校对"行）→ 写入 `study/生活与社会/红绿灯.md` → 报告生成完毕。

验证：
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && wc -l 生活与社会/红绿灯.md
```
Expected: 至少 60 行（含 frontmatter + 各区块）。

- [ ] **Step 2: Dataview 视图验证**

在 Obsidian 打开 `索引/状态-未完成.md`：
- 因《红绿灯》是"全龄完成"状态，**不应**出现在"骨架待写"中 → ✅
打开 `索引/按学段-学前.md` → 《红绿灯》出现 → ✅

- [ ] **Step 3: 触发短语 6️⃣（生成讲解 PPT 轻量版）**

家长说：`把 红绿灯 生成讲解 PPT（轻量）`

→ Claude 调 `pptx` skill → 输出 `study/素材/讲解PPT/红绿灯-轻量.pptx`

验证：
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && ls -la 素材/讲解PPT/红绿灯-轻量.pptx
```
Expected: 文件存在，大小 > 10KB。

家长在 PowerPoint 或 WPS 打开看一眼是否能播放。

- [ ] **Step 4: 触发短语 7️⃣（精装版）— 可选**

如果家长想试精装版：
家长说：`把 红绿灯 生成讲解 PPT（精装）`

→ Claude 调 `nanobanana-ppt-skills` → 输出 `study/素材/讲解PPT/红绿灯-精装.pptx`

如果此步不可用（网络/skill 失败），先跳过；plan 不阻塞。

- [ ] **Step 5: 触发短语 4️⃣（共读回填）**

家长说：`今天和孩子共读了 红绿灯`

→ Claude 更新 `生活与社会/红绿灯.md` 的 frontmatter `最近共读: 2026-05-06`
→ 创建 `study/杂物间/共读日记/2026-05-06.md`，记一句简记。

验证：
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && grep "最近共读" 生活与社会/红绿灯.md
```
Expected: `最近共读: 2026-05-06`

打开 `索引/最近共读.md` → 出现《红绿灯》→ ✅

- [ ] **Step 6: 提交冒烟测试产物**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add 生活与社会/红绿灯.md 素材/讲解PPT/ 杂物间/共读日记/ && git rm "生活与社会/.gitkeep" "素材/讲解PPT/.gitkeep" "杂物间/共读日记/.gitkeep" 2>/dev/null; git commit -m "test: e2e smoke — 红绿灯 entry + ppt + reading log"
```

> ✅ **阶段 0 完成的标志：本任务所有 Step 都通过**。如果任何一步失败，先回头修，不进 Task 10。

---

## Task 10: 数学骨架批 1（数数到形状，10 篇）

**Files:** 创建 10 个文件在 `study/数学/`

- [ ] **Step 1: 触发批量骨架**

家长说：`为 数学 学段 学前 生成 数数和形状 骨架，一批 10 篇`

Claude 严格按下面清单生成 10 篇骨架。每篇：
- 文件名 = 概念名
- frontmatter 完整（`学科: 数学`、`学段: [学前]`、`状态: 骨架`、英文术语、aliases）
- 一句话定义 + 一句话英文
- 各区块用 `🚧` 占位
- `🔗 相关` 区块至少 3 个候选 wiki 链接（即使目标尚不存在也先链）

**第 1 批清单：**
1. 数数
2. 0
3. 1-10
4. 形状-圆
5. 形状-方
6. 形状-三角
7. 形状-椭圆
8. 形状-菱形
9. 大小
10. 长短

骨架样板（以《数数》为例，必须严格遵循）：
````markdown
---
title: 数数
aliases: [counting, count]
学科: 数学
学段: [学前]
主题: [数感, 启蒙]
状态: 骨架
英文术语: counting
首次共读: 
最近共读: 
---

# 数数

> **一句话**：把东西一个一个对应到 1、2、3……
> **English**: Counting is matching objects to numbers one by one.

🚧 详细内容待写。

## 🔗 相关
[[1-10]] · [[0]] · [[多少]] · [[加法]]
````

- [ ] **Step 2: 验证**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && ls 数学/*.md | wc -l
```
Expected: `10`

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && grep -L "状态: 骨架" 数学/*.md
```
Expected: 空输出（每篇都含此字段）。

- [ ] **Step 3: 家长扫一遍**

家长在 Obsidian 打开 10 篇文件，扫一眼：
- 有没有重要漏掉的？（如"奇数偶数"是否要补）
- 有没有写飞的？

如有调整，改一两篇即可，不必全推倒。

- [ ] **Step 4: 提交**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git rm 数学/.gitkeep 2>/dev/null; git add 数学/ && git commit -m "feat(数学): skeleton batch 1 — counting and shapes (10 entries)"
```

---

## Task 11: 数学骨架批 2（比较与运算启蒙，10 篇）

**Files:** 在 `study/数学/` 再增 10 篇

- [ ] **Step 1: 触发**

家长说：`为 数学 学段 学前 生成 比较和运算启蒙 骨架，一批 10 篇`

**第 2 批清单：**
1. 轻重
2. 多少
3. 对称
4. 加法
5. 减法
6. 凑十
7. 十进制
8. 时间-钟表
9. 人民币认识
10. 序数

每篇严格按 Task 10 的样板格式生成。

- [ ] **Step 2: 验证**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && ls 数学/*.md | wc -l
```
Expected: `20`

- [ ] **Step 3: 家长扫一遍 + 提交**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add 数学/ && git commit -m "feat(数学): skeleton batch 2 — comparison and arithmetic primer (10 entries)"
```

---

## Task 12: 英语骨架批 1（基础主题词汇 1，10 篇）

**Files:** 创建 10 个文件在 `study/英语/`

- [ ] **Step 1: 触发**

家长说：`为 英语 学段 学前 生成 基础主题词汇 骨架，一批 10 篇`

**清单：**
1. 颜色-基本（colors）
2. 动物-家养（pets）
3. 动物-野生（wild animals）
4. 家庭成员（family）
5. 身体部位（body parts）
6. 食物-水果（fruits）
7. 食物-主食（staples）
8. 天气（weather）
9. 数字 1-10（numbers）
10. 问候语（greetings）

英语骨架的特殊要求：`英文术语` 字段必填；`aliases` 至少含中英两种叫法。

样板：
````markdown
---
title: 颜色-基本
aliases: [colors, basic colors, 颜色]
学科: 英语
学段: [学前]
主题: [词汇, 主题词]
状态: 骨架
英文术语: basic colors
首次共读: 
最近共读: 
---

# 颜色-基本

> **一句话**：红、黄、蓝、绿……身边最常见的几种颜色英文怎么说。
> **English**: The most common color words in English.

🚧 详细内容待写。

## 🔗 相关
[[彩虹]] · [[食物-水果]] · [[动物-家养]]
````

- [ ] **Step 2: 验证 + 提交**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && ls 英语/*.md | wc -l
```
Expected: `10`

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git rm 英语/.gitkeep 2>/dev/null; git add 英语/ && git commit -m "feat(英语): skeleton batch 1 — basic vocabulary topics (10 entries)"
```

---

## Task 13: 英语骨架批 2（动作与礼貌，5 篇）

**Files:** 在 `study/英语/` 再增 5 篇

- [ ] **Step 1: 触发**

家长说：`为 英语 学段 学前 生成 动作和礼貌 骨架，一批 5 篇`

**清单：**
1. 动作词-基本（action verbs）
2. 形状词（shape words）
3. 大小词（size words）
4. 感官词（sensory words）
5. 礼貌用语（polite expressions）

格式同 Task 12。

- [ ] **Step 2: 验证 + 提交**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && ls 英语/*.md | wc -l
```
Expected: `15`

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add 英语/ && git commit -m "feat(英语): skeleton batch 2 — action verbs, descriptors, manners (5 entries)"
```

---

## Task 14: 生活与社会骨架批 1（出行与场所，10 篇）

**Files:** 创建 10 个文件在 `study/生活与社会/`（已有 1 篇《红绿灯》— 跳过）

- [ ] **Step 1: 触发**

家长说：`为 生活与社会 学段 学前 生成 出行与场所 骨架，一批 10 篇（红绿灯已存在请跳过）`

**清单：**（**红绿灯已在 Task 9 完成**，本批不重复）
1. 人行道
2. 超市
3. 医院
4. 医生
5. 护士
6. 警察
7. 消防员
8. 银行
9. 邮局
10. 公交车

样板：
````markdown
---
title: 超市
aliases: [supermarket]
学科: 生活与社会
学段: [学前, 小学]
主题: [生活场景]
状态: 骨架
英文术语: supermarket
首次共读: 
最近共读: 
---

# 超市

> **一句话**：买日常东西的大商店，自己挑、自己付钱。
> **English**: A supermarket is a large store where people pick and buy daily goods themselves.

🚧 详细内容待写。

## 🔗 相关
[[钱]] · [[买东西]] · [[排队]] · [[红绿灯]]
````

- [ ] **Step 2: 验证 + 提交**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && ls 生活与社会/*.md | wc -l
```
Expected: `11`（含 Task 9 的《红绿灯》）

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add 生活与社会/ && git commit -m "feat(生活与社会): skeleton batch 1 — public places and roles (10 entries)"
```

---

## Task 15: 生活与社会骨架批 2（日常护理与意外，10 篇）

**Files:** 在 `study/生活与社会/` 再增 10 篇

- [ ] **Step 1: 触发**

家长说：`为 生活与社会 学段 学前 生成 日常护理与意外应对 骨架，一批 10 篇`

**清单：**
1. 地铁
2. 刷牙
3. 洗手
4. 生病
5. 迷路怎么办
6. 电话
7. 钱
8. 买东西
9. 排队
10. 垃圾分类

格式同 Task 14。

- [ ] **Step 2: 验证 + 提交**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && ls 生活与社会/*.md | wc -l
```
Expected: `21`

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add 生活与社会/ && git commit -m "feat(生活与社会): skeleton batch 2 — daily care and emergencies (10 entries)"
```

---

## Task 16: 生活与社会骨架批 3（节日，5 篇）

**Files:** 在 `study/生活与社会/` 再增 5 篇

- [ ] **Step 1: 触发**

家长说：`为 生活与社会 学段 学前 生成 节日 骨架，一批 5 篇`

**清单：**
1. 节日-春节
2. 节日-中秋
3. 节日-端午
4. 节日-元旦
5. 节日-儿童节

样板：
````markdown
---
title: 节日-春节
aliases: [Spring Festival, Chinese New Year, 春节]
学科: 生活与社会
学段: [学前, 小学]
主题: [节日, 中国传统]
状态: 骨架
英文术语: Spring Festival
首次共读: 
最近共读: 
---

# 节日-春节

> **一句话**：中国人最大的节日，家人团圆、贴春联、放鞭炮、吃饺子。
> **English**: Spring Festival is the most important holiday in China for family reunions.

🚧 详细内容待写。

## 🔗 相关
[[钱]] · [[节日-元旦]]
````

- [ ] **Step 2: 验证 + 提交**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && ls 生活与社会/*.md | wc -l
```
Expected: `26`

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git add 生活与社会/ && git commit -m "feat(生活与社会): skeleton batch 3 — festivals (5 entries)"
```

---

## Task 17: 阶段 1 验证

**Files:** 不修改文件，仅验证。

- [ ] **Step 1: 文件总数核验**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && echo "数学: $(ls 数学/*.md 2>/dev/null | wc -l)"; echo "英语: $(ls 英语/*.md 2>/dev/null | wc -l)"; echo "生活与社会: $(ls 生活与社会/*.md 2>/dev/null | wc -l)"
```
Expected:
```
数学: 20
英语: 15
生活与社会: 26
```
（生活与社会 26 = 25 骨架 + 1 完整《红绿灯》）

- [ ] **Step 2: 骨架数核验**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && grep -l "状态: 骨架" 数学/*.md 英语/*.md 生活与社会/*.md | wc -l
```
Expected: `60`

- [ ] **Step 3: frontmatter 完整性核验**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && for f in 数学/*.md 英语/*.md 生活与社会/*.md; do for k in title 学科 学段 状态 英文术语; do grep -q "^${k}:" "$f" || echo "缺 ${k}: $f"; done; done
```
Expected: 空输出（每个文件每个必填字段都有）。

- [ ] **Step 4: Dataview 视图核验**

家长在 Obsidian 打开 `索引/状态-未完成.md`：
- "骨架待写"表格至少 60 行 → ✅
打开 `索引/按学段-学前.md`：
- "学前可读"只有《红绿灯》（仅它已升级到完整状态） → ✅
- "学前阶段全量"61 行 → ✅

- [ ] **Step 5: 死链扫描（可选，但推荐）**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && grep -ohE "\[\[[^]]+\]\]" 数学/*.md 英语/*.md 生活与社会/*.md | sort -u > /tmp/all-wikilinks.txt && wc -l /tmp/all-wikilinks.txt
```

家长可在 Obsidian 打开"图谱视图"（Graph view），看是否所有 60+ 节点形成连通网络（孤岛节点是优化信号但不阻塞验证）。

- [ ] **Step 6: 标记里程碑**

Run:
```bash
cd "C:/Users/tjusu/Desktop/cc/family/kids/study" && git tag -a v0.1-skeleton -m "Phase 1 complete: 60 entry skeletons + 1 full entry (红绿灯)"
```

---

## 阶段 2/3/4：延续阅读（不在本 plan 范围）

阶段 0+1 完成后，进入 spec 第 6 节定义的：

- **阶段 2（试用 1 周）**：不预先生成内容，仅按孩子真问到时用触发 1️⃣ 把骨架升级或新建词条。每周日用 4️⃣ 回填共读、用 5️⃣ 找漏链。
- **阶段 3（按月扩展）**：第 1 个月补完学前骨架的"共读版"正文；第 2 个月开始用触发 6️⃣/7️⃣ 生成讲解 PPT；按孩子升学进度用 3️⃣ 扩学段。
- **阶段 4（长期维护）**：每季度审"出处与参考资料"；孩子识字后开放观察使用频次。

如需为某次扩展（例如"补完学前数学的共读版正文 20 篇"）单独写新 plan，重新调用 brainstorming → writing-plans 流程。

---

## Self-Review

**Spec coverage check:**

| Spec 节 | 对应任务 | 状态 |
|---|---|---|
| 1. 目录结构 | Task 2 | ✅ |
| 2. 词条模板 | Task 3 + Task 8（Templater wire） | ✅ |
| 3. 骨架生成策略 | Tasks 10–16 | ✅ |
| 4. 7 条触发短语 | Task 5（文档）+ Task 9（端到端跑通 4 条）| ✅ |
| 5. Obsidian 插件 + Dataview 视图 | Tasks 6, 7 | ✅ |
| 6. 实施路线图 阶段 0 | Tasks 1–9 | ✅ |
| 6. 实施路线图 阶段 1 | Tasks 10–17 | ✅ |
| 6. 阶段 2/3/4 | 延续阅读小节 | ✅（明确不在本 plan）|
| 7. 风险与缓解 | git 自第 1 任务起、出处必填、按需填充原则贯穿任务 | ✅ |
| 8. YAGNI 边界 | 不预生成 K-12、不做习题/打卡 | ✅ |
| 附录 A：60 篇骨架 | Tasks 10/11/12/13/14/15/16 = 10+10+10+5+10+10+5 = 60 | ✅ |

**Placeholder scan:** 模板里的 `🚧` 是**有意的占位**（spec 明确要求），不算 plan failure。其它 TBD/TODO 已无。

**Type consistency:** 所有任务里 frontmatter 字段名一致（`title`/`aliases`/`学科`/`学段`/`主题`/`状态`/`英文术语`/`首次共读`/`最近共读`）；状态值集合一致（`骨架` / `共读版完成` / `全龄完成`）；触发短语编号 1️⃣–7️⃣ 全文一致。

**Edge cases:**
- 学前已有《红绿灯》先完成（Task 9），Task 14 跳过它，避免重名 ✅
- `.gitkeep` 在每个文件夹首次有真实内容时被 `git rm` 清掉（不留死文件）✅
- Templater 的 `<% tp.date.now() %>` 在 frontmatter 内合法（YAML 字符串值），首次共读字段会写入纯日期字符串 ✅
