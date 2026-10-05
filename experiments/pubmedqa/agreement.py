"""Second judge for citation support: Flash re-judges the sentences MiniCheck scored.

    python experiments/pubmedqa/agreement.py            # judge 100 questions x A1, A2, A4
    python experiments/pubmedqa/agreement.py --report

Rules (fixed before any output is read):
- Questions: 100 drawn with a fixed seed from the main run's test_full split; arms A1, A2, A4.
- Unit: every non-absence sentence that carries a citation, judged against the passages the
  method showed for the PMIDs it cites (the same input MiniCheck saw). One call per answer.
- Reported: agreement and Cohen's kappa between Flash and MiniCheck; each arm's unsupported rate
  among cited sentences under both judges; the VeritasMed - plain RAG gap under Flash with a
  paired bootstrap interval. Caveat: Flash also generated and checked VeritasMed's answers, so it
  may favour them; MiniCheck shares no model with any method.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run  # noqa: E402

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

SEED = 20261005
N = 100
ARMS = ["A1", "A2", "A4"]
NAMES = {"A1": "Plain RAG", "A2": "VeritasMed", "A4": "Gold abstract"}
OUT = HERE / "runs" / "agreement"
JUDGE = """You check citations. For each numbered sentence, decide whether its cited passages
establish all of its material content (numbers, direction of findings, population, comparison,
strength of the conclusion). Ordinary paraphrase is fine; outside knowledge is not. A sentence is
not supported if any material part is missing from or contradicted by its cited passages.
Return JSON only: {"judgments": [{"id": <number>, "supported": true | false}, ...]} with one item
per sentence."""


def load(name: str) -> dict:
    path = HERE / "runs" / "main" / name
    return {r["pmid"]: r for r in map(json.loads, path.read_text(encoding="utf8").splitlines())}


def units(arm: str, pmids: list[str]) -> dict[str, dict]:
    answers, scored = load(f"test_full-{arm}.jsonl"), load(f"test_full-{arm}.scored.jsonl")
    out = {}
    for pmid in pmids:
        row, sc = answers.get(pmid), scored.get(pmid)
        if not row or row["status"] != "ok" or not sc:
            continue
        sents = [(i, s) for i, s in enumerate(sc["sentences"]) if not s["absence"] and s["cites"]]
        keys = sorted({k for _, s in sents for k in s["cites"]})
        passages = {k: "\n\n".join(c["text"] for c in row["chunks"] if f"PMID:{c['doc_id']}" == k) for k in keys}
        out[pmid] = {"sentences": [{"id": i, "text": s["text"], "cites": s["cites"], "minicheck": s.get("cited")} for i, s in sents],
                     "passages": {k: v for k, v in passages.items() if v}}
    return out


def kappa(pairs: list[tuple[int, int]]) -> float:
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default="key2")
    ap.add_argument("--budget", type=float, default=12.8)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--allow-peak", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ids = sorted(json.loads((HERE / "manifest.json").read_text())["splits"]["test_full"])
    pmids = sorted(random.Random(SEED).sample(ids, N))
    if args.report:
        return report(pmids)

    from medrag.verification.gateway import FlashGateway
    gateway = FlashGateway()
    guard = run.Guard(args.key, args.budget, 0.03, args.allow_peak)
    for arm in ARMS:
        path = OUT / f"test_full-{arm}.jsonl"
        previous = run.done(path)
        todo = [(p, u) for p, u in units(arm, pmids).items() if u["sentences"] and p not in previous]
        print(f"[{arm} · flash judge] {len(todo)} to run · spent ${run.spent(args.key):.2f}", flush=True)

        def work(job, arm=arm, path=path) -> None:
            pmid, unit = job
            if not guard.ok():
                return
            row = {"pmid": pmid, "arm": arm, "usage": []}
            try:
                payload = {"passages": unit["passages"],
                           "sentences": [{"id": s["id"], "text": s["text"], "cites": s["cites"]} for s in unit["sentences"]]}
                response = gateway.invoke([SystemMessage(content=JUDGE), HumanMessage(content=json.dumps(payload, ensure_ascii=False))])
                row["usage"].append(dict(response.usage_metadata or {}))
                got = {int(j["id"]): bool(j["supported"]) for j in json.loads(response.content)["judgments"]
                       if isinstance(j, dict) and isinstance(j.get("supported"), bool)}
                row["sentences"] = [{**s, "flash": int(got[s["id"]]) if s["id"] in got else None} for s in unit["sentences"]]
                row["status"] = "ok" if all(s["flash"] is not None for s in row["sentences"]) else "partial"
            except Exception as exc:  # noqa: BLE001 - kept as a result
                row.update(status="error", error_type=type(exc).__name__, error=str(exc)[:300])
            row["usd"] = round(run.charge(args.key, f"agreement/{arm}/{pmid}", row["usage"]), 6)
            run.append(path, row)

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(work, todo))
        rows = run.done(path)
        print(f"  saved {len(rows)} · {dict(Counter(r['status'] for r in rows.values()))} · spent ${run.spent(args.key):.2f}", flush=True)
        if guard.stopped:
            print(f"STOPPED: {guard.stopped}. Re-run the same command to resume.", flush=True)
            return


def report(pmids: list[str]) -> None:
    per_arm, lines = {}, []
    for arm in ARMS:
        rows = run.done(OUT / f"test_full-{arm}.jsonl")
        per_arm[arm] = {p: [s for s in r.get("sentences", []) if s.get("flash") is not None and s.get("minicheck") is not None]
                        for p, r in rows.items()}
    pairs = [(s["flash"], s["minicheck"]) for arm in ARMS for sents in per_arm[arm].values() for s in sents]
    agree = sum(a == b for a, b in pairs) / len(pairs)
    lines += [f"Flash vs MiniCheck on {len(pairs)} cited sentences ({N} questions x {', '.join(ARMS)}): "
              f"agreement {100 * agree:.1f}%, Cohen's kappa {kappa(pairs):.2f}", "",
              "| Method | Sentences | Unsupported (MiniCheck) | Unsupported (Flash) | Agreement |", "|---|---|---|---|---|"]
    rate = lambda sents, key: 1 - sum(s[key] for s in sents) / len(sents)  # noqa: E731
    for arm in ARMS:
        sents = [s for v in per_arm[arm].values() for s in v]
        lines.append(f"| {NAMES[arm]} | {len(sents)} | {100 * rate(sents, 'minicheck'):.1f}% | {100 * rate(sents, 'flash'):.1f}% | "
                     f"{100 * sum(s['flash'] == s['minicheck'] for s in sents) / len(sents):.1f}% |")
    # Paired bootstrap of the A2 - A1 unsupported-rate gap under each judge, over shared questions.
    shared = sorted(set(per_arm["A1"]) & set(per_arm["A2"]))
    rng = random.Random(SEED)

    def gap(sample, key):
        a = [s for p in sample for s in per_arm["A2"][p]]
        b = [s for p in sample for s in per_arm["A1"][p]]
        return rate(a, key) - rate(b, key) if a and b else None

    lines.append("")
    for key in ("minicheck", "flash"):
        diffs = sorted(d for d in (gap([rng.choice(shared) for _ in shared], key) for _ in range(10_000)) if d is not None)
        lines.append(f"VeritasMed - plain RAG, unsupported among cited sentences ({key}): {100 * gap(shared, key):+.1f} pp "
                     f"[{100 * diffs[int(0.025 * len(diffs))]:+.1f}, {100 * diffs[int(0.975 * len(diffs)) - 1]:+.1f}] over {len(shared)} questions")
    cost = sum(r["usd"] for arm in ARMS for r in run.done(OUT / f"test_full-{arm}.jsonl").values())
    lines += ["", f"Cost ${cost:.2f}. Flash also generated and checked VeritasMed's answers and may favour them."]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
