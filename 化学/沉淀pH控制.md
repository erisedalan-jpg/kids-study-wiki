---
title: 沉淀pH控制
aliases: [沉淀pH控制]
学科: 化学
学段: [高中]
主题: []
状态: 骨架
英文术语: Precipitation pH Control
---

# 沉淀pH控制

> **一句话**：通过调控溶液的 pH 使某些金属离子生成氢氧化物沉淀，而另一些离子不沉淀，从而利用溶度积（Ksp）差异实现离子分离的化学方法。
> **English**: A chemical method that separates metal ions by adjusting the pH to selectively precipitate certain metal hydroxides based on differences in their solubility product constants (Ksp).

## 🎓 考点精讲

**定义/原理**
核心原理是难溶氢氧化物 $M(OH)_n$ 的沉淀溶解平衡：$M^{n+} + nOH^- \rightleftharpoons M(OH)_n(s)$。沉淀析出的条件是离子积 $Q_c = c(M^{n+}) \cdot c(OH^-)^n > K_{sp}$。
由 $K_{sp}$ 可推导出沉淀 pH 公式：
- **开始沉淀**（$Q_c = K_{sp}$）：pH = $14 + \frac{1}{n} \lg \frac{K_{sp}}{c_0(M^{n+})}$（常温）
- **沉淀完全**（残留 $c(M^{n+}) \leq 1.0\times 10^{-5} \text{mol/L}$）：pH = $14 + \frac{1}{n} \lg \frac{K_{sp}}{1.0\times 10^{-5}}$

**关键方法**
1. **计算步骤**：①写出沉淀溶解平衡与 Ksp 表达式；②代入目标离子浓度求 $c(OH^-)$；③计算 pOH，换算为 pH。
2. **沉淀顺序判断**：离子初始浓度相近时，一般 $K_{sp}$ 越小（或形成沉淀所需 pH 越低）的氢氧化物越先析出。
3. **试剂选择**：常用不引入新杂质的难溶氧化物或碳酸盐（如 FeO、CuO、MgO、MnCO₃ 等）调节 pH，不仅促进 $Fe^{3+}$ 水解沉淀，还可利用其消耗 H⁺使平衡正向移动。

**典型应用**
高考中常出现在**工艺流程除杂**与**离子分离**情境：
- **铁离子除杂**：含 $Cu^{2+}$ 酸性浸出液中常含 $Fe^{3+}$，必须先将 $Fe^{2+}$ 氧化为 $Fe^{3+}$（因 $Fe(OH)_3$ 沉淀 pH 远低于 $Fe(OH)_2$），再加入 CuO 等调 pH ≈ 3–4，使 $Fe^{3+}$ 转化为 $Fe(OH)_3$ 沉淀滤除，而主元素 $Cu^{2+}$ 不沉淀。
- **pH 区间计算**：工艺题会要求控制 pH 范围——下限确保目标离子不开始沉淀，上限确保杂质离子沉淀完全（$c \leq 10^{-5} \text{mol/L}$）。需代入 Ksp 数据精确计算。

## ⚠️ 高频易错点

- **混淆开始沉淀与沉淀完全的判据**：开始沉淀是 $Q_c = K_{sp}$（残留浓度仍为原浓度或接近原浓度），沉淀完全须满足残留浓度 ≤ $1.0\times 10^{-5} \text{mol/L}$，两者所求 pH 差距大。
- **忽视变价预处理**：$Fe^{2+}$ 直接调 pH 无法有效除铁，必须先用 $H_2O_2$ 等氧化为 $Fe^{3+}$，否则 $Fe(OH)_2$ 沉淀 pH 过高，会导致主元素共沉淀或除杂失败。
- **调节剂选择不当**：加入 $NaOH$、$NH_3 \cdot H_2O$ 等强碱会引入 $Na^+$、$NH_4^+$ 杂质，且易导致局部过碱使主元素损失；标准解法应选用与酸反应且阳离子为所需主离子的氧化物或碳酸盐。
- **忽略两性氢氧化物**：$Al(OH)_3$、$Zn(OH)_2$ 在 pH 过高时会因生成 $[Al(OH)_4]^-$、$[Zn(OH)_4]^{2-}$ 而重新溶解，因此 pH 控制必须设定上限，避免“沉淀后又溶解”。

## 🌐 中英对照（术语表）

| 中文 | English | 说明 |
|------|---------|------|
| 沉淀溶解平衡 | Precipitation-dissolution equilibrium | 难溶电解质与其溶解离子间的动态平衡 |
| 溶度积常数 $K_{sp}$ | Solubility product constant | 难溶电解质饱和溶液中离子浓度幂之积，温度一定时为常数 |
| 离子积 $Q_c$ | Ion product | 任意时刻离子浓度幂之积，用于与 $K_{sp}$ 比较判断沉淀生成或溶解 |
| 沉淀完全的离子判据 | Criterion for complete precipitation | 通常规定残留离子浓度 ≤ $1.0\times 10^{-5} \text{mol/L}$ |
| 两性氢氧化物 | Amphoteric hydroxide | 既能溶于酸又能溶于强碱的氢氧化物，如 $Al(OH)_3$、$Zn(OH)_2$ |

## 📑 出处与参考资料

- **教材**：(待主会话核对教材索引)
- **课标**：🚧
- **生成校对**：DeepSeek-complex 生成于 2026-05-15，由家长核对

## 🔗 相关考点

- [[溶度积常数]]
- [[离子除杂]]
- [[Fe3+与Fe2+的转化]]
- [[工艺流程|化学工艺流程]]
- [[氨水调节pH]]