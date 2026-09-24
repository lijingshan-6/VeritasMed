"""Pinned public answer-level annotations, preserved at their original span granularity."""
from collections import Counter
import hashlib
from pathlib import Path
from statistics import median

from .answer_audit import AuditInput, AuditSource
from .scifact import object_hash, read_jsonl

REVISION = "c103204b9ce28d6bbad859304bf30de72b8ed8fe"
HASHES = {"response.jsonl": "e4c2e4ac24fff676d8984cc61c35d791612fadc58015335d97dd632375e18073",
          "source_info.jsonl": "0dffc26ea9f3c1c3d7c7e8336b56ef1646e3cec876edffcca3c9c624d12d578b"}
SEED = "veritasmed-answer-audit-v1-2026-09-24"


def prepare(cache: Path):
    for name, digest in HASHES.items():
        if hashlib.sha256((cache / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Modified RAGTruth source: {name}")
    sources = {s["source_id"]: s for s in read_jsonl(cache / "source_info.jsonl")}
    responses = read_jsonl(cache / "response.jsonl")
    test_sources = {r["source_id"] for r in responses if r["split"] == "test"}
    candidates = [r for r in responses if r["split"] == "train" and r["quality"] == "good"
                  and r["source_id"] not in test_sources and sources[r["source_id"]]["task_type"] == "Summary"
                  and len(r["response"]) <= 12000 and len(sources[r["source_id"]]["source_info"]) <= 50000]
    for row in candidates:
        for label in row["labels"]:
            if not label["text"].strip() or row["response"][label["start"]:label["end"]] != label["text"]:
                raise ValueError("Official training annotation does not match its exact character slice")
    counts, used_sources, selected = Counter(), set(), []
    for row in sorted(candidates, key=lambda r: object_hash([SEED, r["id"]])):
        category = "annotated_error" if row["labels"] else "unmarked"
        if counts[category] == 12 or row["source_id"] in used_sources:
            continue
        selected.append(row)
        counts[category] += 1
        used_sources.add(row["source_id"])
    if len(selected) != 24:
        raise ValueError("Cannot satisfy the declared 12+12 source-disjoint pilot")
    # Reserve by metadata only: do not select on test labels or expose test answer text to models.
    reserved, seen = [], set()
    pool = [r for r in responses if r["split"] == "test" and r["quality"] == "good"
            and sources[r["source_id"]]["task_type"] == "Summary"]
    for row in sorted(pool, key=lambda r: object_hash([SEED, "reserve", r["source_id"], r["id"]])):
        if row["source_id"] in seen:
            continue
        reserved.append({"source_id": row["source_id"], "response_id": row["id"]})
        seen.add(row["source_id"])
        if len(reserved) == 60:
            break
    if len(reserved) != 60:
        raise ValueError("Fewer than 60 reservable source groups")
    cases = []
    for row in selected:
        source = sources[row["source_id"]]
        item = AuditInput(answer=row["response"], sources=[AuditSource(id=row["source_id"],
                          title=f"RAGTruth {source['source']} · source {row['source_id']}", text=source["source_info"])])
        cases.append({"id": row["id"], "input": item, "gold_spans": row["labels"], "source_id": row["source_id"]})
    manifest = {"dataset": "RAGTruth", "revision": REVISION, "files": HASHES,
                "split": "official train development pilot", "seed": SEED, "task_type": "Summary",
                "candidate_responses": len(candidates), "selected_counts": dict(counts),
                "implicit_true_policy": "Counts as unsupported in supplied sources; never relabelled from world knowledge",
                "cases": [{"response_id": c["id"], "source_id": c["source_id"],
                           "input_sha256": object_hash(c["input"].model_dump()), "gold_spans": c["gold_spans"]}
                          for c in cases],
                "reserved_official_test": reserved,
                "note": "24 curated-by-rule development answers; 60 test source IDs reserved but not executed. Public data may be in pretraining."}
    return cases, manifest


def char_set(text, spans):
    return {i for s in spans for i in range(s["start"], s["end"]) if not text[i].isspace()}


def score_answers(cases: list[dict], rows: list[dict]):
    by_id = {r["case_id"]: r["audit"] for r in rows}
    if len(by_id) != len(rows) or not set(by_id) <= {c["id"] for c in cases}:
        raise ValueError("Duplicate or unknown answer IDs")
    counts = Counter()
    details = []
    tokens = Counter()
    models = Counter()
    for case in cases:
        audit = by_id.get(case["id"])
        answer = case["input"].answer
        gold = char_set(answer, case["gold_spans"])
        flagged = [c["answer_span"] for c in audit["claims"] if c["status"] == "ok"
                   and c["relation"] in ("contradicted", "insufficient")] if audit else []
        predicted = char_set(answer, flagged)
        extracted = char_set(answer, [c["answer_span"] for c in audit["claims"] if c["answer_span"]]) if audit else set()
        hit_any = hit_half = extracted_any = 0
        for span in case["gold_spans"]:
            target = char_set(answer, [span])
            hit_any += bool(target & predicted)
            hit_half += len(target & predicted) * 2 >= len(target)
            extracted_any += bool(target & extracted)
        counts.update(gold_spans=len(case["gold_spans"]), span_hit_any=hit_any, span_hit_half=hit_half,
                      extracted_gold_spans=extracted_any, gold_characters=len(gold),
                      predicted_characters=len(predicted), overlap_characters=len(gold & predicted),
                      labelled_error_answers=bool(gold), unmarked_answers=not gold,
                      detected_error_answers=bool(gold and predicted), false_positive_answers=bool(not gold and predicted),
                      implicit_true_spans=sum(s.get("implicit_true", False) for s in case["gold_spans"]),
                      completed_answers=bool(audit and audit["status"] == "ok"))
        if audit:
            counts["logical_calls"] += len(audit["calls"])
            for call in audit["calls"]:
                counts["failed_calls"] += call["status"] != "ok"
                if call.get("usage") is not None:
                    counts["calls_with_usage"] += 1
                    tokens.update({k: v for k, v in call["usage"].items() if isinstance(v, int)})
                models.update(["|".join(call.get("transport_metadata", {}).get("model_identifiers", [])) or "unavailable"])
        details.append({"response_id": case["id"], "source_id": case["source_id"],
                        "status": audit["status"] if audit else "not_run", "gold_spans": len(case["gold_spans"]),
                        "hit_any": hit_any, "hit_half": hit_half, "extracted_hit_any": extracted_any,
                        "flagged_claims": len(flagged), "gold_characters": len(gold),
                        "predicted_characters": len(predicted), "overlap_characters": len(gold & predicted)})
    def ratio(a, b):
        return counts[a] / counts[b] if counts[b] else None
    return {"total_answers": len(cases), "counts": dict(counts),
            "answer_error_recall": ratio("detected_error_answers", "labelled_error_answers"),
            "answer_error_precision": counts["detected_error_answers"] / (counts["detected_error_answers"] + counts["false_positive_answers"])
            if counts["detected_error_answers"] + counts["false_positive_answers"] else None,
            "unmarked_answer_false_positive_rate": ratio("false_positive_answers", "unmarked_answers"),
            "gold_span_recall_any_overlap": ratio("span_hit_any", "gold_spans"),
            "gold_span_recall_half_overlap": ratio("span_hit_half", "gold_spans"),
            "gold_span_extraction_coverage": ratio("extracted_gold_spans", "gold_spans"),
            "character_precision": ratio("overlap_characters", "predicted_characters"),
            "character_recall": ratio("overlap_characters", "gold_characters"),
            "character_f1": 2 * counts["overlap_characters"] / (counts["gold_characters"] + counts["predicted_characters"])
            if counts["gold_characters"] + counts["predicted_characters"] else None,
            "reported_tokens": dict(tokens) if counts["calls_with_usage"] else None,
            "response_models": dict(models), "per_answer": details,
            "median_answer_seconds": median(r["audit"]["elapsed_seconds"] for r in rows) if rows else None,
            "summed_answer_seconds": sum(r["audit"]["elapsed_seconds"] for r in rows),
            "interpretation": "Public nonmedical development answers. Span overlap measures location, not semantic completeness; broad claims can flag extra characters. No three-class gold accuracy."}
