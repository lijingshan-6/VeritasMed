# 文档导航

当前发布版本是 v0.8.0；工作树中的整理和下一阶段计划记在 [CHANGELOG](../CHANGELOG.md)。
**Ask 是产品入口，Audit 在回答内，Research 是独立实验展示。** Flash / Direct 保持默认。

## 当前维护的入口

| 目的 | 文档 |
|---|---|
| 安装并展示 | [项目 README](../README.md)、[启动与配置](configuration.md) |
| 多轮问答、保存、导入与逐轮审计 | [对话指南](conversation-guide.md) |
| 看 claim 与原文、运行新审计 | [审计指南](audit-demo.md) |
| 真实医学演示 / 研究比较 | [医学演示](medical-demo.md)、[Research 演示](research-demo.md) |
| 改代码 | [当前架构](architecture.md)、[Ask 工作流](agent-workflow.md)、[脚本索引](../scripts/README.md) |
| 看已经证明和未证明什么 | [研究总览](research-overview.md) → [报告目录](reports/README.md) |
| 重算实验 | [复现指南](research-reproduction.md)、[数据目录](../data/README.md)、[MiniCheck](minicheck-research.md) |
| 下一步怎么做 | [技术路线](verification-roadmap.md) → [v0.9 问题覆盖研究计划](plans/v0.9-question-coverage.md) |
| 配置边界与来源归属 | [MCP 控制](mcp_security.md)、[研究来源](research-sources.md)、[标注边界](verification-label-policy.md) |
| 找旧阶段 | [历史版本](history.md)、[归档说明](archive/README.md)、[版本说明](releases/v0.8.0.md) |
| 本轮清理内容 | [里程碑整理记录](milestone-v0.8-review.md) |

## 哪些东西放在哪里

- `reports/`：实际研究报告、逐题案例及失败分析；包括不利结果。
- `plans/`：版本协议；v0.5–v0.8 是历史合同，下一阶段入口只有 v0.9 计划。
- `archive/worklogs/`、`archive/plans/`：逐轮实施记录与早期日期方案，不作为现行使用说明。
- `releases/`：版本交付记录；研究阶段不一定有同名 Git tag。
- `decisions/`：仍需记住的范围和产品决定，如 Flash 默认、Ask 为主。
- `../data/`：原始实验、来源、冻结清单和标签。文档清理不删研究失败或改原始分数。

## 维护约定

功能说明只在 README、相应指南和架构中维护；研究数字由保存工件生成，改脚本后重算，
不要在多份路线/工作日志里手抄一套“最新总成绩”。历史日志保留当时语态，通过索引说明身份。
每次研究保留输入、输出、失败和暴露边界。原文定位不等于语义正确，模型分歧不等于论文冲突。
本轮旧文件去向见 [归档说明](archive/README.md)，新命令不要再使用旧路径。
