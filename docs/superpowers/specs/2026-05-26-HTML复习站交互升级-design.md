# HTML 复习站交互升级 + 扩量 — 设计

> 日期：2026-05-26 ｜ 状态：已确认，待实现
> 背景：`00-元/scripts/gen_html.py`（576 行）生成离线静态站（数物化生 4 科 weight≥10 = 594 词条 + 吉林真题 + KaTeX 渲染 + 基础标题搜索），但**纯只读**，无任何复习状态。

## 目标

1. **B1 交互升级**：给离线站加纯前端（localStorage）复习能力——错题/掌握标记、进度、间隔复习提醒、状态筛选、导出导入
2. **B2 扩量**：词条阈值 ≥10 → **≥3**（594 → 2340），仍 4 科、仅吉林真题

约束：
- 完全离线 `file://`，手机/平板可用，零后端、零网络依赖（除已有 KaTeX vendor）
- 与 `mock_review.py` 那条「真题 frontmatter → markdown 回写 mastery」链路**解耦**，互不读写，避免双真相源冲突
- 不改词条/真题源文件；所有状态只存浏览器 localStorage

非目标：不做账号/多用户、不做云同步、不碰英语与北京/湖南真题。

## 现状关键结构（gen_html.py，实测）

- `render_page(title, content_html, depth, extra_head)`：**唯一 HTML 包裹函数**，所有页面（词条/真题/索引/首页）都经它输出 → 注入共享 JS/CSS 的唯一入口。
- 词条页 `gen_atom_page` / 真题页 `gen_exam_page`：各自 `path.stem` 是稳定唯一标识 → 用作 localStorage key。
- 索引页 `gen_subject_index`：列表项 `<li class="weight色" data-title="...">`，已有 `filterEntries(q)` 标题即时过滤。
- `vendor/style.css` 已被各页引用；KaTeX 走 `vendor/katex/`。
- `SUBJECTS = ["数学","物理","化学","生物"]`、`--threshold` 参数已存在。

## 设计

### B2 扩量（先做，简单）

1. `gen_html.py` 默认 `--threshold` 由 10 改为 **3**（命令行仍可覆盖）。
2. 首页 `gen_home` 与索引页 `gen_subject_index` 中硬编码的「weight ≥ 10」「top 30」文案改为读实际阈值变量，避免文案与产出不符。
3. 真题范围维持「仅吉林」现状（`gen_exam_page` 已按本省渲染，无需改）。
4. 验证生成规模：~2340 词条页 + 吉林真题页，确认生成耗时与目录体积可接受（预计词条页 4 倍，仍秒级~十秒级）。

### B1 交互升级（纯前端）

新增**单个共享脚本** `docs/student/vendor/review.js`，由 `gen_html.py` 写出（与 KaTeX 同属 vendor），并在 `render_page` 头部统一注入。所有复习逻辑集中此处，页面侧只放最小 DOM 钩子。

**localStorage 数据模型**（单 key，整体 JSON）：

```
key: "kids-review-v1"
value: {
  "<stem>": { "s": "ok"|"fuzzy"|"wrong", "t": <last-mark-epoch-ms> },
  ...
}
```

`<stem>` 同时覆盖词条页与真题页（stem 全局唯一，无需区分类型）。版本号 `v1` 便于将来迁移。

**功能与落点**：

| 功能 | 页面侧钩子（gen_html 注入） | review.js 行为 |
|---|---|---|
| 三态标记 | 词条页/真题页标题下加 `<div class="review-mark" data-stem="...">`，含 ✅已掌握 / ⚠️模糊 / ❌错题 三按钮 | 点击写 localStorage，高亮当前态，记时间戳 |
| 索引进度条 | 索引页顶部加 `<div id="progress">` 占位 | 读全量状态，统计本科已掌握/总数，渲染进度条 + 百分比 |
| 索引状态色点 | 复用现有 `<li data-title>`，加 `data-stem` | 加载时给每行注入状态色点（绿/黄/红/灰未标） |
| 状态筛选 | 索引页搜索框旁加筛选下拉（全部/错题/模糊/未复习/今日该复习） | 扩展现有 `filterEntries`，按 `data-stem` 状态 + 标题双条件过滤 |
| 间隔复习（Leitner） | 同上「今日该复习」选项 | 规则：`wrong`→1 天、`fuzzy`→3 天、`ok`→7 天后到期、再隔次升 15 天（简化：按 状态×间隔表 + 时间戳判到期）。索引页可选「今日该复习」置顶过滤 |
| 导出/导入 | 首页加「导出复习记录 / 导入」两按钮 | 导出：`localStorage` → 下载 `kids-review-YYYYMMDD.json`；导入：读文件覆盖/合并 |

**间隔表**（Leitner 简化，写死在 review.js）：

| 当前状态 | 复习间隔（天） |
|---|---|
| wrong（错题） | 1 |
| fuzzy（模糊） | 3 |
| ok（已掌握） | 7 |
| 未标记 | 不进复习队列 |

「今日该复习」= `now - t >= 间隔`。本版不做多级 Leitner 升降盒（YAGNI），仅按当前态固定间隔；如不够用再迭代。

### 单元边界

- `review.js`：自包含，暴露 `Review.mark(stem,state)` / `Review.renderProgress(subject)` / `Review.applyFilter(mode,q)` / `Review.exportJSON()` / `Review.importJSON(file)`。不依赖页面其它脚本，可独立打开 console 测试。
- `gen_html.py` 改动收敛在：①阈值默认值与文案 ②`render_page` 注入 `review.js` ③三个 `gen_*_page` 各加最小 DOM 钩子 ④写出 `review.js` 文件。不动 `md_to_html`/链接解析/KaTeX 逻辑。

## 验收标准

- `python 00-元/scripts/gen_html.py --apply`（默认阈值 3）生成站点，4 科索引词条数合计 ≈ 2340。
- `file://` 打开任一词条页：点 ❌错题 → 刷新后仍高亮；打开对应学科索引页 → 该词条显红点。
- 索引页进度条随标记增减实时更新；「错题」「未复习」「今日该复习」筛选结果正确。
- 标记错题当天，「今日该复习」不含它（间隔 1 天未到）；手动改系统时间或时间戳验证到期后出现（实现期用临时缩短间隔自测）。
- 首页导出得到 JSON 文件；清空 localStorage 后导入 → 状态恢复。
- 断网 / 无 KaTeX vendor 时页面仍可读、标记仍可用（review.js 不依赖网络）。

## 风险

- **localStorage 按 origin 隔离**：`file://` 下不同设备/浏览器各自独立，换设备靠导出导入（已设计）。手机若用「下载到本地再打开」路径变化可能换 origin → 导出导入兜底。
- **扩量后生成体积**：2340 词条页 + 吉林真题页，HTML 文件数显著上升；`docs/*.zip` 学生包随之变大（已 gitignore，按需重打）。实现时记录实际体积。
- **stem 跨词条/真题碰撞**：词条与真题 stem 命名空间不同（真题带年份卷号），实测无碰撞；若将来出现，key 前缀加类型再升 `v2`。
