你正在复检一篇由 DeepSeek 自动生成的「家庭学习 Wiki」词条骨架。
你的任务是发现问题，**不要重写整篇**——给出结构化的修订建议清单。

## 待审词条原文

```markdown
{atom_markdown}
```

## 词条元信息

- 学科：{subject}
- 学段：{stage}
- 学期：{semester}
- 模型标签：{model_tag}
- 复检角色：{reviewer_role}   # opus / sonnet / deepseek-self

## 检查清单（逐项判定 PASS / FAIL / WARN）

1. **frontmatter 合规**：7 字段齐全且顺序正确；`aliases` 首位 = bare-name
2. **正文层数与学段匹配**：学前/小学 3 层、初中 2 层、高中 1 层
3. **红线 1（不编 URL/书名/教材路径）**：「教材」行应为「(待主会话核对教材索引)」占位
4. **红线 3（不确定数据带"待家长核对"）**：具体数字 / 年代 / 比例旁是否标注
5. **红线 4（价值观 / 刻板印象）**：是否存在性别 / 地域 / 民族倾向
6. **红线 5（古文 / 敏感议题应路由）**：若主题敏感却生成了内容，应判 FAIL 并要求路由
7. **链接占位合理**：相关词条若不确定写 🚧，不应编造同名词条
8. **中英对照表至少 3 行**且词性 / 例句不空

## 输出格式（严格 JSON，单行或多行均可，但必须可 json.loads）

```json
{{
  "verdict": "pass" | "fix_minor" | "fix_major" | "reroute_to_opus",
  "issues": [
    {{"item": 1, "level": "FAIL|WARN", "msg": "frontmatter 缺少 状态 字段"}},
    {{"item": 3, "level": "FAIL", "msg": "教材行编造了具体页码"}}
  ],
  "fix_suggestions": [
    "把第 14 行的 '人教版数学三上 P52' 改为占位"
  ],
  "reroute_reason": ""   // 仅 verdict=reroute_to_opus 时填写
}}
```

只输出该 JSON 对象，不要任何其它文字、注释或代码块包裹。
