# 数据、实验与历史工件目录

[English](../docs/en/data-catalogue.md) | **简体中文**

这里混合了不同年代、不同标签来源的材料。目录名中的 `golden` 不代表专家真值，
`final` 也不代表今天仍未曝光。先读 [研究总览](../docs/research-overview.md)，再进入相应原始记录。

## 各目录的作用

| 目录 | 内容与证据地位 | 对应解释 |
|---|---|---|
| [golden](golden) | 早期 AI 生成 50 题 / 39 题 hard set；保留历史，不作为当前核查器可靠性依据 | [旧评测重算](../docs/reports/evaluation_report.md) |
| [eval](eval) | 早期检索/回答/Agent 输出、不同候选、校验值和旧报告 | [v0.1 审查](https://github.com/lijingshan-6/medrag-agent/blob/v0.8.0/docs/release-review.md) |
| [benchmark/veritasmed_v1](benchmark/veritasmed_v1) | 第一轮来源绑定题集、生成/筛选/模型审阅及基线 | [数据卡](benchmark/veritasmed_v1/dataset_card.md) |
| [benchmark/veritasmed_v1_1](benchmark/veritasmed_v1_1) | 50 题（15 开发 / 35 当时保留）、原文锚点、模型挑战及开发 AI 裁决；无独立临床专家 gold | [数据卡](benchmark/veritasmed_v1_1/dataset_card.md)、[v0.4 结果](../docs/reports/agent-v0.4-flash-report.md) |
| `benchmark/veritasmed_v1_1/v04_*`, `deepseek_*` | 多轮 Qwen/Flash/Pro、失败/余额阻断/重复/首次最终结果；`runtime_code/` 是当时源码快照 | [历史目录](../docs/history.md) |
| [verification/scifact_pilot](verification/scifact_pilot) | 30 对公开标签适配试跑 | [试跑报告](../docs/reports/verification-v0.5-pilot.md) |
| [verification/controlled_v1](verification/controlled_v1) | 48 个简单构造控制、多种核查方式 | [诊断报告](../docs/reports/verification-v0.5-diagnostics.md) |
| [verification/ragtruth_v1](verification/ragtruth_v1) | 24 个 train 自然回答、Direct/Split、60 个官方 test 来源预留元数据 | [完整回答报告](../docs/reports/verification-v0.5-answer-audit.md) |
| [verification/context_v1](verification/context_v1) | 126 次 Context/元文本开发、消融、重复 | [语境报告](../docs/reports/verification-v0.5-context-audit.md) |
| [verification/quote_v2](verification/quote_v2)、[specific_error_v2](verification/specific_error_v2) | 精确定位重放、36 次调用、具体错误的 AI 开发复核；复核不是独立 gold | [定位/具体错误报告](../docs/reports/verification-v0.5-specific-errors.md) |
| [verification/gateway_probe](verification/gateway_probe) | 提供方标识与 token 等接口观测，不验证底层权重身份 | [网关观测](../docs/verification-gateway-observations.md) |
| [verification/v06](verification/v06) | SciFact 固定目标、MiniCheck、校准、医学构造、自然回答、重复/消融及标签敏感性 | [目录说明](verification/v06/README.md) |
| [verification/v07](verification/v07) | 20 题开发两轮 / 40 题最终、三臂固定文献工具比较 | [目录说明](verification/v07/README.md) |
| [verification/v08](verification/v08) | 来源曝光快照、R1 定位重放、R2 的 348 次审计、上下文开发 | [目录说明](verification/v08/README.md) |
| [demo](demo) | authored UI 示例和真实保存演示分别标识；不混入可靠性评估 | [会话演示](demo/conversations/README.md)、[真实医学](demo/medical/README.md) |

## 如何读一项实验

依次读协议/manifest（计划对象及标签）→ freeze / environment（当时方法与配置）→
predictions / raw / attempts（逐次实际输出与失败）→ metrics / summary（派生统计）→ 报告。
不是所有早期实验都有后来的完整工件格式；不得事后补写一个“调用前冻结”的时间戳。
缺少当时信息时保留缺口，不能由今天的配置猜出历史环境。

同一题的重复、同一篇来源的构造变体和不同模型调用不是独立样本。失败保留在原分母中。
公开人工标签、来源文本上的作者构造、开发 AI 复核、纯定位和模型自评必须分开。

## 保留与复现

- 不修改原始输出、失败、旧标签、历史源码和出版方 XML 字节；勘误写独立说明/敏感性分析。
- `summary.json`、`*-metrics.json` 和部分 Markdown 是可重算派生物；运行命令见
  [研究复现](../docs/research-reproduction.md)，不要手工润色数字。
- 新实验另建运行目录。历史最终区已被阅读/用于展示，重跑只能称重复或回归。
- 官方 RAGTruth test 的 60 个来源预留截至 v0.8 未运行；后续使用必须另立合同。
- `.benchmark-runtime/`、`.demo-runtime/`、原始大语料、索引、模型、密钥和用户会话不随 Git 分发。
  旧 v1.1 的完整检索需要原语料；当前三篇论文演示可从仓库快照重建，不能混称可复现范围。
- 代码的 Apache-2.0 不重新许可文献/数据集；许可与来源见 [归属说明](../docs/research-sources.md)。

v0.8 审查时跟踪工件主要体积来自保存的研究文本：v08 约 22 MiB、v06 约 12.5 MiB、
v1.1 约 11.3 MiB。保留它们比删除后只留一张好看的表更有用；未为节省体积压缩或改写原始数据。
