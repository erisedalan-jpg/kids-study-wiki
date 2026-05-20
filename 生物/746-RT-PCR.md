---
title: RT-PCR
aliases: [RT-PCR, 逆转录PCR, 反转录PCR]
学科: 生物
学段: [高中]
主题: [基因工程, 病毒检测]
状态: 骨架
英文术语: Reverse Transcription PCR
weight: 7
weight_breakdown: {"prov_gen":{"吉林-不分":1},"source":{"课标必考":0,"学习路径":0,"alias":2},"period":"高中","config_version":"2026-05-20","computed":"2026-05-20"}
吉林反链: 1
黑龙江反链: 0
北京反链: 0
湖南反链: 0
alias_count: 2
学习路径出现: 0
mastery: 未学
last_review: null
wrong_count: 0
review_count: 0
---

# RT-PCR

> **一句话**：RT-PCR 是一种以 RNA 为起始模板，通过逆转录酶先合成互补 DNA （cDNA），再以 cDNA 为模板进行 PCR 扩增，从而检测或定量特定 RNA 分子的技术。
> **English**: RT-PCR is a laboratory technique that combines reverse transcription of RNA into complementary DNA (cDNA) and amplification of specific cDNA targets using the polymerase chain reaction, used to detect or quantify RNA.

## 🎓 考点精讲

RT-PCR 的核心原理是将**逆转录**与**体外 DNA 扩增**偶联，解决了普通 PCR 不能直接以 RNA 为模板的局限。其操作分两步：

1. **逆转录（RT 反应）**：在逆转录酶（依赖 RNA 的 DNA 聚合酶，如 AMV 或 MMLV 逆转录酶）催化下，以 RNA 为模板，以 Oligo(dT)、随机六聚体或基因特异性引物为引物，在 37–42 °C 条件下合成与 RNA 互补的单链 cDNA。
2. **PCR 扩增**：以 cDNA 第一链为模板，加入目的基因上下游引物与热稳定 DNA 聚合酶（如 Taq 酶），经过变性（~95°C）、退火（50–65°C）、延伸（72°C）的循环，指数式扩增目标 cDNA 片段。扩增产物可通过琼脂糖凝胶电泳（终点法）或荧光信号（实时定量法，即 RT-qPCR）进行检测。

在方法上，区分“一步法”与“两步法”是解题关键：
- **一步法 RT-PCR**：逆转录与 PCR 在同一反应管中连续进行，操作简便、污染风险低，适用于高通量检测，但灵敏度和优化空间有限。
- **两步法 RT-PCR**：先独立完成逆转录得到 cDNA，再取部分 cDNA 作为后续 PCR 模板。灵活性高，可同时分析多个基因，但步骤增多，易引入污染。

**高考典型设问**：
- 考查新冠病毒（SARS-CoV-2）核酸检测的原理：新冠病毒为单链+RNA 病毒，从咽拭子样本中提取病毒 RNA 后，用 RT-PCR 检测其特定基因（如 ORF1ab 区或 N 基因），若扩增曲线出现指数增长且 Ct 值低于阈值，则为阳性。此过程涉及逆转录酶的来源及作用条件。
- 基因表达分析：比较某基因在不同组织中的 mRNA 水平，要先逆转录成 cDNA，再以内参基因（如 GAPDH 或 β-actin）为对照进行半定量或定量 PCR。

## ⚠️ 高频易错点

- **混淆 PCR 与 RT-PCR 的模板要求**：普通 PCR 以 DNA 为模板，所用 DNA 聚合酶无逆转录活性；RT-PCR 必须先以 RNA 为模板逆转录出 cDNA，若直接加入 Taq 酶和引物无法扩增 RNA。
- **误认为逆转录酶需高温激活**：逆转录酶的最适温度通常为 37–42 °C，过高会失活。后续 PCR 步骤中的高温变性并不会“活化”逆转录酶，而是依赖热稳定 Taq 酶。
- **引物选择的对照设置错误**：研究基因表达时，若用 Oligo(dT) 逆转录，则只获得含 polyA 尾的 mRNA 的 cDNA；若需分析无 polyA 的非编码 RNA，必须改用随机六聚体引物或特异性引物。
- **混淆 Ct 值与模板量的关系**：RT-qPCR 中，Ct 值（荧光信号达到阈值的循环数）与起始模板（RNA/cDNA）拷贝数的对数呈负线性关系，Ct 值越低表示起始模板量越高，而非越低。

## 🌐 中英对照（术语表）

| 中文 | English | 说明 |
|------|---------|------|
| 逆转录酶 | reverse transcriptase | 以 RNA 为模板合成 cDNA 的酶，来自逆转录病毒或经基因工程改造。 |
| 互补 DNA | complementary DNA (cDNA) | 由逆转录反应合成的、与 RNA 模板呈碱基互补配对的 DNA 单链。 |
| 热稳定 DNA 聚合酶 | thermostable DNA polymerase | 如 Taq 酶，能耐受 PCR 变性高温（~95 °C）而保持催化活性。 |
| 循环阈值 | cycle threshold (Ct) | 在 RT-qPCR 中荧光信号超过背景阈值所需的扩增循环数，用于定量。 |

> 注：用于检测的 RT-*q*PCR（实时定量/实时荧光 PCR）在高中阶段通常泛称为“荧光 RT-PCR”或直接称作 RT-PCR，高考设问若涉及扩增曲线与 Ct 值，即指实时定量 RT-PCR。

## 📑 出处与参考资料

- **教材**：(待主会话核对教材索引)
- **课标**：🚧 高中生物学·选择性必修·生物技术与工程 · 基因工程 / 病毒检测应用
- **生成校对**：DeepSeek-complex 生成于 2026-05-16，由家长核对

## 🔗 相关考点

- [[410-PCR|PCR]] 
- [[494-核酸检测|核酸检测]] 
- [[295-中心法则|中心法则]] 
- [[逆转录病毒]] 
- [[实时荧光定量PCR]]

<!-- exam-backlinks-start -->
## 高考真题命中
- [[2022-全国乙-12]]
<!-- exam-backlinks-end -->
