"""Reconstruct one saved audit with original sentences; entirely offline."""
import argparse
import json
from pathlib import Path

from medrag.verification.scifact import object_hash, prepare_pilot, read_jsonl
from medrag.verification.schema import Decision, bind_evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id")
    parser.add_argument("--cache", type=Path, default=Path(".benchmark-runtime/scifact"))
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    cases, manifest = prepare_pilot(args.cache)
    settings = json.loads((args.run / "run.json").read_text(encoding="utf-8"))
    if object_hash(manifest) != settings["manifest_sha256"]:
        raise ValueError("Source data do not match this run")
    case = next((c for c in cases if c.input.case_id == args.case_id), None)
    if case is None:
        parser.error("Case ID is not in the declared pilot")
    result = next((r for r in read_jsonl(args.run / "predictions.jsonl")
                   if r["case_id"] == args.case_id), None)
    bound = []
    if result and result["status"] == "ok":
        bound = [s.model_dump() for s in bind_evidence(case.input.document,
                                                      Decision.model_validate(result["decision"]))]
    print(json.dumps({"input": case.input.model_dump(), "prediction": result,
                      "resolved_evidence": bound, "reference_relation": case.relation,
                      "reference_rationale_sets": case.rationale_sets,
                      "note": "Reference annotations are used only for offline inspection, never model input."},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
