"""Offline comparison with public annotations; never an LLM judge."""
from collections import Counter
from statistics import mean, median

from .schema import GoldCase, Relation, bind_evidence, Decision


def score(cases: list[GoldCase], records: list[dict]) -> dict:
    by_id = {r["case_id"]: r for r in records}
    if len(by_id) != len(records):
        raise ValueError("Duplicate result IDs")
    expected = {c.input.case_id for c in cases}
    if not set(by_id) <= expected:
        raise ValueError("Unexpected result IDs")
    labels = [x.value for x in Relation]
    matrix = {label: {p: 0 for p in labels + ["error", "not_run"]} for label in labels}
    mismatches, statuses = [], Counter()
    rationale_matches = rationale_eligible = quote_bindings_ok = 0
    for case in cases:
        result = by_id.get(case.input.case_id, {"status": "not_run"})
        status = result["status"]
        statuses[status] += 1
        predicted = (result["decision"]["relation"] if status == "ok"
                     else "not_run" if status == "not_run" else "error")
        matrix[case.relation][predicted] += 1
        if predicted != case.relation:
            mismatches.append({"case_id": case.input.case_id, "gold": case.relation,
                               "predicted": predicted, "status": status})
        if status == "ok":
            decision = Decision.model_validate(result["decision"])
            spans = bind_evidence(case.input.document, decision)
            rebuilt = [s.model_dump(exclude={"text"}) for s in spans]
            quote_bindings_ok += bool(spans) and rebuilt == result["evidence"]
        if case.rationale_sets:
            rationale_eligible += 1
            if status == "ok":
                ids = set(result["decision"]["sentence_ids"])
                rationale_matches += predicted == case.relation and any(
                    ids == set(gold) for gold in case.rationale_sets)
    per_class = {}
    for label in labels:
        tp = matrix[label][label]
        actual = sum(matrix[label].values())
        predicted = sum(row[label] for row in matrix.values())
        precision = tp / predicted if predicted else None
        recall = tp / actual if actual else None
        f1 = 2 * tp / (actual + predicted) if actual + predicted else None
        per_class[label] = {"gold_count": actual, "predicted_count": predicted,
                            "correct_count": tp, "precision": precision,
                            "recall": recall, "f1": f1}
    elapsed = [r["elapsed_seconds"] for r in records if "elapsed_seconds" in r]
    usage = [r["usage"] for r in records if r.get("usage") is not None]
    total = len(cases)
    correct = sum(matrix[label][label] for label in labels)
    gold_unsupported = sum(sum(matrix[label].values()) for label in labels if label != "supported")
    accepted_unsupported = sum(matrix[label]["supported"] for label in labels if label != "supported")
    return {
        "total": total, "attempted": len(records), "statuses": dict(statuses),
        "correct": correct, "accuracy_all_cases": correct / total if total else None,
        "valid_output_coverage": statuses["ok"] / total if total else None,
        "confusion_matrix": matrix, "per_class": per_class,
        "macro_f1": mean(m["f1"] for m in per_class.values() if m["f1"] is not None),
        "unsupported_accepted": accepted_unsupported, "gold_unsupported": gold_unsupported,
        "false_acceptance_rate": accepted_unsupported / gold_unsupported if gold_unsupported else None,
        "label_and_exact_rationale_match": {"matched": rationale_matches, "eligible": rationale_eligible},
        "exact_source_bindings": {"matched": quote_bindings_ok,
                                  "eligible": sum(r["status"] == "ok" and bool(r["evidence"]) for r in records)},
        "latency_seconds": {"mean": mean(elapsed) if elapsed else None,
                            "median": median(elapsed) if elapsed else None,
                            "max": max(elapsed) if elapsed else None},
        "usage": {"reported_calls": len(usage), "attempted_calls": len(records),
                  "reported_token_totals": {k: sum(u[k] for u in usage if isinstance(u.get(k), int))
                                            for k in ("input_tokens", "output_tokens", "total_tokens")}
                  if usage else None},
        "mismatches": mismatches,
        "interpretation": "Public train development pilot; not independent clinical reliability or calibration. Exact rationale mismatch may reflect an alternative valid rationale.",
    }
