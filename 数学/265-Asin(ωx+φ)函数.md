---
title: Asin(ωx+φ)函数
aliases: [Asin(ωx+φ)函数, sinusoidal function, 正弦型函数, 简谐函数]
学科: 数学
学段: [高中]
主题: [必修一, 三角函数, 第五章]
状态: 全龄完成
英文术语: sinusoidal function y=Asin(ωx+φ)
首次共读:
最近共读:
---

## 🎓 $y = A\sin(\omega x + \varphi)$ 函数

### 定义与参数含义

$$y = A\sin(\omega x + \varphi) \quad (A > 0, \omega > 0)$$

| 参数 | 名称 | 物理/数学含义 |
|:---:|:---:|-------------|
| $A$ | 振幅（amplitude）| 函数值的最大值（峰值），$y \in [-A, A]$ |
| $\omega$ | 角频率（angular frequency）| 影响周期 $T = \dfrac{2\pi}{\omega}$；$\omega$ 越大，振荡越快 |
| $\varphi$ | 初相（initial phase）| 影响图象的水平位置；正值向左移 |
| $T = \dfrac{2\pi}{\omega}$ | 周期（period）| 一次完整振荡所需的 $x$ 的变化量 |
| $f = \dfrac{1}{T} = \dfrac{\omega}{2\pi}$ | 频率（frequency）| 单位 $x$ 内振荡的次数 |

### 关键特征

**最大值**：$A$，当 $\omega x + \varphi = \dfrac{\pi}{2} + 2k\pi$ 时取得，即 $x = \dfrac{\pi/2 - \varphi + 2k\pi}{\omega}$

**最小值**：$-A$，当 $\omega x + \varphi = -\dfrac{\pi}{2} + 2k\pi$ 时取得

**零点**：当 $\omega x + \varphi = k\pi$ 时，即 $x = \dfrac{k\pi - \varphi}{\omega}$

**图象中心线**：$y = 0$（若有垂直移位 $y = A\sin(\omega x + \varphi) + b$，中心线为 $y = b$）

### 从图象求参数（五步法）

1. **振幅 $A$**：$A = \dfrac{y_{\max} - y_{\min}}{2}$（最大值减最小值再除以 $2$）
2. **周期 $T$**：从图象中读出一个完整周期的 $x$ 跨度，$\omega = \dfrac{2\pi}{T}$
3. **初相 $\varphi$**：代入特殊点（如最大值点、零点），建立方程求 $\varphi$，并结合 $|\varphi|$ 的限制条件选择

### 典型例题

**例1**：写出满足以下条件的函数：振幅 $2$，周期 $\pi$，图象过点 $(0, \sqrt{3})$ 且 $|\varphi| \leq \dfrac{\pi}{2}$。

解：$A = 2$，$T = \pi$，$\omega = \dfrac{2\pi}{\pi} = 2$，$f(x) = 2\sin(2x + \varphi)$。

代入 $x = 0, y = \sqrt{3}$：$2\sin\varphi = \sqrt{3}$，$\sin\varphi = \dfrac{\sqrt{3}}{2}$。

$\varphi = \dfrac{\pi}{3}$ 或 $\varphi = \pi - \dfrac{\pi}{3} = \dfrac{2\pi}{3}$。

条件 $|\varphi| \leq \dfrac{\pi}{2}$，故 $\varphi = \dfrac{\pi}{3}$，$f(x) = 2\sin\!\left(2x + \dfrac{\pi}{3}\right)$。

**例2**：$y = 3\sin\!\left(2x - \dfrac{\pi}{6}\right)$ 的最大值、最小值和周期。

解：$A = 3$（最大值 $3$，最小值 $-3$），$\omega = 2$，$T = \dfrac{2\pi}{2} = \pi$。

最大值在 $2x - \dfrac{\pi}{6} = \dfrac{\pi}{2}$，即 $x = \dfrac{\pi}{3}$ 时取得（加 $k\pi$ 得全部最大值点）。

**例3**：判断 $y = -2\sin(3x + 1)$ 的振幅和周期。

解：$y = -2\sin(3x+1) = 2\sin(3x+1+\pi)$（利用 $-\sin\theta = \sin(\theta+\pi)$）。

振幅 $A = 2$，$\omega = 3$，周期 $T = \dfrac{2\pi}{3}$。

（或直接：振幅取 $|A| = |-2| = 2$，周期 $T = 2\pi/3$，初相 $\varphi = 1 + \pi$，但需调整为标准形式）

### 物理背景

$y = A\sin(\omega t + \varphi)$ 描述**简谐运动**（simple harmonic motion），如弹簧振子、单摆小角度摆动、交流电压/电流。其中：
- $t$ 为时间，$\omega$ 为角速度（rad/s），$T = 2\pi/\omega$ 为振动周期（秒）
- 在交流电中，$f = 50$ Hz（中国），$T = 0.02$ s，$\omega = 100\pi$ rad/s

### 易错点

1. **振幅取绝对值**：若写成 $y = -3\sin(2x)$，振幅是 $3$ 而非 $-3$（振幅恒为正）
2. **周期公式**：$T = 2\pi/\omega$，$\omega$ 是括号内 $x$ 的系数，不是 $A$ 或 $\varphi$
3. **$\varphi$ 不是移位量**：移位量是 $\varphi/\omega$（将 $x$ 增大 $\varphi/\omega$ 相当于整体左移该量）
4. **初相的多解**：由 $\sin\varphi = c$ 解出 $\varphi$ 时，有两个主值，需用附加条件（$|\varphi| \leq \pi/2$ 等）筛选
5. **有垂直位移时振幅不变**：$y = A\sin(\omega x+\varphi) + b$ 中，振幅仍为 $A$，中心线上移 $b$，最大值为 $A+b$

### 与初中知识的衔接

初中没有 $y = A\sin(\omega x + \varphi)$ 的专题，但学习了函数变换（平移、伸缩）。高中将这些变换应用于三角函数，$y = A\sin(\omega x + \varphi)$ 是描述一切周期振荡现象的通用数学语言。

## 📑 出处与参考资料

- 课标依据：《普通高中数学课程标准（2017年版2020年修订）》必修内容 A 类
- 本地教材：[[素材/教材/ChinaTextbook/高中/数学/人教版（A版）（主编：章建跃&李增沪）-人民教育出版社/普通高中教科书·数学（A版）必修 第一册.pdf]]（第五章，页码待家长核对）
- 百科参考：正弦型函数（Sinusoidal function），简谐运动（Simple harmonic motion），振幅、周期、频率
- 生成校对：Claude Sonnet 4.6，2026-05-09

## 🔗 相关词条

- [[269-三角函数图象变换|三角函数图象变换]]
- [[310-正弦函数图象与性质|正弦函数图象与性质]]
- [[276-余弦函数图象与性质|余弦函数图象与性质]]
- [[303-弧度制|弧度制]]
- [[270-三角函数应用|三角函数应用]]
- [[283-函数的图象变换|函数的图象变换]]
- [[272-三角恒等变换|三角恒等变换]]

<!-- exam-backlinks-start -->
## 高考真题命中
- [[2016-理-15]]
<!-- exam-backlinks-end -->
