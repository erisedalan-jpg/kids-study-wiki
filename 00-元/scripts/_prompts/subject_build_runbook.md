# 学科建库 Runbook（v4-pro 批量建词条标准流程）

> 适用：新建/扩充某学科某学段词条（如小学道法/美术/音乐、初高中政史地、真题派生）。
> 同一管线反复用——照单执行，不要每次重新推导。坑都踩过并固化在工具里。
> 模板参考：`00-元/模板/词条模板-小学.md`（两层）；高中单层 🎓 由 gen 提示模板按 stage 自动切。

## 0. 概念源（topics.jsonl）

- **有学习路径** → `extract_topics_*.py` 从路径 `[[概念]]` 抽（初中政史地即此法）。
- **无学习路径**（如高中政史地）→ Opus 按教材逐册逐单元枚举 `gen_topics_*.py`。
- 行格式：`{"title","subject","stage","semester","topic"}`。
- **去碰撞**：与已有他学段同概念的，title 加 `（高中）` 等后缀区分；否则会与已存条目裸名相撞（概念应单条跨学段）。

## 1. 快照（出事能回溯）

```bash
python 00-元/scripts/stats.py            # 记下各科起点计数
```

## 2. 生成（v4-pro，后台）

```bash
python 00-元/scripts/gen_atom_skeleton.py \
  --topics-file docs/superpowers/working/topics_<X>.jsonl \
  --model complex \
  --out-manifest 00-元/scripts/_llm_logs/<X>.manifest.jsonl
```

- 输出裸名 `<学科>/<裸名>.md`（无序号，后续 renumber）。
- manifest `routed_to_opus` = 敏感/理论议题，**未生成**，由 Opus 亲写（单层/两层按学段；中立、贴统编教材）。
- ⚠️ 写 builder 脚本时，生成逻辑必须收进 `if __name__ == "__main__":`——否则被 import 时模块级循环会重写裸名，与已编号文件撞出重复（曾 31 组）。

## 3. ⭐ 生成体检门（renumber 前**必跑**，不过不准下一步）

```bash
python 00-元/scripts/validate_gen.py <学科...>      # exit 1 = 有硬错误
```

拦截 5 类 v4-pro 故障（实战踩过）：代码围栏包裹 / 提示模板吐出（`接下来按学段`、`[[bare-name]]`）/ frontmatter 缺字段 / 学期带括号 `[选必一]` / 跨学段裸名碰撞。
**全过再继续**；有错先修（去围栏、整条重写吐模板件、删跨段重复、裸值化学期）。

## 4. 注入学期 + 序号化

```bash
python 00-元/scripts/add_semester.py <学科> docs/superpowers/working/topics_<X>.jsonl
# 默认空值守卫（不覆盖已有学期）+ 块式感知（学期插在主题行前，不破坏块式 学段）
python 00-元/scripts/renumber.py <学科> --rebuild
python 00-元/scripts/fix_stale_links.py --apply      # renumber 后必跑
```

- XUEQI_ORDER 新学段键缺失（如政治必修四/历史纲要上下）须先补 `_utils.py`。

## 5. 教材引用回填

- 按 `学科×学期 → 本地 ChinaTextbook PDF` 映射，替换占位「待主会话核对教材索引」。
- 占位文案可能有变体（`待主会话核对教材路径` 等）+ 全/半角括号——回填正则要兼容。
- 参考 `docs/superpowers/working/backfill_textbook_*zsd.py`。

## 6. 英文术语回填

- v4-pro 常漏写 frontmatter `英文术语`（正文却有英文）。Opus 亲译标准教材术语写入。
- 参考 `docs/superpowers/working/write_eng_terms_*zsd.py`（按裸名匹配，仅填空值）。

## 7. 规范链接

```bash
python 00-元/scripts/fix_wikilinks.py --apply        # [[X]] → [[NN-X|X]]
python 00-元/scripts/fix_latex_delim.py --apply      # \(\)\[\] → $；注意其 manifest 范围限制，
# 范围外的数学/物理公式条目需 Grep 扫 \( \[ 手清
```

## 8. 体检验收

```bash
python 00-元/scripts/audit_entries.py --dir <学科> --grade <初中|高中>
# 混学段目录：--grade 只筛该段；audit 按 frontmatter 自动判正文层数
```

- **判读**：真缺陷（缺字段/缺层/aliases/教材/LaTeX）必须清零；
  纯**前沿裸链**（指向未建概念）= 新建科固有特征，**列 backlog 不强推**（量大建之有害，同高中结论）。
- 分类脚本思路：某条全部失败项都含「裸链」→ backlog；否则真缺陷，逐条修。

## 9. 收尾

```bash
python 00-元/scripts/stats.py --write                # 刷新 CLAUDE.md 计数表
python -m unittest discover -s "00-元/scripts/tests" -p "test_*.py"   # 122 用例基线
```

- 人工更新 CLAUDE.md「已完成进度」备注（含本轮踩坑教训）。
- 高中不进吉林冲刺权重域 → 无需 compute_weight/gen_html（仅高中数物化生 weight≥10 进站）。

## 已知 v4-pro 故障速查（→ 体检门已覆盖）

| 现象 | 签名 | 处置 |
|---|---|---|
| 整段提示模板吐进正文 | `接下来按学段` / `[[bare-name]]` / `给 3-6 岁` | 整条 Opus 重写 |
| 代码围栏包裹全文 | 文件以 ``` 开头 | 去首尾围栏 + 去重复行 |
| 块式 frontmatter 被 add_semester 打散 | `学段:` 空 + 孤立 `  - 初中` | 重写该 frontmatter；新 add_semester 已防 |
| 学期写成列表 | `学期: [选必一]` | 裸值化 `选必一` |
| 跨学段同概念重复 | 同裸名两文件 | 删重复（概念单条跨学段） |
