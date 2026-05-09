---
title: 相似三角形判定-SAS
aliases: [相似三角形判定-SAS, SAS similarity, 边角边相似]
学科: 数学
学段: [初中]
主题: [九下, 相似]
状态: 全龄完成
英文术语: SAS similarity criterion
首次共读:
最近共读:
---

# 相似三角形判定-SAS

> **一句话**：两边成比例且夹角相等（SAS），则两三角形相似。

---

## 📚 给 6-12 岁（自读版）

### SAS 判定

如果两个三角形中：
1. **有一对角相等**（这对角是夹角）
2. **夹这个角的两条边分别成比例**

那么这两个三角形相似。

### SAS 的含义

S = Side（边），A = Angle（角）

**边-角-边**：两边成比例，夹角相等。

### 图示理解

$\triangle ABC$ 和 $\triangle DEF$：
- $\angle A = \angle D$（夹角相等）
- $\dfrac{AB}{DE} = \dfrac{AC}{DF}$（夹这个角的两边成比例）

→ $\triangle ABC \sim \triangle DEF$

---

## 🎓 给 12+（进阶版）

### 定理

**SAS 判定定理**：若 $\triangle ABC$ 和 $\triangle DEF$ 中，$\angle A = \angle D$，且

$$\frac{AB}{DE} = \frac{AC}{DF}$$

则 $\triangle ABC \sim \triangle DEF$。

### SAS 与全等 SAS 的区别

| | 全等 SAS | 相似 SAS |
|--|---------|---------|
| 夹角 | 相等 | 相等 |
| 两边 | 对应相等 | 对应成比例 |

相似 SAS 是全等 SAS 的推广。

### 典型例题

**例 1**：$\triangle ABC$ 中，$D$、$E$ 分别是 $AB$、$AC$ 上的点，$AD=2, DB=4, AE=3, EC=6$，证明 $\triangle ADE \sim \triangle ABC$。

证明：
$$\frac{AD}{AB} = \frac{2}{6} = \frac{1}{3}, \quad \frac{AE}{AC} = \frac{3}{9} = \frac{1}{3}$$
$\angle A = \angle A$（公共角），由 SAS 判定：$\triangle ADE \sim \triangle ABC$，相似比 $= 1:3$。

**例 2**：已知 $\dfrac{PA}{PB} = \dfrac{PC}{PD}$，$\angle P$ 为公共角，判断 $\triangle PAC$ 与 $\triangle PBD$ 是否相似。

解：$\dfrac{PA}{PB} = \dfrac{PC}{PD}$（已知），$\angle P = \angle P$（公共角），由 SAS：$\triangle PAC \sim \triangle PBD$。

### SAS 的应用场景

SAS 特别适用于：
- 含有**公共角**且给出两侧边长比的情形
- 题目给出两边之比而非角度信息的情形

### 易错点

- ❌ 两边成比例但夹角不同，不能用 SAS
- ❌ 是"夹角"，不是任意一个角；$\dfrac{AB}{DE} = \dfrac{BC}{EF}$ 且 $\angle A = \angle D$ 不能用 SAS（$\angle A$ 不是 $AB$、$BC$ 的夹角）

---

## 📑 出处

- 教材：[[素材/教材/ChinaTextbook/初中/数学/人教版-人民教育出版社/九年级/义务教育教科书·数学九年级下册.pdf]] 第27章第3节（页码待家长核对）
- 课标：义务教育数学课程标准(2022)·图形与几何·相似三角形判定
- 生成校对：Claude 生成于 2026-05-09，请家长对照实体教材核实页码。

---

## 🔗 相关词条

[[相似三角形定义]] · [[相似三角形判定-AA]] · [[相似三角形判定-SSS]] · [[相似三角形性质]] · [[全等三角形]] · [[比例的基本性质]] · [[平行线分线段成比例]]
