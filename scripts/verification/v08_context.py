"""Run the frozen constructed intent cases. No retrieval or clinical scoring."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from medrag.agent.conversation import ContextTurn, RESOLUTION_PROMPT, resolve_context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "data/verification/v08/context-dev.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases_bytes = args.cases.read_bytes()
    data = json.loads(cases_bytes)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "manifest.json").write_text(json.dumps({
        "scope": "Developer-constructed intent diagnostics, not clinical gold or held-out semantic evaluation",
        "case_sha256": sha256(cases_bytes).hexdigest(), "cases": data,
        "prompt": RESOLUTION_PROMPT,
        "resolver_sha256": sha256((ROOT / "src/medrag/agent/conversation.py").read_bytes()).hexdigest(),
        "max_parallel_calls": 3, "retries": "No semantic retry; provider transport follows configured factory",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def run(case):
        try:
            result = resolve_context(case["query"], [ContextTurn(**c) for c in case["context"]]).model_dump()
            expect = case["expected"]
            reference = result["resolved_query"].split("(not evidence):\n", 1)[-1].lower()
            checks = {"mode": result["status"] == expect["mode"],
                      "exact_question": result["needs_clarification"] or result["resolved_query"].startswith(case["query"]),
                      "referent": all(term.lower() in reference for term in expect.get("reference_contains", [])),
                      "scope": all(term.lower() not in reference for term in expect.get("reference_excludes", []))}
            record = {"id": case["id"], "result": result, "checks": checks, "passed": all(checks.values())}
        except Exception as error:
            # Never serialize upstream exception strings which may contain request details.
            record = {"id": case["id"], "passed": False, "error_type": type(error).__name__}
        (args.output / f"{case['id']}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{case['id']}: {'pass' if record['passed'] else 'review'}", flush=True)
        return record

    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(run, data["cases"]))
    summary = {"scope": data["scope"], "cases": len(records), "passed": sum(r["passed"] for r in records),
               "review": [r["id"] for r in records if not r["passed"]],
               "total_tokens": sum((r.get("result", {}).get("usage") or {}).get("total_tokens", 0) for r in records),
               "interpretation": "Pass means the declared intent checks passed, not that an answer or medical claim is correct."}
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
