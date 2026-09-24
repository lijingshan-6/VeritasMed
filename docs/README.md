# 文档索引与维护范围

更新：2026-09-24。当前为 **v0.4.0 已发布研究展示里程碑，研究基线为 Flash**；v0.5 开发中。
主分支提供当前入口，固定版本见 [`v0.4.0` 标签](https://github.com/lijingshan-6/medrag-agent/tree/v0.4.0)。
开发 15/15、独立重复 10/10、首次保留测试 31/35；详见 [版本说明](releases/v0.4.0.md)。
模型选择及下一轮优先级以 [当前决定](decisions/2026-09-23-flash-research-baseline.md) 为准。
Qwen 修复报告与 Pro/Flash 对比记录的是不同运行，不能互相替代成绩。

下一阶段（2026-09-24）：[技术路线](verification-roadmap.md) 与
[v0.5 文本审计实施计划](plans/v0.5-text-verification.md)。先验证文本忠实性核查，
复用公开人工标注；医学证据分级与跨文献可比性不作为首期交付门槛。

已完成的第一轮工作见 [v0.5 固定证据试跑报告](verification-v0.5-pilot.md)：独立核查模块与
30 条公开标注样本已跑通，25/30 标签一致；局限、全部分歧和复现命令一并公开。

[第二轮受控诊断与消融](verification-v0.5-diagnostics.md)已完成：12 个文献组、48 条构造样本，
三方案均为 48/48，尚未发现结构化核查增益。使用 [标注规范](verification-label-policy.md)
解释标签边界，[网关观测](verification-gateway-observations.md)记录模型标识和用量限制。

整段回答阶段见 [执行协议](plans/v0.5-answer-audit.md)、[研究报告](verification-v0.5-answer-audit.md)
及 [真实审计面板](audit-demo.md)。这一轮提前接入面板，用自然回答的人工错误范围测量漏审，
不把简单构造题的高分外推成应用可靠性。

## 持续维护的入口

| 文档 | 回答什么 | 什么时候更新 |
|---|---|---|
| [项目 README](../README.md) | 做什么、如何启动、目前效果与限制 | 功能、启动方法或最新结果变化时 |
| [演示与研究配置](demo.md) / [配置示例](../.env.example) | 怎么演示、怎样选择本地或 Flash 后端、怎样运行开发题 | 配置或运行入口变化时，两处同步 |
| [Agent 工作流](agent-workflow.md) | 当前实际执行的步骤、证据处理和失败边界 | Agent 行为变化时，按源码更新 |
| [Flash 效果报告](agent-v0.4-flash-report.md) / [工作记录](agent-v0.4-flash-worklog.md) | 当前修复、逐轮失败、开发/重复/保留测试状态 | 每轮完成并对照原文审阅后更新 |
| [Flash 基线决定](decisions/2026-09-23-flash-research-baseline.md) | 为什么选 Flash、下一轮先解决什么 | 新决定以新的日期记录，旧决定注明被替代 |
| [Pro/Flash 对比报告](agent-model-comparison-report.md) | 已完成的对比说明了什么、哪些问题仍在 Agent 中 | 发现解读错误时注明修正；新运行另存报告 |
| [题集说明](../data/benchmark/veritasmed_v1_1/dataset_card.md) / [审阅指南](benchmark-review-guide.md) | 黄金题集的来源、划分、证据和评分标准 | 题集新版本或审阅协议变化时；冻结版本保留 |
| [v0.4 版本说明](releases/v0.4.0.md) / [变更记录](../CHANGELOG.md) | 当前交付状态、剩余限制、实际发布了什么 | 一轮修复完成或实际发布时 |

修改功能后，只同步相关说明。最新状态放在上述入口，逐次实验细节放在对应报告，
不再把完整工作流、所有成绩和下一轮任务复制到每一份文档。

## 保留的实验记录

| 阶段 | 阅读入口 | 性质 |
|---|---|---|
| 已发布 v0.3 | [报告](agent-v0.3-report.md) / [发布说明](releases/v0.3.0.md) | 发布时的结果，不是当前模型成绩 |
| v0.4 首轮 Qwen | [报告](agent-v0.4-report.md) / [实施记录](agent-v0.4-worklog.md) | 首轮候选的失败和限制 |
| v0.4 Qwen 修复 | [报告](agent-v0.4-repaired-report.md) / [修复记录](agent-v0.4-repair-worklog.md) | 指定 Qwen 配置下的开发集结果 |
| OpenHub Pro/Flash | [对比报告](agent-model-comparison-report.md) / [实验计划](superpowers/plans/2026-09-22-deepseek-agent-comparison.md) | 两轮共 44 个真实 Agent 答案及逐题判定 |
| 已发布 v0.4 Flash | [效果报告](agent-v0.4-flash-report.md) / [工作记录](agent-v0.4-flash-worklog.md) / [版本说明](releases/v0.4.0.md) | 冻结实现、开发/重复/首次保留测试与真实演示 |

报告链接到相应逐题页面和原始数据。`*-cases.md` 等生成页面应通过报告中的脚本重新生成，
不要手改分数或用一次成功重试覆盖失败。新答案需要重新对照原文审阅；离线重算已有分数
不会生成新答案，也不是新一轮效果评测。

## 历史设计与专项说明

[原始项目规格](project_spec.md)、[早期架构](architecture.md)、
[v0.4 初始计划](superpowers/plans/2026-09-22-veritasmed-agent-v0.4.md) 以及
`superpowers/` 下其他带日期方案保留设计背景，不作为当前配置或成绩入口。
旧模型名、旧指标和未完成设想不逐段改写成今天的实现。

前端设计、MCP、安全、端口和旧审计文档在修改对应功能时再维护；它们描述的范围与
阶段不应扩大为当前整套系统的保证。日常使用先看项目 README 和演示指南。

## 本次交付与后续维护

- Flash 收敛报告、开发/重复/保留测试逐题案例、真实界面截图与导出示例已齐备，历史候选说明保留。
- 工作流或界面行为改变后：更新工作流及相关演示步骤；截图注明真实运行还是固定示例。
- v0.4 已同步 README 获取方式、版本说明和变更记录；后续版本另记日期和发布标签。

35 道保留题已经用于本次冻结后的评测，后续可用于回归，但不能再次称为未见测试。
下一轮以新报告记录对遗漏、证据标签和可读性的改进，保留本次四道失败的原始判定。
