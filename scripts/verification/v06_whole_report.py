"""Offline whole-answer diagnostics; location coverage is never called semantic accuracy."""

from collections import Counter
import json

from medrag.verification.ragtruth import score_answers
from medrag.verification.scifact import read_jsonl
from v06_whole import load_cases
from v06_prepare import OUT
from v06_fixed import dump


def spans(claim):
    return claim.get("answer_spans", [claim["answer_span"]] if claim.get("answer_span") else [])


def positions(text, ss):
    return {i for s in ss for i in range(s["start"], s["end"]) if not text[i].isspace()}


def runtime_summary(rows):
    audits = [r["audit"] for r in rows]
    calls = [c for a in audits for c in a.get("calls", [])]
    claims = [c for a in audits for c in a.get("claims", [])]
    usages = [(c.get("usage") or {}).get("total_tokens") for c in calls]
    return {
        "recorded_answers": len(rows),
        "audit_statuses": dict(Counter(a["status"] for a in audits)),
        "claim_statuses": dict(Counter(c["status"] for c in claims)),
        "decomposition_statuses": dict(
            Counter(c.get("decomposition_status", "not_applicable") for c in claims)
        ),
        "binding_states": {
            "parent": dict(
                Counter(c["parent_binding"]["status"] for c in claims if c.get("parent_binding"))
            ),
            "answer_fragment": dict(
                Counter(b["status"] for c in claims for b in c.get("answer_bindings", []))
            ),
            "evidence": dict(
                Counter(b["status"] for c in claims for b in c.get("evidence_bindings", []))
            ),
        },
        "answers_at_cap": sum(bool(a.get("claims_at_cap")) for a in audits),
        "logical_calls": len(calls),
        "reported_tokens": sum(t for t in usages if t is not None),
        "calls_without_token_usage": sum(t is None for t in usages),
        "sum_elapsed_seconds": sum(a.get("elapsed_seconds", 0) for a in audits),
        "note": "Latency is summed per-answer elapsed time, not batch wall time. Missing usage is not zero cost. Claim states and coverage do not measure semantic fidelity.",
    }


def constructed(cases, rows):
    by_id = {r["case_id"]: r["audit"] for r in rows}
    details = []
    c = Counter()
    numeric = Counter()
    for case in cases:
        audit = by_id.get(case["id"], {})
        claims = audit.get("claims", [])
        answer = case["input"].answer
        c.update(
            planned_answers=1,
            completed_answers=audit.get("status") == "ok",
            logical_calls=len(audit.get("calls", [])),
        )
        for claim in claims:
            numeric[claim.get("numeric_diagnostic", {}).get("status", "not_run")] += 1
        for fact in case["facts"]:
            target = positions(answer, [fact])
            extracted = positions(answer, [s for cl in claims for s in spans(cl)])
            related = [
                cl for cl in claims if len(positions(answer, spans(cl)) & target) * 2 >= len(target)
            ]
            judgments = {cl["relation"] for cl in related if cl["status"] == "ok"}
            prediction = next(iter(judgments)) if len(judgments) == 1 else None
            wrong = fact["relation"] != "supported"
            c.update(
                facts=1,
                non_supported_facts=wrong,
                supported_facts=not wrong,
                fully_located=target <= extracted,
                half_located=len(target & extracted) * 2 >= len(target),
                full_coverage_matching_relation=target
                <= positions(
                    answer,
                    [
                        s
                        for cl in claims
                        if cl["status"] == "ok" and cl["relation"] == fact["relation"]
                        for s in spans(cl)
                    ],
                ),
                location_matched_decisions=prediction is not None,
                wrong_fact_accepted=wrong and prediction == "supported",
                supported_fact_accepted=not wrong and prediction == "supported",
                unsupported_fact_flagged=wrong and prediction in ("contradicted", "insufficient"),
                exact_relation_match=prediction == fact["relation"],
            )
            details.append(
                {
                    "case_id": case["id"],
                    "group_id": case["group_id"],
                    "variant": case["variant"],
                    "gold_fact": fact,
                    "location_linked_prediction": prediction,
                    "matching_claim_ids": [cl["id"] for cl in related],
                    "full_extraction_coverage": target <= extracted,
                }
            )
    return {
        "counts": dict(c),
        "numeric_diagnostics": dict(numeric),
        "per_fact": details,
        "scope": "Authored source-grounded diagnostic facts; character-based matching may miss faithful parses or include broad assertions. These are location-linked judgments, not independent clinical/semantic accuracy.",
    }


def main():
    report = {}
    for dataset in ("medical_development", "medical_transfer", "natural"):
        path = OUT / "whole" / dataset / "predictions.jsonl"
        if not path.exists():
            continue
        cases = load_cases(dataset)
        rows = read_jsonl(path)
        result = {}
        for method in ("direct", "split", "atomic_v1"):
            selected = [r for r in rows if r["method"] == method]
            if dataset.startswith("medical_"):
                result[method] = constructed(cases, selected)
            else:
                flattened = []
                for r in selected:
                    # Give the old scorer every bound original fragment, not normalized text.
                    a = r["audit"]
                    flattened.append(
                        {
                            **r,
                            "audit": {
                                **a,
                                "claims": [
                                    {**c, "answer_span": s} for c in a["claims"] for s in spans(c)
                                ],
                            },
                        }
                    )
                result[method] = score_answers(cases, flattened)
                result[method]["caveat"] = (
                    "Unmarked alarms are not established false positives; span overlap is localization only. Original scorer field names retained for historical continuity."
                )
            result[method]["runtime"] = runtime_summary(selected)
        report[dataset] = result
    repeat = OUT / "whole/repeat/predictions.jsonl"
    if repeat.exists():
        rows = read_jsonl(OUT / "whole/natural/predictions.jsonl") + read_jsonl(repeat)
        ids = json.loads((OUT / "natural.json").read_text(encoding="utf8"))["repeat_ids"]
        stability = {}
        for method in ("direct", "atomic_v1"):
            changes = []
            for case_id in ids:
                records = [r for r in rows if r["case_id"] == case_id and r["method"] == method]
                alarms = [
                    {
                        i
                        for c in r["audit"]["claims"]
                        if c["status"] == "ok" and c["relation"] in ("contradicted", "insufficient")
                        for s in spans(c)
                        for i in range(s["start"], s["end"])
                    }
                    for r in records
                ]
                changes.append(
                    {
                        "case_id": case_id,
                        "completed_runs": len(records),
                        "alarm_presence_changed": len({bool(a) for a in alarms}) > 1,
                        "alarm_locations_changed": any(a != alarms[0] for a in alarms[1:])
                        if alarms
                        else None,
                        "statuses": [r["audit"]["status"] for r in records],
                    }
                )
            stability[method] = {
                "planned_sources": 12,
                "per_source": changes,
                "changed_alarm_presence": sum(c["alarm_presence_changed"] for c in changes),
                "changed_alarm_locations": sum(bool(c["alarm_locations_changed"]) for c in changes),
            }
        report["repeat"] = stability
    dump(OUT / "whole-metrics.json", report)
    print(
        json.dumps(
            {
                d: {m: r.get("counts", r.get("changed_alarm_presence")) for m, r in results.items()}
                for d, results in report.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
