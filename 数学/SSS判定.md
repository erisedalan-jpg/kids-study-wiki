---
title: SSS判定
aliases: [SSS判定, SSS congruence, 三边判定, side-side-side]
学科: 数学
学段: [初中, 高中]
主题: [几何, 八上, 全等三角形]
状态: 全龄完成
英文术语: SSS congruence criterion
首次共读:
最近共读:
---

# SSS判定

> **课本定义**：三组对应边分别相等的两个三角形全等（简写成"边边边"或"SSS"）。

---

## 📚 6-12 岁（回溯版）

### 什么是 SSS？

SSS 是 **Side-Side-Side**（边-边-边）的缩写。

**结论**：如果两个三角形的三条边分别对应相等，那么这两个三角形全等。

$$AB = DE, \quad BC = EF, \quad CA = FD \implies \triangle ABC \cong \triangle DEF \ (\text{SSS})$$

### 为什么三边确定三角形？

三根木棒，长度固定后，只能拼成**一种形状**的三角形（硬三角形）——这就是三角形的稳定性！

相比之下，四边形可以变形（菱形可以压扁），所以四边形没有类似的"SSS"判定。

### 使用步骤

1. 找出两个三角形
2. 验证三对边分别相等（找公共边、已知相等的边、计算得出的相等边）
3. 写出全等式，注明（SSS）
4. 利用对应元素相等得出结论

### 例子

已知四边形 $ABCD$ 中，$AB = CD$，$AD = CB$，对角线 $BD$。

在 $\triangle ABD$ 和 $\triangle CDB$ 中：$AB = CD$，$AD = CB$，$BD = BD$（公共边）

∴ $\triangle ABD \cong \triangle CDB$（SSS）

---

## 🎓 12+ 进阶版

### 严格定理

**SSS 判定定理**：若 $AB = DE$，$BC = EF$，$CA = FD$，则 $\triangle ABC \cong \triangle DEF$。

### 证明思路（构造法）

以 $EF$ 为底，构造 $\triangle D'EF$ 使得 $D'E = AB = DE$，$D'F = CA = DF$，$D'EF = \triangle ABC$（SSS 公理）。

再证 $\triangle D'EF \cong \triangle DEF$（$ED' = ED$，$FD' = FD$，$EF = EF$，由 SSS 公理）

∴ $D'$ 与 $D$ 重合，即 $\triangle ABC \cong \triangle DEF$。

（在公理体系中，SSS 通常作为公理或通过尺规作图的唯一性得到保证。）

### 典型例题

**例题 1**：已知 $O$ 是 $AC$ 和 $BD$ 的交点，$OA = OC$，$OB = OD$，用 SSS 证明 $\triangle AOB \cong \triangle COD$。

证明：在 $\triangle AOB$ 和 $\triangle COD$ 中：

$OA = OC$（已知），$OB = OD$（已知），$AB = CD$？

注意：此题三边中 $AB$ 和 $CD$ 不一定相等，不能直接用 SSS，应改用 SAS（∠AOB = ∠COD，对顶角）。

**说明**：此例说明使用 SSS 前必须确认**三对边**都相等，少一对就要换其他判定。

**例题 2**：如图，$PA = PB$，$QA = QB$，用 SSS 证明 $\angle APQ = \angle BPQ$。

证明：在 $\triangle PAQ$ 和 $\triangle PBQ$ 中：

$PA = PB$（已知），$QA = QB$（已知），$PQ = PQ$（公共边）

∴ $\triangle PAQ \cong \triangle PBQ$（SSS）

∴ $\angle APQ = \angle BPQ$（对应角相等）✓

### 易错点

1. SSS 要求**三对**边相等，只有两对边相等不能用 SSS（可能需要 SAS 或其他条件）。
2. 公共边也是"已知相等"的一对边，是 SSS 证明中的常用条件。
3. SSS 只适用于**三角形**，多边形没有 SSS 全等判定。

### 知识联系

- → [[全等三角形性质]]：全等后利用对应元素
- → [[SAS判定]]：两边夹角判定，与 SSS 配合使用
- → [[三角形高中线角平分线]]：全等证明三线重合

---

## 🌐 中英对照

| 中文 | English |
|------|---------|
| SSS 判定 | SSS congruence criterion |
| 三边 | three sides |
| 公共边 | common side |
| 三角形稳定性 | rigidity of triangle |
| 全等 | congruent |

---

## 📑 出处

- **教材**：[[素材/教材/ChinaTextbook/初中/数学/人教版-人民教育出版社/八年级/义务教育教科书·数学八年级上册.pdf]] 第十二章 — 待家长核对具体页码
- **课标**：义务教育数学课程标准（2022 年版）
- **拓展**：欧几里得《几何原本》命题 8
- **生成校对**：Claude 生成于 2026-05-08

---

## 🔗 相关词条

- [[全等图形]]
- [[全等三角形性质]]
- [[SAS判定]]
- [[ASA-AAS-HL判定]]
- [[三角形分类]]
- [[线段垂直平分线]]
