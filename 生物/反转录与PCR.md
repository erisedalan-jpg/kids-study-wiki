---
title: 反转录与PCR
aliases: [反转录与PCR, RT-PCR，反转录PCR，逆转录PCR]
学科: 生物
学段: [高中]
主题: []
状态: 骨架
英文术语: Reverse Transcription and PCR
---

# 反转录与PCR

> **一句话**：反转录是以RNA为模板合成互补DNA（cDNA）的过程，PCR是体外酶促扩增特定DNA片段的技术，两者结合（RT-PCR）可实现对RNA病毒的检测与基因表达定量。
> **English**: Reverse transcription is the process of synthesizing complementary DNA (cDNA) from an RNA template, while PCR is an in vitro technique for amplifying specific DNA fragments; their combination (RT-PCR) enables RNA virus detection and gene expression quantification.

## 🎓 考点精讲

**定义/原理**
- **反转录（逆转录）**：在逆转录酶作用下，以RNA为模板合成一条互补DNA链（cDNA），形成RNA-DNA杂交分子，再水解RNA链，以cDNA为模板合成双链DNA。实质是遗传信息从RNA流向DNA，中心法则的补充。
- **PCR（聚合酶链式反应）**：在体外模拟DNA复制，需要模板DNA、一对引物、耐热DNA聚合酶（Taq酶）、四种脱氧核苷酸（dNTPs）。通过高温变性（解旋双链）→低温退火（引物与单链模板互补配对）→适温延伸（Taq酶沿引物方向合成新链）三步循环（≈30次），实现目的DNA指数级扩增。扩增量公式：2ⁿ（n为循环次数）。
- **RT-PCR（反转录-PCR）**：先以mRNA/病毒RNA为模板逆转录生成cDNA，再以cDNA为模板进行PCR扩增。常用于RNA病毒检测（如新冠病毒）与基因表达分析。

**关键方法**
- 检测RNA病毒的标准流程：提取样本总RNA→逆转录合成cDNA→PCR扩增病毒特异性片段→电泳或荧光检测。
- 引物设计是PCR成败核心：引物需与靶序列两端互补，GC含量40%~60%，两引物Tm值相近，避免发夹结构或引物二聚体。
- 区分RT-PCR与qPCR（定量PCR）：本题聚焦扩增与反转录原理，qPCR是结合荧光标记对PCR反应进行实时定量，属进阶考点。

**典型应用**
- **高考常见设问**：“新冠病毒核酸检测涉及哪些关键生物技术？”——答案核心是逆转录与PCR，需说明病毒RNA经逆转录后PCR检测。
- **选择题陷阱**：误认为PCR所需酶为DNA连接酶或解旋酶，实则高温解旋无需解旋酶，Taq酶是核心合成酶。
- **情境题**：给定引物序列与靶基因序列，要求写出扩增产物或判断引物结合位置。

## ⚠️ 高频易错点

- **混淆逆转录酶与Taq酶的角色**：逆转录酶负责以RNA为模板合成cDNA，Taq酶负责以DNA为模板延伸合成新链。PCR过程中不涉及逆转录酶。
- **误以为PCR需要解旋酶**：PCR通过高温（90–95°C）使DNA双链变性解旋，不依赖解旋酶；退火时引物与模板互补配对，延伸时由Taq酶催化磷酸二酯键形成。
- **PCR循环次数与DNA总量关系的误算**：n次循环后理论产物量为2ⁿ个双链DNA，但引物耗尽后进入平台期，实际低于理论值。引物、dNTPs等消耗限制扩增（选择题图像判断类）。
- **纠错**：PCR不能扩增RNA，直接以RNA为模板无法起反应，必须先逆转录为cDNA再进行PCR——这是“检测RNA病毒为何必须反转录”的高频答题点。

## 🌐 中英对照（术语表）

| 中文 | English | 说明 |
|------|---------|------|
| 逆转录 / 反转录 | Reverse Transcription | 以RNA为模板合成DNA的过程 |
| 聚合酶链式反应 | Polymerase Chain Reaction (PCR) | 体外扩增特定DNA片段的技术 |
| 引物 | Primer | 一小段与模板互补的寡核苷酸，提供延伸起点 |
| 耐热DNA聚合酶（Taq酶） | Taq DNA Polymerase | 在高温下仍具活性的DNA合成酶 |
| 互补DNA | Complementary DNA (cDNA) | 由RNA逆转录获得的DNA |

## 📑 出处与参考资料

- **教材**：(待主会话核对教材索引)
- **课标**：分子与细胞/遗传与进化模块——“中心法则”与“基因工程工具酶”相关要求 🚧
- **生成校对**：DeepSeek-complex 生成于 2026-05-16，由家长核对

## 🔗 相关考点

- [[中心法则]]
- [[DNA 复制]]
- [[基因工程的基本操作程序]]
- [[PCR 引物设计与计算]]
- [[核酸检测与免疫学检测]]