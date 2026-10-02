# 研究报告与逐题记录

[English](../en/reports/README.md) | **简体中文**

先读 [研究总览](../research-overview.md)，再按问题查对应报告。不同任务的分母和标签来源
不同，不能合并成整体可靠率。报告既保留成功，也保留错误接受、漏项、未完成和负结果。

| 阶段 | 主报告 | 相关细节 |
|---|---|---|
| 早期工程诊断 | [旧评测](evaluation_report.md)、[hard set](hard_set_report.md)、[延迟](latency_report.md) | AI 题和模型评分，不是独立 gold |
| 题集重建 | [v1](benchmark-report.md)、[v1.1](benchmark-v1.1-report.md) | [旧审阅指南](../archive/plans/benchmark-review-guide.md) |
| v0.3 / v0.4 | [v0.3](agent-v0.3-report.md)、[v0.4 候选](agent-v0.4-report.md)、[修复](agent-v0.4-repaired-report.md)、[模型比较](agent-model-comparison-report.md)、[Flash 发布](agent-v0.4-flash-report.md) | 同目录全部 `agent-*-cases.md`；各主报告链接各轮，含失败 |
| v0.5 | [固定目标](verification-v0.5-pilot.md)、[控制](verification-v0.5-diagnostics.md)、[整段回答](verification-v0.5-answer-audit.md)、[语境](verification-v0.5-context-audit.md)、[具体错误](verification-v0.5-specific-errors.md) | 早期试跑、AI 阅读与公开标签分别说明 |
| v0.6 | [核查可靠性、消融、校准](verification-v0.6-report.md) | [提取复核](verification-v0.6-extraction-review.md) |
| v0.7 | [同工具流程比较](verification-v0.7-report.md) | [40 个最终案例](verification-v0.7-cases.md) |
| v0.8 | [限定语与对话](verification-v0.8-report.md) | [来源盘点](verification-v0.8-exposure.md)、[离线定位](verification-v0.8-localization.md)、[六例复核](verification-v0.8-extraction-review.md) |

原始 JSON / JSONL 与冻结输入在 [data](../../data/README.md)。主报告中有来源、标签、
样本范围和重算命令；[复现指南](../research-reproduction.md)统一列出运行入口。
已完成阶段的协议在 `../plans/`，当时过程见 [工作日志](../archive/README.md)。
下一轮只有 [v0.9 计划](../plans/v0.9-question-coverage.md)，尚无新的结果。
