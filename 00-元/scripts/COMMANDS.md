# 常用命令速查

> 从 CLAUDE.md 下沉的命令手册。学科建库完整流程见 `_prompts/subject_build_runbook.md`。

```bash
# 进度刷新（同时改 CLAUDE.md 进度表，依赖 AUTO-PROGRESS 锚点）
python 00-元/scripts/stats.py --write

# 单测（124 用例全过为基线；环境无 pytest，用 unittest）
python -m unittest discover -s "00-元/scripts/tests" -p "test_*.py"

# 链接体检与修复
python 00-元/scripts/analyze_links.py                # 报告漏 alias / 死链
python 00-元/scripts/fix_wikilinks.py --apply        # 规范化无管线 [[X]]
python 00-元/scripts/fix_stale_links.py --apply      # 修 renumber 致 stale 号链（必跑）
python 00-元/scripts/fix_latex_delim.py --apply      # \(\)\[\] → $$

# 生成体检门（gen_atom_skeleton 后、renumber 前必跑）
python 00-元/scripts/validate_gen.py 历史 政治 地理

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

# 学生复习权重
python 00-元/scripts/compute_weight.py --apply              # 全库重算
python 00-元/scripts/compute_weight.py --subject 数学 --top 20  # 单科 top 调试
python 00-元/scripts/init_review_fields.py --apply          # 一次性补错题本/mastery 默认字段（幂等）
python 00-元/scripts/mock_review.py                          # 校验字段就绪（占位反写脚本）

# 学生 HTML 静态站（docs/student/，离线手机/平板用）
python 00-元/scripts/gen_html.py --fetch-katex              # 首次联网拉 KaTeX（~250KB）
python 00-元/scripts/gen_html.py --apply --threshold 10     # 4 科 weight≥10 = 610 词条 + 1666 真题
```
