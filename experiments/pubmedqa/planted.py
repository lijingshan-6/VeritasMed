"""Planted-error study: does the Direct audit flag errors we insert, and how often does it flag the
same sentence when it is left untouched?

    python experiments/pubmedqa/planted.py --n 200          # plant, then audit clean + planted
    python experiments/pubmedqa/planted.py --n 200 --report

Rules (fixed before any audit output is read):
- Pool: VeritasMed (A2) answers from the main run. A target sentence is a cited, non-absence
  sentence that MiniCheck judged supported by its own cited passages, so the clean version is
  (independently) supported before we touch it.
- Four error types, assigned round-robin over a seeded shuffle; an answer gets the first type
  that fits it (number needs a digit in the sentence):
    number      one reported number changed
    direction   direction or significance of one finding reversed
    population  population, comparison group or setting replaced by one the study did not involve
    overreach   finding stated more strongly than the study supports (causal, universal, certain)
- Flash rewrites only the target sentence. Invalid rewrites (unchanged, citation lost) are kept
  as planting failures and excluded; the replacement is not re-drawn.
- Each answer is audited twice, clean and planted, with the same sources (the passages the
  method used, one source per PMID). One attempt each; failures are kept.
- Flagged: some valid audit claim whose answer span overlaps the target sentence has relation
  contradicted or insufficient. Detection = flagged in the planted answer; false alarm = flagged
  in the clean answer. Audit failures count as not flagged (reported separately).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run  # noqa: E402  (sets the experiment environment, ledger and guards)

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

SEED = 20261005
TYPES = ["number", "direction", "population", "overreach"]
CITE = re.compile(r"\[(PMID:\d+)\]")
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
OUT = HERE / "runs" / "planted"
PLANT = """You help build a test set for a citation checker. Rewrite ONE sentence from a biomedical
answer so that it contains exactly one error of the requested type, and is otherwise unchanged.
The error must make the sentence wrong with respect to the study, while staying fluent and
plausible. Keep every citation marker such as [PMID:123] exactly as it is.
Types:
- number: change one reported number (count, percentage, ratio, p-value, interval, duration).
- direction: reverse the direction or significance of one finding (higher<->lower,
  improved<->worsened, significant<->not significant, associated<->not associated).
- population: replace the population, comparison group or setting with one the study did not
  involve (e.g. children<->adults, intervention<->control, inpatients<->outpatients).
- overreach: state the finding more strongly than the study supports (association -> causation,
  some -> all patients, suggests -> proves); do not change numbers.
Return JSON only: {"modified": "<the full rewritten sentence>", "changed_from": "<original words>",
"changed_to": "<new words>"}"""


def split(answer: str) -> list[tuple[int, int]]:
    """Character spans of sentences, using the scoring splitter."""
    spans, start = [], 0
    for m in SENTENCE.finditer(answer):
        spans.append((start, m.start()))
        start = m.end()
    spans.append((start, len(answer)))
    return [(a, b) for a, b in spans if answer[a:b].strip()]


def load(name: str) -> dict:
    path = HERE / "runs" / "main" / name
    return {r["pmid"]: r for r in map(json.loads, path.read_text(encoding="utf8").splitlines())}


def candidates() -> list[dict]:
    answers, scored = load("test_full-A2.jsonl"), load("test_full-A2.scored.jsonl")
    pool = []
    for pmid in sorted(answers):
        row, sc = answers[pmid], scored.get(pmid)
        if row["status"] != "ok" or not sc:
            continue
        answer = " ".join(row["answer"].split())  # same normalisation as score.py
        spans = split(answer)
        if len(spans) != len(sc["sentences"]):
            continue
        targets = [i for i, s in enumerate(sc["sentences"])
                   if not s["absence"] and s["cites"] and s.get("cited") == 1]
        if targets:
            pool.append({"pmid": pmid, "answer": answer, "spans": spans, "targets": targets, "chunks": row["chunks"]})
    return pool


def assign(pool: list[dict], n: int) -> list[dict]:
    rng = random.Random(SEED)
    rng.shuffle(pool)
    items, counts = [], Counter()
    for entry in pool:
        if len(items) == n:
            break
        for kind in sorted(TYPES, key=lambda t: (counts[t], TYPES.index(t))):
            fits = [i for i in entry["targets"]
                    if kind != "number" or re.search(r"\d", CITE.sub("", entry["answer"][slice(*entry["spans"][i])]))]
            if fits:
                i = rng.choice(fits)
                items.append({**entry, "type": kind, "target": i})
                counts[kind] += 1
                break
    return items


def sources(chunks: list[dict]):
    from medrag.verification.answer_audit import AuditSource
    by_doc: dict[str, list[str]] = {}
    for c in chunks:
        by_doc.setdefault(c["doc_id"], []).append(c["text"])
    return [AuditSource(id=f"PMID:{d}", title=f"PubMed {d}", text="\n\n".join(texts)) for d, texts in by_doc.items()]


def flagged(audit: dict, span: tuple[int, int]) -> dict:
    hits = [c for c in audit.get("claims", []) if c["status"] == "ok" and c["answer_span"]
            and c["answer_span"]["start"] < span[1] and c["answer_span"]["end"] > span[0]]
    relations = Counter(c["relation"] for c in hits)
    return {"covered": bool(hits), "relations": dict(relations),
            "flagged": relations["contradicted"] + relations["insufficient"] > 0,
            "contradicted": relations["contradicted"] > 0,
            "elsewhere_flags": sum(1 for c in audit.get("claims", []) if c["status"] == "ok" and c not in hits
                                   and c["relation"] != "supported")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--key", default="key2")
    ap.add_argument("--budget", type=float, default=12.8)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--allow-peak", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "test_full-planted.jsonl"
    if args.report:
        return report(path)

    from medrag.verification.answer_audit import AuditRequest, audit_answer
    from medrag.verification.gateway import FlashGateway
    gateway = FlashGateway()
    items = assign(candidates(), args.n)
    previous = run.done(path)
    todo = [it for it in items if it["pmid"] not in previous]
    guard = run.Guard(args.key, args.budget, 0.03, args.allow_peak)
    print(f"[planted] {len(items)} items ({dict(Counter(i['type'] for i in items))}) · {len(todo)} to run · spent ${run.spent(args.key):.2f}", flush=True)

    def audit(answer: str, item: dict) -> dict:
        return audit_answer(AuditRequest(answer=answer, sources=sources(item["chunks"]), strategy="direct"), gateway)

    def work(item: dict) -> None:
        if not guard.ok():
            return
        a, b = item["spans"][item["target"]]
        original = item["answer"][a:b]
        row = {"pmid": item["pmid"], "type": item["type"], "original": original, "usage": []}
        try:
            response = gateway.invoke([SystemMessage(content=PLANT), HumanMessage(content=json.dumps(
                {"type": item["type"], "sentence": original}, ensure_ascii=False))])
            row["usage"].append(dict(response.usage_metadata or {}))
            out = json.loads(response.content)
            modified = " ".join(str(out.get("modified", "")).split())
            row.update(modified=modified, changed_from=out.get("changed_from"), changed_to=out.get("changed_to"))
            if not modified or modified == original or CITE.findall(modified) != CITE.findall(original):
                row["status"] = "plant_invalid"
            else:
                planted = item["answer"][:a] + modified + item["answer"][b:]
                clean_audit, planted_audit = audit(item["answer"], item), audit(planted, item)
                for au in (clean_audit, planted_audit):
                    row["usage"] += [c["usage"] for c in au["calls"] if c.get("usage")]
                row.update(status="ok", clean=flagged(clean_audit, (a, b)), planted=flagged(planted_audit, (a, a + len(modified))),
                           clean_audit_status=clean_audit["status"], planted_audit_status=planted_audit["status"],
                           clean_audit=clean_audit, planted_audit=planted_audit, planted_answer=planted)
        except Exception as exc:  # noqa: BLE001 - kept as a result
            row.update(status="error", error_type=type(exc).__name__, error=str(exc)[:300])
        row["usd"] = round(run.charge(args.key, f"planted/{item['type']}/{item['pmid']}", row["usage"]), 6)
        run.append(path, row)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, todo))
    rows = run.done(path)
    print(f"  saved {len(rows)}/{len(items)} · {dict(Counter(r['status'] for r in rows.values()))} · spent ${run.spent(args.key):.2f}", flush=True)
    if guard.stopped:
        print(f"STOPPED: {guard.stopped}. Re-run the same command to resume.", flush=True)


def wilson(k: int, n: int) -> tuple[float, float]:
    if not n:
        return (0.0, 0.0)
    z, p = 1.96, k / n
    centre, half = (p + z * z / (2 * n)) / (1 + z * z / n), z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)
    return centre - half, centre + half


def report(path: Path) -> None:
    rows = list(run.done(path).values())
    ok = [r for r in rows if r["status"] == "ok"]
    lines = [f"Planted-error study: {len(rows)} items, {len(ok)} audited "
             f"({sum(r['status'] == 'plant_invalid' for r in rows)} invalid plants, {sum(r['status'] == 'error' for r in rows)} errors); "
             f"cost ${sum(r['usd'] for r in rows):.2f}", "",
             "| Error type | n | Detected (planted flagged) | Contradicted | False alarm (same sentence, clean) | Target not covered (planted) |",
             "|---|---|---|---|---|---|"]
    summary = {}
    for kind in TYPES + ["all"]:
        sel = [r for r in ok if kind == "all" or r["type"] == kind]
        n = len(sel)
        if not n:
            continue
        det = sum(r["planted"]["flagged"] for r in sel)
        con = sum(r["planted"]["contradicted"] for r in sel)
        fa = sum(r["clean"]["flagged"] for r in sel)
        unc = sum(not r["planted"]["covered"] for r in sel)
        pct = lambda k: f"{100 * k / n:.0f}% [{100 * wilson(k, n)[0]:.0f}, {100 * wilson(k, n)[1]:.0f}]"  # noqa: E731
        lines.append(f"| {kind} | {n} | {pct(det)} | {pct(con)} | {pct(fa)} | {unc} |")
        summary[kind] = {"n": n, "detected": det, "contradicted": con, "false_alarm": fa, "not_covered": unc}
    statuses = Counter((r["clean_audit_status"], r["planted_audit_status"]) for r in ok)
    lines += ["", f"Audit statuses (clean, planted): {dict(statuses)}",
              "Flagged = an audit claim overlapping the target sentence is contradicted or insufficient; 95% Wilson intervals."]
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf8")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
