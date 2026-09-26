"""Predeclared whole-answer development, transfer and repeat runs."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from medrag.verification.answer_audit import audit_answer
from medrag.verification.atomic_audit import audit_atomic
from medrag.verification.atomic_schema import AtomicAuditRequest
from medrag.verification.scifact import object_hash, read_jsonl
from v06_prepare import OUT, ROOT, SEED, walk
from v06_medical import cases as medical_cases
from v06_fixed import dump
from v06_source import code_hashes
from run_queue import provider_blocked, results


def natural_prepare():
    from medrag.verification.ragtruth import HASHES
    import hashlib

    cache = ROOT / ".benchmark-runtime/ragtruth"
    for name, digest in HASHES.items():
        if hashlib.sha256((cache / name).read_bytes()).hexdigest() != digest:
            raise ValueError("RAGTruth file changed")
    sources = {s["source_id"]: s for s in read_jsonl(cache / "source_info.jsonl")}
    responses = read_jsonl(cache / "response.jsonl")
    excluded = {r["source_id"] for r in responses if r["split"] == "test"}
    for directory in ("ragtruth_v1", "context_v1", "quote_v2"):
        for row in walk(
            json.loads(
                (ROOT / f"data/verification/{directory}/run01/manifest.json").read_text(
                    encoding="utf8"
                )
            )
        ):
            if "source_id" in row:
                excluded.add(row["source_id"])
    selected = []
    counts = {True: 0, False: 0}
    for r in sorted(responses, key=lambda r: object_hash([SEED, "natural", r["id"]])):
        s = sources[r["source_id"]]
        marked = bool(r["labels"])
        if (
            r["split"] != "train"
            or r["quality"] != "good"
            or s["task_type"] != "Summary"
            or r["source_id"] in excluded
            or counts[marked] >= 18
        ):
            continue
        if len(r["response"]) > 12000 or len(s["source_info"]) > 50000:
            continue
        if any(r["response"][x["start"] : x["end"]] != x["text"] for x in r["labels"]):
            raise ValueError("Label span mismatch")
        item = AtomicAuditRequest(
            answer=r["response"],
            sources=[
                {
                    "id": r["source_id"],
                    "title": f"RAGTruth {s['source']} · source {r['source_id']}",
                    "text": s["source_info"],
                }
            ],
        )
        selected.append(
            {
                "case_id": r["id"],
                "group_id": r["source_id"],
                "source_id": r["source_id"],
                "input_sha256": object_hash(item.model_dump()),
                "gold_spans": r["labels"],
            }
        )
        excluded.add(r["source_id"])
        counts[marked] += 1
        if len(selected) == 36:
            break
    if len(selected) != 36:
        raise ValueError("Cannot satisfy natural development selection")
    manifest = {
        "seed": SEED,
        "purpose": "36 fresh training sources, development only",
        "cases": selected,
        "repeat_ids": [c["case_id"] for c in selected[:12]],
        "counts": {"annotated_error": 18, "unmarked": 18},
    }
    path = OUT / "natural.json"
    if path.exists() and json.loads(path.read_text(encoding="utf8")) != manifest:
        raise ValueError("Natural manifest changed")
    dump(path, manifest)


def load_cases(dataset):
    if dataset.startswith("medical_"):
        return medical_cases(dataset)
    manifest = json.loads((OUT / "natural.json").read_text(encoding="utf8"))
    responses = {
        r["id"]: r for r in read_jsonl(ROOT / ".benchmark-runtime/ragtruth/response.jsonl")
    }
    sources = {
        r["source_id"]: r
        for r in read_jsonl(ROOT / ".benchmark-runtime/ragtruth/source_info.jsonl")
    }
    result = []
    for e in manifest["cases"]:
        r, s = responses[e["case_id"]], sources[e["source_id"]]
        item = AtomicAuditRequest(
            answer=r["response"],
            sources=[
                {
                    "id": e["source_id"],
                    "title": f"RAGTruth {s['source']} · source {e['source_id']}",
                    "text": s["source_info"],
                }
            ],
        )
        if object_hash(item.model_dump()) != e["input_sha256"]:
            raise ValueError("Natural input changed")
        if dataset == "repeat" and e["case_id"] not in manifest["repeat_ids"]:
            continue
        result.append({**e, "id": e["case_id"], "input": item})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["natural_prepare", "prepare", "run"])
    p.add_argument(
        "--dataset", choices=["medical_development", "medical_transfer", "natural", "repeat"]
    )
    p.add_argument(
        "--run-dir", type=Path, help="Fresh output directory for a separately recorded repeat"
    )
    args = p.parse_args()
    if args.action == "natural_prepare":
        natural_prepare()
        print("Frozen 36 natural development sources")
        return
    cases = load_cases(args.dataset)
    schedule = []
    for c in cases:
        methods = (
            ["direct", "split", "atomic_v1"]
            if args.dataset != "repeat"
            else ["direct", "atomic_v1"]
        )
        for method in methods:
            for attempt in [2, 3] if args.dataset == "repeat" else [1]:
                schedule.append({"case_id": c["id"], "method": method, "attempt": attempt})
    schedule.sort(key=lambda j: object_hash([SEED, "whole-order", j]))
    paths = [
        "src/medrag/verification/" + f
        for f in [
            "atomic_audit.py",
            "atomic_schema.py",
            "numeric_checks.py",
            "answer_audit.py",
            "quote_audit.py",
            "gateway.py",
        ]
    ]
    protocol = {
        "schedule": schedule,
        "dataset": args.dataset,
        "input_hashes": {c["id"]: c["input_sha256"] for c in cases},
        "code_hashes": code_hashes(paths),
        "workers": 3,
        "method_limit": "atomic at most 3 calls; original Split at most 25 calls; report unequal compute",
        "scoring": "original frozen RAGTruth location measures; constructed fact coverage separately; no semantic gold from model consensus",
    }
    directory = args.run_dir or OUT / "whole" / args.dataset
    if args.action == "prepare":
        directory.mkdir(parents=True, exist_ok=False)
        dump(directory / "protocol.json", protocol)
        print(f"Frozen {len(schedule)} answer audits")
        return
    if json.loads((directory / "protocol.json").read_text(encoding="utf8")) != protocol:
        raise ValueError("Protocol changed")
    if args.dataset == "medical_transfer" and not (OUT / "method-freeze.json").exists():
        raise ValueError("Freeze before transfer")
    from medrag.verification.gateway import FlashGateway

    gateway = FlashGateway()
    gateway.client = gateway.client.with_options(max_retries=0)
    gateway.settings["sdk_max_retries"] = 0
    predictions = directory / "predictions.jsonl"
    rows = read_jsonl(predictions) if predictions.exists() else []
    done = {(r["case_id"], r["method"], r["attempt"]) for r in rows}
    jobs = [j for j in schedule if (j["case_id"], j["method"], j["attempt"]) not in done]
    by_id = {c["id"]: c for c in cases}
    record = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "settings": gateway.settings,
        "pending": len(jobs),
        "dispatch": "bounded continuous queue; launch frozen order, save completion order; at most 3 jobs",
    }
    attempt_path = directory / f"attempt-{len(list(directory.glob('attempt-*.json'))) + 1}.json"
    dump(attempt_path, record)

    def execute(j):
        c = by_id[j["case_id"]]
        item = c["input"].model_copy(update={"strategy": j["method"]})
        audit = (
            audit_atomic(item, gateway)
            if j["method"] == "atomic_v1"
            else audit_answer(item, gateway)
        )
        return {
            **j,
            "group_id": c["group_id"],
            "input_sha256": c["input_sha256"],
            "strategy": j["method"],
            "audit": audit,
        }

    count = len(done)
    for row in results(jobs, execute, workers=3):
        with predictions.open("a", encoding="utf8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        count += 1
        print(
            f"{count}/{len(schedule)} {row['case_id']} {row['method']} {row['audit']['status']}",
            flush=True,
        )
        if provider_blocked(row):
            record["stop_reason"] = "provider_access_or_balance"
    record.update(completed_total=count, finished_utc=datetime.now(timezone.utc).isoformat())
    dump(attempt_path, record)


if __name__ == "__main__":
    main()
