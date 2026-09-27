"""Recompute one saved Flash run from explicit source-reviewed assessments, without models."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import fmean, median

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from medrag.benchmark.saved_run import recompute_saved_run, render_cases  # noqa: E402
from report_model_comparison import recompute_declared_questions  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--case-name", required=True, help="Markdown filename stem under docs/reports/")
    args = parser.parse_args()
    args.directory = ROOT / args.directory
    questions = ROOT / "data/benchmark/veritasmed_v1_1/questions.jsonl"
    raw_path = args.directory / "flash_raw.json"
    review_path = args.directory / "flash_assessments.jsonl"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    if raw["split"] == "development":
        report = recompute_declared_questions(questions, raw_path, review_path)
    else:
        report = recompute_saved_run(questions, raw_path, review_path)
    rows = raw["results"]
    scores = report["results"]
    reviews = [json.loads(line) for line in review_path.read_text(encoding="utf-8").splitlines() if line]
    calls = [c for r in rows for c in r.get("api_calls", [])]
    if raw["model"].casefold() != "deepseek-v4.1-flash" or {
        c.get("request_settings", {}).get("model") for c in calls
    } != {raw["model"]}:
        raise ValueError("This report expects a Flash-only run")
    usage_calls = [c for c in calls if isinstance(c.get("usage"), dict)]
    answerable = [r for r in scores if r["answerability"] != "unanswerable"]
    times = [r["latency_seconds"] for r in rows]
    summary = {
        "model": raw["model"], "split": raw["split"], "questions": len(rows),
        "strict_passes": sum(r["metrics"]["strict_pass"] for r in scores),
        "unsupported_material_claims": sum(r["metrics"]["unsupported_material_claim_count"] for r in scores),
        "missing_qualifiers": sum(r["metrics"]["missing_required_qualifier_count"] for r in scores),
        "all_required_evidence_found": sum(r["retrieval_metrics"]["all_required_found"] for r in answerable),
        "answerable_questions": len(answerable),
        "execution_errors": sum(bool(r.get("error")) for r in rows),
        "self_check_passes": sum(r["faithful"] for r in rows),
        "coverage_label_mismatches": sum(not r["presentation_review"]["coverage_label_correct"] for r in reviews),
        "mean_seconds": fmean(times), "median_seconds": median(times), "max_seconds": max(times),
        "answers_over_300s": sum(t > 300 for t in times),
        "regenerations": sum(r["regen_count"] for r in rows),
        "query_rewrites": sum(r["iterations"] for r in rows),
        "answers_with_source_quote_repair": sum(any(h.get("kind") == "source_quote" for h in r.get("repair_history", [])) for r in rows),
        "answers_with_source_projection": sum(any(h.get("kind") == "source_projection" for h in r.get("repair_history", [])) for r in rows),
        "answers_with_design_scope_repair": sum(any(h.get("kind") == "design_scope" for h in r.get("repair_history", [])) for r in rows),
        "mean_answer_words": fmean(len(r["answer"].split()) for r in rows),
        "model_calls": len(calls),
        "calls_with_reported_usage": len(usage_calls),
        "reported_input_tokens": sum(c["usage"].get("input_tokens", 0) for c in usage_calls) if usage_calls else None,
        "reported_output_tokens": sum(c["usage"].get("output_tokens", 0) for c in usage_calls) if usage_calls else None,
        "failed_ids": [r["id"] for r in scores if not r["metrics"]["strict_pass"]],
    }
    for name, payload in (("flash_scored.json", report), ("summary.json", summary)):
        (args.directory / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (ROOT / f"docs/reports/{args.case_name}.md").write_text(
        render_cases(report, questions, version="v0.4-flash"), encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
