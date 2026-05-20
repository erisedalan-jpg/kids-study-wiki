---
title: ASA-AAS-HL判定
aliases: [ASA-AAS-HL判定, ASA AAS HL congruence, 角边角判定, 角角边判定, 斜边直角边]
学科: 数学
学段: [初中, 高中]
主题: [几何, 八上, 全等三角形]
状态: 全龄完成
英文术语: ASA, AAS, HL congruence criteria
首次共读:
最近共读:
weight: 4
weight_breakdown: {"prov_gen":{},"source":{"课标必考":0,"学习路径":0,"alias":4},"period":"高中","config_version":"2026-05-20","computed":"2026-05-20"}
吉林反链: 0
黑龙江反链: 0
北京反链: 0
湖南反链: 0
alias_count: 4
学习路径出现: 0
mastery: 未学
last_review: null
wrong_count: 0
review_count: 0
---

# ASA-AAS-HL判定

> **课本定义**：**ASA**：两角和它们的夹边分别相等，则两三角形全等（"角边角"）；**AAS**：两角和其中一角的对边分别相等，则两三角形全等（"角角边"）；**HL**：直角三角形斜边和一条直角边分别相等，则两直角三角形全等（"斜边直角边"）。

---

## 📚 6-12 岁（回溯版）

### 三种判定一览

| 缩写 | 全称 | 条件 | 关键字 |
|------|------|------|--------|
| **ASA** | Angle-Side-Angle | 两角 + 夹边 | 边被两角夹住 |
| **AAS** | Angle-Angle-Side | 两角 + 其中一角的对边 | 边不在两角之间 |
| **HL** | Hypotenuse-Leg | 斜边 + 一直角边 | 仅限直角三角形 |

### ASA（角边角）

两角和**夹边**相等 → 全等

$$\angle A = \angle D,\quad AB = DE,\quad \angle B = \angle E \implies \triangle ABC \cong \triangle DEF \ (\text{ASA})$$

夹边 $AB$ 被 $\angle A$ 和 $\angle B$ 夹住。

### AAS（角角边）

两角确定后，第三个角自动确定（内角和 180°），因此 AAS 可从 ASA 推出。

$$\angle A = \angle D,\quad \angle B = \angle E,\quad BC = EF \implies \triangle ABC \cong \triangle DEF \ (\text{AAS})$$

### HL（斜边直角边）

专用于直角三角形！

$$\angle C = \angle F = 90°,\quad AB = DE \ (\text{斜边}),\quad BC = EF \ (\text{直角边}) \implies \triangle ABC \cong \triangle DEF \ (\text{HL})$$

---

## 🎓 12+ 进阶版

### 严格证明：AAS 由 ASA 推出

已知 $\angle A = \angle D$，$\angle B = \angle E$，$BC = EF$。

由内角和：$\angle C = 180° - \angle A - \angle B = 180° - \angle D - \angle E = \angle F$

在 $\triangle ABC$ 和 $\triangle DEF$ 中：$\angle B = \angle E$（已知），$BC = EF$（已知），$\angle C = \angle F$（已证）

由 ASA，$\triangle ABC \cong \triangle DEF$。$\blacksquare$

### 严格证明：HL 由 SSS 推出（利用勾股定理）

已知 $\angle C = \angle F = 90°$，$AB = DE$，$BC = EF$。

由勾股定理：$AC = \sqrt{AB^2 - BC^2} = \sqrt{DE^2 - EF^2} = DF$

三边均相等，由 SSS，$\triangle ABC \cong \triangle DEF$。$\blacksquare$

### 典型例题

**例题 1（ASA）**：已知 $AB \parallel CD$，$AB = CD$（平行且相等），$M$ 是 $AC$ 中点，证明 $M$ 也是 $BD$ 中点。

证明：在 $\triangle AMB$ 和 $\triangle CMD$ 中：

$\angle MAB = \angle MCD$（内错角，$AB \parallel CD$），$AB = CD$，$\angle MBA = \angle MDC$（内错角）

由 ASA，$\triangle AMB \cong \triangle CMD$

∴ $MB = MD$，即 $M$ 是 $BD$ 中点。✓

**例题 2（HL）**：已知直角三角形 $\triangle ABC$（$\angle C = 90°$）和 $\triangle DEF$（$\angle F = 90°$），$AB = DE$，$AC = DF$，证明两三角形全等。

证明：在直角三角形 $\triangle ABC$ 和 $\triangle DEF$ 中：

$\angle C = \angle F = 90°$，$AB = DE$（斜边相等），$AC = DF$（直角边相等）

由 HL，$\triangle ABC \cong \triangle DEF$。✓

### 判定方法总结与选择

| 已知条件 | 选用判定 |
|----------|----------|
| 三边相等 | SSS |
| 两边夹角 | SAS |
| 两角夹边 | ASA |
| 两角一对边 | AAS |
| 直角三角形斜边+直角边 | HL |
| 两边非夹角 | 无法直接判定（SSA 无效）|

### 易错点

1. **ASA 的"夹边"**：边必须在两个角之间，不能搞错位置。
2. **HL 仅限直角三角形**：非直角三角形不能用 HL。
3. **AAA 不是全等判定**：三角相等只能说明相似，不能说明全等（大小可能不同）。

### 知识联系

- → [[146-SSS判定|SSS判定]]、[[145-SAS判定|SAS判定]]：配套使用的全等判定
- → [[152-全等三角形性质|全等三角形性质]]：全等后的推论
- → [[171-等腰三角形性质|等腰三角形性质]]：等腰三角形中常用 ASA 或 AAS

---

## 🌐 中英对照

| 中文 | English |
|------|---------|
| 角边角 | angle-side-angle (ASA) |
| 角角边 | angle-angle-side (AAS) |
| 斜边直角边 | hypotenuse-leg (HL) |
| 斜边 | hypotenuse |
| 直角边 | leg |
| 内错角 | alternate interior angles |

---

## 📑 出处

- **教材**：[[素材/教材/ChinaTextbook/初中/数学/人教版-人民教育出版社/八年级/义务教育教科书·数学八年级上册.pdf]] 第十二章 — 待家长核对具体页码
- **课标**：义务教育数学课程标准（2022 年版）
- **拓展**：欧几里得《几何原本》命题 26
- **生成校对**：Claude 生成于 2026-05-08

---

## 🔗 相关词条

- [[153-全等图形|全等图形]]
- [[152-全等三角形性质|全等三角形性质]]
- [[146-SSS判定|SSS判定]]
- [[145-SAS判定|SAS判定]]
- [[171-等腰三角形性质|等腰三角形性质]]
- [[173-线段垂直平分线|线段垂直平分线]]
