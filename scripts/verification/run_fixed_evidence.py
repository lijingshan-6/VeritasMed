"""Run the predeclared Flash pilot, preserving every logical call and failure."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import subprocess
import time
from urllib.parse import urlsplit

from medrag.verification.scifact import object_hash, prepare_pilot
from medrag.verification.scoring import score
from medrag.verification.verifier import PROMPT_VERSION, SYSTEM_PROMPT, verify


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(".benchmark-runtime/scifact"))
    parser.add_argument("--manifest", type=Path,
                        default=Path("data/verification/scifact_pilot/selection.json"))
    parser.add_argument("--output", type=Path, required=True, help="New directory; never overwritten")
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=3)
    args = parser.parse_args()
    cases, regenerated = prepare_pilot(args.cache)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest != regenerated:
        raise ValueError("Inputs/selection do not match the predeclared manifest")

    # The existing factory loads the local ignored .env; the verifier itself remains independent.
    from medrag.agent.llms import make_llm_think
    if os.environ.get("LLM_BACKEND", "").lower() != "openhub":
        raise ValueError("This pilot requires the configured OpenAI-compatible Flash profile")
    model = os.environ.get("OPENHUB_MODEL", "")
    if model.lower() != "deepseek-v4.1-flash":
        raise ValueError("This pilot is fixed to DeepSeek-V4.1-Flash; no automatic model substitution")
    endpoint = urlsplit(os.environ.get("OPENHUB_BASE_URL", ""))
    if endpoint.username or endpoint.password or endpoint.query:
        raise ValueError("Endpoint must not embed credentials")
    llm = make_llm_think(structured=True)
    args.output.mkdir(parents=True, exist_ok=False)
    sources = sorted(Path("src/medrag/verification").glob("*.py"))
    sources += sorted(Path("scripts/verification").glob("*.py"))
    sources += [Path("src/medrag/agent/llms.py")]
    metadata = {
        "started_utc": datetime.now(timezone.utc).isoformat(), "baseline": "direct_flash_full_abstract",
        "prompt_version": PROMPT_VERSION, "system_prompt": SYSTEM_PROMPT,
        "manifest_sha256": object_hash(manifest), "model_requested": model,
        "base_url": endpoint.geturl(), "reasoning_effort": os.environ.get("OPENHUB_REASONING_EFFORT", "high"),
        "max_tokens": int(os.environ.get("OPENHUB_MAX_TOKENS", "32768")),
        "timeout_seconds": float(os.environ.get("LLM_TIMEOUT_SECONDS", "60")),
        "workers": args.workers, "streaming": True, "sdk_max_retries": 1,
        "logical_attempts_per_case": 1, "repair_calls": 0, "fallback": None,
        "python": platform.python_version(),
        "package_versions": {p: version(p) for p in ("langchain-openai", "langchain-core", "openai", "pydantic")},
        "git_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "code_sha256_normalized_lf": {p.as_posix(): hashlib.sha256(
            p.read_text(encoding="utf-8").encode("utf-8")).hexdigest() for p in sources},
        "note": "Declared development pilot. Requested model name is gateway routing metadata, not independently verified model identity.",
    }
    write_json(args.output / "run.json", metadata)
    records = []
    started = time.perf_counter()

    def retain(result):
        records.append(result)
        with (args.output / "predictions.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
        print(f"{len(records)}/{len(cases)} {result['case_id']} {result['status']}", flush=True)

    # First call is part of the declared sample, not a discarded probe.
    first = verify(cases[0].input, llm)
    retain(first)
    stop_reason = None
    if first["status"] == "execution_error":
        stop_reason = "First call failed; remaining paid calls not started"
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            # Batches bound requests already in flight if access/balance becomes unavailable.
            for offset in range(1, len(cases), args.workers):
                futures = [pool.submit(verify, c.input, llm) for c in cases[offset:offset + args.workers]]
                for future in as_completed(futures):
                    result = future.result()
                    retain(result)
                    if result.get("http_status") in (401, 402, 403, 429):
                        stop_reason = "Provider access, balance or rate limit; stopped after current batch"
                if stop_reason:
                    break
    metadata.update(completed_utc=datetime.now(timezone.utc).isoformat(),
                    wall_seconds=round(time.perf_counter() - started, 3), stop_reason=stop_reason)
    write_json(args.output / "run.json", metadata)
    summary = score(cases, records)
    write_json(args.output / "metrics.json", summary)
    print(json.dumps({"correct": summary["correct"], "total": summary["total"],
                      "statuses": summary["statuses"], "stop_reason": stop_reason}, indent=2))


if __name__ == "__main__":
    main()
