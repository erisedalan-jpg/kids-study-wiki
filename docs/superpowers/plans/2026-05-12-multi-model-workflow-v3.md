# 多模型工作流 v3 · Opus 核心 + 多 agent 分级

- **日期**：2026-05-12
- **状态**：active（CLAUDE.md 精简版已落地，本文为完整设计）
- **替代**：旧路由原则「古文 / 历史人物 / 敏感议题 / < 60 词条 → 主会话；现代说明文 + 数理化生概念 + ≥ 60 词条 → sonnet 子代理」

## 背景与触发

- DeepSeek API 密钥已配置（DEEPSEEK_API_KEY 全局环境变量）
- `deepseek-reasoner` 即将弃用 → `Task.REASONING` 已从 `_llm_router.py` 删除，工作并入 `Task.COMPLEX`（v4-pro）
- 不使用 Anthropic API（Claude Code 订阅）→ `_llm_router.py` 已删除 Anthropic 通路
- Sonnet 4.6 子代理 quota 重置日期：2026-05-15（距今 3 天）
- 现有脚手架：5 个 DeepSeek 流水线脚本 + 5 个真题脚本 + `gen_atom_skeleton.py` / `review_dispatch.py` / 工具箱（renumber/stats/...）

## 1. 模型角色定位

| 模型 | 身份 | 主职 | 禁区 |
|---|---|---|---|
| **Opus 4.7** (1M ctx) | 🎯 核心 / 编排 / 终审 | 拆批 · 起 subagent · 审 verdict · 古文/敏感议题亲自写 · 跨学段一致性 · **字符级编码审查** | 不亲自生成大批量概念词条 |
| **Sonnet 4.6** | 🤝 并行工人 | subagent 并行复检 · 整理 topics · checklist 跑 · **字符级 OCR 判断** | 不再做大批量主体生成（v4-pro 更稳） |
| **DeepSeek v4-pro** | ⚙️ 批量生成 + 自检 | 词条骨架（**含小批量**）· 长文 · 50% 自检 · lexicon 概念抽取（仅概念名，不做字符级 OCR 判断） | 古文 / 古诗 / 敏感议题 · **字符级编码审查 / OCR 完整性判断**（噪声 > 信号） |
| **DeepSeek v4-flash** | ⚙️ 轻量清洗 | OCR 抽样（短题） · 短文本清洗 · 字段抽取 | 整条词条生成 · 长解答题字符审查（升 sonnet/opus） |
| **零 LLM 脚本** | 🔧 流水线 | renumber/stats/analyze_links/真题流水线/golden test | — |

**与旧规则的核心转变**
- ❌ 「< 60 词条 → 主会话亲自生成」**废弃**
- ✅ 小批量也走 v4-pro，Opus 改为「编排 + 终审」
- ❌ `Task.REASONING` / `deepseek-reasoner` 弃用
- ✅ 推理 / 自检并入 `Task.COMPLEX` → v4-pro
- ⚠️ **新规则 (2026-05-12)**：字符级编码审查 / 细粒度 OCR 完整性判断不走 v4-pro（实测噪声率 ~80% vs 真实 bug ~5%），改走 Opus 主会话或 Sonnet subagent

## 2. 四层分级架构

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Tier 0 · 策略层【Opus 主会话】                                        │
│   接需求 → 拆批 → 找缺口 → 起 subagent → 审 → 决定放行                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ dispatch
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│ Tier 1A · 生成层          │    │ Tier 1B · 辅助 subagent   │
│ 【DeepSeek v4-pro】       │    │ 【Sonnet via Agent 工具】 │
│ gen_atom_skeleton.py      │    │ 抽 topics / 解析学习路径 / │
│ 含小批量、含 lexicon 体检 │    │ 扩省份 checklist 跑       │
└──────────────┬───────────┘    └──────────────┬───────────┘
               │ manifest.jsonl                │ topics.jsonl
               ▼                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Tier 2 · 复检层（10/40/50 三档 + 触发型 5-10% 交叉复检）              │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐     │
│  │ 50% DeepSeek 自检 │ │ 40% Sonnet 并行  │ │ 10% Opus 抽检    │     │
│  │  v4-pro 直接 API  │ │  N 个 subagent   │ │  主会话亲跑      │     │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ verdict.json × N
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Tier 3 · 终审层【Opus 牵头】                                         │
│   --ingest → 扫 fix_major/reroute_to_opus → 修正/重生成              │
│   → cross_check.py 一致性报告 → renumber + stats --write             │
└─────────────────────────────────────────────────────────────────────┘
```

## 3. 三条主工作流

### 工作流 A · 词条生成（≥ 1 条统一流程）

```text
① Opus 拆批
   - 看 进度表 / 学习路径文档 / check_missing.py 找缺口
   - 起 sonnet subagent 帮忙抽 topics.jsonl（多文档解析）

② v4-pro 批量生成
   python 00-元/scripts/gen_atom_skeleton.py \
       --topics-file topics.jsonl --model complex \
       --out-manifest 00-元/scripts/_llm_logs/<批次>.manifest.jsonl
   ※ 小批量（< 30 条）也走这里，不再 Opus 亲自写
   ※ 古文/古诗/敏感议题：topics.jsonl 打 route: opus，触发 ROUTE_TO_OPUS

③ 三档复检 + 可选交叉
   python 00-元/scripts/review_dispatch.py --manifest <X>.manifest.jsonl
   # 新学科/新配置首批可加：--cross-check 10
   # 稳定期：--cross-check 5 或不加

④ Sonnet subagent 并行跑 sonnet 队列
   - Opus 用 dispatching-parallel-agents 模式
   - 一次 Agent 调用塞 N 个 subagent（每人 5-10 条 prompt）
   - 每个 subagent 完成后写 verdict.json 到 reviews/

⑤ Opus 亲自跑 opus 队列 + 收回
   - 主会话逐条读 opus.prompt.md → verdict.json
   - 一次会话上限 50 条
   python 00-元/scripts/review_dispatch.py --manifest <X>.manifest.jsonl --ingest

⑥ 终审 + 落盘
   - Opus 扫 fix_major / reroute_to_opus
   - cross_check.py 出一致性报告（如开启）
   - 通过 → renumber.py + stats.py --write
```

### 工作流 B v2 · 真题分析（含 5 处优化）

```text
Step 0【Opus】拆批
  - 看「真题分析进度 / 已知限制」节
  - 列本轮卷次清单

Step 1【v4-pro】lexicon 前置体检 ★ 新增 (优化 #2)
  - 跑 build_subject_lexicon.py 重建词库
  - 抽样 5-10 道上批题干 → v4-pro 抽考点 → 对比 lexicon
  - 输出"建议新增 alias / 缺词条"清单 → Opus 审
  - 工具：00-元/scripts/lexicon_health_check.py（待落地）

Step 2【脚本】parse → tag → render → aggregate
  ※ render_exam_atoms 改 1 行：文件名前缀加年份 (优化 #4)
    旧：新课标II-08.md  →  新：2024-新课标II-08.md
    + frontmatter 新增 paper_year 字段

Step 3【v4-flash】OCR 抽样校验 ★ 新增 (优化 #1)
  - 每卷抽 3 题，切分文本 vs 原 PDF 文本对比
  - 偏差超阈值 → 警告 + 标记
  - 工具：00-元/scripts/ocr_sample_check.py（待落地）

Step 4【Sonnet subagent】tag 缺口兜底
  - 候选 tag 为空 / 跨 tier 不一致的题
  - subagent 内调 v4-pro 判断该归到哪些考点
  - 输出 patch.jsonl 给 Opus

Step 5【Opus】终审 + lexicon 修补
  - 审 OCR 警告 + tag patch
  - 维护 lexicon 召回 + alias 修补
  - 决定本批次能否落盘

Step 6【脚本】跨卷一致性 + 反链回填

※ 扩省份/学科 (优化 #5)：
  - 起 sonnet subagent 跑扩省份 checklist
  - prompt：00-元/scripts/_prompts/extend_province_checklist.md（待落地）
  - subagent 跑：yaml diff → 重建 lexicon → 18 单测 → 试跑 1 卷
  - Opus 只审 subagent 报告

※ golden 回归测试 (优化 #6)：
  - 固定 2024 新课标Ⅱ 输入 → 比对 manifest 字节级相同
  - 工具：00-元/scripts/tests/test_exam_pipeline_golden.py（待落地）
  - 任何流水线脚本改动后必跑
```

**已知未采纳的优化点 #3**（反向覆盖统计：跑完一批后统计哪些概念词条 0 真题引用）—— 暂不做，理由：当前数据量不足以做统计推断。

### 工作流 C · 体检 / 索引维护（零 LLM）

```text
周期跑：
  python 00-元/scripts/analyze_links.py
  python 00-元/scripts/check_naming_conflicts.py
  python 00-元/scripts/check_missing.py
→ Opus 处理输出清单
```

## 4. subagent 编排约束

**何时起 sonnet subagent**
- 复检层 ≥ 10 条 sonnet 配额的 prompt → `Agent(subagent_type=general-purpose)` 批跑
- 准备 topics.jsonl 需读 ≥ 3 份学习路径文档 → `Agent(subagent_type=Explore)`
- 真题流水线 tag 兜底 → 1 个通用 subagent（内部调 _llm_router 调 v4-pro）
- 真题扩省份 checklist → 1 个通用 subagent 跑标准动作

**并行度**
- 一次 `dispatching-parallel-agents` 最多 5 个 sonnet subagent 同时起
- 每个 subagent 任务量 5-10 条 verdict（≈ 20-40k tokens）

**subagent 必带上下文**
- 学科 / 学段 / 学期 / 模板要求（A/B/C 模式）
- 数据契约（manifest 字段 + verdict JSON schema）
- 失败兜底：解析失败时写 `verdict=fix_major + error` 字段

**Opus 不该起 subagent 的场景**
- < 5 条 prompt：主会话自跑更快
- 古文 / 古诗 / 敏感议题：质量风险大于并行收益
- 跨学科一致性判断：需要 Opus 长上下文整体把握

## 5. 交叉复检规则（按场景触发，非每批必跑）

| 触发场景 | 比例 | 目的 |
|---|---:|---|
| 新学科首批（如首跑道法） | **10%** | 校准 review prompt 在新领域的适用性 |
| 新 reviewer 配置（改了 review_atom.md） | **10%** | 验证 prompt 改动 |
| 大版本流水线改动（manifest schema 变化） | **10%** | 防止解析层 bug |
| 稳定期（同学科 ≥ 3 批） | **5% 或 0%** | 抽稽即可 |

**实现**
- `review_dispatch.py --cross-check N`：在原 10/40/50 分桶基础上，随机抽 N% 的条目额外分给另一档 reviewer（总成本 +N%）
- `cross_check.py`：扫 manifest 找有 2 份 review 的 entry → 一致性报告（pass/pass、pass/fix_minor、pass/fix_major 各多少）→ 冲突项 escalate Opus 仲裁

## 6. 5/12–5/15 过渡期（sonnet quota 未恢复）

| 阶段 | 复检比例 | 备注 |
|---|---|---|
| 5/12–5/14 | `--ratio 30,0,70` | Opus 30% + v4-pro 70%，sonnet 跳过 |
| 5/15 起 | `--ratio 10,40,50` | 标准三档 |
| 紧急冲量（仅低风险批次） | 跳过 review_dispatch 直接 renumber | 慎用 |

## 7. 待落地代码改动清单

| P | 文件 | 功能 | 与工作流关系 |
|:---:|---|---|---|
| **P0** | `00-元/scripts/lexicon_health_check.py` | lexicon 前置体检（v4-pro） | 工作流 B Step 1（优化 #2） |
| **P0** | `00-元/scripts/ocr_sample_check.py` | OCR 抽样校验（v4-flash） | 工作流 B Step 3（优化 #1） |
| **P0** | `00-元/scripts/render_exam_atoms.py` 改 1 行 | 文件名加年份前缀 + paper_year frontmatter | 工作流 B Step 2（优化 #4） |
| **P1** | `00-元/scripts/cross_check.py` + `review_dispatch.py --cross-check N` | 交叉复检 | 工作流 A Step 3/⑥ |
| **P1** | `00-元/scripts/_prompts/extend_province_checklist.md` | 扩省份 sonnet subagent prompt | 工作流 B 扩省份（优化 #5） |
| **P2** | `00-元/scripts/tests/test_exam_pipeline_golden.py` | golden 回归测试 | 工作流 B 流水线改动护栏（优化 #6） |

**P0 完成前不开 P2/P3 续跑**（否则要重跑旧数据补年份前缀）。

## 8. 与旧规则的迁移

| 旧 | 新 |
|---|---|
| `< 60 词条 → 主会话` | 删除阈值；古文/敏感议题路由 → topics.jsonl `route: opus` |
| `≥ 60 词条 → sonnet 子代理`（生成） | sonnet 改为复检层 / 辅助 subagent，不再生成主体 |
| 复检 10/40/50 | 不变，新增 5-10% 触发型交叉复检 |
| `Task.REASONING` / `deepseek-reasoner` | 删除，并入 `Task.COMPLEX` / `v4-pro` |
| `--model reasoning`（gen_atom_skeleton） | 删除选项 |

## 9. 验证清单（v3 正式投产前）

- [ ] P0 三件代码改动落地
- [ ] 工作流 A 跑通：小学道法 60 条（首批，开 `--cross-check 10`）
- [ ] 工作流 B v2 跑通：真题 P2 续跑 1 张卷（验证 Step 1/2/3 新增节点）
- [ ] CLAUDE.md 精简版落地（pointer 指本文档）
- [ ] sonnet quota 恢复后切回 `--ratio 10,40,50`

## 10. 关联文档

- 真题分析设计：`docs/superpowers/specs/2026-05-10-jilin-math-exam-analysis-design.md`
- 真题分析 plan：`docs/superpowers/plans/2026-05-10-jilin-math-exam-analysis-plan.md`
- 跨省份扩展 plan：`docs/superpowers/plans/2026-05-15-跨省份跨学科扩展.md`
- 元工作流：`00-元/工作流.md`
- 命名规则：`00-元/命名规则.md`
