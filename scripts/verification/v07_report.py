"""Compare original and accepted workflow decisions against independent public labels."""

import argparse
from collections import Counter
import json
from pathlib import Path

from medrag.verification.research_metrics import fixed_metrics, paired_intervals
from medrag.verification.scifact import read_jsonl
from v06_fixed import dump
from v07_benchmark import V07, METHODS, load_tasks


def report(split, directory=None):
    tasks = load_tasks(split)
    entries = [e for e, t in tasks]
    gold = {e["case_id"]: e for e in entries}
    path = (directory or V07 / split) / "predictions.jsonl"
    protocol = json.loads((path.parent / "protocol.json").read_text(encoding="utf8"))
    rows = read_jsonl(path) if path.exists() else []
    result = {
        "split": split,
        "planned_queries": len(tasks),
        "task": "named-paper fixed-corpus claim verification",
        "action_protocol": protocol.get("action_protocol", "original_strict_json"),
        "methods": {},
    }
    for method in METHODS:
        selected = [r for r in rows if r["method"] == method]
        accepted = []
        drafts = []
        c = Counter()
        matrix = Counter()
        statuses = Counter()
        call_statuses = Counter()
        call_errors = Counter()
        adaptations = Counter()
        for row in selected:
            e = gold[row["case_id"]]
            r = row["result"]
            statuses[r["status"]] += 1
            call_statuses.update(call.get("status", "unknown") for call in r["calls"])
            call_errors.update(call["error_type"] for call in r["calls"] if call.get("error_type"))
            adaptations.update(
                note["kind"] for call in r["calls"] for note in call.get("action_adapter", [])
            )
            c["replies_with_dsml_marker"] += sum(
                "DSML" in str(call.get("raw_output", "")) for call in r["calls"]
            )
            answer = r.get("answer") if isinstance(r.get("answer"), dict) else {}
            correct_doc = answer.get("document_id") == e["document_id"]
            usable = bool(
                answer.get("relation") in ("supported", "contradicted", "insufficient")
                and correct_doc
            )
            raw = int(answer["relation"] == "supported") if usable else None
            accepted.append(
                {
                    "case_id": e["case_id"],
                    "status": "ok"
                    if r["status"] == "ok" and usable
                    else r["status"]
                    if r["status"] != "ok"
                    else "wrong_document",
                    "binary_prediction": raw,
                }
            )
            drafts.append(
                {
                    "case_id": e["case_id"],
                    "status": "ok"
                    if usable and r["status"] in ("ok", "needs_review", "verification_failed")
                    else "invalid_answer",
                    "binary_prediction": raw,
                }
            )
            c.update(
                target_read=e["document_id"] in r["read_document_ids"],
                model_calls=r["model_calls"],
                tool_calls=r["tool_calls"],
                needs_review=r["status"] == "needs_review",
                budget_exhausted=r["status"] == "budget_exhausted",
                correct_three_class=r["status"] == "ok"
                and correct_doc
                and answer.get("relation") == e["relation"],
            )
            c["reported_tokens"] += sum(
                (call.get("usage") or {}).get("total_tokens", 0) for call in r["calls"]
            )
            c["sum_elapsed_seconds"] += r["elapsed_seconds"]
            matrix[
                (
                    e["relation"],
                    answer.get("relation", "no_answer")
                    if r["status"] == "ok" and correct_doc
                    else r["status"]
                    if r["status"] != "ok"
                    else "wrong_document",
                )
            ] += 1
        result["methods"][method] = {
            "accepted": fixed_metrics(entries, accepted),
            "original_draft": fixed_metrics(entries, drafts),
            "workflow_counts": dict(c),
            "execution_statuses": dict(statuses),
            "call_statuses": dict(call_statuses),
            "call_error_types": dict(call_errors),
            "action_adaptations": dict(adaptations),
            "three_class_matrix": [
                {"gold": g, "prediction": p, "n": n} for (g, p), n in matrix.items()
            ],
        }
    result["paired_differences"] = {
        f"structured_minus_{m}": paired_intervals(
            result["methods"][m]["accepted"], result["methods"]["structured_workflow"]["accepted"]
        )
        for m in ("direct_reader", "autonomous_tools")
    }
    result["scope"] = (
        "Public source labels evaluate the specified paper relation, not every sentence of the generated explanation. Fixed candidate sets and named-paper questions do not establish broad Ask/clinical superiority."
    )
    result["protocol_diagnostic"] = (
        "Execution/call error breakdown was added during first development. Before final inference, a second development run repaired conflicting finish instructions and explicitly normalized a leading JSON object with discarded DSML suffix or a complete bare answer. Original replies and initial parse errors remain recorded; suffix content is never a tool result or model history. The first development run is retained separately. This is an application-protocol comparison, not isolated model reasoning."
    )
    dump(directory / "metrics.json" if directory else V07 / f"{split}-metrics.json", result)
    print(
        json.dumps(
            {
                m: {"accepted": r["accepted"]["counts"], "workflow": r["workflow_counts"]}
                for m, r in result["methods"].items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("split", choices=["development", "final"])
    p.add_argument("--run-dir", type=Path, help="Recompute a separately retained run in place")
    args = p.parse_args()
    report(args.split, args.run_dir)
