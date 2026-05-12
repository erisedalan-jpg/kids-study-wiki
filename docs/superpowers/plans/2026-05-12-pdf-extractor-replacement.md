# PDF 提取库更换 plan

- **日期**：2026-05-12
- **状态**：长期工作（占位 plan，未启动）
- **决策**：放弃短期/中期修补，长期换库重做 parse_exam_pdf
- **阻塞**：Phase 1 task #5 golden test（要等换库后用新 baseline 跑）/ Phase 2 真题 P2 续跑（建议等换库稳定后再开始，否则新数据继续累积同样的 OCR 错误）

## 背景

Phase 1 任务 #4 反向跑 87 题，OCR 不完整率 70/87 = 80%。Opus 抽样 10 题核对：

- **真 OCR 问题 4/10 (40%)**：根因都是 pdfplumber 把题号上方的"游离数学定义行"切到 stem 之外
  - 例：2022 文 Q1，PDF 里 `M ={2,4,6,8,10}, N=...` 在 `1. 集合...` 之前独立成行 → 切丢
  - 例：2023 Q5，PDF 里 `x²` 在题号上方独立行 → 椭圆方程 `x²/3 + y² = 1` 变成 `y² = 1`
- **LLM 过敏 4/10**：分数/组合数纵向排版（PDF 提取本身没错，LLM 看不惯）
- **图片题 2/10**：茎叶图 / 方格表是图片，pdfplumber 抓不到（任何文本提取库都救不了）

外推：70 不完整题里约 **28 题（40%）是真 OCR 问题**，可通过换库解决。

短期修补 (`fix_orphan_stem_lines.py`) 可救回 60-70% 真问题（即 ~18 题），但留下：
- 复数符号 (B(3/2,-1) 的分数) 仍丢失 — 自动化救不回，要重切
- 跨年累积技术债：每张新卷继续暴露相同 bug
- 修补脚本本身要维护

**结论**：换库一次性解决根因比反复打补丁更划算。

## 候选库（待评估）

| 库 | 优势 | 风险 | 依赖体积 |
|---|---|---|---|
| **PyMuPDF (fitz)** | 数学公式提取最佳，保留布局；社区活跃 | AGPL 许可（非商用 OK），需 C 扩展编译 | ~30 MB |
| **pdftotext** (xpdf/poppler) | 命令行老牌工具，`-layout` 模式保留位置 | 需要系统级二进制（Windows 安装麻烦） | 系统包 |
| **pdfminer.six** | 纯 Python，可控性强 | 速度慢，数学公式提取也不算好 | 纯 Python |
| **视觉 LLM** (Claude / GPT-4V) | 真正"读懂"题面（含图片题），公式准 | 贵 ~¥0.1/卷，API 速率限制 | API 调用 |

## 评估步骤（启动时执行）

```text
Step 1. 选 1 张代表性卷做 dry-run（推荐 2022 文 — 有最多类型的 OCR bug）
Step 2. 对 PyMuPDF / pdftotext / 视觉 LLM 三个候选各跑一遍
        - 输出 questions.json
        - 跑 lexicon_health_check.py 看 OCR 不完整率
        - 记录公式/上下标/分数保真度
Step 3. 三选一（标准）：
        - OCR 不完整率 < 20%（v4-pro 标记）
        - 4 个已知真问题题（2022 文 Q1/Q21、2022 理 Q1、2023 Q5）全部修好
        - 不引入新 bug（用 lexicon health 对照确认）
Step 4. 重写 parse_exam_pdf.py（保持 CLI 兼容 + manifest schema 兼容）
Step 5. 重跑 4 卷 87 题 → 新 questions.json
Step 6. 重跑 render_exam_atoms / aggregate_exam_indices
Step 7. 重跑 lexicon_health_check 出新基线
Step 8. 跑 task #5 golden test 固化新基线
```

## 风险与兼容性

- **questions.json schema 变化**：换库可能引入新字段（如 `figure_refs` 图片引用）— 影响下游 render_exam_atoms。建议保持 8 个必需字段不变，新字段可选
- **22 词条反链**：现有 22 个数学概念词条末尾的 exam-backlinks 区段需重生（aggregate_exam_indices 幂等可重跑，无需手动改）
- **真题词条文件名**：bare_name 唯一性已修（任务 #2），跨年同名不冲突，可放心重生覆盖
- **18 个单元测试**：parse_exam_pdf / tag_questions / render_exam_atoms 的测试要随之更新；可能需要新 fixture
- **依赖**：PyMuPDF AGPL 在私有家庭 wiki 无许可问题；pdftotext 在 Windows 装 poppler 较麻烦，视觉 LLM 增加 API 成本但解决图片题
- **Phase 2 P2 续跑暂缓**：换库前续跑会继续累积 OCR 债，建议等换库完成

## 工作量估算

| 阶段 | 时长 |
|---|---|
| Step 1-3 评估 + 选型 | 半天 |
| Step 4 重写 parse_exam_pdf | 半天 |
| Step 5-7 重跑 + 对照验证 | 半天 |
| Step 8 golden test | 半小时 |
| **合计** | **1.5 天** |

## 启动条件（任意一条满足即可启动）

- Phase 2 P2 续跑正式启动前（避免累积新 OCR 债）
- sonnet quota 恢复后有空闲时段（评估 step 主会话 + sonnet subagent 并行最快）
- 用户主动触发

## 触发短语建议

未来用户说"启动 PDF 提取库评估"或 `/exam pdf-lib eval` → 主会话从 Step 1 开始执行本 plan。

## 关联文档

- 多模型工作流 v3：`docs/superpowers/plans/2026-05-12-multi-model-workflow-v3.md`
- 原真题分析 plan：`docs/superpowers/plans/2026-05-10-jilin-math-exam-analysis-plan.md`
- 跨省份扩展 plan：`docs/superpowers/plans/2026-05-15-跨省份跨学科扩展.md`
- 体检报告：`docs/superpowers/working/lexicon_health_2026-05-12-report.md`
- OCR 核对样本：`docs/superpowers/working/ocr_check_samples_2026-05-12.md`
