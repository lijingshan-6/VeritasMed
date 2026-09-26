"""Predeclare a conservative three-call Direct control using scheduled repeats."""

import argparse
import json

from medrag.verification.scifact import object_hash, read_jsonl
from v06_fixed import dump
from v06_prepare import OUT
from v06_whole import load_cases
from v06_whole_report import runtime_summary


def signal(audit):
    if audit.get("status") != "ok" or not audit.get("claims") or audit.get("claims_at_cap"):
        return "needs_review"
    claims = audit["claims"]
    if any(c["status"] != "ok" for c in claims):
        return "needs_review"
    return (
        "alarm"
        if any(c["relation"] in ("contradicted", "insufficient") for c in claims)
        else "no_alarm"
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["prepare", "report"])
    args = p.parse_args()
    natural = json.loads((OUT / "natural.json").read_text(encoding="utf8"))
    ids = natural["repeat_ids"]
    protocol = {
        "case_ids": ids,
        "selection": "The same 12 sources already selected for E6; no new inference or outcome-based sample selection",
        "direct_control": "Use original + attempts 2 and 3. Only if all three complete and share answer-level alarm presence accept that signal. Otherwise needs_review. No majority vote, new judge, pooling spans or treating agreement as truth.",
        "atomic_control": "Use first atomic_v1 attempt only, with its existing at-most-three-call cap. Partial/unbound/still-compound/capped output remains needs_review.",
        "scope": "Budget control of answer-level alarm presence only; no claim-level semantic accuracy or assertion of complete auditing. Unmarked alarms are not all false positives.",
        "reason": "Medical development location-linked results suggest fewer errors accepted by decomposition. Inspect whether scheduled three-call Direct changes conservative alarm coverage; do not infer gains from extra calls alone.",
    }
    path = OUT / "budget-protocol.json"
    if args.action == "prepare":
        if (OUT / "whole/repeat/predictions.jsonl").exists():
            raise ValueError("Declare budget control before repeated outputs exist")
        if path.exists() and json.loads(path.read_text(encoding="utf8")) != protocol:
            raise ValueError("Budget protocol changed")
        dump(path, protocol)
        print("Predeclared Direct-three agreement control on the existing 12-source repeat list")
        return
    if json.loads(path.read_text(encoding="utf8")) != protocol:
        raise ValueError("Frozen budget control changed")
    cases = {c["id"]: c for c in load_cases("natural")}
    rows = read_jsonl(OUT / "whole/natural/predictions.jsonl") + read_jsonl(
        OUT / "whole/repeat/predictions.jsonl"
    )
    details = []
    used = {"direct_three": [], "atomic_first": []}
    for case_id in ids:
        direct = [r for r in rows if r["case_id"] == case_id and r["method"] == "direct"]
        atom = [
            r
            for r in rows
            if r["case_id"] == case_id and r["method"] == "atomic_v1" and r["attempt"] == 1
        ]
        if len(direct) != 3 or len(atom) != 1:
            raise ValueError("Finish all scheduled repeats before scoring")
        values = [signal(r["audit"]) for r in direct]
        agreed = (
            values[0] if len(set(values)) == 1 and values[0] != "needs_review" else "needs_review"
        )
        used["direct_three"].extend(direct)
        used["atomic_first"].extend(atom)
        details.append(
            {
                "case_id": case_id,
                "public_errors": len(cases[case_id]["gold_spans"]),
                "direct_signals": values,
                "direct_three": agreed,
                "atomic_first": signal(atom[0]["audit"]),
            }
        )
    methods = {}
    for method in used:
        methods[method] = {
            "planned": len(ids),
            "alarm": sum(d[method] == "alarm" for d in details),
            "no_alarm": sum(d[method] == "no_alarm" for d in details),
            "needs_review": sum(d[method] == "needs_review" for d in details),
            "annotated_error_answers": sum(d["public_errors"] > 0 for d in details),
            "alarms_on_annotated_error_answers": sum(
                d["public_errors"] > 0 and d[method] == "alarm" for d in details
            ),
            "unmarked_answers": sum(d["public_errors"] == 0 for d in details),
            "alarms_on_unmarked_answers": sum(
                d["public_errors"] == 0 and d[method] == "alarm" for d in details
            ),
            "runtime": runtime_summary(used[method]),
        }
    dump(
        OUT / "budget-metrics.json",
        {
            "protocol_sha256": object_hash(protocol),
            "methods": methods,
            "details": details,
            "scope": protocol["scope"],
        },
    )
    print(json.dumps(methods, indent=2))


if __name__ == "__main__":
    main()
