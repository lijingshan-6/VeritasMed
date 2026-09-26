"""Freeze and execute paired named-paper research workflows; no labels sent to models."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from medrag.agent.research_workflow import LiteratureTask, run_research
from medrag.verification.scifact import object_hash, read_jsonl
from v06_fixed import dump
from v06_prepare import ROOT, OUT, SEED, load_cases
from v06_source import code_hashes
from run_queue import provider_blocked, results

V07 = ROOT / "data/verification/v07"
METHODS = ["direct_reader", "autonomous_tools", "structured_workflow"]


def prepare_cases():
    manifest = json.loads((OUT / "splits.json").read_text(encoding="utf8"))
    cases = load_cases()
    distractor_ids = sorted(
        {e["document_id"] for e in manifest["entries"] if e["split"] == "development"}
    )
    groups = {e["group_id"] for e in manifest["entries"] if e["split"].startswith("v07_")}
    selected = []
    for group in sorted(groups):
        es = [e for e in manifest["entries"] if e["group_id"] == group]
        e = min(es, key=lambda e: object_hash([SEED, "v07-query", e["case_id"]]))
        case = cases[e["case_id"]]
        ids = sorted(distractor_ids, key=lambda doc: object_hash([SEED, e["case_id"], doc]))[:7] + [
            e["document_id"]
        ]
        ids.sort(key=lambda doc: object_hash([SEED, "presentation", e["case_id"], doc]))
        selected.append(
            {
                **e,
                "document_ids": ids,
                "question": f'Does the paper "{case.input.document.title}" support this claim: {case.input.claim}',
            }
        )
    result = {
        "seed": SEED,
        "parent_manifest_sha256": object_hash(manifest),
        "task": "named-paper fixed-corpus fact inquiry",
        "gold_origin": "SciFact public annotations; no final labels in inference payload",
        "cases": selected,
        "limits": {"model_calls": 6, "nonmodel_tools": 8, "api_concurrency": 3},
        "methods": METHODS,
    }
    V07.mkdir(parents=True, exist_ok=True)
    p = V07 / "manifest.json"
    if p.exists() and json.loads(p.read_text(encoding="utf8")) != result:
        raise ValueError("v0.7 manifest changed")
    dump(p, result)
    print("Frozen 20 development and 40 final source-group queries")


def load_tasks(split):
    from medrag.verification.schema import EvidenceDocument

    manifest = json.loads((V07 / "manifest.json").read_text(encoding="utf8"))
    cases = load_cases()
    corpus = {
        str(d["doc_id"]): EvidenceDocument(
            document_id=str(d["doc_id"]), title=d["title"], sentences=d["abstract"]
        )
        for d in read_jsonl(ROOT / ".benchmark-runtime/scifact/corpus.jsonl")
    }
    return [
        (
            e,
            LiteratureTask(
                question=e["question"],
                target_title=cases[e["case_id"]].input.document.title,
                claim=cases[e["case_id"]].input.claim,
                documents=[corpus[d] for d in e["document_ids"]],
            ),
        )
        for e in manifest["cases"]
        if e["split"] == f"v07_{split}"
    ]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["cases", "prepare", "run"])
    p.add_argument("--split", choices=["development", "final"])
    p.add_argument(
        "--run-dir",
        type=Path,
        help="Fresh output directory; final-source repeats are not fresh tests",
    )
    args = p.parse_args()
    if args.action == "cases":
        prepare_cases()
        return
    tasks = load_tasks(args.split)
    schedule = [{"case_id": e["case_id"], "method": m} for e, t in tasks for m in METHODS]
    schedule.sort(key=lambda j: object_hash([SEED, "v07-order", j]))
    files = [
        "src/medrag/agent/research_workflow.py",
        "src/medrag/verification/verifier.py",
        "src/medrag/verification/gateway.py",
    ]
    protocol = {
        "split": args.split,
        "action_protocol": "v2_explicit_finish_and_recorded_format_normalization",
        "schedule": schedule,
        "input_hashes": {e["case_id"]: object_hash(t.model_dump()) for e, t in tasks},
        "code_hashes": code_hashes(files),
        "scoring": "Named target doc ID, public relation label, bound sentence IDs; review/failures not counted correct; independently report original draft.",
    }
    directory = args.run_dir or V07 / args.split
    if args.action == "prepare":
        directory.mkdir(parents=True, exist_ok=False)
        dump(directory / "protocol.json", protocol)
        print(f"Frozen {len(schedule)} workflow jobs")
        return
    if json.loads((directory / "protocol.json").read_text(encoding="utf8")) != protocol:
        raise ValueError("Frozen workflow changed")
    if args.split == "final" and not (V07 / "method-freeze.json").exists():
        raise ValueError("Freeze selection before final")
    from medrag.verification.gateway import FlashGateway

    model = FlashGateway()
    model.client = model.client.with_options(max_retries=0)
    model.settings["sdk_max_retries"] = 0
    path = directory / "predictions.jsonl"
    prior = read_jsonl(path) if path.exists() else []
    done = {(r["case_id"], r["method"]) for r in prior}
    jobs = [j for j in schedule if (j["case_id"], j["method"]) not in done]
    by_id = {e["case_id"]: (e, t) for e, t in tasks}
    count = len(done)
    attempt = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "settings": model.settings,
        "pending": len(jobs),
        "dispatch": "bounded continuous queue; launch frozen order, save completion order; at most 3 jobs",
    }
    attempt_path = directory / f"attempt-{len(list(directory.glob('attempt-*.json'))) + 1}.json"
    dump(attempt_path, attempt)

    def execute(job):
        e, t = by_id[job["case_id"]]
        return {
            **job,
            "group_id": e["group_id"],
            "input_sha256": object_hash(t.model_dump()),
            "result": run_research(t, model, job["method"]),
        }

    for r in results(jobs, execute, workers=3):
        with path.open("a", encoding="utf8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        count += 1
        print(
            f"{count}/{len(schedule)} {r['case_id']} {r['method']} {r['result']['status']}",
            flush=True,
        )
        if provider_blocked(r):
            attempt["stop_reason"] = "provider_access_or_balance"
    attempt.update(completed_total=count, finished_utc=datetime.now(timezone.utc).isoformat())
    dump(attempt_path, attempt)


if __name__ == "__main__":
    main()
