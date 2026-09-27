# 脚本入口：演示、复现与历史开发

从仓库根目录运行。普通使用只需要下表第一组，不必顺次运行全部编号脚本。
环境安装见 [项目 README](../README.md)。

## 当前使用

| 命令 / 文件 | 用途 | 是否调用模型 |
|---|---|---|
| `python scripts/run_showcase.py` | 5173 无密钥真实会话回放 | 否 |
| `python scripts/run_demo.py --conversations` | 三篇论文完整 Ask；首次准备独立检索索引 | 提问后调用 Flash；建索引下载/加载 BGE |
| `python scripts/run_audit_demo.py` | 5174 独立审计与研究工作台 | 回放不调用；提交新审计会调用 |
| `local_services.py` | 上述启动器的内部共用实现 | 否 |
| `prepare_conversation_demo.py`, `prepare_medical_demo.py` | 从随库原文生成演示语料 | 否 |
| `bootstrap_demo.py` | 建立隔离的嵌入式 Qdrant 演示库 | 本地嵌入模型 |
| `record_conversation_demo.py` | 记录新的真实 Ask + 审计；先读协议、使用独立 run-dir | **是，付费** |
| `export_openapi.py` | REST 类型源；随后运行前端 `generate-types` | 否 |

会话打包在 `frontend/scripts/package-conversation-demo.mjs`，读取既存原始记录。
它要求所有计划审计文件存在后才写导出，不能把文件缺失当成成功跳过。

## 研究重算与另存实验

`verification/` 中按 v0.5（无版本前缀）、v06、v07、v08 保留明确实验合同。
报告命令集中在 [复现指南](../docs/research-reproduction.md)，数据在 [工件目录](../data/README.md)。
`*_report.py` 多数是离线重算；`*_run.py`、`*_benchmark.py`、`run_queue.py` 和
`run_v06_v07.py` 不能仅凭文件名当作无模型调用命令，先读其 `--help` 与对应协议。

R2 重算从完整原始审计重新计算机械指标、核对冻结任务和输入指纹；不会调用模型或重写预测。
历史算法/提示不能共用新实现后仍称原实验。`benchmark/` 保留题集 v1/v1.1、模型比较、
v0.3/v0.4 评分与历史发布重算；`report_release.py` 的范围是早期保存评测，
**它通过不等于当前版本所有实验通过或临床可靠**。

## 旧流水线与辅助脚本

| 文件 | 保留理由 / 当前边界 |
|---|---|
| `01_ingest_pubmed.py`, `02_ingest_pmc.py`, `04_build_index.py` | 自建完整语料库；不是轻量演示的前置步骤 |
| `06_compare_pipelines.py`, `08_eval_retrieval.py`, `09_eval_answer.py`, `11_eval_agent.py` | 早期检索与 Agent 比较；参数/指标合同不同于当前审计 |
| `07_generate_golden.py`, `12_build_hard_set.py`, `parse_golden_dataset.py` | 旧 AI 题集生成/转换，历史名称 golden 不代表独立专家标注 |
| `13_eval_report.py`, `14_update_eval_report.py` | 早期报告脚本，保留复现；当前旧报告的确定性入口是 `report_release.py` |
| `10_smoke_test_agent.py`, `quick_demo.py` | 手工完整栈/旧 P1–P5 CLI，可能调用模型；不用于新可靠性结论 |
| `qdrant_status.py` | 旧 PowerShell 设置流程查询服务型 Qdrant；不检查嵌入式演示库 |
| `_inspect_qdrant.py` | 服务型 Qdrant payload 调试，不是健康检查；需已有非空集合 |

早期评测的两个校验/模型调用函数仍有重复，但迁移它们对当前产品没有收益，且会扩大历史
环境的改动面。活跃入口共用服务管理和图输入，Ask 节点和证据绑定已按职责拆包；
`benchmark/run_agent.py` 的新运行快照自动收集这些包的源码，旧快照不改写。
报告输出统一到 `docs/reports/`，付费运行的原始输出路径不变。下一阶段设计见
[v0.9 计划](../docs/plans/v0.9-question-coverage.md)，当前没有新的 v09 运行器或实验数据。
