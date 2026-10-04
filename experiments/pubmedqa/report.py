"""Summarize a scored run: one JSON summary and a Markdown table. No API calls.

Per arm (failed answers stay in every denominator):
  accuracy / macro-F1     judged verdict vs expert label
  unsupported rate        share of non-absence sentences NOT supported by their own cited passages
                          (uncited sentences count as unsupported); A1, A2, A4
  paper consistency       share of non-absence sentences MiniCheck accepts against the gold abstract
  retrieval hit           gold abstract among the passages the method used; A1, A2
  cost, calls, latency    from the ledger-priced usage of each answer
Paired differences vs a reference arm use a question-level bootstrap (10,000 resamples, fixed seed).
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = {"A0": "Closed-book", "A1": "Plain RAG", "A2": "VeritasMed", "A3": "VeritasMed (verbatim)", "A4": "Gold abstract"}


def load(path: Path) -> dict[str, dict]:
    return {r["pmid"]: r for r in map(json.loads, path.read_text(encoding="utf8").splitlines())} if path.exists() else {}


def per_question(arm: str, answers: dict, judged: dict, scored: dict, ids: list[str]) -> dict[str, dict]:
    out = {}
    for pmid in ids:
        a, j, s = answers.get(pmid, {}), judged.get(pmid, {}), scored.get(pmid, {})
        sents = [x for x in s.get("sentences", []) if not x["absence"]]
        out[pmid] = {
            "correct": float(j.get("verdict") is not None and j.get("verdict") == j.get("label")),
            "verdict": j.get("verdict"), "label": j.get("label"),
            "n_sent": len(sents), "n_absence": sum(x["absence"] for x in s.get("sentences", [])),
            "supported": sum(x.get("cited") == 1 for x in sents) if arm != "A0" else None,
            "consistent": sum(x.get("gold") == 1 for x in sents),
            "hit": float(pmid in {c["doc_id"] for c in a.get("chunks", [])}) if arm in ("A1", "A2", "A3") else None,
            "usd": a.get("usd", 0.0), "calls": len(a.get("usage", [])), "seconds": a.get("seconds", 0.0),
            "ok": a.get("status") == "ok",
        }
    return out


def macro_f1(rows) -> float:
    f1s = []
    for lab in ("yes", "no", "maybe"):
        tp = sum(r["verdict"] == lab and r["label"] == lab for r in rows)
        fp = sum(r["verdict"] == lab and r["label"] != lab for r in rows)
        fn = sum(r["verdict"] != lab and r["label"] == lab for r in rows)
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return sum(f1s) / 3


def ratio(rows, key):
    num = sum(r[key] for r in rows if r[key] is not None)
    den = sum(r["n_sent"] for r in rows if r[key] is not None)
    return num / den if den else None


def bootstrap(a: dict, b: dict, metric, n=10_000, seed=20261005):
    ids = sorted(set(a) & set(b))
    rng = random.Random(seed)
    diffs = []
    for _ in range(n):
        sample = [rng.choice(ids) for _ in ids]
        x, y = metric([a[i] for i in sample]), metric([b[i] for i in sample])
        if x is not None and y is not None:
            diffs.append(x - y)
    diffs.sort()
    point = metric([a[i] for i in ids]) - metric([b[i] for i in ids])
    return {"diff": point, "low": diffs[int(0.025 * len(diffs))], "high": diffs[int(0.975 * len(diffs)) - 1]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--arms", default="A0,A1,A2,A4")
    ap.add_argument("--reference", default="A1")
    args = ap.parse_args()
    run = HERE / "runs" / args.run
    ids = json.loads((HERE / "manifest.json").read_text())["splits"][args.split]
    table, rows_by_arm = {}, {}
    for arm in args.arms.split(","):
        rows = per_question(arm, load(run / f"{args.split}-{arm}.jsonl"), load(run / f"{args.split}-{arm}.judged.jsonl"),
                            load(run / f"{args.split}-{arm}.scored.jsonl"), ids)
        rows_by_arm[arm] = rows
        v = list(rows.values())
        supported = ratio(v, "supported")
        table[arm] = {
            "name": NAMES[arm], "questions": len(v), "completed": sum(r["ok"] for r in v),
            "accuracy": statistics.mean(r["correct"] for r in v), "macro_f1": macro_f1(v),
            "unsupported_rate": None if supported is None else 1 - supported,
            "paper_consistency": ratio(v, "consistent"),
            "retrieval_hit": statistics.mean(r["hit"] for r in v) if v[0]["hit"] is not None else None,
            "sentences_per_answer": statistics.mean(r["n_sent"] for r in v),
            "absence_statements": sum(r["n_absence"] for r in v),
            "usd_per_question": statistics.mean(r["usd"] for r in v), "calls_per_question": statistics.mean(r["calls"] for r in v),
            "median_seconds": statistics.median(r["seconds"] for r in v),
        }
    ref = args.reference
    acc = lambda rs: statistics.mean(r["correct"] for r in rs)  # noqa: E731
    uns = lambda rs: (lambda s: None if s is None else 1 - s)(ratio(rs, "supported"))  # noqa: E731
    con = lambda rs: ratio(rs, "consistent")  # noqa: E731
    paired = {}
    for arm in rows_by_arm:
        if arm == ref:
            continue
        paired[f"{arm}-{ref}"] = {"accuracy": bootstrap(rows_by_arm[arm], rows_by_arm[ref], acc),
                                  "paper_consistency": bootstrap(rows_by_arm[arm], rows_by_arm[ref], con)}
        if arm != "A0":
            paired[f"{arm}-{ref}"]["unsupported_rate"] = bootstrap(rows_by_arm[arm], rows_by_arm[ref], uns)
    summary = {"run": args.run, "split": args.split, "arms": table, "paired_vs_" + ref: paired}
    (run / f"{args.split}-summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf8")

    pct = lambda x: "—" if x is None else f"{100 * x:.1f}%"  # noqa: E731
    lines = ["| Method | Accuracy | Macro-F1 | Unsupported sentences | Consistent with paper | Retrieval hit | $ / question | Median s |",
             "|---|---|---|---|---|---|---|---|"]
    for t in table.values():
        lines.append(f"| {t['name']} | {pct(t['accuracy'])} | {t['macro_f1']:.3f} | {pct(t['unsupported_rate'])} | {pct(t['paper_consistency'])} | "
                     f"{pct(t['retrieval_hit'])} | ${t['usd_per_question']:.4f} | {t['median_seconds']:.0f} |")
    lines += ["", f"Paired differences vs {NAMES[ref]} (percentage points, 95% bootstrap interval):", ""]
    for key, d in paired.items():
        parts = [f"{m}: {100 * v['diff']:+.1f} [{100 * v['low']:+.1f}, {100 * v['high']:+.1f}]" for m, v in d.items()]
        lines.append(f"- {key}: " + "; ".join(parts))
    (run / f"{args.split}-summary.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
