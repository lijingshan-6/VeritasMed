"""Explain complete saved context experiments with paired case tables; no model calls."""
import argparse
import hashlib
import json
from pathlib import Path

from context_benchmark import OLD, metrics_for, select_cases, write_json
from medrag.verification.scifact import object_hash, read_jsonl


def compact(text):
    return text.replace("|", "\\|").replace("\n", " ")


def matches_recorded_text_hash(data, expected):
    # The pre-run protocol recorded native Windows bytes. Git checks out JSONL as LF.
    # Accept only line-ending equivalents; all JSON text and record order stay exact.
    lf = data.replace(b"\r\n", b"\n")
    return expected in {hashlib.sha256(value).hexdigest() for value in (data, lf, lf.replace(b"\n", b"\r\n"))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path("data/verification/context_v1/run01"))
    parser.add_argument("--cache", type=Path, default=Path(".benchmark-runtime/ragtruth"))
    args = parser.parse_args()
    groups, manifest = select_cases(args.cache)
    protocol = json.loads((args.run / "protocol.json").read_text(encoding="utf8"))
    state = json.loads((args.run / "run.json").read_text(encoding="utf8"))
    rows = read_jsonl(args.run / "predictions.jsonl")
    def key(row):
        return row["group"], row["case_id"], row["strategy"]
    if "completed_utc" not in state or len(rows) != len(protocol["schedule"]) or sorted(map(key, rows)) != sorted(map(key, protocol["schedule"])):
        raise ValueError("Wait for every scheduled attempt; partial runs are not a completed comparison")
    if object_hash(manifest) != protocol["manifest_sha256"]:
        raise ValueError("Manifest changed")
    original_bytes = (OLD / "predictions.jsonl").read_bytes()
    if not matches_recorded_text_hash(original_bytes, protocol["old_predictions_sha256"]):
        raise ValueError("Original control output changed")
    saved = json.loads((args.run / "metrics.json").read_text(encoding="utf8"))
    original = [r for r in read_jsonl(OLD / "predictions.jsonl") if r["strategy"] == "direct"]
    lines = ["# Context 实验：逐回答对照", "", "全部样本是开发数据。警报与官方错误范围重叠衡量定位，不代表三分类语义正确。", "",
             "旧组 Direct 来自上轮，其余是本轮调用；新组 Direct / Context 同批次交错。所有引用来自保存工件，没有追加模型裁判。", ""]
    changes = []
    for group in ("regression", "development"):
        paired = {}
        for variant in ("direct", "context"):
            selected = original if group == "regression" and variant == "direct" else [r for r in rows if r["group"] == group and r["strategy"] == variant]
            computed = metrics_for(groups[group], selected)
            if computed != saved[group][variant]:
                raise ValueError("Saved metrics differ")
            paired[variant] = {r["case_id"]: r["audit"] for r in selected}
        lines += [f"## {group}", "", "| 回答 / 来源 | gold 数 | Direct 任意 / 半范围命中 | Context 任意 / 半范围命中 | 警报条数 D → C | 字符警报 D → C |", "|---|---:|---:|---:|---:|---:|"]
        details = {v: {c["response_id"]: c for c in saved[group][v]["per_answer"]} for v in paired}
        for case in groups[group]:
            case_id = case["id"]
            d, c = details["direct"][case_id], details["context"][case_id]
            lines.append(f"| {case_id} / {case['source_id']} | {len(case['gold_spans'])} | {d['hit_any']} / {d['hit_half']} | {c['hit_any']} / {c['hit_half']} | {d['flagged_claims']} → {c['flagged_claims']} | {d['predicted_characters']} → {c['predicted_characters']} |")
            changes.append({"group": group, "case_id": case_id, "source_id": case["source_id"],
                            "gold_spans": len(case["gold_spans"]), "direct": d, "context": c})
        lines += ["", "### 原始警报与标签", "", "无标注错误并不保证没有问题；这里保留每条警报供查阅，不将开发解释写回 gold。", ""]
        for case in groups[group]:
            case_id = case["id"]
            lines += [f"#### 回答 {case_id}", ""]
            if case["gold_spans"]:
                lines += [f"- 原 gold [{s['start']}:{s['end']}]：{compact(s['text'])}" for s in case["gold_spans"]]
            else:
                lines.append("- 原 gold：无标注错误。")
            for variant in ("direct", "context"):
                audit = paired[variant][case_id]
                flags = [c for c in audit["claims"] if c["status"] == "ok" and c["relation"] in ("contradicted", "insufficient")]
                lines.append(f"- {variant}：{audit['status']}；{len(flags)} 条警报。")
                for claim in flags:
                    lines += ["", f"> {compact(claim['quote'])}", "", f"{variant} / {claim['relation']}：{compact(claim['explanation'])}"]
                if audit.get("meta_text"):
                    lines += ["", f"{variant} 元文本路由：" + " / ".join(compact(m["quote"]) for m in audit["meta_text"]) + "。这不是来源支持判断。"]
            lines.append("")
    d, c = [saved["development"][v] for v in ("direct", "context")]
    conditions = {
        "half_span_recall_not_lower": c["counts"]["span_hit_half"] >= d["counts"]["span_hit_half"],
        "fewer_unmarked_answers_flagged": c["counts"]["false_positive_answers"] < d["counts"]["false_positive_answers"],
        "higher_character_f1": c["character_f1"] > d["character_f1"],
    }
    decision = {"predeclared_effect_conditions": conditions, "meets_predeclared_effect_conditions": all(conditions.values()),
                "execution_completeness": {"direct": d["counts"]["completed_answers"], "context": c["counts"]["completed_answers"],
                                           "expected_per_method": 24},
                "note": "The three predeclared effect conditions permit considering a candidate, not automatic promotion. Execution completeness is reported separately, not added to those conditions after seeing results. No clinical reliability or statistical superiority claim."}
    write_json(args.run / "paired_effects.json", {"cases": changes, "decision": decision,
               "original_control_lf_sha256": hashlib.sha256(original_bytes.replace(b"\r\n", b"\n")).hexdigest()})
    (args.run / "paired_cases.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf8")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
