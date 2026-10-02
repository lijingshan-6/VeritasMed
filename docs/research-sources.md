# 研究来源与归属

[English](en/research-sources.md) | **简体中文**

Apache-2.0 适用于项目代码，不替代数据、论文或权重的许可证。上游完整语料与模型权重下载到
忽略的本地缓存；小段来源、演示摘要、claim 与实际工具响应随研究记录保留。

## SciFact

David Wadden、Shanchuan Lin、Kyle Lo、Lucy Lu Wang、Madeleine van Zuylen、Arman Cohan、
Hannaneh Hajishirzi，**Fact or Fiction: Verifying Scientific Claims**，EMNLP 2020。
[论文](https://arxiv.org/abs/2004.14974) · [数据和代码](https://github.com/allenai/scifact) ·
[上游许可](https://github.com/allenai/scifact/blob/master/LICENSE.md)。

上游分别规定：claim/证据标注 **CC BY 4.0**，Semantic Scholar S2ORC 摘要 **ODC-By 1.0**，
代码 **Apache-2.0**。随库保留的相应材料遵循各自许可。语料 ID 是 SciFact ID，不是 PubMed ID；
来源记录保留论文题名。

项目把 claim/文献对转成来源组划分、构造诊断和指定论文查询。构造回答与变换标为开发者/AI 工作；
不按模型结果重写公开关系标签。三个工作流演示包含八篇原始候选摘要，无需另下载即可查看工具输入；
研究 trace 也保留实际读过的文字。这些是有出处的数据摘录，不是新编医学证据。

## RAGTruth

[RAGTruth: A Hallucination Corpus for Developing Trustworthy Retrieval-Augmented Language Models](https://github.com/ParticleMedia/RAGTruth)。
固定版本来源和响应文件另行下载。[保留许可](../data/verification/ragtruth_v1/LICENSE-RAGTruth)、
来源 ID 与 manifest 随派生实验保存。警报范围指标与 AI 诊断是项目派生内容；公开标错范围
不为迎合模型而重标。无标错回答不构成完整专家正确性保证。

## GRADE 医学演示

Seaquist 等（2024），[GRADE 低血糖结局](https://doi.org/10.1371/journal.pone.0309907)，CC0。
[来源卡和原始 XML](../data/demo/medical/README.md)记录精确摘要提取。
未修改的 Agent 回答、组别交换和证据移除各有不同来源标识；后两项明确是构造。

[v0.8 两轮导出](../data/verification/v08/grade-conversation-smoke.json)复用 CC0 摘要，
保留两次实际 Ask 与一次 Direct 审计；它是产品例子，不是独立医学评测或专家标注。

[离线定位重放](reports/verification-v0.8-localization.md)复用 SciFact/RAGTruth Atomic 输出和
三个 GRADE 审计，只改定位，保留原判断，不新增专家标签。[暴露盘点](reports/verification-v0.8-exposure.md)
记录复用与候选 ID；机械筛选不是临床标注或新黄金集。

## MiniCheck

Liyan Tang、Philippe Laban、Greg Durrett，**MiniCheck: Efficient Fact-Checking of LLMs
on Grounding Documents**，EMNLP 2024。[论文](https://arxiv.org/abs/2404.10774) ·
[代码](https://github.com/Liyan06/MiniCheck) ·
[模型](https://huggingface.co/lytang/MiniCheck-Flan-T5-Large)。

可选适配器使用固定上游输入/评分格式，改用明确的完整输入长度上限，而非静默截断或上游
分块聚合。精确 revision、模型/代码许可与改动见 [MiniCheck 环境](minicheck-research.md)。不再分发权重。

## v0.8 对话演示

三篇论文的回放保留出版社 XML 和全部原始摘要段落：Seaquist 等（2024，GRADE，CC0）、
Lee 等（2016，糙米纯素饮食 RCT，CC BY 4.0）、Figueira 等（2013，运动交叉 RCT，
Creative Commons Attribution）。旧论文快照没有注明 CC BY 版本，不推断补写。
完整题名、作者、DOI/PMID/PMCID、许可与哈希见
[来源 manifest](../data/demo/conversations/source-manifest.json) 和
[归属说明](../data/demo/conversations/README.md)。

规范化语料保留段落顺序；模型回答明确标为输出，不是原文或 gold。九题推理前固定，失败和
澄清记录保留。只有摘要，不代表全文或现行指南覆盖。新录制的对话仍是演示，后续暴露盘点
必须把来源视为已使用。

R2 增加 24 个此前未用的 SciFact 来源组（另有四个选择时只看输入后排除的组）和 12 个
RAGTruth train 来源，现均已曝光。v0.8 前的盘点保留为不可变选择前快照；新增使用记录
写入新的 manifest/输出目录，不重写旧盘点。
