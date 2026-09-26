"""Publish seeded development replays and final aggregate data, without model calls."""

import argparse
import json

from medrag.verification.scifact import object_hash, read_jsonl
from v06_fixed import dump
from v06_prepare import ROOT, SEED
from v07_benchmark import METHODS, V07, load_tasks

DEST = ROOT / "data/demo/research"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "export"])
    parser.add_argument(
        "--examples-only",
        action="store_true",
        help="Export completed development replays without publishing final scores",
    )
    args = parser.parse_args()
    tasks = load_tasks("development")
    ids = sorted(
        [e["case_id"] for e, _ in tasks],
        key=lambda key: object_hash([SEED, "workflow-demo", key]),
    )[:3]
    selection = {
        "case_ids": ids,
        "rule": "First three development cases ordered by seeded hash, selected before workflow inference; not selected by performance",
        "manifest_sha256": object_hash(
            json.loads((V07 / "manifest.json").read_text(encoding="utf8"))
        ),
    }
    path = DEST / "selection.json"
    if args.action == "prepare":
        DEST.mkdir(parents=True, exist_ok=True)
        if path.exists() and json.loads(path.read_text(encoding="utf8")) != selection:
            raise ValueError("Replay selection changed")
        dump(path, selection)
        print(f"Selected {ids} for saved workflow demonstration")
        return
    if json.loads(path.read_text(encoding="utf8")) != selection:
        raise ValueError("Replay selection changed")
    rows = read_jsonl(V07 / "development/predictions.jsonl")
    attempt_settings = [
        {"attempt_file": p.name, "settings": json.loads(p.read_text(encoding="utf8"))["settings"]}
        for p in sorted((V07 / "development").glob("attempt-*.json"))
    ]
    by_id = {(r["case_id"], r["method"]): r for r in rows}
    catalogue = []
    for e, task in tasks:
        if e["case_id"] not in ids:
            continue
        results = {}
        for method in METHODS:
            row = by_id[(e["case_id"], method)]
            if row["input_sha256"] != object_hash(task.model_dump()):
                raise ValueError("Replay input does not match recorded inference")
            results[method] = row["result"]
        case_id = e["case_id"]
        record = {
            "input": task.model_dump(),
            "results": results,
            "reference": {
                "document_id": e["document_id"],
                "relation": e["relation"],
                "origin": "SciFact public annotation of the specified paper/claim; not a grade for every sentence of the explanation",
            },
            "provenance": {
                "case_id": case_id,
                "split": "development",
                "input_sha256": object_hash(task.model_dump()),
                "results_sha256": object_hash(results),
                "selection": selection["rule"],
                "run_settings": attempt_settings,
                "note": "Saved development inference. Three methods receive the same named-paper question and fixed eight-paper corpus. Public relation labels were withheld from model input. No live model calls are made while replaying.",
            },
        }
        dump(DEST / f"{case_id}.json", record)
        catalogue.append({"id": case_id, "label": task.claim})
    catalogue.sort(key=lambda e: ids.index(e["id"]))
    dump(DEST / "catalogue.json", catalogue)
    if args.examples_only:
        print("Exported three completed development replays; no final score publication")
        return
    final = json.loads((V07 / "final-metrics.json").read_text(encoding="utf8"))
    report = {
        "status": "completed",
        "planned_queries": final["planned_queries"],
        "task": final["task"],
        "action_protocol": final["action_protocol"],
        "scope": final["scope"],
        "methods": {
            method: {
                "accepted": {k: v for k, v in data["accepted"].items() if k != "details"},
                "workflow_counts": data["workflow_counts"],
                "execution_statuses": data["execution_statuses"],
                "call_statuses": data["call_statuses"],
                "call_error_types": data["call_error_types"],
                "action_adaptations": data["action_adaptations"],
                "original_draft": {
                    k: v for k, v in data["original_draft"].items() if k != "details"
                },
                "three_class_matrix": data["three_class_matrix"],
            }
            for method, data in final["methods"].items()
        },
        "paired_differences": final["paired_differences"],
        "protocol_diagnostic": final["protocol_diagnostic"],
        "note": "Final queries were evaluated once after the development freeze. Above replays are seeded development examples, not the final test. Missing/review outputs remain in all-case denominators.",
    }
    dump(DEST / "results.json", report)
    print("Exported three complete replay bundles and final aggregate report")


if __name__ == "__main__":
    main()
