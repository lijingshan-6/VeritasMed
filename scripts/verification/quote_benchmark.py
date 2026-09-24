"""Small, source-disjoint whole-answer / fixed-target Flash development comparison."""
import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

from context_benchmark import select_cases, metrics_for, write_json
from medrag.verification.answer_audit import AuditInput, DIRECT_PROMPT, VERIFY_PROMPT, audit_answer, text_hash
from medrag.verification.quote_audit import QUOTE_PROMPT, FIXED_QUOTE_PROMPT, audit_quotes, audit_fixed_direct, locate_quote
from medrag.verification.scifact import object_hash, read_jsonl

SEED = "veritasmed-unique-quote-v2-2026-09-24"
ROOT = Path("data/verification/quote_v2/run01")


def cases_for(cache):
    old, prior = select_cases(cache)
    previous = old["regression"] + old["development"]
    sources = {s["source_id"]: s for s in read_jsonl(cache / "source_info.jsonl")}
    responses = read_jsonl(cache / "response.jsonl")
    excluded = {c["source_id"] for c in previous} | {r["source_id"] for r in responses if r["split"] == "test"}
    excluded_texts = {text_hash(sources[s]["source_info"]) for s in excluded if isinstance(sources[s]["source_info"], str)}
    counts, used, cases, fixed = Counter(), set(), [], []
    candidates = [r for r in responses if r["split"] == "train" and r["quality"] == "good" and r["source_id"] not in excluded
                  and sources[r["source_id"]]["task_type"] == "Summary" and len(r["response"]) <= 12000
                  and len(sources[r["source_id"]]["source_info"]) <= 50000]
    for row in sorted(candidates, key=lambda r: object_hash([SEED, r["id"]])):
        source = sources[row["source_id"]]
        digest = text_hash(source["source_info"])
        category = "annotated" if row["labels"] else "unmarked"
        if counts[category] == 4 or digest in used or digest in excluded_texts:
            continue
        item = AuditInput(answer=row["response"], sources=[{"id": row["source_id"],
                          "title": f"RAGTruth {source['source']} · source {row['source_id']}", "text": source["source_info"]}])
        cases.append({"id": row["id"], "source_id": row["source_id"], "input": item, "gold_spans": row["labels"]})
        # The task supplies a target to BOTH methods; it intentionally measures no extraction.
        if row["labels"]:
            target = row["labels"][0]["text"]
            fixed_item, expected = item, "non_support"
            origin = "First original public error span in dataset order; full original answer retained as context. Binary mapping only."
        else:
            sentences = re.split(r"(?<=[.!?])\s+|\n+", source["source_info"])
            eligible = [s for s in sentences if 40 <= len(s) <= 320 and locate_quote(source["source_info"], s)["status"] == "unique"]
            if not eligible:
                raise ValueError("Selected source has no exact-copy control; do not silently reselect after freeze")
            target = eligible[0]
            fixed_item = item.model_copy(update={"answer": target})
            expected, origin = "supported", "First 40..320 character unique source sentence/line, copied verbatim as an authored positive control. Not a human-labelled natural claim."
        if locate_quote(fixed_item.answer, target)["status"] != "unique":
            raise ValueError("Selected fixed target is ambiguous; review protocol before any calls")
        fixed.append({"id": row["id"], "source_id": row["source_id"], "input": fixed_item,
                      "target": target, "expected_binary": expected, "label_origin": origin})
        used.add(digest)
        counts[category] += 1
        if len(cases) == 8:
            break
    if len(cases) != 8:
        raise ValueError("Eight new sources required")
    repeats = [next(c["id"] for c in cases if bool(c["gold_spans"]) == positive) for positive in (True, False)]
    manifest = {"seed": SEED, "dataset_revision": prior["dataset_revision"], "files": prior["files"], "official_split": "train",
                "prior_manifest_sha256": object_hash(prior), "excluded_source_ids": sorted(excluded),
                "whole": [{"case_id": c["id"], "source_id": c["source_id"], "input_sha256": object_hash(c["input"].model_dump()),
                           "source_sha256": text_hash(c["input"].sources[0].text), "gold_spans": c["gold_spans"]} for c in cases],
                "fixed": [{k: v for k, v in c.items() if k != "input"} | {"input_sha256": object_hash(c["input"].model_dump())} for c in fixed],
                "repeat_ids": repeats, "reserved_official_test": prior["reserved_official_test"],
                "policy": "8 new development sources; 4+4 balanced, public nonmedical. All official test IDs and exact source duplicates excluded. No clinical, natural prevalence or independent semantic accuracy claim."}
    return cases, fixed, manifest


def hashes():
    paths = [Path(__file__), *[Path("src/medrag/verification") / f for f in
                             ("quote_audit.py", "answer_audit.py", "context_audit.py", "ragtruth.py", "gateway.py", "schema.py", "scifact.py")],
             Path("scripts/verification/context_benchmark.py")]
    return {p.as_posix(): text_hash(p.read_text(encoding="utf8")) for p in paths}


def summarize(cases, fixed, rows, output):
    result = {"whole": {}, "fixed": {}, "repeat": []}
    for method in ("direct", "quote_v2"):
        selected = [r for r in rows if r["task"] == "whole" and r["strategy"] == method and r["attempt"] == 1]
        result["whole"][method] = metrics_for(cases, selected)
        counts, details = Counter(), []
        for case in fixed:
            row = next((r for r in rows if r["task"] == "fixed" and r["strategy"] == method and r["case_id"] == case["id"] and r["attempt"] == 1), None)
            audit = row["audit"] if row else {}
            valid = audit.get("status") == "ok" and len(audit.get("claims", [])) == 1
            predicted = audit["claims"][0]["relation"] if valid else None
            agrees = valid and ((predicted == "supported") == (case["expected_binary"] == "supported"))
            counts.update(total=1, complete=valid, binary_agrees=agrees, non_support=case["expected_binary"] == "non_support",
                          non_support_accepted=case["expected_binary"] == "non_support" and predicted == "supported",
                          supported_control_flagged=case["expected_binary"] == "supported" and predicted in ("contradicted", "insufficient"))
            details.append({"case_id": case["id"], "expected_binary": case["expected_binary"], "predicted_relation": predicted,
                            "status": audit.get("status", "not_run"), "agrees": agrees})
        result["fixed"][method] = {"counts": dict(counts), "cases": details,
                                  "meaning": "Only binary public-error/copy-control agreement; no semantic rationale or three-class score."}
    for row in [r for r in rows if r["attempt"] == 2]:
        first = next((r for r in rows if r["attempt"] == 1 and all(r[k] == row[k] for k in ("task", "strategy", "case_id"))), None)
        def signature(r):
            return [(c["quote"], c["relation"], c["status"]) for c in r["audit"]["claims"]]
        result["repeat"].append({"task": row["task"], "case_id": row["case_id"], "first_status": first["audit"]["status"] if first else "not_run",
                                 "repeat_status": row["audit"]["status"], "exact_claim_signature_agrees": signature(first) == signature(row) if first else None})
    calls = [c for r in rows for c in r["audit"]["calls"]]
    result["execution"] = {"attempted": len(rows), "planned": 36, "complete": sum(r["audit"]["status"] == "ok" for r in rows),
        "calls_with_usage": sum(c.get("usage") is not None for c in calls),
        "reported_tokens": sum((c.get("usage") or {}).get("total_tokens", 0) for c in calls),
        "reported_models": dict(Counter(m for c in calls for m in c.get("transport_metadata", {}).get("model_identifiers", [])))}
    write_json(output / "metrics.json", result)
    print(json.dumps(result["execution"], ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "report"))
    parser.add_argument("--cache", type=Path, default=Path(".benchmark-runtime/ragtruth"))
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    cases, fixed, manifest = cases_for(args.cache)
    if args.action == "prepare":
        from medrag.verification.gateway import FlashGateway
        args.output.mkdir(parents=True, exist_ok=False)
        schedule = [{"task": task, "case_id": c["id"], "strategy": method, "attempt": 1}
                    for task, selected in (("whole", cases), ("fixed", fixed)) for c in selected for method in ("direct", "quote_v2")]
        schedule += [{"task": task, "case_id": case_id, "strategy": "quote_v2", "attempt": 2}
                     for task in ("whole", "fixed") for case_id in manifest["repeat_ids"]]
        schedule.sort(key=lambda j: object_hash([SEED, "schedule", j]))
        write_json(args.output / "manifest.json", manifest)
        write_json(args.output / "protocol.json", {"prepared_utc": datetime.now(timezone.utc).isoformat(), "schedule": schedule,
            "workers": 3, "manifest_sha256": object_hash(manifest), "code_hashes": hashes(), "settings": FlashGateway().settings,
            "prompts": {"direct_whole": DIRECT_PROMPT, "direct_fixed": VERIFY_PROMPT, "quote_whole": QUOTE_PROMPT, "quote_fixed": FIXED_QUOTE_PROMPT},
            "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "decision": "No default promotion from this small development batch. Report execution, original location scores and fixed binary agreement separately; inspect actual reasons without a model judge."})
        print(json.dumps({"calls": len(schedule), "whole": manifest["whole"], "fixed": manifest["fixed"]}, ensure_ascii=False, indent=2))
        return
    protocol = json.loads((args.output / "protocol.json").read_text(encoding="utf8"))
    if object_hash(manifest) != protocol["manifest_sha256"]:
        raise ValueError("Frozen inputs changed")
    if args.action == "report":
        summarize(cases, fixed, read_jsonl(args.output / "predictions.jsonl"), args.output)
        return
    from medrag.verification.gateway import FlashGateway
    gateway = FlashGateway()
    if hashes() != protocol["code_hashes"] or gateway.settings != protocol["settings"]:
        raise ValueError("Code/settings changed after freeze")
    if (args.output / "run.json").exists() or (args.output / "predictions.jsonl").exists():
        raise ValueError("Keep original attempts; never overwrite")
    lookup = {task: {c["id"]: c for c in selected} for task, selected in (("whole", cases), ("fixed", fixed))}
    def execute(job):
        case = lookup[job["task"]][job["case_id"]]
        if job["task"] == "fixed":
            fn = audit_fixed_direct if job["strategy"] == "direct" else audit_quotes
            audit = fn(case["input"], gateway, case["target"])
        else:
            audit = (audit_answer if job["strategy"] == "direct" else audit_quotes)(case["input"], gateway)
        return {**job, "audit": audit}
    state = {"started_utc": datetime.now(timezone.utc).isoformat(), "settings": gateway.settings}
    write_json(args.output / "run.json", state)
    rows, jobs, stop = [], iter(protocol["schedule"]), False
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = {pool.submit(execute, next(jobs)) for _ in range(3)}
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                row = future.result()
                rows.append(row)
                with (args.output / "predictions.jsonl").open("a", encoding="utf8") as stream:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(f"{len(rows)}/36 {row['task']} {row['case_id']} {row['strategy']} #{row['attempt']} {row['audit']['status']}", flush=True)
                stop |= any(c.get("http_status") in (401, 402, 403, 429) for c in row["audit"]["calls"])
            if not stop:
                for _ in done:
                    job = next(jobs, None)
                    if job:
                        pending.add(pool.submit(execute, job))
    state.update(finished_utc=datetime.now(timezone.utc).isoformat(), attempted=len(rows), all_attempted=len(rows) == len(protocol["schedule"]),
                 stop_reason="Provider access/balance/rate limit; keep attempts" if stop else None)
    write_json(args.output / "run.json", state)
    summarize(cases, fixed, rows, args.output)


if __name__ == "__main__":
    main()
