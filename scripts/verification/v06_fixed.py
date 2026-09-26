"""Execute frozen fixed-claim runs. Resume missing jobs, never overwrite attempts."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from medrag.verification.scifact import object_hash, read_jsonl
from medrag.verification.verifier import SYSTEM_PROMPT, verify
from v06_prepare import OUT, load_cases
from v06_source import code_hashes
from run_queue import provider_blocked, results


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    parser.add_argument(
        "--split", choices=["pilot", "score_fit", "threshold_select", "final"], required=True
    )
    parser.add_argument("--method", choices=["flash", "minicheck"], required=True)
    parser.add_argument(
        "--run-dir", type=Path, help="Fresh output directory for a separately recorded repeat"
    )
    args = parser.parse_args()
    manifest = json.loads((OUT / "splits.json").read_text(encoding="utf8"))
    jobs = [
        e
        for e in manifest["entries"]
        if (
            e["case_id"] in manifest["pilot_ids"]
            if args.split == "pilot"
            else e["split"] == args.split
        )
    ]
    jobs.sort(key=lambda e: object_hash(["fixed-order-v1", e["case_id"]]))
    directory = args.run_dir or OUT / "fixed" / f"{args.split}-{args.method}"
    from medrag.verification import minicheck_adapter

    files = [
        "src/medrag/verification/" + n
        for n in ["minicheck_adapter.py", "verifier.py", "gateway.py", "schema.py"]
    ]
    protocol = {
        "split": args.split,
        "method": args.method,
        "manifest_sha256": object_hash(manifest),
        "schedule": jobs,
        "prompt": SYSTEM_PROMPT,
        "model_revision": minicheck_adapter.REVISION,
        "code_hashes": code_hashes(files),
        "retries": "SDK retries disabled; resume only jobs never attempted",
        "concurrency": 3 if args.method == "flash" else 1,
    }
    if args.action == "prepare":
        directory.mkdir(parents=True, exist_ok=False)
        dump(directory / "protocol.json", protocol)
        print(f"Frozen {len(jobs)} {args.split} jobs for {args.method}")
        return
    if json.loads((directory / "protocol.json").read_text(encoding="utf8")) != protocol:
        raise ValueError("Frozen protocol differs; do not run")
    if args.split != "pilot" and not (OUT / "fixed-method-freeze.json").exists():
        raise ValueError("Select and freeze methods before calibration/final evaluation")
    if args.method == "flash":
        from medrag.verification.gateway import FlashGateway

        model = FlashGateway()
        model.client = model.client.with_options(max_retries=0)
        model.settings["sdk_max_retries"] = 0

        def fn(x):
            return verify(x, model)
    else:
        model = minicheck_adapter.MiniCheckAdapter()
        fn = model.verify
    predictions = directory / "predictions.jsonl"
    prior = read_jsonl(predictions) if predictions.exists() else []
    done = {r["case_id"] for r in prior}
    pending = [e for e in jobs if e["case_id"] not in done]
    cases = load_cases()
    attempt = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "pending": len(pending),
        "settings": model.settings,
        "dispatch": "bounded continuous queue; launch frozen order, save completion order",
    }
    attempt_path = directory / f"attempt-{len(list(directory.glob('attempt-*.json'))) + 1}.json"
    dump(attempt_path, attempt)

    def execute(job):
        item = cases[job["case_id"]].input
        if object_hash(item.model_dump()) != job["input_sha256"]:
            raise ValueError("Input changed")
        result = fn(item)
        if args.method == "flash":
            result["binary_prediction"] = (
                int(result["decision"]["relation"] == "supported")
                if result["status"] == "ok"
                else None
            )
        return {"group_id": job["group_id"], "input_sha256": job["input_sha256"], **result}

    workers = 3 if args.method == "flash" else 1
    count = len(done)
    for row in results(pending, execute, workers=workers):
        with predictions.open("a", encoding="utf8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        count += 1
        print(f"{count}/{len(jobs)} {row['case_id']} {row['status']}", flush=True)
        if provider_blocked(row):
            attempt["stop_reason"] = "provider_access_or_balance"
    attempt["finished_utc"] = datetime.now(timezone.utc).isoformat()
    attempt["completed_total"] = count
    dump(attempt_path, attempt)


if __name__ == "__main__":
    main()
