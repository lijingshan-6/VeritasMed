"""Build denominator-explicit milestone reports from complete saved runs; no inference."""

import json

from medrag.verification.scifact import read_jsonl
from v06_prepare import OUT, ROOT
from v07_benchmark import V07


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def pct(value):
    return "不可用" if value is None else f"{100 * value:.1f}%"


def ci(record):
    interval = record["ci95"]
    return (
        "不可用"
        if interval is None
        else f"{100 * record['difference']:+.1f} pp [{100 * interval[0]:+.1f}, {100 * interval[1]:+.1f}]"
    )


def table(headers, rows):
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(str(v) for v in row) + " |" for row in rows),
        ]
    )


def require_complete():
    runs = {
        OUT / "fixed/final-flash": 339,
        OUT / "fixed/final-minicheck": 339,
        OUT / "whole/medical_development": 180,
        OUT / "whole/medical_transfer": 96,
        OUT / "whole/natural": 108,
        OUT / "whole/repeat": 48,
        V07 / "development": 60,
        V07 / "development-original": 60,
        V07 / "final": 120,
    }
    for directory, expected in runs.items():
        if len(read_jsonl(directory / "predictions.jsonl")) != expected:
            raise ValueError(f"Finish the planned run before publishing: {directory}")


def v06_report():
    fixed = read(OUT / "fixed-final-metrics.json")
    cal = read(OUT / "calibration-final.json")
    whole = read(OUT / "whole-metrics.json")
    ablation = read(OUT / "ablation-metrics.json")
    budget = read(OUT / "budget-metrics.json")
    sensitivity = read(OUT / "medical-label-sensitivity.json")
    lines = [
        "# v0.6 审计可靠性研究报告（随 v0.7.0 交付）",
        "本报告将固定目标、医学构造和自然回答分开。公开人工标签提供外部参照；构造事实与 AI 开发复核不是独立医学 gold。所有计划样本及失败均保留。",
        "**决定：Direct 保持默认，atomic-v1 与 MiniCheck 保留研究选项。校准未得到满足预设条件的接受阈值，不发布逐条可信度百分比。**",
        "## 数据与冻结",
        table(
            ["用途", "来源组 / 配对或回答", "性质"],
            [
                ["固定目标开发试跑", "60 配对", "未用于最终成绩"],
                ["分数拟合", "50 组 / 87 对", "SciFact train"],
                ["独立阈值选择", "50 组 / 91 对", "SciFact train"],
                ["固定目标最终", "247 组 / 339 对", "官方 dev，一次冻结后运行；不是官方 test"],
                ["医学开发", "15 组 / 60 回答", "原义、改写、单错误、移证据"],
                ["医学转移", "8 组 / 32 回答", "同样为构造诊断，不是临床泛化"],
                ["自然回答开发", "36 来源 / 36 回答", "18 有公开错误，18 无标错"],
                ["预定重复", "12 来源 / 每方法共 3 次", "原次 + 两次独立调用"],
                ["自然回答最终储备", "60 来源", "未启用；整段语义评分与默认升级证据不足"],
            ],
        ),
        "P0 以 claim 与全部关联文献构成连通组隔离，同时排除旧试跑、构造与医学语料暴露。v0.7 的 20/40 组先另留。医学计划的 24 组减为 23：文献 42291761 摘要年份矛盾且截断，未勉强标注。公开数据可能进入模型训练，来源隔离不等于无预训练污染。",
        "协议、标签来源、逐次设置与精确推理代码见 [v06 工件](../data/verification/v06/README.md)。本次没有提示调优后覆盖首轮记录。",
        "## E1：固定 claim 与完整摘要",
        "Flash 固定核查器与 pinned MiniCheck-Flan-T5-Large 接收相同目标和完整摘要，不给 gold 关系或依据句。MiniCheck 只做二分类；超出 2048 token 显式失败，不静默截断。本表合并 Contradicted / Insufficient 为 Non-supported。",
        "公开关系标签可能依赖领域别名或隐含推理，而 Flash 提示限制仅凭提供文本；相同输入不等于两种方法学到了相同判断政策。标签仍保留，不按输出重标；不能把所有分歧简单归为模型医学能力高低。",
    ]
    rows = []
    for method in ("flash", "minicheck"):
        r = fixed[method]
        c = r["counts"]
        rows.append(
            [
                method,
                f"{c['completed']}/{c['total']}",
                f"{c['correct']}/{c['total']}",
                f"{c['false_accept']}/{c['nonsupport']}",
                f"{c['true_accept']}/{c['support']}",
                pct(r["support_precision"]),
                pct(r["balanced_accuracy"]),
            ]
        )
    lines += [
        table(
            [
                "方法",
                "完成",
                "二分类正确",
                "非支持被接受",
                "支持召回",
                "支持精度",
                "Balanced accuracy",
            ],
            rows,
        ),
        "失败/未完成不会成为正确非支持。主表分母包含全部计划配对。共同成功子集另存 JSON，不能替代主表。",
        "Flash 还需要合法依据句编号才算完成，MiniCheck 只输出二分类，没有等价的引用合同。因此主表包含额外输出合同的影响，不能把所有无效引用都解释成语义分类错误。",
        "另列事后标签诊断：仅忽略 Flash 的无效依据引用、保留其已解析关系标签时，完成 "
        + str(fixed["flash"]["parsed_relation_diagnostic"]["counts"]["completed"])
        + "/339，二分类正确 "
        + str(fixed["flash"]["parsed_relation_diagnostic"]["counts"]["correct"])
        + "/339。此补充在 E2 发现引用失败后、固定最终运行过程中登记，未用于选择方法、阈值或默认；原始主表和失败不被替换。完整分母与明细在 JSON。",
        "![固定核查比较](assets/v07-fixed-verifiers.png)",
        table(
            ["MiniCheck − Flash", "配对差值及 95% 来源组 bootstrap 区间"],
            [
                [
                    "错误接受率（越低越好）",
                    ci(fixed["minicheck_minus_flash"]["false_acceptance_rate"]),
                ],
                ["支持召回（越高越好）", ci(fixed["minicheck_minus_flash"]["support_recall"])],
            ],
        ),
        "247 个连通组、2,000 次配对重采样，seed 260926。零观察错误或退化区间不等于零风险。预定升级要求错误接受改善且支持召回下降不超过 3 个百分点，不能只比较总准确率。",
        "### Flash 的三分类与依据",
        table(
            ["公开标签", "输出", "数量"],
            [[x["gold"], x["prediction"], x["n"]] for x in fixed["flash"]["three_class_matrix"]],
        ),
        "依据句对照：`"
        + json.dumps(
            fixed["flash"]["rationale_annotation_comparison"]["counts"], ensure_ascii=False
        )
        + "`。这里只比较是否命中公开依据集合；替代有效依据可能未被标注。文字位置有效不等于判断正确。",
        table(
            ["方法", "每对中位秒数", "累计秒数", "已报告 API tokens", "无 token 用量记录数"],
            [
                [
                    m,
                    fixed[m]["runtime"]["median_seconds"],
                    round(fixed[m]["runtime"]["sum_elapsed_seconds"], 1),
                    f"{fixed[m]['runtime']['reported_tokens']:,}",
                    fixed[m]["runtime"]["records_without_token_usage"],
                ]
                for m in ("flash", "minicheck")
            ],
        ),
        "MiniCheck 使用本机 RTX 4060 Laptop / FP32；时间不含权重加载。其无 API usage 不代表没有计算成本。Flash 的模型名是网关返回字段，不能独立认证底层权重身份。模型版本、环境和响应字段在原始工件中保留。",
        "## 校准：没有可发布的接受规则",
        f"仅在 87 对拟合一个 logistic 映射，在另 91 对按预定网格选择阈值：接受项经验错误率 ≤5%，至少 20 对且涉及 10 来源组。**没有合格阈值**。最终仍评估冻结映射，Brier raw={cal['brier_raw']:.4f}，映射后={cal['brier_calibrated']:.4f}，完成 {cal['completed']}/{cal['planned_pairs']}。",
        "![可靠性及风险覆盖](assets/v07-calibration.png)",
        "最终曲线用于描述分布，不用于重新挑阈值。阈值为 null 时，接受风险为不可估计，不能把零接受写成零风险。每组预选代表样本和风险区间另存 `calibration-final.json`。此分数针对文本支持关系，不是医学事实为真的概率。",
        "## E3：完整回答与构造事实",
        "**下面主表按原冻结构造标签重算，其中 medical-15 存在已记录的来源范围疑点；紧随主表给出统一去掉该组的敏感性结果。保留原记录不等于继续把已知疑点当作无误标签。**",
        "医学每条回答有两个预先写定的事实单元。以下通过原回答字符位置关联提取结果：至少覆盖一个目标一半的非空白字符才关联；关联判断分歧则不作确定决定。宽 claim 可能混入相邻事实；忠实的规范化也可能少覆盖原文字符。因此这些是**位置关联诊断，不是语义准确率**。",
    ]
    for dataset, title in (
        ("medical_development", "开发 15 组"),
        ("medical_transfer", "转移 8 组"),
    ):
        rows = []
        for method, r in whole[dataset].items():
            c = r["counts"]
            rows.append(
                [
                    method,
                    f"{c['completed_answers']}/{c['planned_answers']}",
                    f"{c['fully_located']}/{c['facts']}",
                    f"{c['wrong_fact_accepted']}/{c['non_supported_facts']}",
                    f"{c['supported_fact_accepted']}/{c['supported_facts']}",
                    f"{c['unsupported_fact_flagged']}/{c['non_supported_facts']}",
                ]
            )
        lines += [
            f"### {title}",
            table(
                [
                    "方法",
                    "回答完成",
                    "事实原文全覆盖",
                    "位置关联错误放行",
                    "位置关联正确支持",
                    "位置关联错误警报",
                ],
                rows,
            ),
        ]
    lines += [
        "未提取、未完成与无法关联仍留在原分母。不给只成功拆出的简单项单独充当总成绩。",
        "### 构造标签勘误与敏感性",
        "在开发输出已经存在后的全 23 组来源文本复看中，发现 medical-15 的 Natsal-3 编号没有出现在给定标题/选定原句中。人数本身有依据，但完整命名事实的 Supported 标签需要限定。原标签、输入、推理和主表均未改写。以下对所有方法统一去掉该组四个变体，只是事后敏感性分析，不是独立专家复核或新确认性成绩。其余组亦未获无误认证。",
        table(
            ["方法", "来源 / 回答 / 事实", "位置关联错误放行", "位置关联正确支持"],
            [
                [
                    m,
                    f"{sensitivity['remaining_groups']} / {sensitivity['remaining_answers']} / {r['counts']['facts']}",
                    f"{r['counts']['wrong_fact_accepted']}/{r['counts']['non_supported_facts']}",
                    f"{r['counts']['supported_fact_accepted']}/{r['counts']['supported_facts']}",
                ]
                for m, r in sensitivity["methods"].items()
            ],
        ),
        "[勘误记录](../data/verification/v06/medical-label-review.json)与 [完整敏感性明细](../data/verification/v06/medical-label-sensitivity.json)保留发现时间、来源和限制。若未来修订题集，应另建版本并重新冻结，不覆盖本轮输入。",
        "### 自然回答：公开错误范围",
        table(
            ["方法", "回答完成", "错误任意重叠", "错误至少半覆盖", "无标错回答上有警报"],
            [
                [
                    m,
                    f"{r['counts']['completed_answers']}/36",
                    f"{r['counts']['span_hit_any']}/{r['counts']['gold_spans']}",
                    f"{r['counts']['span_hit_half']}/{r['counts']['gold_spans']}",
                    f"{r['counts']['false_positive_answers']}/{r['counts']['unmarked_answers']}",
                ]
                for m, r in whole["natural"].items()
            ],
        ),
        "沿用旧计分字段以便重算，其中 false_positive 命名仅指无标错回答上的警报，不是已确认误报。重叠不能证明抓到了具体错误，更长警报也会提升重叠。自然回答不是医学诊断集。",
        "### 实际计算量",
        table(
            ["数据区", "方法", "调用", "已报告 tokens", "每回答均秒数", "无 usage 调用"],
            [
                [
                    d,
                    m,
                    r["runtime"]["logical_calls"],
                    f"{r['runtime']['reported_tokens']:,}",
                    round(
                        r["runtime"]["sum_elapsed_seconds"] / r["runtime"]["recorded_answers"], 1
                    ),
                    r["runtime"]["calls_without_token_usage"],
                ]
                for d in ("medical_development", "medical_transfer", "natural")
                for m, r in whole[d].items()
            ],
        ),
        "这是逐回答延迟，不是并行批次墙钟时间。Direct 通常 1 调用；原 Split 逐项核查，最多 25；atomic-v1 一次提取后分批核查，最多 3。不能把额外计算带来的变化全归因于结构。",
        "## E2 / E4 / E5：机制诊断",
        f"按 seed 预选 3 来源全部 4 变体，共 12 回答。E2 两核查器在同一个冻结独立事实表上共 {ablation['E2_same_standalone_targets']['counts']['targets']} 个目标，双方完成 {ablation['E2_same_standalone_targets']['counts']['both_completed']}，二分类分歧 {ablation['E2_same_standalone_targets']['counts']['disagreed']}。相同输入哈希逐项保留；不把原回答拼进证据来让它自证。解析本身无独立语义 gold，分歧不决定谁正确。",
        f"E2 执行状态：Flash {json.dumps(ablation['E2_same_standalone_targets']['flash_statuses'])}；MiniCheck {json.dumps(ablation['E2_same_standalone_targets']['minicheck_statuses'])}。Flash 三项未完成来自无效依据引用，不能被算成正确非支持；MiniCheck 没有这一引用输出合同。",
        "这三项都位于 medical-06：源视图中的多句文字合成一个输入证据单元（编号 0），Flash 输出编号 1，触发 SentenceOutOfRange，同时保留了原 supported 标签和解释。输入包装与引用合同也是待改进环节；本轮未补写编号、重跑或抹掉失败。",
        f"E4 去掉显式槽位但保留同一提取表、原回答、来源：{json.dumps(ablation['E4_explicit_slots']['counts'], ensure_ascii=False)}。一次开发消融的变化可能包含模型随机性；不能据增加警报宣布槽位有效。",
        f"E5 数字规则为建议性诊断：{json.dumps(ablation['E5_numeric_rules']['on'], ensure_ascii=False)}；关闭时无规则提示，改变语义决定 0。多数字、缺单位、区间或语境不确定保持 unresolved。没有把数字碰巧相同当作事实支持。",
        "### 拆分保真度的实质缺口",
        "[12 条预选输入的 AI 开发复核](verification-v0.6-extraction-review.md)发现：季度分母在某规范化子事实中未显式保留；数值槽位有时只写单位；重复/复合事实被自报 atomic。原文定位使问题可见，但不能修复语义。该复核不冒充独立标注，也不声称全量保真度已经验证。",
        "另一个瓶颈是过短片段在回答中重复，虽然父段可能唯一，当前冻结定位规则仍要求片段在全文唯一；未绑定的事实不进入核查。自然 Atomic 的绑定状态计数：`"
        + json.dumps(whole["natural"]["atomic_v1"]["runtime"]["binding_states"], ensure_ascii=False)
        + "`。父段约束下的定位可作为后续受控改进，但本轮没有补跑后覆盖这些未检查项。",
        "## E6：重复与调用预算控制",
        table(
            ["方法", "来源数", "三次之间警报有无改变", "警报位置集合改变"],
            [
                [m, r["planned_sources"], r["changed_alarm_presence"], r["changed_alarm_locations"]]
                for m, r in whole["repeat"].items()
            ],
        ),
        "这些变化来自相同冻结输入的真实独立重复；没有挑最好一次。三次同意不是正确标签。",
        table(
            ["保守答案级控制", "明确警报", "无警报", "需复核", "有标错回答上的警报", "调用总数"],
            [
                [
                    m,
                    r["alarm"],
                    r["no_alarm"],
                    r["needs_review"],
                    f"{r['alarms_on_annotated_error_answers']}/{r['annotated_error_answers']}",
                    r["runtime"]["logical_calls"],
                ]
                for m, r in budget["methods"].items()
            ],
        ),
        "医疗开发位置指标出现小幅收益后、重复输出生成前，预定利用同一 12 来源追加此分析。Direct 的三次都完成且警报有无一致才保留信号，其他情况需复核；atomic 取第一次、最多三调用。只比较答案级警报，不汇合原文范围、不用多数票当正确，也不以保留率掩盖失败。见 `budget-protocol.json` 与全部明细。",
        "## 产品与发布决定",
        "原子拆分、限定词槽位、原文多片段绑定、数字建议和单独 MiniCheck 结果已接入真实记录面板。Direct 仍为默认；模型分歧只提示审阅。三类 GRADE 演示明确区分真实 Agent 原答、构造组别互换和构造删证据。",
        "没有获得覆盖整段语义、提取保真度和支持召回非劣的足够证据，故不升级默认、不自动修复答案、不使用 60 来源自然回答保留集。证据分级、临床适用性和跨研究冲突裁决继续单列研究。v0.6 的交付随 v0.7.0 合并发布，不伪造独立 v0.6.0 发布。",
        "[实施协议](plans/v0.6-audit-reliability.md) · [复现](research-reproduction.md) · [MiniCheck 环境与上游](minicheck-research.md) · [v0.7 工作流对照](verification-v0.7-report.md)",
    ]
    (ROOT / "docs/verification-v0.6-report.md").write_text(
        "\n\n".join(lines) + "\n", encoding="utf8"
    )


def v07_report():
    final = read(V07 / "final-metrics.json")
    development = read(V07 / "development-metrics.json")
    original = read(V07 / "development-original/metrics.json")
    methods = ("direct_reader", "autonomous_tools", "structured_workflow")
    lines = [
        "# v0.7 工作流比较：结构是否值得？",
        "本次完成固定文献事实查询的三臂比较：读全部摘要一次回答、Flash 自主调工具、规定检索—读取—草稿—核查流程。**这是受限新研究模块，不能据此宣称历史完整 Ask graph、开放医学研究或临床结论已验证。**",
        "**结论：这批最终 40 题没有证明规定流程改善判断。直接阅读与自主工具均 35/40 二分类正确，规定流程最终接受且正确 31/40；三臂错误接受均 2/19。保留简单对照，不据这版结果启用自动答案修复。**",
        "## 设计与可比范围",
        "20 个独立 train 来源组用于开发，40 个另留组用于一次冻结后最终比较；每组按 seed 一题。每题给目标论文标题与待核查 claim，候选库为目标 + 7 篇固定干扰摘要。模型看不到标签和正确依据。公开 SciFact 标签只评指定论文关系，不评答案中每个解释句的正确性。",
        "相同 Flash 网关配置、输入语料、公共 search/read/verify 工具和调用上限。两工具臂最多 6 次模型调用、8 次非模型工具调用；verify 消耗同一模型预算。自主臂用应用层 JSON action 协议，不是 provider 原生 tool_calls。结构化臂选择精确标题匹配的论文；题目已命名目标，其搜索难度较低。不能外推到未知论文的开放检索。",
        "Direct reader 一次读取八篇摘要；其计算量和上下文量与工具臂不同，这是明确保留的更简单方案。报告实际 token、耗时与调用，不能只凭相同上限称计算预算完全相等。",
        "首轮开发后修正自主动作协议，三臂在相同 20 道开发题上完整重跑一次，再冻结最终方法；首轮记录保留，未排除表现不好的基线。结构化臂保留原始草稿与核查意见，发生分歧或核查失败则保留判断，不自动改成核查器的答案；核查器不充当 gold。",
        "## 一次最终比较",
        table(
            [
                "方法",
                "可接受完成",
                "二分类正确 / 全题",
                "非支持被接受",
                "支持召回",
                "支持精度",
                "三分类正确 / 全题",
            ],
            [
                [
                    m,
                    f"{final['methods'][m]['accepted']['counts']['completed']}/40",
                    f"{final['methods'][m]['accepted']['counts']['correct']}/40",
                    f"{final['methods'][m]['accepted']['counts']['false_accept']}/{final['methods'][m]['accepted']['counts']['nonsupport']}",
                    f"{final['methods'][m]['accepted']['counts']['true_accept']}/{final['methods'][m]['accepted']['counts']['support']}",
                    pct(final["methods"][m]["accepted"]["support_precision"]),
                    f"{final['methods'][m]['workflow_counts']['correct_three_class']}/40",
                ]
                for m in methods
            ],
        ),
        "失败、未检查、分歧、预算耗尽和错文献均进入全题分母，不算正确拒答。二分类将 contradicted/insufficient 合并；三分类不合并。",
        "### 执行与协议限制",
        table(
            ["方法", "流程状态", "初次解析/调用错误类型", "动作格式归一化", "含 DSML 标记回复"],
            [
                [
                    m,
                    json.dumps(final["methods"][m]["execution_statuses"], ensure_ascii=False),
                    json.dumps(final["methods"][m]["call_error_types"], ensure_ascii=False),
                    json.dumps(final["methods"][m]["action_adaptations"], ensure_ascii=False),
                    final["methods"][m]["workflow_counts"]["replies_with_dsml_marker"],
                ]
                for m in methods
            ],
        ),
        "首轮开发暴露两项协议问题：自主提示中 finish 包装与裸答案格式要求冲突；收到的 JSON action 后混入 DSML 标记。最终题保持未运行，先保留首轮全部记录，再修正提示，并在第二轮开发中增加明确格式归一化：只取开头完整 JSON 对象、丢弃且不执行 DSML 后缀；完整裸答案包装为 finish，仍检查已读文献与真实引用。不会把模拟工具输出作为证据。",
        "第二轮仍记录完整原回复、最初解析错误和归一化说明，因此初始 JSONDecodeError 不必然等于最终流程失败；请结合状态和动作适配次数。第一轮失败未被覆盖，第二轮三臂完整重跑后才冻结最终方法。收到的 DSML 文本不能判定问题来自底层模型还是网关转换，也不等于医学推理错误。",
        "三臂分数同时反映输出合同/适配、完成率和关系判断；原生工具调用的其他实现未在本轮比较。因此规定流程若领先，不能把全部差距归因于 Agent 推理结构，也不能外推为强模型自主工具能力的上限。",
        "![三臂工作流与成本](assets/v07-workflow-comparison.png)",
        table(
            ["结构化 − 对照", "错误接受率差值 95% CI", "支持召回差值 95% CI"],
            [
                [m, ci(r["false_acceptance_rate"]), ci(r["support_recall"])]
                for m, r in final["paired_differences"].items()
            ],
        ),
        "按 40 来源组配对 bootstrap，2,000 次，seed 260926。区间退化和小类分母均需保留；点估计领先不等于证实结构有效。",
        "### 实际成本与保留的原答",
        table(
            [
                "方法",
                "目标论文读到",
                "原草稿二分类正确",
                "需复核",
                "调用 / 题",
                "已报告 tokens / 题",
                "均秒 / 题",
            ],
            [
                [
                    m,
                    f"{final['methods'][m]['workflow_counts']['target_read']}/40",
                    f"{final['methods'][m]['original_draft']['counts']['correct']}/40",
                    final["methods"][m]["workflow_counts"]["needs_review"],
                    round(final["methods"][m]["workflow_counts"]["model_calls"] / 40, 2),
                    round(final["methods"][m]["workflow_counts"]["reported_tokens"] / 40),
                    round(final["methods"][m]["workflow_counts"]["sum_elapsed_seconds"] / 40, 1),
                ]
                for m in methods
            ],
        ),
        "原草稿表保留被核查器拒绝的答案；它和最终可接受结果不是同一指标。逐调用输出、证据句 ID、工具参数、返回内容和模型标识均在原始记录。耗时为端到端逐题时间，不能用 API token 数推算本地 GPU 或货币成本。",
        "规定流程比直接读取使用更少已报告 tokens，但逐题延迟更长，支持召回也更低；这些是不同维度，不能只按调用次数或 token 单项宣布更便宜、更好。直接阅读与自主工具二分类分数相同，三分类逐题输出并非完全相同。",
        "### 四个需复核项究竟是什么",
        table(
            ["最终 case", "公开关系", "原草稿", "核查器", "含义"],
            [
                [
                    "scifact-train-788-4740447",
                    "supported",
                    "supported",
                    "insufficient",
                    "已正确支持的原答被保留",
                ],
                [
                    "scifact-train-296-4398832",
                    "supported",
                    "supported",
                    "insufficient",
                    "已正确支持的原答被保留",
                ],
                [
                    "scifact-train-1229-1676568",
                    "supported",
                    "supported",
                    "insufficient",
                    "已正确支持的原答被保留",
                ],
                [
                    "scifact-train-790-15493354",
                    "contradicted",
                    "insufficient",
                    "contradicted",
                    "核查器指出三分类差异；二分类原答已属非支持",
                ],
            ],
        ),
        "四条原答在合并非支持的二分类中均正确，但只有前三条精确匹配公开三分类标签。不能把第四条核查一概叫误报，也不能把弃权计为已纠正答案。它保留了原答等待审阅，没有自动修改。完整原答与来源见 [40 题逐题记录](verification-v0.7-cases.md)。",
        "## 开发集另列：第二轮协议",
        table(
            ["方法", "二分类正确 / 全题", "完成", "非支持被接受", "支持召回"],
            [
                [
                    m,
                    f"{development['methods'][m]['accepted']['counts']['correct']}/20",
                    f"{development['methods'][m]['accepted']['counts']['completed']}/20",
                    f"{development['methods'][m]['accepted']['counts']['false_accept']}/{development['methods'][m]['accepted']['counts']['nonsupport']}",
                    f"{development['methods'][m]['accepted']['counts']['true_accept']}/{development['methods'][m]['accepted']['counts']['support']}",
                ]
                for m in methods
            ],
        ),
        "这些题用于观察实现及冻结决定，不与最终 40 题合并提升样本量。展示页的三道回放在运行前按 seed 选自开发题；不代表三道最佳案例。",
        "### 保留的首轮开发：协议问题",
        table(
            ["方法", "完成 / 20", "二分类正确 / 20", "含 DSML 回复"],
            [
                [
                    m,
                    original["methods"][m]["accepted"]["counts"]["completed"],
                    original["methods"][m]["accepted"]["counts"]["correct"],
                    original["methods"][m]["workflow_counts"]["replies_with_dsml_marker"],
                ]
                for m in methods
            ],
        ),
        "首轮自主臂 0/20 完成暴露的是当前提示/适配缺陷，不能作为强模型自主工具能力的有效上限。第二轮未增加论文、标签、工具权限或调用上限；不是按题挑选两轮最好结果。原始清单、完整回复与首次分数见 [development-original](../data/verification/v07/development-original/metrics.json)。所有开发观察已曝光，仅最终 40 来源承担冻结后的独立比较。",
        "## 如何解释及继续研究",
        "本实验能回答：在已知目标论文、固定小候选库和固定 Flash 配置下，规定流程如何改变支持关系判断、保留率与成本。它不能单独回答：完整医学 Agent 是否胜过强模型自由使用全部生产工具。",
        "仍保留 Direct 审计默认。自动答案修复与审计驱动的开放补检索没有作为已证明有效的功能上线：v0.6 暴露了核查误报与限定词损失，强行把核查器输出作为修复目标可能损害正确内容。后续先扩展未指定论文、需要补找证据的独立任务，再测每一步的作用；本次最终集合已曝光，只能做回归。",
        "## 复现、原始记录与演示",
        "[全部原始输出和冻结清单](../data/verification/v07/README.md) · [离线重算与另存新运行](research-reproduction.md) · [产品演示](research-demo.md) · [实施协议](plans/v0.7-agent-comparison.md)。",
        "标签来源为 [SciFact 官方数据格式](https://github.com/allenai/scifact/blob/master/doc/data.md)。引用文献无标注依据仅作该摘要信息不足，不是全球无证据。公共数据训练污染、标题提示、固定干扰、单模型和小组数均限制泛化。",
    ]
    (ROOT / "docs/verification-v0.7-report.md").write_text(
        "\n\n".join(lines) + "\n", encoding="utf8"
    )


if __name__ == "__main__":
    require_complete()
    v06_report()
    v07_report()
    print("Wrote the two milestone research reports from complete saved experiments")
