---
title: CRISPR
aliases: [CRISPR, CRISPR-Cas9, 成簇规律间隔短回文重复]
学科: 生物
学段: [高中]
主题: [选必三, 基因工程]
状态: 进阶完成
英文术语: CRISPR-Cas9
weight: 2
weight_breakdown: {"prov_gen":{},"source":{"课标必考":0,"学习路径":0,"alias":2},"period":"高中","config_version":"2026-05-20","computed":"2026-05-20"}
吉林反链: 0
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

# CRISPR
> **一句话**：一种由RNA引导Cas9核酸酶在基因组特定位点进行精确切割的基因编辑系统，是目前最高效、最常用的基因组编辑工具。
> **English**: An RNA-guided genome editing system in which the Cas9 nuclease is directed by a guide RNA to cut specific DNA sequences in the genome.

---

## 🎓 高中进阶
### 定义
CRISPR（Clustered Regularly Interspaced Short Palindromic Repeats，成簇规律间隔短回文重复序列）是细菌和古菌免疫系统的核心组成部分。科学家将其改造为基因编辑工具，称为**CRISPR-Cas9系统**，由两部分组成：
- **Cas9蛋白**：具有双链DNA切割活性的核酸酶
- **导向RNA（sgRNA/gRNA）**：由研究者人工设计的短RNA序列，引导Cas9到达基因组特定位置

2020年，詹妮弗·杜德纳（Jennifer Doudna）和艾曼纽·沙朗提耶（Emmanuelle Charpentier）因CRISPR-Cas9的开发获诺贝尔化学奖。

### 原理 / 步骤 / 应用

**CRISPR-Cas9的天然功能（细菌免疫）**

细菌在被噬菌体感染时，会将噬菌体DNA片段整合进自身基因组的CRISPR区域（记忆）。再次感染时，转录生成crRNA，与tracrRNA结合形成导向RNA，引导Cas9识别并切割入侵噬菌体的DNA——类似"获得性免疫"。

**改造后的CRISPR-Cas9工作原理**

```
设计sgRNA（约20个碱基，与目标DNA互补）
↓
sgRNA + Cas9蛋白 → 复合体
↓
sgRNA引导复合体在基因组中搜索互补序列
↓
找到目标序列（需含PAM序列：5'-NGG-3'）
↓
Cas9在PAM上游3 bp处切割双链DNA → 产生双链断裂（DSB）
↓
细胞修复（NHEJ → 敲除；HDR+模板 → 精确修正）
```

**PAM序列的作用**

PAM（Protospacer Adjacent Motif，原间隔序列邻近基序）是Cas9识别切割位点的必要元素，常见PAM为**5'-NGG-3'**（SpCas9），Cas9在PAM上游3 bp处切割。sgRNA设计时需在目标序列3'末端确认含有PAM。

**CRISPR-Cas9与传统基因编辑工具的比较**

| 特点 | CRISPR-Cas9 | ZFN / TALEN |
|------|------------|-------------|
| 识别机制 | RNA引导（核酸，易设计） | 蛋白质识别（氨基酸，难设计） |
| 设计难度 | 低（合成一段RNA） | 高（需设计蛋白质） |
| 成本 | 低 | 高 |
| 特异性 | 高（20 bp识别序列） | 高 |
| 脱靶效应 | 存在，可通过改进降低 | 较低 |

**主要应用**

| 领域 | 应用 |
|------|------|
| 基础研究 | 建立基因敲除细胞系和动物模型 |
| 医学治疗 | Casgevy（治疗镰刀型细胞贫血症/β地贫，2023年获批） |
| 农业育种 | 精确改良农作物（抗病、高产、营养强化） |
| 诊断检测 | SHERLOCK / DETECTR（利用Cas13/Cas12检测病原体核酸） |
| 基础科学 | 功能基因组学筛选（全基因组CRISPR文库） |

### 典型例题
**例**：CRISPR-Cas9系统中，sgRNA的作用是什么？PAM序列的功能是什么？若sgRNA序列与目标基因不完全互补，会导致什么问题？

**解析**：sgRNA（单导向RNA）通过碱基互补配对引导Cas9蛋白找到基因组上的目标位点，起"分子导航"作用。PAM序列是Cas9识别切割位点的必要标志，Cas9须在含PAM的位点才能结合和切割。若sgRNA与目标序列不完全互补，Cas9可能在**非目标位点**发生切割（脱靶效应），导致非预期的基因突变，这是CRISPR技术目前需要改进的安全问题之一。

### 易错点
- CRISPR本身指细菌基因组中的特殊重复序列，CRISPR-**Cas9**才是基因编辑系统
- sgRNA引导Cas9识别的是**DNA**（不是RNA），靠碱基互补配对定位目标
- CRISPR-Cas9编辑后，细胞仍需通过NHEJ或HDR**修复DNA**，编辑结果取决于修复方式

---

## 🌐 中英对照
### 词汇
| 中文 | 英文 |
|------|------|
| CRISPR | Clustered Regularly Interspaced Short Palindromic Repeats |
| Cas9蛋白 | CRISPR-associated protein 9 (Cas9) |
| 导向RNA | single guide RNA (sgRNA) |
| PAM序列 | protospacer adjacent motif (PAM) |
| 脱靶效应 | off-target effect |
| 双链断裂 | double-strand break (DSB) |
| 基因敲除 | gene knockout |

### 例句
- CRISPR-Cas9 uses a guide RNA to direct the Cas9 nuclease to a specific genomic location for cutting. （CRISPR-Cas9利用导向RNA将Cas9核酸酶引导至特定基因组位置进行切割。）
- The first CRISPR-based medicine, Casgevy, was approved in 2023 for sickle cell disease. （首个基于CRISPR的药物Casgevy于2023年获批用于治疗镰刀型细胞贫血症。）

---

## 📑 出处
- **教材**：[[素材/教材/ChinaTextbook/高中/生物学/人教版-人民教育出版社/普通高中教科书·生物学选择性必修3 生物技术与工程.pdf]] 第3章
- **课标**：普通高中生物学课程标准(2017年版2020年修订)
- **百科**：维基百科"CRISPR"
- **生成校对**：Claude 生成于 2026-05-10

## 🔗 相关词条
[[413-基因编辑|基因编辑]] [[411-基因工程|基因工程]] [[412-基因治疗|基因治疗]] [[414-基因诊断|基因诊断]] [[419-转基因生物|转基因生物]]
