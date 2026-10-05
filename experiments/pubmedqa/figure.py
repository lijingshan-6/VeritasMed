"""Draw the Experiment A figure from a run's summary.json (run report.py first)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COLORS = {"A0": "#9aa0a6", "A1": "#4c78a8", "A2": "#d1495b", "A4": "#59a14f"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main")
    ap.add_argument("--split", default="test_full")
    ap.add_argument("--out", default=str(ROOT / "docs" / "assets" / "experiment-a.png"))
    args = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = json.loads((HERE / "runs" / args.run / f"{args.split}-summary.json").read_text(encoding="utf8"))
    arms = s["arms"]
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.15, 1]})

    for arm, t in arms.items():
        if t["unsupported_rate"] is None:
            continue
        x, y = 100 * t["unsupported_rate"], 100 * t["accuracy"]
        left.scatter(x, y, s=4000 * t["usd_per_question"] + 60, color=COLORS[arm], alpha=0.85, edgecolor="white", zorder=3)
        left.annotate(f"{t['name']}\n${t['usd_per_question']:.4f}/q", (x, y), xytext=(10, -4), textcoords="offset points", fontsize=9)
    closed = arms.get("A0")
    if closed:
        left.axhline(100 * closed["accuracy"], color=COLORS["A0"], ls="--", lw=1)
        left.text(2, 100 * closed["accuracy"] + 0.4, f"Closed-book accuracy {100 * closed['accuracy']:.1f}%", fontsize=8, color="#5f6368")
    left.set_xlim(0, 55)
    left.set_ylim(50, 70)
    left.set_xlabel("Unsupported sentences (%)  ← better")
    left.set_ylabel("Accuracy vs expert label (%)")
    left.set_title("Same accuracy, half the unsupported sentences", fontsize=11)
    left.grid(alpha=0.25)

    robust = s.get("robustness", {})
    names = [a for a in ("A1", "A2", "A4") if a in robust]
    groups = [("cited_only_support", "Cited sentences"), ("support_own_words", "Own-words sentences")]
    width = 0.26
    for j, arm in enumerate(names):
        vals = [100 * robust[arm][k] for k, _ in groups]
        bars = right.bar([i + (j - 1) * width for i in range(len(groups))], vals, width, color=COLORS[arm], label=arms[arm]["name"])
        right.bar_label(bars, fmt="%.0f", fontsize=8, padding=2)
    right.set_xticks(range(len(groups)), [g for _, g in groups])
    right.set_ylim(0, 100)
    right.set_ylabel("Supported by cited passages (%)")
    right.set_title("Gap holds without uncited or copied sentences", fontsize=11)
    right.legend(fontsize=8, frameon=False, loc="upper right")
    right.grid(axis="y", alpha=0.25)

    n = arms["A1"]["questions"]
    fig.suptitle(f"PubMedQA, {n} official test questions · same model, corpus and retriever for every method", fontsize=10, color="#5f6368")
    fig.tight_layout()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=160)
    print(args.out)


if __name__ == "__main__":
    main()
