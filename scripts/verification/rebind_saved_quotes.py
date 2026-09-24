"""Binding-only counterfactual on saved outputs. No inference, prompt effect or label changes."""
from collections import Counter
import json
from pathlib import Path

from context_benchmark import select_cases, write_json
from medrag.verification.answer_audit import text_hash
from medrag.verification.quote_audit import QuoteOutput, bind_quote_claim, locate_quote
from medrag.verification.scifact import read_jsonl


def compact_binding(binding):
    # Avoid duplicating the same quoted text in span + candidates for every successful match.
    return {"status": binding["status"], "match_count": binding["match_count"],
            "candidate_offsets": [[s["start"], s["end"]] for s in binding["candidates"]],
            "candidates_truncated": binding.get("candidates_truncated", False)}


def main():
    groups, _ = select_cases(Path(".benchmark-runtime/ragtruth"))
    cases = {c["id"]: c for group in groups.values() for c in group}
    path = Path("data/verification/context_v1/run01/predictions.jsonl")
    rows, counts = [], Counter()
    for record in read_jsonl(path):
        audit, item = record["audit"], cases[record["case_id"]]["input"]
        raw = audit["calls"][0]["raw_output"].strip()
        if raw.startswith("```json\n") and raw.endswith("\n```"):
            raw = raw[8:-4]
        raw = json.loads(raw)
        # Drop ONLY model-generated positions/context IDs, never change quote, reason or verdict.
        output = QuoteOutput.model_validate({"claims": [{k: v for k, v in c.items() if k in ("quote", "relation", "explanation")} |
            {"evidence": [{k: v for k, v in e.items() if k in ("quote", "source_id")} for e in c["evidence"]]} for c in raw["claims"]],
            "meta_text": [{k: v for k, v in m.items() if k != "occurrence"} for m in raw.get("meta_text", [])]})
        claims = [bind_quote_claim(item, c, i) for i, c in enumerate(output.claims)]
        meta = []
        for m in output.meta_text:
            binding = locate_quote(item.answer, m.quote)
            span = binding["span"]
            overlap = bool(span and any(c["answer_span"] and max(span["start"], c["answer_span"]["start"]) < min(span["end"], c["answer_span"]["end"]) for c in claims))
            meta.append({"quote": m.quote, "binding": binding, "overlaps_claim": overlap,
                         "complete": binding["status"] == "unique" and not overlap})
        complete = bool(claims or meta) and all(c["status"] == "ok" for c in claims) and all(m["complete"] for m in meta)
        before = audit["status"] == "ok"
        counts.update(total=1, originally_complete=before, rebind_complete=complete,
                      recovered=not before and complete, newly_unresolved=before and not complete,
                      still_incomplete=not before and not complete)
        rows.append({"case_id": record["case_id"], "group": record["group"], "strategy": record["strategy"],
                     "original_audit_id": audit["id"], "original_status": audit["status"], "counterfactual_complete": complete,
                     "claim_bindings": [{"id": c["id"], "status": c["status"],
                                         "answer": compact_binding(c["bindings"]["answer"]),
                                         "evidence": [{"source_id": b["source_id"], **compact_binding(b)} for b in c["bindings"]["evidence"]]}
                                        for c in claims],
                     "meta_bindings": [{**m, "binding": compact_binding(m["binding"])} for m in meta]})
    out = Path("data/verification/specific_error_v2")
    write_json(out / "binding_replay.json", {"scope": "Offline binding-only counterfactual, not new model calls. Exact existing quotes, verdicts and reasons unchanged; never replaces historical outcomes.",
               "source_predictions_text_sha256": text_hash(path.read_text(encoding="utf8")), "counts": dict(counts), "rows": rows})
    print(json.dumps(dict(counts)))
    for r in rows:
        if (r["original_status"] == "ok") != r["counterfactual_complete"] or not r["counterfactual_complete"]:
            print(r["case_id"], r["group"], r["strategy"], r["original_status"], "->", r["counterfactual_complete"])


if __name__ == "__main__":
    main()
