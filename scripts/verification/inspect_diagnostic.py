"""View a controlled case, original sentence mapping and every saved arm offline."""
import argparse
import json
from pathlib import Path

from medrag.verification.diagnostics import load_diagnostics
from medrag.verification.scifact import object_hash, read_jsonl
from medrag.verification.schema import Decision, bind_evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id")
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path(".benchmark-runtime/scifact"))
    args = parser.parse_args()
    specification = Path("data/verification/controlled_v1/families.json")
    cases, manifest = load_diagnostics(args.cache, specification)
    protocol = json.loads((args.run / "protocol.json").read_text(encoding="utf-8"))
    if object_hash(manifest) != protocol["manifest_sha256"]:
        raise ValueError("Sources or construction differ from this run")
    case = next((c for c in cases if c.input.case_id == args.case_id), None)
    if case is None:
        parser.error("Unknown diagnostic case ID")
    provenance = next(c for c in manifest["cases"] if c["case_id"] == args.case_id)
    spec = json.loads(specification.read_text(encoding="utf-8"))
    family = next(f for f in spec["families"] if f["family_id"] == provenance["family_id"])
    outputs = []
    for row in read_jsonl(args.run / "predictions.jsonl"):
        if row["case_id"] != args.case_id:
            continue
        spans = []
        if row["status"] == "ok":
            for span in bind_evidence(case.input.document, Decision.model_validate(row["decision"])):
                spans.append({**span.model_dump(), "original_sentence_id": provenance["original_sentence_ids"][span.sentence_id]})
        outputs.append({"arm": row["arm"], "prediction": row, "resolved_evidence": spans})
    print(json.dumps({"claim": case.input.claim, "reference_relation": case.relation,
                      "reference_provenance": manifest["label_provenance"], "construction": family,
                      "provenance": provenance, "title": case.input.document.title,
                      "text_view": [{"id": i, "original_sentence_id": provenance["original_sentence_ids"][i], "text": text}
                                    for i, text in enumerate(case.input.document.sentences)],
                      "outputs": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
