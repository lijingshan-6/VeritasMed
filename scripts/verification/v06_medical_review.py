"""Post-hoc source-view sensitivity; original labels and primary scores remain intact."""

import json

from medrag.verification.scifact import object_hash, read_jsonl
from v06_fixed import dump
from v06_prepare import OUT
from v06_whole import load_cases
from v06_whole_report import constructed


def main():
    review = json.loads((OUT / "medical-label-review.json").read_text(encoding="utf8"))
    removed = {i["group_id"] for i in review["issues"]}
    cases = [c for c in load_cases("medical_development") if c["group_id"] not in removed]
    rows = read_jsonl(OUT / "whole/medical_development/predictions.jsonl")
    result = {
        "label_review_sha256": object_hash(review),
        "scope": "Post-hoc developer/AI source-view sensitivity. Frozen primary labels/results retained. Not independent semantic gold or new confirmatory evidence.",
        "excluded_groups": sorted(removed),
        "remaining_groups": len({c["group_id"] for c in cases}),
        "remaining_answers": len(cases),
        "methods": {
            m: constructed(
                cases, [r for r in rows if r["method"] == m and r["group_id"] not in removed]
            )
            for m in ("direct", "split", "atomic_v1")
        },
    }
    dump(OUT / "medical-label-sensitivity.json", result)
    print(json.dumps({m: r["counts"] for m, r in result["methods"].items()}, indent=2))


if __name__ == "__main__":
    main()
