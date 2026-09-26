"""Offline same-table comparison and advisory numeric-rule accounting."""

from collections import Counter
import json

from medrag.verification.scifact import read_jsonl
from v06_prepare import OUT
from v06_fixed import dump


def main():
    directory = OUT / "ablations"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf8"))
    original = {r["case_id"]: r["audit"] for r in manifest["rows"]}
    no_slots = read_jsonl(directory / "no_slots.jsonl")
    slot_counts = Counter()
    slot_details = []
    for row in no_slots:
        a = original[row["case_id"]]
        b = row.get("audit", {})
        left = {c["id"]: c for c in a["claims"]}
        right = {c["id"]: c for c in b.get("claims", [])}
        for key, c in left.items():
            other = right.get(key, {})
            slot_counts.update(
                planned_facts=1,
                both_completed=c["status"] == other.get("status") == "ok",
                relation_changed=c["relation"] != other.get("relation"),
                status_changed=c["status"] != other.get("status"),
            )
            slot_details.append(
                {
                    "case_id": row["case_id"],
                    "fact_id": key,
                    "with_slots": {"relation": c["relation"], "status": c["status"]},
                    "without_slots": {
                        "relation": other.get("relation"),
                        "status": other.get("status", "not_run"),
                    },
                }
            )
    flash = read_jsonl(directory / "flash.jsonl")
    mini = read_jsonl(directory / "minicheck.jsonl")
    by_mini = {(r["case_id"], f["fact_index"]): f for r in mini for f in r.get("facts", [])}
    comp = []
    counts = Counter()
    for r in flash:
        for f in r.get("facts", []):
            other = by_mini.get((r["case_id"], f["fact_index"]))
            a = f["result"]
            if other and f["input_sha256"] != other["input_sha256"]:
                raise ValueError("Checkers did not receive identical inputs")
            b = other["result"] if other else {}
            pa = int(a["decision"]["relation"] == "supported") if a["status"] == "ok" else None
            pb = b.get("binary_prediction") if b.get("status") == "ok" else None
            both = pa is not None and pb is not None
            counts.update(targets=1, both_completed=both, disagreed=both and pa != pb)
            comp.append(
                {
                    "case_id": r["case_id"],
                    "fact_index": f["fact_index"],
                    "flash": pa,
                    "minicheck": pb,
                    "raw_support_score": b.get("raw_support_score"),
                }
            )
    numeric = Counter(
        c.get("numeric_diagnostic", {}).get("status", "not_run")
        for r in manifest["rows"]
        for c in r["audit"]["claims"]
    )
    result = {
        "E2_same_standalone_targets": {
            "counts": dict(counts),
            "flash_statuses": dict(
                Counter(f["result"]["status"] for r in flash for f in r.get("facts", []))
            ),
            "minicheck_statuses": dict(
                Counter(f["result"]["status"] for r in mini for f in r.get("facts", []))
            ),
            "per_fact": comp,
            "interpretation": "Disagreement is not correctness; parsed targets have no independent semantic gold.",
        },
        "E4_explicit_slots": {
            "counts": dict(slot_counts),
            "per_fact": slot_details,
            "interpretation": "Changes on the same extraction, source and answer. More warnings are not automatically better.",
        },
        "E5_numeric_rules": {
            "on": dict(numeric),
            "off_advisory_flags": 0,
            "semantic_decisions_changed": 0,
            "interpretation": "Diagnostic only. Unresolved contexts are retained; no clinical contradiction or default change inferred.",
        },
    }
    dump(OUT / "ablation-metrics.json", result)
    print(json.dumps({k: v.get("counts", v) for k, v in result.items()}, indent=2))


if __name__ == "__main__":
    main()
