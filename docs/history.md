# 历史版本与实验阅读顺序

[English](en/history.md) | **简体中文**

当前使用见 [文档首页](README.md)。这里区分研究阶段、候选记录和实际 Git tag；
旧文中的“当前”“最终”只指当时。后续维护不会重打已有 tag。

| 阶段 | 实际交付 | 主要记录 |
|---|---|---|
| v0.1 / v0.2 | 候选/阶段记录，没有同名 tag | [v0.1](releases/v0.1.0.md)、[v0.2](releases/v0.2.0.md)、[早期材料说明](archive/README.md) |
| v0.3 | v0.3.0 | [发布](releases/v0.3.0.md)、[题集 v1.1](reports/benchmark-v1.1-report.md)、[当时结果](reports/agent-v0.3-report.md) |
| v0.4 | v0.4.0；先有 Qwen 候选，后改 Flash | [候选](reports/agent-v0.4-report.md)、[修复](reports/agent-v0.4-repaired-report.md)、[模型比较](reports/agent-model-comparison-report.md)、[最终 Flash](reports/agent-v0.4-flash-report.md)、[发布](releases/v0.4.0.md) |
| v0.5 | v0.5.0 | [发布](releases/v0.5.0.md)、[完整回答](reports/verification-v0.5-answer-audit.md)、[具体错误](reports/verification-v0.5-specific-errors.md) |
| v0.6 + v0.7 | 一起随 v0.7.0 交付，没有 v0.6.0 tag | [v0.6](reports/verification-v0.6-report.md)、[v0.7](reports/verification-v0.7-report.md)、[发布](releases/v0.7.0.md) |
| v0.7.1 | 恢复以 Ask 为中心 | [产品决定](decisions/2026-09-27-conversation-first-product.md)、[发布](releases/v0.7.1.md) |
| v0.8 | v0.8.0：持久对话、逐版本审计、限定语诊断 | [发布](releases/v0.8.0.md)、[报告](reports/verification-v0.8-report.md)、[实施记录](archive/worklogs/development-v0.8-worklog.md) |
| v0.8 后续维护 | 当前工作树，见 CHANGELOG Unreleased | [整理记录](milestone-v0.8-review.md)、[下一阶段计划](plans/v0.9-question-coverage.md) |

v0.4 的每轮真实答案、失败、余额阻断、重复和首次最终运行仍保留在 `reports/` 与
[Flash 工作日志](archive/worklogs/agent-v0.4-flash-worklog.md)；不按最佳结果挑选。
v0.6/v0.7 的协议修订见 [共同日志](archive/worklogs/research-v0.6-v0.7-worklog.md)，
首轮工具失败仍在 `data/verification/v07/development-original/`。

本次整理移动文档、合并旧说明，Git 固定版本仍能访问原路径。正文链接和生成脚本已迁移；
冻结实验 JSON 中的历史路径是当次记录，保留原样。完整旧文件去向见 [归档说明](archive/README.md)。
不要按今天代码重写旧协议，也不要把已曝光最终题重新当作未见题。
