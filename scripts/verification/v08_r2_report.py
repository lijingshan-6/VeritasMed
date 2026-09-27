"""Summarize saved R2 calls, with source-group paired descriptive intervals."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import statistics

from v08_r2_metrics import score

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/verification/v08/r2"
METHODS = ["direct", "atomic_v1", "atomic_v2"]


def object_hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf8")).hexdigest()


def phase_records(phase, cases, manifest_sha):
    """Recompute metrics from saved judgments, respecting the frozen schedule.

    A duplicate cannot stand in for a missing job. Cached metrics are checked,
    not silently trusted or overwritten; this function makes no model calls.
    """
    protocol = json.loads((OUT / phase / "protocol.json").read_text(encoding="utf8"))
    if protocol["phase"] != phase or protocol["manifest_sha256"] != manifest_sha:
        raise ValueError(f"{phase}: input manifest differs from the saved protocol")
    metric_path = "scripts/verification/v08_r2_metrics.py"
    if object_hash((ROOT / metric_path).read_text(encoding="utf8")) != protocol["code_hashes"][metric_path]:
        raise ValueError("Metric definition differs from the frozen run; use its original source")
    if phase == "final":
        frozen = json.loads((OUT / "method-freeze.json").read_text(encoding="utf8"))
        if frozen["manifest_sha256"] != manifest_sha or frozen["code_hashes"] != protocol["code_hashes"]:
            raise ValueError("Final protocol differs from the pre-inference freeze")
    def key(row):
        return row["case_id"], row["method"], row["attempt"]
    schedule = {key(job) for job in protocol["schedule"]}
    if len(schedule) != len(protocol["schedule"]):
        raise ValueError(f"{phase}: duplicate scheduled job")
    file = OUT / phase / "predictions.jsonl"
    if not file.exists():
        return [], len(schedule)
    records, seen = [], set()
    with file.open(encoding="utf8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            job = key(row)
            if job not in schedule or job in seen:
                raise ValueError(f"{phase}: duplicate or unscheduled prediction {job}")
            seen.add(job)
            case, audit = cases[row["case_id"]], row["audit"]
            expected_input = object_hash(case["input"])
            if row["input_sha256"] != expected_input or case["input_sha256"] != expected_input:
                raise ValueError(f"{job}: input fingerprint mismatch")
            if row["group_id"] != case["group_id"] or audit["strategy"] != row["method"]:
                raise ValueError(f"{job}: wrong source group or audit method")
            def text_hash(text):
                return hashlib.sha256(text.encode("utf8")).hexdigest()
            if (audit["answer_sha256"] != text_hash(case["input"]["answer"])
                    or audit["source_hashes"] != {s["id"]: text_hash(s["text"]) for s in case["input"]["sources"]}):
                raise ValueError(f"{job}: audit belongs to different answer/source texts")
            recomputed = score(case, audit)
            if recomputed != row["metrics"]:
                raise ValueError(f"{job}: cached metrics differ from the frozen scoring rule")
            records.append({**row, "metrics": recomputed})
    return records, len(schedule)


def counts(records, cases):
    targets = [t for r in records for t in r["metrics"]["targets"]]
    negative_ids = {
        (c["id"], t["id"]) for c in cases.values() for t in c.get("targets", [])
        if t.get("kind") == "negation" or t.get("literal_value") is None
    }
    negative = [t for r in records for t in r["metrics"]["targets"]
                if (r["case_id"], t["target_id"]) in negative_ids]
    errors = [t for t in targets if t["deliberate_error"]]
    calls = [call for r in records for call in r["audit"]["calls"]]
    claims = [c for r in records for c in r["audit"]["claims"]]
    natural = [r for r in records if cases[r["case_id"]]["split"] == "natural"]
    return {
        "answers": len(records),
        "source_groups": len({r["group_id"] for r in records}),
        "completed_answers": sum(r["metrics"]["completed_answer"] for r in records),
        "answers_at_claim_cap": sum(bool(r["audit"].get("claims_at_cap")) for r in records),
        "answer_statuses": dict(Counter(r["audit"]["status"] for r in records)),
        "claim_statuses": dict(Counter(c["status"] for c in claims)),
        "targets": len(targets),
        "anchors": sum(t["anchor_count"] for t in targets),
        "covered_anchors": sum(t["covered_anchors"] for t in targets),
        "joint_targets": sum(bool(t["joint_claim_ids"]) for t in targets),
        "completed_joint_targets": sum(bool(t["completed_claim_ids"]) for t in targets),
        "literal_targets": sum(t["literal_value_in_interpretation"] is not None for t in targets),
        "literal_preserved": sum(t["literal_value_in_interpretation"] is True for t in targets),
        "negation_targets": len(negative),
        "negation_joint": sum(bool(t["joint_claim_ids"]) for t in negative),
        "constructed_error_controls": len(errors),
        "error_literal_preserved": sum(t["literal_value_in_interpretation"] is True for t in errors),
        "error_warned": sum(any(v != "supported" for v in t["completed_relations"]) for t in errors),
        "error_supported_only": sum(bool(t["completed_relations"]) and all(v == "supported" for v in t["completed_relations"]) for t in errors),
        "error_unassessed": sum(not t["completed_relations"] for t in errors),
        "duplicate_flags": sum(r["metrics"]["duplicate_flags"] for r in records),
        "compound_or_uncertain": sum(r["metrics"]["compound_or_uncertain"] for r in records),
        "natural_marked_spans": sum(r["metrics"]["natural_gold_spans"] for r in records),
        "natural_overlapped_spans": sum(r["metrics"]["natural_marked_spans_overlapped"] for r in records),
        "natural_marked_answers": sum(bool(r["metrics"]["natural_gold_spans"]) for r in records),
        "natural_marked_answers_warned": sum(bool(r["metrics"]["natural_gold_spans"]) and r["metrics"]["has_completed_warning"] for r in records),
        "natural_unmarked_answers": sum(not r["metrics"]["natural_gold_spans"] for r in natural),
        "natural_unmarked_answers_warned": sum(not r["metrics"]["natural_gold_spans"] and r["metrics"]["has_completed_warning"] for r in natural),
        "calls": len(calls),
        "calls_with_usage": sum(bool(c.get("usage")) for c in calls),
        "reported_tokens": sum((c.get("usage") or {}).get("total_tokens", 0) or 0 for c in calls),
        "sum_audit_seconds": round(sum(r["audit"]["elapsed_seconds"] for r in records), 3),
        "median_audit_seconds": statistics.median(r["audit"]["elapsed_seconds"] for r in records) if records else None,
    }


def group_score(records, metric):
    targets = [t for r in records for t in r["metrics"]["targets"]]
    if metric == "completed_answers":
        return sum(r["metrics"]["completed_answer"] for r in records) / len(records)
    if metric == "anchor_coverage":
        return sum(t["covered_anchors"] for t in targets) / sum(t["anchor_count"] for t in targets)
    if metric == "joint_targets":
        return sum(bool(t["joint_claim_ids"]) for t in targets) / len(targets)
    if metric == "completed_joint_targets":
        return sum(bool(t["completed_claim_ids"]) for t in targets) / len(targets)
    if metric == "literal_preserved":
        numeric = [t for t in targets if t["literal_value_in_interpretation"] is not None]
        return sum(t["literal_value_in_interpretation"] for t in numeric) / len(numeric)
    raise ValueError(metric)


def paired(records):
    groups = defaultdict(lambda: defaultdict(list))
    for record in records:
        groups[record["group_id"]][record["method"]].append(record)
    output = {}
    for candidate in METHODS[1:]:
        complete = [g for g in groups.values() if len(g[candidate]) == len(g["direct"]) == 4]
        result = {}
        for metric in ["anchor_coverage", "joint_targets", "completed_joint_targets",
                       "literal_preserved", "completed_answers"]:
            delta = [group_score(g[candidate], metric) - group_score(g["direct"], metric) for g in complete]
            if not delta:
                continue
            rng = random.Random("v08-r2-paired-" + candidate + metric)
            samples = sorted(statistics.mean(rng.choices(delta, k=len(delta))) for _ in range(10000))
            result[metric] = {"source_groups": len(delta), "candidate_minus_direct": statistics.mean(delta),
                              "percentile_95": [samples[249], samples[9749]]}
        output[candidate] = result
    return output


def markdown(result):
    if result["status"] != "completed":
        raise ValueError("Do not publish a completed report before all scheduled attempts exist")
    names = {"direct": "Direct", "atomic_v1": "Atomic v1", "atomic_v2": "Atomic v2"}
    lines = [
        "# v0.8：限定语可追溯，不等于语义可靠性升级",
        "",
        "v0.8 完成对话产品、父句范围定位和限定语诊断。**Direct / Flash 保持默认**。",
        "Atomic v2 把更多解释条件接回原文，也增加了需要查看的提取状态。",
        "这里没有新的专家 gold，不据构造题或字符共现宣称医学核查准确率提高。",
        "",
        "本报告由保存的输出重算；[协议与清单](../../data/verification/v08/r2/README.md)、",
        "[完整汇总](../../data/verification/v08/r2/summary.json)、",
        "[六例 AI 开发复核](verification-v0.8-extraction-review.md)可逐项查看。",
        "",
        "## 研究分层与默认决定",
        "",
        "- R1：167 次历史审计、1,203 个事实；可定位 1,097 → 1,179，82 项恢复，0 项退步，24 项仍未解决。",
        "  只重放位置，没有模型调用或新增语义判断。[定位明细](verification-v0.8-localization.md)。",
        "- R2：24 个此前未使用来源组，每组 4 个变体，共 96 个构造回答（含 24 个故意数字错误）。",
        "  12 组开发、12 组最终；另有 12 个 RAGTruth train 自然回答、6 个预选输入的 Direct/v2 三次重复。",
        "- R3：盘点后只剩 1 对未曝光公开 SciFact 标签，且为 insufficient；不足以做新三类语义泛化比较。",
        "  暂缓该研究，不用 AI 自判补 gold。[来源盘点](verification-v0.8-exposure.md)。",
        "",
        "六个来源包含显式否定目标。研究作者看过构造输入，最终模型输出在候选冻结后才生成；",
        "这不是输入对开发者盲法的外部测试。来源按文献关联组隔离，四个变体不能当作四篇独立论文。",
        "自然样本按有/无标错各取六个，不代表自然错误发生率。60 个官方 test 来源继续保留。",
        "",
        "只开发一个 v2 候选，没有为正结果做第二轮提示或条件放宽。所有调用及失败保留，",
        "Direct 最多一次调用，Atomic 最多三次 / 48 个事实；Flash-only，并发不超过三，SDK retries 为零。",
        "原始 v1 和历史结果没有被覆盖。固定模型、数据与规则后，最终区仅运行预定的一次。",
        "",
        "## 构造回答的机械诊断",
        "",
        "**各列含义不能混淆**：锚点覆盖是预标注短语能否被定位；同项共现是一个 claim 的片段/限定语",
        "包含目标全部锚点；数字保留还要求该项解释中有原数字。数字列的前提是同项共现，",
        "不是独立的数字识别率。一个 Direct 引用段可较长，v2 则按设计返回额外限定语。",
        "这样的结构收益不能直接解释成组别—数值语义映射正确。",
        "完整完成指本次返回的核查项均完成，不保证没有漏提取。达到声明的事实数量上限也不能证明穷尽。",
        "三种方法的提取合同不同；v2 将部分无锚点或缺字面数字的项列为 needs_review，因此完成率",
        "也反映新增规则带来的复核负担，不能直接作为三者语义准确率的排名。",
        "",
    ]
    for phase, label in [("development", "开发"), ("final", "冻结后的最终区")]:
        lines += [
            "### " + label, "",
            "| 方法 | 完整完成回答 | 锚点覆盖 | 同项共现目标 | 完成核查且共现 | 数字与条件保留 |",
            "|---|---|---|---|---|---|",
        ]
        for method in METHODS:
            c = result["phases"][phase]["methods"][method]
            lines.append(
                f"| {names[method]} | {c['completed_answers']}/{c['answers']} | "
                f"{c['covered_anchors']}/{c['anchors']} | {c['joint_targets']}/{c['targets']} | "
                f"{c['completed_joint_targets']}/{c['targets']} | "
                f"{c['literal_preserved']}/{c['literal_targets']} |"
            )
        lines += [
            "",
            "| 方法 | 否定目标共现 | 错误对照：完整锚点警报 | 同条件下仅 supported | 未覆盖全部条件或未完成 |",
            "|---|---|---|---|---|",
        ]
        for method in METHODS:
            c = result["phases"][phase]["methods"][method]
            lines.append(
                f"| {names[method]} | {c['negation_joint']}/{c['negation_targets']} | "
                f"{c['error_warned']}/{c['constructed_error_controls']} | "
                f"{c['error_supported_only']}/{c['constructed_error_controls']} | "
                f"{c['error_unassessed']}/{c['constructed_error_controls']} |"
            )
        lines.append("")
    lines += [
        "错误对照表也要求目标的全部锚点进入同一条已完成事实。因此，最后一列可能包括已经警报",
        "错误数字、但没有同时引用另一句条件的 Direct 输出；它不等于模型完全没发现错误。",
        "警报可以是 contradicted 或 insufficient。构造预期来自作者的文本变换，不是独立临床标签。",
        "",
        "## 来源组配对区间",
        "",
        "以下为最终区候选减 Direct，单位为百分点。10,000 次固定种子来源组 bootstrap，",
        "每组四变体一起抽样，各来源组权重相等。区间仅描述这个小样本；未作多重比较校正。",
        "",
        "| 候选 | 锚点覆盖差 [95% 区间] | 同项共现差 | 完成且共现差 | 数字与条件保留差 | 回答完整完成差 |",
        "|---|---|---|---|---|---|",
    ]
    for method, metrics in result["phases"]["final"]["paired_source_intervals"].items():
        cells = []
        for metric in ["anchor_coverage", "joint_targets", "completed_joint_targets", "literal_preserved", "completed_answers"]:
            m = metrics[metric]
            lo, hi = m["percentile_95"]
            cells.append(f"{100*m['candidate_minus_direct']:+.1f} [{100*lo:+.1f}, {100*hi:+.1f}]")
        lines.append("| " + names[method] + " | " + " | ".join(cells) + " |")
    lines += [
        "",
        "表中的共现指标不能作为“错误放行降低、正确支持召回不下降”的默认升级条件。",
        "缺少合格的新语义比较，因此无论机械指标多高，都不据此升级默认策略。",
        "",
        "## 自然回答开发样本",
        "",
        "| 方法 | 完整完成 | 有标错回答出现警报 | 标错片段被警报范围覆盖 | 无标错回答出现警报 |",
        "|---|---|---|---|---|",
    ]
    for method in METHODS:
        c = result["phases"]["natural"]["methods"][method]
        lines.append(
            f"| {names[method]} | {c['completed_answers']}/{c['answers']} | "
            f"{c['natural_marked_answers_warned']}/{c['natural_marked_answers']} | "
            f"{c['natural_overlapped_spans']}/{c['natural_marked_spans']} | "
            f"{c['natural_unmarked_answers_warned']}/{c['natural_unmarked_answers']} |"
        )
    lines += [
        "",
        "警报范围与标错相交可能只是更长引用或限定语覆盖；不代表抓到了具体错误。",
        "无标错回答的警报不自动等于假阳性。本版自然样本是开发诊断，不充当独立最终可靠性分数。",
        "额外 AI 阅读记录了警方消息归因、职业角色泛化和屏幕人物的共同分歧；既有公开标签和分母",
        "均未改写，见[开发复核](verification-v0.8-extraction-review.md)。模型一致不能代替标注裁定。",
        "",
        "## 重复与实际资源",
        "",
        "六个输入在第一次结果出现前固定，每个方法共三次。以下保留完成状态与逐目标共现警报的变化，",
        "不通过多数票生成正确答案。完整逐目标序列见汇总 JSON。",
        "",
        "| 输入 | 方法 | 三次状态 | 逐目标完成关系是否一致 |",
        "|---|---|---|---|",
    ]
    for row in result["repeat_variability"]:
        signatures = {json.dumps(a["target_relations"], sort_keys=True) for a in row["attempts"]}
        lines.append(f"| {row['case_id']} | {names[row['method']]} | "
                     + " / ".join(a["status"] for a in row["attempts"])
                     + f" | {'一致' if len(signatures) == 1 else '有变化'} |")
    lines += ["", "| 阶段 | 方法 | 调用数 | 有用量的调用 | 报告 token | 单次审计中位秒 | 事实数触顶回答 |", "|---|---|---|---|---|---|---|"]
    for phase in ["development", "natural", "repeat", "final"]:
        for method in METHODS:
            c = result["phases"][phase]["methods"][method]
            if not c["answers"]:
                continue
            lines.append(f"| {phase} | {names[method]} | {c['calls']} | {c['calls_with_usage']} | "
                         f"{c['reported_tokens']:,} | {c['median_audit_seconds']:.1f} | {c['answers_at_claim_cap']}/{c['answers']} |")
    lines += [
        "",
        f"共 {result['all_recorded_calls']} 次审计内模型调用，供应商报告 {result['all_reported_tokens']:,} token。",
        "这不包括上下文诊断和医学 Ask 演示，也不是按价格换算的账单；缺失用量不冒充零用量。",
        "审计耗时包含其顺序调用。并行执行时，耗时加总不等于实际墙钟时间。",
        "",
        "## 交付与仍未证明的部分",
        "",
        "产品保留对话、答案版本、原文与逐次审计；Atomic v2 的父句、片段和限定语可联动查看。",
        "字面数字规则会增加不必要的待查看，例如统计模型拆成多个 predictor 后省去同一年龄范围；",
        "无警报也可能漏条件。六例阅读对此给出具体观察，但不能替代独立专家标签。",
        "",
        "三组真实医学对话另外保存，问题在推理前固定。第二组的单数指代没有触发澄清，模型回答了",
        "两项研究的时长。第三组最后一轮只引用时长、没有完整回答死亡率子问题，界面保留部分覆盖。",
        "第二组还把“不要比较疗效”的写作约束误当证据缺口，产生多余的部分覆盖标签。",
        "这些边界原样保留，医学演示不计入 R2。Direct 审计通过也不代表回答满足了整个问题。",
        "",
        "后续需要新的语义标签和明确的失败任务，才能比较提取保真、补检索和修复。",
        "目前不发布校准可信度百分比、不自动裁决跨研究冲突、不以核查器自己的判断证明修复有效。",
        "",
        "[对话指南](../conversation-guide.md) · [版本说明](../releases/v0.8.0.md) · [复现](../research-reproduction.md)",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT / "summary.json")
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf8"))
    cases = {c["id"]: c for c in manifest["cases"] + manifest["natural_cases"]}
    phases = {}
    all_rows = []
    phase_rows = {}
    for phase in ("development", "natural", "repeat", "final"):
        records, expected = phase_records(phase, cases, object_hash(manifest))
        phase_rows[phase] = records
        all_rows.extend(records)
        phases[phase] = {
            "planned": expected, "recorded": len(records),
            "methods": {m: counts([r for r in records if r["method"] == m], cases) for m in METHODS},
        }
        if phase in {"development", "final"}:
            phases[phase]["paired_source_intervals"] = paired(records)
    repeats = []
    for case_id in manifest["repeat_case_ids"]:
        for method in manifest["repeat_methods"]:
            records = [r for r in phase_rows["development"] + phase_rows["repeat"]
                       if r["case_id"] == case_id and r["method"] == method]
            records.sort(key=lambda r: r["attempt"])
            repeats.append({"case_id": case_id, "method": method, "attempts": [
                {"attempt": r["attempt"], "status": r["audit"]["status"],
                 "target_relations": [t["completed_relations"] for t in r["metrics"]["targets"]],
                 "target_joint": [bool(t["joint_claim_ids"]) for t in r["metrics"]["targets"]]}
                for r in records]})
    result = {
        "status": "completed" if all(v["planned"] == v["recorded"] for v in phases.values()) else "in_progress",
        "scope": "AI-authored textual diagnostics, not expert gold or semantic generalization. R3 deferred; Direct/Flash remains default.",
        "interval_method": "10000 deterministic paired bootstrap resamples of source groups; equal group weight, all four variants together. Descriptive small-sample percentile intervals; no multiple-comparison correction.",
        "latency_note": "Recorded audit duration includes its sequential calls; summed durations are not wall-clock elapsed because up to 3 audits overlap.",
        "phases": phases, "repeat_variability": repeats,
        "all_recorded_calls": sum(len(r["audit"]["calls"]) for r in all_rows),
        "all_reported_tokens": sum((c.get("usage") or {}).get("total_tokens", 0) or 0 for r in all_rows for c in r["audit"]["calls"]),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    if args.markdown:
        args.markdown.write_text(markdown(result), encoding="utf8", newline="\n")
    print(result["status"], {k: v["recorded"] for k, v in phases.items()})


if __name__ == "__main__":
    main()
