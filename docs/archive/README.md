# 归档与删除说明

2026-09-27 文档收拢后，当前指南留在 `docs/`，研究报告统一放在 `docs/reports/`。
`worklogs/` 保留逐轮实施、失败与候选演进；`plans/` 收存原 `superpowers/` 的日期方案和旧 benchmark 审阅指南。
版本协议仍在 `docs/plans/`，发布记录仍在 `docs/releases/`。它们不是当前自动执行指令。

## 已合并或替换的说明

| 原文档 | 当前去向 |
|---|---|
| `PORTS.md`、`demo.md` | [启动配置](../configuration.md)；旧模型运行和旧实验请走 [历史](../history.md) |
| `code-map.md`、早期 `architecture.md` | [当前架构](../architecture.md)，细节见 [Ask 工作流](../agent-workflow.md) |
| `project_spec.md`、`frontend_design.md` | 当前产品以 [对话指南](../conversation-guide.md)、[架构](../architecture.md)、[路线](../verification-roadmap.md) 为准 |
| 早期 API / 安全 / 集成测试 / 发布审查 | 当时的问题及限制见下方固定快照；不再作为当前合规或已通过的保证 |

## 为什么不继续维护早期大报告

旧设计包含 MiMo 默认、单轮标签历史、smart gate 和早期 AI 50 题成绩；这些不能继续描述今天的
Flash 会话产品。旧安全报告的“合规”“不可抵赖”也超出实际实现。有效说明已收进当前架构、
MCP 文档和指南；重复的旧说明从工作树移除，不再只加一句“历史”就仍留在首页竞争。
早期评测数据和生成报告仍保留，它们作为历史诊断而非医学 gold。

以下是移除前的固定版本，供需要审查历史的人查阅；不代表当前版本的测试或实现状态：

- [原始规格](https://github.com/lijingshan-6/medrag-agent/blob/v0.8.0/docs/project_spec.md)
- [早期架构](https://github.com/lijingshan-6/medrag-agent/blob/v0.8.0/docs/architecture.md)
- [旧前端设计](https://github.com/lijingshan-6/medrag-agent/blob/v0.8.0/docs/frontend_design.md)
- [旧安全测试](https://github.com/lijingshan-6/medrag-agent/blob/v0.8.0/docs/security_test_report.md)
- [旧集成测试](https://github.com/lijingshan-6/medrag-agent/blob/v0.8.0/docs/test_report_integration.md)
- [早期 API 可靠性修复](https://github.com/lijingshan-6/medrag-agent/blob/v0.8.0/docs/api-reliability-report.md)
- [早期发布审查](https://github.com/lijingshan-6/medrag-agent/blob/v0.8.0/docs/release-review.md)
- [9 月 18 日里程碑审查](https://github.com/lijingshan-6/medrag-agent/blob/v0.8.0/docs/milestone-audit-2026-09-18.md)
- [9 月 18 日检查记录](https://github.com/lijingshan-6/medrag-agent/blob/v0.8.0/docs/validation-2026-09-18.md)

本轮没有删除实验原始数据、冻结方法副本、逐题坏结果或历史标签。需要重算时使用
[复现指南](../research-reproduction.md)中的新报告路径；JSON 中的旧路径仍可在当次 tag 找到。
