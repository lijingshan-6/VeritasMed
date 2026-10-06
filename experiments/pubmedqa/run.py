"""Run answer arms and the verdict judge on a frozen split, within a spending limit.

    python experiments/pubmedqa/run.py answer --split pilot --arms A0,A1,A2,A4
    python experiments/pubmedqa/run.py judge  --split pilot --arms A0,A1,A2,A4

- One attempt per question and arm; failures are kept. Re-running resumes missing items only.
- Spending is priced from the usage each call reports (default-group prices, 2x in the gateway's
  peak windows) and appended to a ledger. Dispatch stops before the --budget for --key is reached.
- No new work starts in the gateway's peak windows unless --allow-peak is given.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNTIME = ROOT / ".exp-runtime" / "pubmedqa"
os.environ.setdefault("QDRANT_PATH", str(RUNTIME / "qdrant"))
os.environ.setdefault("QDRANT_COLLECTION", "pubmedqa_exp")
os.environ.setdefault("MEDRAG_DATA_DIR", str(RUNTIME))
# A3 runs the same harness against another source tree (the verbatim variant, see a3-verbatim.patch).
sys.path.insert(0, os.environ.get("MEDRAG_SRC", str(ROOT / "src")))
sys.path.insert(0, str(HERE))

import pyarrow  # noqa: E402,F401  -- native runtimes must load before Qdrant on Windows
import sentence_transformers  # noqa: E402,F401

import arms  # noqa: E402

PRICE = {"input": 0.256849, "output": 0.770548}  # USD per 1M tokens, default group
SHANGHAI = timezone(timedelta(hours=8))
ARMS = {"A0": "closed_book", "A1": "vanilla_rag", "A2": "veritasmed", "A3": "veritasmed_verbatim", "A4": "gold_context", "A5": "strict_rag"}
LEDGER = RUNTIME / "ledger.jsonl"
_lock = threading.Lock()


def peak(now: datetime | None = None) -> bool:
    t = (now or datetime.now(SHANGHAI)).astimezone(SHANGHAI)
    return t.weekday() < 5 and (9 <= t.hour < 12 or 14 <= t.hour < 18)


def cost(usage: list[dict], at: datetime) -> float:
    mult = 2.0 if peak(at) else 1.0
    return sum(((u.get("input_tokens") or 0) * PRICE["input"] + (u.get("output_tokens") or 0) * PRICE["output"]) / 1e6
               for u in usage) * mult


def spent(key: str) -> float:
    if not LEDGER.exists():
        return 0.0
    return sum(r["usd"] for r in map(json.loads, LEDGER.read_text(encoding="utf8").splitlines()) if r["key"] == key)


def charge(key: str, label: str, usage: list[dict]) -> float:
    now = datetime.now(SHANGHAI)
    usd = cost(usage, now)
    with _lock, LEDGER.open("a", encoding="utf8") as f:
        f.write(json.dumps({"at": now.isoformat(), "key": key, "item": label, "usd": round(usd, 6), "calls": len(usage),
                            "missing_usage": sum(1 for u in usage if u.get("output_tokens") is None)}) + "\n")
    return usd


def done(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {r["pmid"]: r for r in map(json.loads, path.read_text(encoding="utf8").splitlines())}


def append(path: Path, row: dict) -> None:
    with _lock, path.open("a", encoding="utf8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


class Guard:
    """Stops dispatch at the budget (with a per-item reserve) or at the start of a peak window."""
    def __init__(self, key: str, budget: float, reserve: float, allow_peak: bool):
        self.key, self.budget, self.reserve, self.allow_peak = key, budget, reserve, allow_peak
        self.stopped = ""

    def ok(self) -> bool:
        if self.stopped:
            return False
        if not self.allow_peak and peak():
            self.stopped = "peak window started"
        elif spent(self.key) + self.reserve > self.budget:
            self.stopped = f"budget reached (${spent(self.key):.2f} of ${self.budget:.2f} for key '{self.key}')"
        return not self.stopped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["answer", "judge"])
    ap.add_argument("--split", required=True, choices=["pilot", "dev", "test", "test_full"])
    ap.add_argument("--arms", default="A0,A1,A2,A4")
    ap.add_argument("--run", default="main", help="results go to experiments/pubmedqa/runs/<run>/")
    ap.add_argument("--key", default="key2", help="ledger label of the API key being spent")
    ap.add_argument("--budget", type=float, default=12.8, help="USD limit for this key")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--allow-peak", action="store_true")
    ap.add_argument("--retry-errors", action="store_true", help="re-run items whose last attempt failed (kept in the file)")
    args = ap.parse_args()
    if ("A3" in args.arms.split(",")) != ("MEDRAG_SRC" in os.environ):
        sys.exit("A3 must run alone with MEDRAG_SRC pointing at the verbatim source tree")

    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf8"))
    questions = json.loads((RUNTIME / "questions.json").read_text(encoding="utf8"))
    ids = manifest["splits"][args.split]
    out_dir = HERE / "runs" / args.run
    out_dir.mkdir(parents=True, exist_ok=True)

    from medrag.verification.gateway import FlashGateway
    gateway = FlashGateway()
    retrieve = None
    if args.stage == "answer" and ({"A1", "A2", "A3", "A5"} & set(args.arms.split(","))):
        # Open the embedded store and load models once, before worker threads race to do it.
        from medrag.agent.nodes.retrieval import _get_reranker, _get_retriever
        _get_retriever(); _get_reranker()
        retrieve = arms.make_retriever()
    reserve = {"answer": 0.08, "judge": 0.004}[args.stage]  # worst-case cost of one more item
    guard = Guard(args.key, args.budget, reserve, args.allow_peak)

    for arm in args.arms.split(","):
        name = ARMS[arm]
        path = out_dir / f"{args.split}-{arm}.jsonl"
        if args.stage == "judge":
            source, path = done(path), out_dir / f"{args.split}-{arm}.judged.jsonl"
            previous = done(path)
            todo = [p for p in ids if p in source and source[p]["status"] == "ok"
                    and (p not in previous or (args.retry_errors and previous[p]["status"] != "ok"))]
        else:
            previous = done(path)  # the last attempt per question wins; earlier attempts stay in the file
            todo = [p for p in ids if p not in previous or (args.retry_errors and previous[p]["status"] != "ok")]
        print(f"[{arm} {name} · {args.stage}] {len(todo)} to run · spent ${spent(args.key):.2f}", flush=True)

        def work(pmid: str) -> None:
            if not guard.ok():
                return
            q = questions[pmid]
            if args.stage == "judge":
                try:
                    verdict, usage = arms.judge(gateway, q, source[pmid]["answer"])
                    row = {"pmid": pmid, "arm": arm, "verdict": verdict, "label": q["label"], "usage": [usage], "status": "ok"}
                except Exception as exc:  # noqa: BLE001
                    row = {"pmid": pmid, "arm": arm, "verdict": None, "label": q["label"], "usage": [], "status": "error", "error_type": type(exc).__name__}
            else:
                fn = {"A0": lambda: arms.closed_book(gateway, q), "A1": lambda: arms.vanilla_rag(gateway, q, retrieve),
                      "A2": lambda: arms.veritasmed(q), "A3": lambda: arms.veritasmed(q), "A4": lambda: arms.gold_context(gateway, q),
                      "A5": lambda: arms.strict_rag(gateway, q, retrieve)}[arm]
                row = {"pmid": pmid, "arm": arm, "question": q["question"], **arms.timed(fn)}
            row["usd"] = round(charge(args.key, f"{args.split}/{arm}/{args.stage}/{pmid}", row["usage"]), 6)
            append(path, row)

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(work, todo))
        rows = done(path)
        print(f"  saved {len(rows)}/{len(ids)} · errors {sum(r['status'] != 'ok' for r in rows.values())} · spent ${spent(args.key):.2f}", flush=True)
        if guard.stopped:
            print(f"STOPPED: {guard.stopped}. Re-run the same command to resume.", flush=True)
            return


if __name__ == "__main__":
    main()
