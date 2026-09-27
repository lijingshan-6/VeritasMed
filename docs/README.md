# 文档索引与维护范围

v0.8 已完成收敛：多轮历史、答案版本、逐轮审计、显式上下文和无密钥真实对话回放。
产品主入口是 **Ask（5173）**，Audit 属于答案审阅；5174 是可选独立工作台。
[对话指南](conversation-guide.md) · [实施记录](development-v0.8-worklog.md) ·
[v0.8 版本说明](releases/v0.8.0.md) · [v0.8 研究报告](verification-v0.8-report.md)。

Flash / Direct 保持默认。v0.6 / v0.7 的原始研究与 [v0.7.1 产品修正](releases/v0.7.1.md)
继续保留历史意义；新界面与原文锚点不能作为语义可靠性提升的证据。

## 使用与演示

| 入口 | 内容 |
|---|---|
| [对话与逐轮审计](conversation-guide.md) | 无密钥真实三轮回放、Live 追问、版本和完整会话导出 |
| [项目 README](../README.md) | 获取固定版本、轻量启动、实际能力及关键结果 |
| [原子审计与工作流比较](research-demo.md) | GRADE 三类输入、方法/分歧展示、工具 trace、导出与回答传递 |
| [真实医学 Ask → Audit](medical-demo.md) | 原始 CC0 论文、实际 Agent 记录和完整检索演示 |
| [审计指南](audit-demo.md) | 方法、输入上限、原文位置、状态及新审计 |
| [原完整 Agent 工作流](agent-workflow.md) | 历史 Ask graph 的实际处理步骤，不与受限研究模块混称 |
| [配置示例](../.env.example) / [演示配置](demo.md) | Flash、本地模型、轻量审计与完整检索的不同依赖 |

## 当前研究与决定

| 入口 | 内容 |
|---|---|
| [整体路线](verification-roadmap.md) | 最终形态、当前边界及后续任务 |
| [v0.8 研究报告](verification-v0.8-report.md) | 348 次预定审计全部保留；限定语共现、自然样本、重复、成本与来源组区间分开解释 |
| [v0.8 详细计划](plans/v0.8-conversation-and-audit.md) | 对话记录、上下文追问、每轮审计、父句定位与限定语保真；含阶段交付和研究边界 |
| [v0.8 来源盘点](verification-v0.8-exposure.md) | 剩余公开标签不足；R2 继续构造诊断，R3 新语义泛化比较暂不启动 |
| [v0.8 六例开发复核](verification-v0.8-extraction-review.md) | 原文限定语和规范化事实的具体差异，AI 观察不是独立 gold |
| [v0.8 定位重放](verification-v0.8-localization.md) | 167 次旧审计、82 个事实恢复位置；零新增语义判断 |
| [v0.6 协议](plans/v0.6-audit-reliability.md) | 数据、原子审计、MiniCheck、消融、校准与默认升级条件 |
| [v0.6 研究报告](verification-v0.6-report.md) | 339 对固定目标、医学开发/转移、自然回答、消融、重复与校准的完整结果 |
| [v0.7 协议](plans/v0.7-agent-comparison.md) | 同工具、同模型的三臂文献事实查询 |
| [v0.7 研究报告](verification-v0.7-report.md) / [全部最终案例](verification-v0.7-cases.md) | 40 题三臂原答、正确接受/错误接受、实际成本与开发协议修订 |
| [v0.7 范围决定](decisions/2026-09-26-v07-research-scope.md) | 为什么先做受限对照，完整开放检索/自动修复如何后移 |
| [提取保真度开发复核](verification-v0.6-extraction-review.md) | 预选 12 条的具体限定词/重复问题，明确为 AI 诊断 |
| [构造标签勘误](../data/verification/v06/medical-label-review.json) / [敏感性明细](../data/verification/v06/medical-label-sensitivity.json) | Natsal-3 来源范围疑点；原记录不变，事后分析与主表分开 |
| [研究复现](research-reproduction.md) | 无付费调用的重算、原始输出、另存新运行 |
| [MiniCheck](minicheck-research.md) | 可选隔离环境、模型 revision、输入上限及分数含义 |
| [研究来源归属](research-sources.md) | SciFact、RAGTruth、GRADE 与 MiniCheck 的出处、许可和本项目变换 |
| [v06 工件](../data/verification/v06/README.md) / [v07 工件](../data/verification/v07/README.md) | 冻结清单、逐次结果、全部失败和数据来源 |
| [Flash 基线决定](decisions/2026-09-23-flash-research-baseline.md) | 用户选择 Flash；不加入例行 Pro 回退或 Pro 裁判 |
| [标签边界](verification-label-policy.md) | 公开人工标注、构造诊断和 AI 复核的不同证据地位 |

原文定位不等于语义正确，核查器分歧不等于文献冲突。没有合格校准规则就不显示可信度百分比。
不同任务、模型配置和样本分母的数字不能合并成一项“系统可靠率”。

## 保留的历史记录

| 阶段 | 入口 | 性质 |
|---|---|---|
| v0.3 | [效果报告](agent-v0.3-report.md) / [发布说明](releases/v0.3.0.md) | 当时配置的历史结果 |
| v0.4 Qwen | [初轮](agent-v0.4-report.md) / [修复](agent-v0.4-repaired-report.md) | 不同候选的失败与修复记录 |
| Pro / Flash 比较 | [报告](agent-model-comparison-report.md) | 两轮 44 个真实 Agent 答案及来源审阅 |
| v0.4 Flash | [报告](agent-v0.4-flash-report.md) / [发布](releases/v0.4.0.md) | 开发 15/15、重复 10/10、首次保留 31/35；这些不是新核查器的准确率 |
| v0.5 固定目标 | [试跑](verification-v0.5-pilot.md) / [构造消融](verification-v0.5-diagnostics.md) | 公开标签适配与简单控制 |
| v0.5 完整回答 | [Direct/Split](verification-v0.5-answer-audit.md) / [Context](verification-v0.5-context-audit.md) | 自然回答定位与重复，不等于语义正确率 |
| v0.5 quote-v2 | [具体错误与定位](verification-v0.5-specific-errors.md) / [发布](releases/v0.5.0.md) | AI 开发复核、精确引句与真实医学面板 |

历史最终题已经曝光，后续只能用于回归。保留原标签、首次失败和原始输出；不以一次成功重试替换。
旧方案与数字保留历史含义，不逐段改写成今天的实现。

## 维护规则

功能改变时同步 README、相应使用指南、OpenAPI/types 和 CHANGELOG；研究变化时更新对应协议、
工件说明和由保存输出生成的报告。当前状态集中在这些入口，逐次实验细节放在实施记录。

[原始规格](project_spec.md)、[早期架构](architecture.md) 和 `superpowers/` 下的日期方案是历史设计。
MCP 安全、端口或旧前端专项文档按实际修改范围维护，不能扩大成整套 Web 应用的保证。
