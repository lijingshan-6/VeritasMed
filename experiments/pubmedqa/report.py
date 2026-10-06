"""Summarize a scored run: one JSON summary and a Markdown table. No API calls.

Per arm (failed answers stay in every denominator):
  accuracy / macro-F1     judged verdict vs expert label
  unsupported (Flash)     share of non-absence sentences NOT supported by their own cited passages
                          according to the Flash citation judge (agreement.py); uncited sentences
                          count as unsupported. Primary support metric: on a blinded 150-sentence
                          calibration set Flash agreed with the labels 94.0%, MiniCheck 77.3%.
  unsupported (MiniCheck) the original pre-registered metric, kept for the record; calibration
                          showed MiniCheck rejects correct sentences against full abstracts.
  retrieval hit           gold abstract among the passages the method used; A1-A3
  cost, calls, latency    from the ledger-priced usage of each answer
Paired differences vs a reference arm use a question-level bootstrap (10,000 resamples, fixed seed).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = {"A0": "Closed-book", "A1": "Plain RAG", "A2": "VeritasMed", "A3": "VeritasMed (verbatim)", "A4": "Gold abstract"}
CITE, SPLIT = re.compile(r"\[(PMID:\d+)\]"), re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def load(path: Path) -> dict[str, dict]:
    return {r["pmid"]: r for r in map(json.loads, path.read_text(encoding="utf8").splitlines())} if path.exists() else {}


def flash_labels(arm: str) -> dict[str, dict[int, int]]:
    rows = load(HERE / "runs" / "agreement" / f"test_full-{arm}.jsonl")
    return {p: {s["id"]: s["flash"] for s in r.get("sentences", []) if s.get("flash") is not None} for p, r in rows.items()}


def grams(text: str) -> set:
    t = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(t[i:i + 8]) for i in range(len(t) - 7)}


def per_question(arm: str, answers: dict, judged: dict, scored: dict, flash: dict, ids: list[str]) -> dict[str, dict]:
    out = {}
    for pmid in ids:
        a, j, s = answers.get(pmid, {}), judged.get(pmid, {}), scored.get(pmid, {})
        sents = [(i, x) for i, x in enumerate(s.get("sentences", [])) if not x["absence"]]
        fl = flash.get(pmid, {})
        cited = [(i, x) for i, x in sents if x["cites"]]
        judged_all = arm != "A0" and all(i in fl for i, _ in cited)
        source = grams(" ".join(c["text"] for c in a.get("chunks", [])))
        raw = [CITE.sub("", t) for t in SPLIT.split(" ".join(a.get("answer", "").split())) if t.strip()] if a.get("status") == "ok" else []
        copied = {i for i, t in enumerate(raw) if (g := grams(t)) and len(g & source) / len(g) >= 0.8}
        out[pmid] = {
            "correct": float(j.get("verdict") is not None and j.get("verdict") == j.get("label")),
            "verdict": j.get("verdict"), "label": j.get("label"),
            "n_sent": len(sents), "n_absence": sum(x["absence"] for x in s.get("sentences", [])),
            "n_cited": len(cited), "n_copied": sum(i in copied for i, _ in sents),
            "minicheck": sum(x.get("cited") == 1 for _, x in sents) if arm != "A0" else None,
            "minicheck_cited": sum(x.get("cited") == 1 for _, x in cited) if arm != "A0" else None,
            "flash": sum(fl.get(i) == 1 for i, _ in cited) if judged_all else None,
            "flash_own": (sum(fl.get(i) == 1 for i, _ in cited if i not in copied), sum(i not in copied for i, _ in sents)) if judged_all else None,
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


def unsupported(rows, key, denom="n_sent"):
    rows = [r for r in rows if r[key] is not None]
    den = sum(r[denom] for r in rows)
    return 1 - sum(r[key] for r in rows) / den if den else None


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
    ap.add_argument("--arms", default="A0,A1,A2,A3,A4")
    ap.add_argument("--reference", default="A1")
    args = ap.parse_args()
    run = HERE / "runs" / args.run
    ids = json.loads((HERE / "manifest.json").read_text())["splits"][args.split]
    table, rows_by_arm = {}, {}
    for arm in args.arms.split(","):
        if not (run / f"{args.split}-{arm}.jsonl").exists():
            continue
        rows = per_question(arm, load(run / f"{args.split}-{arm}.jsonl"), load(run / f"{args.split}-{arm}.judged.jsonl"),
                            load(run / f"{args.split}-{arm}.scored.jsonl"), flash_labels(arm), ids)
        rows_by_arm[arm] = rows
        v = list(rows.values())
        own = [r["flash_own"] for r in v if r["flash_own"]]
        table[arm] = {
            "name": NAMES[arm], "questions": len(v), "completed": sum(r["ok"] for r in v),
            "accuracy": statistics.mean(r["correct"] for r in v), "macro_f1": macro_f1(v),
            "unsupported_flash": unsupported(v, "flash"),
            "flash_judged_questions": sum(r["flash"] is not None for r in v),
            "unsupported_flash_cited_only": unsupported(v, "flash", "n_cited"),
            "unsupported_flash_own_words": 1 - sum(a for a, _ in own) / sum(b for _, b in own) if own and sum(b for _, b in own) else None,
            "unsupported_minicheck": unsupported(v, "minicheck"),
            "uncited_share": (lambda n: 1 - sum(r["n_cited"] for r in v) / n if n else None)(sum(r["n_sent"] for r in v)),
            "copied_share": (lambda n: sum(r["n_copied"] for r in v) / n if n else None)(sum(r["n_sent"] for r in v)),
            "retrieval_hit": statistics.mean(r["hit"] for r in v) if v[0]["hit"] is not None else None,
            "sentences_per_answer": statistics.mean(r["n_sent"] for r in v),
            "usd_per_question": statistics.mean(r["usd"] for r in v), "calls_per_question": statistics.mean(r["calls"] for r in v),
            "median_seconds": statistics.median(r["seconds"] for r in v),
        }
    ref = args.reference
    acc = lambda rs: statistics.mean(r["correct"] for r in rs)  # noqa: E731
    paired = {}
    for arm in rows_by_arm:
        if arm == ref:
            continue
        paired[f"{arm}-{ref}"] = {"accuracy": bootstrap(rows_by_arm[arm], rows_by_arm[ref], acc)}
        if arm != "A0":
            judged = lambda rs: unsupported(rs, "flash")  # noqa: E731
            both = {p for p in rows_by_arm[arm] if rows_by_arm[arm][p]["flash"] is not None and rows_by_arm[ref][p]["flash"] is not None}
            if both:
                paired[f"{arm}-{ref}"]["unsupported_flash"] = bootstrap({p: rows_by_arm[arm][p] for p in both},
                                                                        {p: rows_by_arm[ref][p] for p in both}, judged)
            paired[f"{arm}-{ref}"]["unsupported_minicheck"] = bootstrap(rows_by_arm[arm], rows_by_arm[ref], lambda rs: unsupported(rs, "minicheck"))
    summary = {"run": args.run, "split": args.split, "arms": table, "paired_vs_" + ref: paired,
               "note": "unsupported_minicheck is the original pre-registered metric, rejected by the blinded calibration (runs/agreement/)."}
    (run / f"{args.split}-summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf8")

    pct = lambda x: "—" if x is None else f"{100 * x:.1f}%"  # noqa: E731
    lines = ["| Method | Accuracy | Macro-F1 | Unsupported sentences (Flash judge) | Uncited | Retrieval hit | $ / question | Median s | Unsupported (MiniCheck, rejected) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for t in table.values():
        lines.append(f"| {t['name']} | {pct(t['accuracy'])} | {t['macro_f1']:.3f} | {pct(t['unsupported_flash'])} | {pct(t['uncited_share'])} | "
                     f"{pct(t['retrieval_hit'])} | ${t['usd_per_question']:.4f} | {t['median_seconds']:.0f} | {pct(t['unsupported_minicheck'])} |")
    lines += ["", f"Paired differences vs {NAMES[ref]} (percentage points, 95% bootstrap interval):", ""]
    for key, d in paired.items():
        parts = [f"{m}: {100 * v['diff']:+.1f} [{100 * v['low']:+.1f}, {100 * v['high']:+.1f}]" for m, v in d.items()]
        lines.append(f"- {key}: " + "; ".join(parts))
    lines += ["", "Support detail (Flash): cited sentences only / sentences in the method's own words "
              "(<80% of 8-grams found in its passages):", ""]
    for t in table.values():
        if t["unsupported_flash"] is not None:
            lines.append(f"- {t['name']}: {pct(t['unsupported_flash_cited_only'])} / {pct(t['unsupported_flash_own_words'])}; "
                         f"copied sentences {pct(t['copied_share'])}; Flash-judged questions {t['flash_judged_questions']}")
    (run / f"{args.split}-summary.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
