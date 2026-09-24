"""Prepare pinned RAGTruth data, freeze a pilot, execute or rescore whole-answer audits."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

from medrag.verification.answer_audit import DIRECT_PROMPT, EXTRACT_PROMPT, VERIFY_PROMPT, audit_answer
from medrag.verification.ragtruth import HASHES, REVISION, prepare, score_answers
from medrag.verification.scifact import object_hash, read_jsonl


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def hashes():
    paths = [Path(__file__), *[Path("src/medrag/verification") / f for f in
                             ("answer_audit.py", "ragtruth.py", "gateway.py", "schema.py", "scifact.py")]]
    return {p.resolve().relative_to(Path.cwd()).as_posix(): hashlib.sha256(p.read_text(encoding="utf8").encode()).hexdigest() for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download", "prepare", "run", "report"))
    parser.add_argument("--cache", type=Path, default=Path(".benchmark-runtime/ragtruth"))
    parser.add_argument("--output", type=Path, default=Path("data/verification/ragtruth_v1/run01"))
    args = parser.parse_args()
    if args.action == "download":
        args.cache.mkdir(parents=True, exist_ok=True)
        for name, digest in HASHES.items():
            path = args.cache / name
            if not path.exists():
                request = urllib.request.Request(f"https://raw.githubusercontent.com/ParticleMedia/RAGTruth/{REVISION}/dataset/{name}", headers={"User-Agent": "VeritasMed-research"})
                with urllib.request.urlopen(request, timeout=120) as response:
                    data = response.read()
                if hashlib.sha256(data).hexdigest() != digest:
                    raise ValueError("Unexpected source hash")
                path.write_bytes(data)
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("Modified cached data")
        print("Pinned RAGTruth files available in local cache")
        return
    cases, manifest = prepare(args.cache)
    if args.action == "prepare":
        args.output.mkdir(parents=True, exist_ok=False)
        schedule = [{"case_id": c["id"], "strategy": s} for c in cases for s in ("direct", "split")]
        schedule.sort(key=lambda j: object_hash(["answer-audit-order-v1", j]))
        write_json(args.output / "manifest.json", manifest)
        write_json(args.output / "protocol.json", {"prepared_utc": datetime.now(timezone.utc).isoformat(),
            "schedule": schedule, "workers": 3, "manifest_sha256": object_hash(manifest), "code_hashes": hashes(),
            "prompts": {"direct": DIRECT_PROMPT, "extract": EXTRACT_PROMPT, "verify": VERIFY_PROMPT},
            "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "comparison": "Equal inputs and per-call limits; split uses more calls, not equal-compute"})
        print(f"Prepared {len(cases)} development answers; reserved {len(manifest['reserved_official_test'])} test source groups")
        return
    protocol = json.loads((args.output / "protocol.json").read_text(encoding="utf8"))
    if object_hash(manifest) != protocol["manifest_sha256"]:
        raise ValueError("Inputs changed after preparation")
    if args.action == "run":
        from medrag.verification.gateway import FlashGateway
        if hashes() != protocol["code_hashes"]:
            raise ValueError("Code changed after preparation")
        if (args.output / "run.json").exists():
            raise ValueError("Use a new run directory; never overwrite attempts")
        gateway = FlashGateway()
        settings = {"started_utc": datetime.now(timezone.utc).isoformat(), "settings": gateway.settings}
        write_json(args.output / "run.json", settings)
        by_id = {c["id"]: c for c in cases}
        rows = []
        def execute(job):
            item = by_id[job["case_id"]]["input"].model_copy(update={"strategy": job["strategy"]})
            return {**job, "audit": audit_answer(item, gateway)}
        with ThreadPoolExecutor(max_workers=3) as pool:
            for offset in range(0, len(protocol["schedule"]), 3):
                stop = False
                futures = [pool.submit(execute, j) for j in protocol["schedule"][offset:offset+3]]
                for future in as_completed(futures):
                    row = future.result()
                    rows.append(row)
                    with (args.output / "predictions.jsonl").open("a", encoding="utf8") as stream:
                        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    print(f"{len(rows)}/48 answer={row['case_id']} {row['strategy']} {row['audit']['status']} calls={len(row['audit']['calls'])}", flush=True)
                    stop |= any(c.get("http_status") in (401,402,403,429) for c in row["audit"]["calls"])
                if stop:
                    settings["stop_reason"] = "Provider access/balance/rate limit; all completed attempts retained"
                    break
        settings["completed_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(args.output / "run.json", settings)
    else:
        rows = read_jsonl(args.output / "predictions.jsonl")
    metrics = {s: score_answers(cases, [r for r in rows if r["strategy"] == s]) for s in ("direct", "split")}
    if args.action == "report" and (args.output / "metrics.json").exists():
        if metrics != json.loads((args.output / "metrics.json").read_text(encoding="utf8")):
            raise ValueError("Saved and recomputed metrics differ")
    else:
        write_json(args.output / "metrics.json", metrics)
    print(json.dumps({s: {k: m[k] for k in ("counts", "answer_error_recall", "gold_span_recall_half_overlap", "character_precision", "reported_tokens")}
                      for s,m in metrics.items()}, indent=2))


if __name__ == "__main__":
    main()
