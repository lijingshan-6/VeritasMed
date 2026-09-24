"""Freeze, execute, or offline-report the source-grouped diagnostic comparison."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import time

from medrag.verification.diagnostics import load_diagnostics
from medrag.verification.scifact import object_hash, read_jsonl
from medrag.verification.scoring import score
from medrag.verification.structured import PROMPTS, verify_structured
from medrag.verification.verifier import SYSTEM_PROMPT, verify

ARMS = ("direct", "structured", "structured_no_fields")
SEED = "controlled-v1-interleaved-2026-09-24"
SPEC = Path("data/verification/controlled_v1/families.json")
POLICY = Path("docs/verification-label-policy.md")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def code_hashes():
    files = sorted(Path("src/medrag/verification").glob("*.py"))
    files += [Path(__file__), Path("src/medrag/config.py")]
    root = Path.cwd()
    return {p.resolve().relative_to(root).as_posix(): hashlib.sha256(
        p.read_text(encoding="utf-8").encode("utf-8")).hexdigest() for p in files}


def comparison_report(cases, manifest, records):
    scores, lookup = {}, {}
    case_meta = {c["case_id"]: c for c in manifest["cases"]}
    for arm in ARMS:
        rows = [r for r in records if r["arm"] == arm]
        lookup[arm] = {r["case_id"]: r for r in rows}
        metrics = score(cases, rows)
        metrics["interpretation"] = "Constructed development diagnostics, AI reviewed; source deletion and minimal edits, not independently expert-labelled clinical validation."
        families = {}
        for case in cases:
            meta = case_meta[case.input.case_id]
            result = lookup[arm].get(case.input.case_id)
            matched = bool(result and result["status"] == "ok" and result["decision"]["relation"] == case.relation)
            families.setdefault(meta["family_id"], {})[meta["variant"]] = matched
        metrics["families"] = families
        metrics["quartets_all_correct"] = sum(all(v.values()) for v in families.values())
        metrics["equivalent_pair_both_supported"] = sum(v["supported"] and v["equivalent"] for v in families.values())
        metrics["withheld_correctly_insufficient"] = sum(v["withheld"] for v in families.values())
        metrics["response_models"] = dict(Counter(
            "|".join(r.get("transport_metadata", {}).get("model_identifiers", [])) or "unavailable" for r in rows))
        if arm != "direct":
            no_reducer = []
            changed = []
            for row in rows:
                clone = dict(row)
                if row["status"] == "ok":
                    clone.update(decision=row["model_decision"], evidence=row["model_evidence"])
                    if row["decision"]["relation"] != row["model_decision"]["relation"]:
                        changed.append(row["case_id"])
                no_reducer.append(clone)
            ablation = score(cases, no_reducer)
            metrics["without_reducer"] = {k: ablation[k] for k in ("correct", "total", "unsupported_accepted", "mismatches")}
            metrics["reducer_changed_cases"] = changed
        scores[arm] = metrics
    paired = {}
    for arm in ARMS[1:]:
        counts = Counter()
        discordant = []
        for case in cases:
            good = []
            for name in ("direct", arm):
                r = lookup[name].get(case.input.case_id)
                good.append(bool(r and r["status"] == "ok" and r["decision"]["relation"] == case.relation))
            category = "both_correct" if all(good) else "both_wrong_or_unrun" if not any(good) else "direct_only" if good[0] else "alternative_only"
            counts[category] += 1
            if good[0] != good[1]:
                discordant.append({"case_id": case.input.case_id, "outcome": category})
        paired[arm] = {"counts": dict(counts), "discordant": discordant}
    return {"arms": scores, "paired_with_direct": paired,
            "note": "Exploratory paired diagnostics on 12 source groups. No significance or superiority claim; gateway model identity is not independently authenticated."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "report"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path(".benchmark-runtime/scifact"))
    args = parser.parse_args()
    cases, manifest = load_diagnostics(args.cache, SPEC)
    if args.action == "prepare":
        args.output.mkdir(parents=True, exist_ok=False)
        # Randomized blocks keep all three arms close in time for each case.
        schedule = []
        for case in sorted(cases, key=lambda c: object_hash([SEED, c.input.case_id])):
            for arm in sorted(ARMS, key=lambda a: object_hash([SEED, case.input.case_id, a])):
                schedule.append({"case_id": case.input.case_id, "arm": arm})
        write_json(args.output / "manifest.json", manifest)
        write_json(args.output / "protocol.json", {
            "prepared_utc": datetime.now(timezone.utc).isoformat(), "schedule": schedule,
            "schedule_seed": SEED, "workers": 3, "logical_calls": len(schedule),
            "calls_per_case_per_arm": 1, "prompts": {"direct": SYSTEM_PROMPT, **PROMPTS},
            "manifest_sha256": object_hash(manifest), "code_sha256_normalized_lf": code_hashes(),
            "policy_sha256_normalized_lf": hashlib.sha256(POLICY.read_text(encoding="utf-8").encode("utf-8")).hexdigest(),
            "git_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "preregistered_scope": "Development diagnostics; all results retained, no prompt tuning during run",
        })
        print(f"Prepared {len(cases)} cases / {len(schedule)} calls before inference")
        return
    protocol = json.loads((args.output / "protocol.json").read_text(encoding="utf-8"))
    if protocol["manifest_sha256"] != object_hash(manifest):
        raise ValueError("Source/specification changed since preparation")
    if args.action == "run":
        from medrag.verification.gateway import FlashGateway
        if protocol["code_sha256_normalized_lf"] != code_hashes():
            raise ValueError("Code changed since preparation; use a new run directory")
        if (args.output / "predictions.jsonl").exists() or (args.output / "run.json").exists():
            raise ValueError("Run already started; never overwrite earlier attempts")
        gateway = FlashGateway()
        write_json(args.output / "run.json", {
            "started_utc": datetime.now(timezone.utc).isoformat(), "settings": gateway.settings,
            "package_versions": {p: version(p) for p in ("openai", "pydantic", "langchain-core")},
        })
        by_id = {c.input.case_id: c for c in cases}
        records = []
        started = time.perf_counter()

        def execute(job):
            item = by_id[job["case_id"]].input
            if job["arm"] == "direct":
                class Capture:
                    metadata = {}

                    def invoke(self, messages):
                        response = gateway.invoke(messages)
                        self.metadata = response.response_metadata
                        return response
                capture = Capture()
                result = verify(item, capture)
                result["transport_metadata"] = capture.metadata
            else:
                result = verify_structured(item, gateway, job["arm"])
            return {**result, "arm": job["arm"]}

        stopped = None
        with ThreadPoolExecutor(max_workers=3) as pool:
            for offset in range(0, len(protocol["schedule"]), 3):
                futures = [pool.submit(execute, job) for job in protocol["schedule"][offset:offset+3]]
                for future in as_completed(futures):
                    result = future.result()
                    records.append(result)
                    with (args.output / "predictions.jsonl").open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                    print(f"{len(records)}/{len(protocol['schedule'])} {result['arm']} {result['case_id']} {result['status']}", flush=True)
                    if result.get("http_status") in (401, 402, 403, 429):
                        stopped = "Provider access, balance or rate limit; current batch retained"
                if stopped:
                    break
        settings = json.loads((args.output / "run.json").read_text(encoding="utf-8"))
        settings.update(completed_utc=datetime.now(timezone.utc).isoformat(),
                        wall_seconds=round(time.perf_counter()-started, 3), stop_reason=stopped)
        write_json(args.output / "run.json", settings)
    else:
        records = read_jsonl(args.output / "predictions.jsonl")
    report = comparison_report(cases, manifest, records)
    metrics_path = args.output / "metrics.json"
    if args.action == "report" and metrics_path.exists():
        if json.loads(metrics_path.read_text(encoding="utf-8")) != report:
            raise ValueError("Offline results differ from saved metrics")
    else:
        write_json(metrics_path, report)
    print(json.dumps({arm: {k: m[k] for k in ("correct", "total", "statuses", "quartets_all_correct", "response_models")}
                      for arm, m in report["arms"].items()}, indent=2))


if __name__ == "__main__":
    main()
