"""Recompute the paired development comparison from reviewed saved answers, offline."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import fmean, median
from tempfile import TemporaryDirectory

from medrag.benchmark.saved_run import recompute_saved_run, render_cases


def recompute_declared_questions(questions, raw_path, review_path):
    """Use the unchanged scorer for a saved, explicitly declared development subset."""
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    original = questions.read_bytes()
    if raw["questions_sha256"] != hashlib.sha256(original).hexdigest():
        raise ValueError("Run does not match the frozen question file")
    rows = [json.loads(line) for line in original.decode("utf-8").splitlines() if line.strip()]
    development = {q["id"] for q in rows if q["split"] == "development"}
    ids = raw["question_ids"]
    if raw["split"] != "development" or not ids or len(ids) != len(set(ids)) or not set(ids) <= development:
        raise ValueError("Comparison must declare unique development question IDs")
    if set(ids) == development:
        return recompute_saved_run(questions, raw_path, review_path)
    # Adapt only the input envelope in temporary files. The original saved run,
    # frozen gold claims and source-first assessments are never changed.
    subset = "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in rows if q["id"] in ids).encode("utf-8")
    with TemporaryDirectory() as temporary:
        directory = Path(temporary)
        subset_path = directory / "questions.jsonl"
        subset_path.write_bytes(subset)
        derived = dict(raw, questions_sha256=hashlib.sha256(subset).hexdigest())
        derived_path = directory / "answers.json"
        derived_path.write_text(json.dumps(derived, ensure_ascii=False), encoding="utf-8")
        report = recompute_saved_run(subset_path, derived_path, review_path)
    report["question_ids"] = ids
    report["derived_subset_sha256"] = hashlib.sha256(subset).hexdigest()
    report["input_sha256"]["questions"] = hashlib.sha256(original).hexdigest()
    report["input_sha256"]["answers"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path,
                        default=Path("data/benchmark/veritasmed_v1_1/deepseek_comparison_streaming"))
    parser.add_argument("--case-prefix", default="agent-model-comparison")
    args = parser.parse_args()
    questions = Path("data/benchmark/veritasmed_v1_1/questions.jsonl")
    models = {}
    rows_by_model = {}
    configs = []
    for label in ("pro", "flash"):
        raw_path = args.directory / f"{label}_raw.json"
        review_path = args.directory / f"{label}_assessments.jsonl"
        report = recompute_declared_questions(questions, raw_path, review_path)
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        reviews = [json.loads(line) for line in review_path.read_text(encoding="utf-8").splitlines()]
        configs.append((raw["runtime_config"], raw["runtime_file_sha256"]))
        calls = [c for r in raw["results"] for c in r.get("api_calls", [])]
        requested = {c.get("request_settings", {}).get("model") for c in calls}
        if requested != {raw["model"]}:
            raise ValueError(f"{label}: per-question model selection was not preserved: {requested}")
        scores = {r["id"]: r for r in report["results"]}
        rows_by_model[label] = scores
        times = [r["latency_seconds"] for r in raw["results"]]
        answerable = [r for r in report["results"] if r["answerability"] != "unanswerable"]
        models[label] = {
            "model": raw["model"], "questions": len(scores),
            "strict_passes": sum(r["metrics"]["strict_pass"] for r in scores.values()),
            "unsupported_material_claims": sum(r["metrics"]["unsupported_material_claim_count"] for r in scores.values()),
            "missing_qualifiers": sum(r["metrics"]["missing_required_qualifier_count"] for r in scores.values()),
            "all_required_evidence_found": sum(r["retrieval_metrics"]["all_required_found"] for r in answerable),
            "answerable_questions": len(answerable),
            "execution_errors": sum(bool(r.get("error")) for r in raw["results"]),
            "self_check_passes": sum(r["faithful"] for r in raw["results"]),
            "self_check_rejects_content_pass": sum(scores[r["id"]]["metrics"]["strict_pass"] and not r["faithful"] for r in raw["results"]),
            "self_check_accepts_content_fail": sum(not scores[r["id"]]["metrics"]["strict_pass"] and r["faithful"] for r in raw["results"]),
            "coverage_contract_mismatches": sum(not r["presentation_review"]["coverage_label_correct"] for r in reviews),
            "unnecessary_detail_or_repetition": sum(r["presentation_review"]["unnecessary_detail_or_repetition"] for r in reviews),
            "mean_seconds": fmean(times), "median_seconds": median(times), "max_seconds": max(times),
            "answers_over_existing_300s_api_deadline": sum(t > 300 for t in times),
            "regenerations": sum(r["regen_count"] for r in raw["results"]),
            "query_rewrites": sum(r["iterations"] for r in raw["results"]),
            "answers_with_source_quote_replacement": sum(
                any(h.get("kind") == "source_quote" for h in r.get("repair_history", []))
                for r in raw["results"]),
            "mean_answer_words": fmean(len(r["answer"].split()) for r in raw["results"]),
            "model_calls": len(calls),
            "length_truncated_calls": sum(c.get("response_metadata", {}).get("finish_reason") == "length" for c in calls),
            "reported_input_tokens": sum((c.get("usage") or {}).get("input_tokens", 0) for c in calls),
            "reported_output_tokens": sum((c.get("usage") or {}).get("output_tokens", 0) for c in calls),
        }
        (args.directory / f"{label}_scored.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        cases = render_cases(report, questions, version="model-comparison")
        cases = cases.replace(
            "The decisions below are Codex source-first adjudications, not independent clinician reviews.",
            "The code includes the archived uncommitted gateway adapter and runner; exact runtime hashes are in the raw artifact.\n"
            "The decisions below are Codex source-first adjudications, not independent clinician reviews.")
        Path(f"docs/reports/{args.case_prefix}-{label}-cases.md").write_text(cases, encoding="utf-8", newline="\n")
    if configs[0] != configs[1]:
        raise ValueError("Models were evaluated with different implementations or common settings")
    paired = [{"id": qid, "pro_pass": rows_by_model["pro"][qid]["metrics"]["strict_pass"],
               "flash_pass": rows_by_model["flash"][qid]["metrics"]["strict_pass"]}
              for qid in rows_by_model["pro"]]
    summary = {"scope": "paired development, through OpenHub, unchanged production graph",
               "test_split_executed": False, "models": models, "paired": paired}
    (args.directory / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                                encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
