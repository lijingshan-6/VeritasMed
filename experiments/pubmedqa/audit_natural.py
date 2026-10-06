"""E2: run the Direct audit on plain-RAG answers and compare its flags with the Flash citation judge.

    python experiments/pubmedqa/audit_natural.py            # 100 audits (judge-agreement sample)
    python experiments/pubmedqa/audit_natural.py --report

Registered in PREREGISTRATION-followup.md. Reference label per non-absence sentence: Flash
citation judgment, uncited = unsupported. Flagged: a valid audit claim overlapping the sentence
is contradicted or insufficient.
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
from planted import flagged, sources, split, wilson  # noqa: E402

SEED, N, ARM = 20261005, 100, "A1"
OUT = HERE / "runs" / "audit-natural"


def load(path: Path) -> dict:
    return {r["pmid"]: r for r in map(json.loads, path.read_text(encoding="utf8").splitlines())} if path.exists() else {}


def sample() -> list[str]:
    ids = sorted(json.loads((HERE / "manifest.json").read_text())["splits"]["test_full"])
    return sorted(random.Random(SEED).sample(ids, N))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default="key3")
    ap.add_argument("--budget", type=float, default=13.5)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--allow-peak", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"test_full-{ARM}-audits.jsonl"
    if args.report:
        return report(path)

    from medrag.verification.answer_audit import AuditRequest, audit_answer
    from medrag.verification.gateway import FlashGateway
    gateway = FlashGateway()
    answers = load(HERE / "runs" / "main" / f"test_full-{ARM}.jsonl")
    previous = run.done(path)
    todo = [p for p in sample() if p not in previous and answers.get(p, {}).get("status") == "ok"]
    guard = run.Guard(args.key, args.budget, 0.03, args.allow_peak)
    print(f"[audit-natural] {len(todo)} to run · spent ${run.spent(args.key):.2f}", flush=True)

    def work(pmid: str) -> None:
        if not guard.ok():
            return
        row = answers[pmid]
        answer = " ".join(row["answer"].split())
        out = {"pmid": pmid, "arm": ARM, "usage": []}
        try:
            audit = audit_answer(AuditRequest(answer=answer, sources=sources(row["chunks"]), strategy="direct"), gateway)
            out["usage"] = [c["usage"] for c in audit["calls"] if c.get("usage")]
            out.update(status="ok", audit_status=audit["status"], answer=answer,
                       sentences=[{"span": list(sp), **flagged(audit, sp)} for sp in split(answer)], audit=audit)
        except Exception as exc:  # noqa: BLE001 - kept as a result
            out.update(status="error", error_type=type(exc).__name__, error=str(exc)[:300])
        out["usd"] = round(run.charge(args.key, f"audit-natural/{ARM}/{pmid}", out["usage"]), 6)
        run.append(path, out)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, todo))
    rows = run.done(path)
    print(f"  saved {len(rows)} · {dict(Counter(r['status'] for r in rows.values()))} · spent ${run.spent(args.key):.2f}", flush=True)


def report(path: Path) -> None:
    audits = run.done(path)
    scored = load(HERE / "runs" / "main" / f"test_full-{ARM}.scored.jsonl")
    flash = {p: {s["id"]: s["flash"] for s in r.get("sentences", []) if s.get("flash") is not None}
             for p, r in load(HERE / "runs" / "agreement" / f"test_full-{ARM}.jsonl").items()}
    units, skipped = [], 0
    for pmid, a in audits.items():
        if a["status"] != "ok" or len(a["sentences"]) != len(scored[pmid]["sentences"]):
            skipped += 1
            continue
        for i, (au, sc) in enumerate(zip(a["sentences"], scored[pmid]["sentences"])):
            if sc["absence"]:
                continue
            ref = 0 if not sc["cites"] else flash.get(pmid, {}).get(i)
            if ref is None:
                continue
            units.append({"pmid": pmid, "i": i, "bottom": i == 0, "unsupported": ref == 0, "flagged": au["flagged"],
                          "contradicted": au["contradicted"], "covered": au["covered"], "cited": bool(sc["cites"])})
    lines = [f"E2: Direct audit on {len(audits)} plain-RAG answers ({skipped} skipped); {len(units)} sentences with a reference label; "
             f"cost ${sum(r['usd'] for r in audits.values()):.2f}", "",
             "| Sentences | Reference unsupported: flagged by audit | Reference supported: flagged by audit |", "|---|---|---|"]
    summary = {}
    for name, sel in [("all", units), ("bottom lines", [u for u in units if u["bottom"]]),
                      ("cited only", [u for u in units if u["cited"]]), ("other sentences", [u for u in units if not u["bottom"]])]:
        bad, good = [u for u in sel if u["unsupported"]], [u for u in sel if not u["unsupported"]]
        cell = lambda xs: (f"{sum(x['flagged'] for x in xs)}/{len(xs)} = {100 * sum(x['flagged'] for x in xs) / len(xs):.0f}% "  # noqa: E731
                           f"[{100 * wilson(sum(x['flagged'] for x in xs), len(xs))[0]:.0f}, {100 * wilson(sum(x['flagged'] for x in xs), len(xs))[1]:.0f}]") if xs else "—"
        lines.append(f"| {name} | {cell(bad)} | {cell(good)} |")
        summary[name] = {"unsupported": [sum(x["flagged"] for x in bad), len(bad)], "supported": [sum(x["flagged"] for x in good), len(good)]}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf8")
    (OUT / "units.jsonl").write_text("".join(json.dumps(u) + "\n" for u in units), encoding="utf8")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
