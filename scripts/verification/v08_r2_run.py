"""Run the frozen v0.8 R2 schedule, retaining every attempt and failure."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
# ruff: noqa: E402
from medrag.verification.answer_audit import audit_answer
from medrag.verification.atomic_audit import audit_atomic
from medrag.verification.atomic_v2 import audit_atomic_v2
from medrag.verification.atomic_v2_schema import AtomicV2Request
from medrag.verification.scifact import object_hash, read_jsonl
from run_queue import provider_blocked, results
from v08_r2_prepare import OUT, save
from v08_r2_metrics import score

FILES = [
    "src/medrag/verification/" + name
    for name in (
        "answer_audit.py",
        "atomic_audit.py",
        "atomic_schema.py",
        "atomic_v2.py",
        "atomic_v2_schema.py",
        "fidelity.py",
        "parent_binding.py",
        "quote_audit.py",
        "gateway.py",
        "numeric_checks.py",
    )
] + ["scripts/verification/v08_r2_metrics.py"]


def hashes():
    return {name: object_hash((ROOT / name).read_text(encoding="utf-8")) for name in FILES}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["prepare", "run", "freeze"])
    p.add_argument(
        "--phase", choices=["development", "natural", "repeat", "final"], default="development"
    )
    p.add_argument("--run-dir", type=Path)
    args = p.parse_args()
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in manifest["cases"] + manifest["natural_cases"]}
    if args.action == "freeze":
        required = {"development": 144, "natural": 36, "repeat": 24}
        for phase, count in required.items():
            rows = read_jsonl(OUT / phase / "predictions.jsonl")
            if len(rows) != count:
                raise ValueError(f"Incomplete {phase}: {len(rows)}/{count}")
        save(
            OUT / "method-freeze.json",
            {
                "manifest_sha256": object_hash(manifest),
                "code_hashes": hashes(),
                "decision": "One anchored candidate, no output-selected retry. Direct remains default; R2 is constructed/textual diagnostics, R3 lacks fresh public labels.",
                "frozen_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
        print("Candidate frozen for one final pass.")
        return
    if args.phase == "repeat":
        jobs = [
            {"case_id": c, "method": m, "attempt": a}
            for c in manifest["repeat_case_ids"]
            for m in manifest["repeat_methods"]
            for a in (2, 3)
        ]
    else:
        jobs = [
            {"case_id": c["id"], "method": m, "attempt": 1}
            for c in cases.values()
            if c["split"] == args.phase
            for m in manifest["methods"]
        ]
    jobs.sort(key=lambda j: object_hash(["v08-r2-dispatch", j]))
    directory = args.run_dir or OUT / args.phase
    protocol = {
        "manifest_sha256": object_hash(manifest),
        "phase": args.phase,
        "schedule": jobs,
        "code_hashes": hashes(),
        "concurrency": 3,
        "sdk_max_retries": 0,
        "limits": {"direct_calls": 1, "atomic_calls": 3, "atomic_facts": 48},
        "retry_policy": "Resume only jobs never recorded. All failures remain; no best-of or majority-vote labels.",
        "metrics": "Target phrase coverage and single-claim anchor co-presence are mechanical, not proof of semantic mapping. Literal preservation separate; constructed numerical warnings separate from natural errors.",
    }
    if args.action == "prepare":
        save(directory / "protocol.json", protocol)
        print(f"Prepared {args.phase}: {len(jobs)} audits.")
        return
    if json.loads((directory / "protocol.json").read_text(encoding="utf-8")) != protocol:
        raise ValueError("Frozen protocol changed")
    if args.phase == "final":
        frozen = json.loads((OUT / "method-freeze.json").read_text(encoding="utf-8"))
        if frozen["code_hashes"] != hashes() or frozen["manifest_sha256"] != object_hash(manifest):
            raise ValueError("Final candidate differs from freeze")
    predictions = directory / "predictions.jsonl"
    prior = read_jsonl(predictions) if predictions.exists() else []
    if any(provider_blocked(r) for r in prior):
        raise ValueError(
            "Provider block retained. Resolve access and use a separately identified continuation."
        )
    done = {(r["case_id"], r["method"], r["attempt"]) for r in prior}
    pending = [j for j in jobs if (j["case_id"], j["method"], j["attempt"]) not in done]
    if not pending:
        print("No unattempted jobs.")
        return
    from medrag.verification.gateway import FlashGateway

    model = FlashGateway()
    model.client = model.client.with_options(max_retries=0)
    model.settings["sdk_max_retries"] = 0
    save(
        directory / f"dispatch-{len(list(directory.glob('dispatch-*.json'))) + 1}.json",
        {
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "settings": model.settings,
            "pending": pending,
            "dispatch": "bounded continuous queue; max 3 requests across this runner",
        },
    )

    def execute(job):
        case = cases[job["case_id"]]
        if object_hash(case["input"]) != case["input_sha256"]:
            raise ValueError("Input fingerprint mismatch")
        item = AtomicV2Request.model_validate({**case["input"], "strategy": job["method"]})
        fn = {"direct": audit_answer, "atomic_v1": audit_atomic, "atomic_v2": audit_atomic_v2}[
            job["method"]
        ]
        audit = fn(item, model)
        return {
            **job,
            "group_id": case["group_id"],
            "variant": case.get("variant", "natural"),
            "input_sha256": case["input_sha256"],
            "audit": audit,
            "metrics": score(case, audit),
        }

    for row in results(pending, execute):
        with predictions.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
        done.add((row["case_id"], row["method"], row["attempt"]))
        print(
            f"{args.phase} {len(done)}/{len(jobs)} {row['case_id']} {row['method']} {row['audit']['status']}",
            flush=True,
        )
        if provider_blocked(row):
            print(
                "Provider access blocked; no new dispatch, retaining in-flight calls.", flush=True
            )


if __name__ == "__main__":
    main()
