# 复现审计与工作流研究

[English](en/research-reproduction.md) | **简体中文**

界面回放只需 README 的轻量安装。研究推理是可选操作，使用所配置 Flash 账户，可能产生数百次
付费调用，没有 Pro 回退。先查看发布的原始结果；重跑已曝光评估只能叫重复，不是新测试。

## 恢复来源输入

在仓库根目录使用轻量 Python 环境：

```sh
python scripts/verification/prepare_scifact.py
python scripts/verification/answer_benchmark.py download
```

下载固定上游数据到 `.benchmark-runtime`，核对输入，保留发布记录。使用冻结 v0.6/v0.7 分区
不需要旧医学大语料；`v06_prepare.py` 重建历史暴露盘点才需要旧本地语料，不是新克隆的启动前提。

## 无模型调用重算保存结果

```sh
python scripts/verification/v06_report.py pilot
python scripts/verification/v06_report.py final
python scripts/verification/v06_whole_report.py
python scripts/verification/v06_ablation_report.py
python scripts/verification/v06_budget.py report
python scripts/verification/v06_medical_review.py
python scripts/verification/v07_report.py development
python scripts/verification/v07_report.py development --run-dir data/verification/v07/development-original
python scripts/verification/v07_report.py final
python scripts/verification/v07_cases.py
python scripts/verification/v07_export.py export
```

校准需要 [独立研究环境](minicheck-research.md) 的 NumPy/scikit-learn。安装后以下命令也不调用模型：

```sh
python scripts/verification/v06_report.py calibrate
python scripts/verification/v06_report.py calibration_final
python scripts/verification/v07_figures.py
python scripts/verification/v07_release_reports.py
```

标签和原始输出不覆盖，指标 JSON 是确定性派生物。发布运行包含失败，应看完整计划分母，
不只成功项。自然回答匹配测标错范围定位，不是完整语义准确率。`v06_medical_review.py` 重现
单列的事后来源视图敏感性分析，不修改冻结标签或替代主要分数。

## v0.8 离线开发结果

恢复上述固定数据后，无模型调用重放旧 Atomic：

~~~sh
python scripts/verification/v08_rebind.py --output output/v08-r1-replay
~~~

输出全部新旧绑定、恢复/未解决表，包括三个不同 GRADE 审计；重复与消融分列。不改旧判断，
不将恢复位置算作已检查事实。见 [定位报告](reports/verification-v0.8-localization.md)。
[来源盘点](reports/verification-v0.8-exposure.md)另需旧本地医学语料；新克隆可读快照，
无需重建盘点即可运行应用与定位重放。

## 单独记录的付费重复

使用新忽略输出目录，保留原结果：

```sh
python scripts/verification/v06_fixed.py prepare --split pilot --method flash --run-dir .benchmark-runtime/my-fixed-repeat
python scripts/verification/v06_fixed.py run --split pilot --method flash --run-dir .benchmark-runtime/my-fixed-repeat

python scripts/verification/v06_whole.py prepare --dataset medical_development --run-dir .benchmark-runtime/my-answer-repeat
python scripts/verification/v06_whole.py run --dataset medical_development --run-dir .benchmark-runtime/my-answer-repeat

python scripts/verification/v07_benchmark.py prepare --split development --run-dir .benchmark-runtime/my-workflow-repeat
python scripts/verification/v07_benchmark.py run --split development --run-dir .benchmark-runtime/my-workflow-repeat
```

每次有冻结排程与输入/来源指纹。续跑跳过既有尝试，失败不静默重试；权限、余额或限流错误
停止新批次。重试失败题需另标实验。多个 API runner 不要同时运行，每个内部最多三请求。
后期使用有界连续队列：空槽按冻结顺序启动、完成即保存；早期为三请求带 barrier 的批次。
`dispatch` 记录新策略，只改变等待，不改推理配置或选题。阻断后保留在途结果。

## 如何读源码快照

`data/verification/v06/frozen-source.json` 保存准备协议时的精确推理源码。发布格式整理仅在
Python AST（包括提示字符串）相同时接受；格式等价映射回原指纹，行为/提示改变会使冻结对照失败。
环境版本见 `environment-flash.json` 和 `environment-minicheck.json`。

工作流比较最终推理前只修订开发协议：finish 指令矛盾，部分回复混合 JSON/DSML。
首轮 60 条全保留于 `v07/development-original`；第二轮完整使用明确 finish 与记录的格式规范化，
不借最终题修协议。`v07/frozen-source-v2.json` 保存修订源码。DSML 后缀仅留原回复，不执行、
不进入模型历史、不当来源证据。完整裸 answer 对象可包装成 finish，read/引用校验和预算仍适用。

JSONL 用实际文件换行划分；JSON 字符串里的 Unicode 段落/行分隔符保留，不能当记录边界。
`run_v06_v07.py` 是原实验排程的付费续跑器，需已完成医学开发与供应商配置，**不是**无密钥报告命令。
正确离线入口在上方。

v0.7 是受限研究流程与自主对照共享工具，不运行完整 Ask 的稠密/稀疏检索、改写及修复。
语料、指定论文任务、调用预算和这个限制是协议的一部分，不由好成绩反推。

## v0.8 保存会话与限定语诊断

以下不调用模型：

```sh
python scripts/prepare_conversation_demo.py
node --experimental-strip-types frontend/scripts/package-conversation-demo.mjs
python scripts/verification/v08_r2_report.py --markdown docs/reports/verification-v0.8-report.md
```

生成器输出中文主报告，不会自动更新英文翻译。维护发布报告时，重算后同步对应英文页与
语言切换链接，两版使用同一份保存的表格和计数。

第一条从有归属快照重建 15 段摘要；第二条用浏览器自身导入/导出合同打包未经修改的 Ask/审计，
要求全部协议审计存在后才替换导出；第三条从保存判断重算指标，核对唯一任务、来源/输入指纹与
冻结指标定义。缓存须一致，缺尝试仍不完整，重复不能补缺。区间按来源组连四个变体一起抽样。
自然回答、人工错误、机械锚点和语义开发观察分列。

`python scripts/run_showcase.py` 打开无密钥会话回放。九题协议、WS 流和审计在
`data/demo/conversations/`。

**付费推理：**`scripts/record_conversation_demo.py` 调完整 Ask，`v08_r2_run.py run` 调 Flash。
不要仅为看发布版运行它们。默认目录仅续未尝试项，独立重复需另标输出目录与不变的输入/协议。
不覆盖旧失败或冻结最终结果。各阶段顺次运行，最大 API 并发三。
R3 因未用公开标签不足暂缓；重用旧最终题只能做回归，不是新测试。

与发布派生物只读比较时写新文件：

```sh
python scripts/verification/v08_r2_report.py --output output/v08-summary.json --markdown output/v08-report.md
```

临时 Markdown 仍使用 `docs/reports/` 相对链接，应在维护的报告位置阅读。重算只证明与保存输入
一致，不证明原判断/标签正确。[研究解释](research-overview.md) · [工件目录](../data/README.md)。
