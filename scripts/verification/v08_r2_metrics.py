"""Predeclared mechanical target coverage. Co-presence is NOT semantic mapping."""

import re


def claim_spans(claim):
    spans = list(
        claim.get("answer_spans") or ([claim["answer_span"]] if claim.get("answer_span") else [])
    )
    spans += [
        q["binding"]["span"] for q in claim.get("qualifier_anchors", []) if q["binding"].get("span")
    ]
    return spans


def covers(spans, anchor):
    # Required phrase may span adjacent quoted pieces; gaps inside it remain gaps.
    return any(
        all(any(s["start"] <= p < s["end"] for s in spans) for p in range(a["start"], a["end"]))
        for a in anchor["acceptable_spans"]
    )


def score(case, audit):
    claims = audit["claims"]
    all_spans = [s for c in claims for s in claim_spans(c)]
    targets = []
    for target in case.get("targets", []):
        joint = [c for c in claims if all(covers(claim_spans(c), a) for a in target["anchors"])]
        completed = [c for c in joint if c["status"] == "ok"]
        interpretations = [c.get("normalized_claim", c["quote"]) for c in joint]
        value = target["literal_value"]
        literal_preserved = (
            None
            if value is None
            else any(
                re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", t, re.I)
                for t in interpretations
            )
        )
        targets.append(
            {
                "target_id": target["id"],
                "anchor_count": len(target["anchors"]),
                "covered_anchors": sum(covers(all_spans, a) for a in target["anchors"]),
                "joint_claim_ids": [c["id"] for c in joint],
                "completed_claim_ids": [c["id"] for c in completed],
                "literal_value_in_interpretation": literal_preserved,
                "deliberate_error": target["deliberate_error"],
                "completed_relations": [c["relation"] for c in completed],
                "returned_relations": [c["relation"] for c in joint],
            }
        )
    warnings = [
        s
        for c in claims
        if c["status"] == "ok" and c["relation"] != "supported"
        for s in claim_spans(c)
    ]
    gold = case.get("gold_spans", [])
    return {
        "targets": targets,
        "completed_answer": audit["status"] == "ok" and bool(claims),
        "claim_count": len(claims),
        "completed_claims": sum(c["status"] == "ok" for c in claims),
        "duplicate_flags": sum(bool(c.get("duplicate_of")) for c in claims),
        "compound_or_uncertain": sum(
            c.get("decomposition_status", "atomic") != "atomic" for c in claims
        ),
        "natural_gold_spans": len(gold),
        "natural_marked_spans_overlapped": sum(
            any(max(s["start"], g["start"]) < min(s["end"], g["end"]) for s in warnings)
            for g in gold
        ),
        "has_completed_warning": bool(warnings),
        "scope": "Exact anchor coverage/co-presence and literal preservation, not semantic mapping or exhaustive truth. Unmarked natural warnings are not assumed false positives.",
    }
