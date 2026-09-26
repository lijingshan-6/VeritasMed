"""Render release research figures from saved metrics only (optional matplotlib)."""

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

from v06_prepare import ROOT, OUT
from v07_benchmark import V07

ASSETS = ROOT / "docs/assets"
COLORS = ["#23664d", "#b57928", "#536db3"]


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def save(fig, name):
    ASSETS.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg"):
        fig.savefig(ASSETS / f"{name}.{suffix}", dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)


def main(fixed_only=False):
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.edgecolor": "#c5c8c3",
            "axes.labelcolor": "#34423c",
            "text.color": "#23362d",
            "figure.facecolor": "#fbfaf6",
            "axes.facecolor": "#fbfaf6",
            "grid.color": "#e0e2dd",
            "axes.axisbelow": True,
            "svg.hashsalt": "veritasmed-v07",
        }
    )
    fixed = read(OUT / "fixed-final-metrics.json")
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.7))
    metrics = [
        ("false_acceptance_rate", "Non-support accepted", "false_accept", "nonsupport"),
        ("support_recall", "Supported recalled", "true_accept", "support"),
        ("all_case_accuracy", "Correct binary decisions", "correct", "total"),
    ]
    for ax, (metric, label, num, den) in zip(axes, metrics):
        for i, method in enumerate(("flash", "minicheck")):
            r = fixed[method]
            ax.bar(i, r[metric], color=COLORS[i], width=0.55)
            c = r["counts"]
            ax.text(i, r[metric] + 0.025, f"{c[num]}/{c[den]}", ha="center")
        ax.set(xticks=[0, 1], xticklabels=["Flash", "MiniCheck"], ylim=(0, 1.12), title=label)
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
        ax.grid(axis="y")
    fig.suptitle("Fixed claims, same full abstracts", fontsize=18, x=0.06, ha="left")
    fig.text(
        0.06,
        0.865,
        "SciFact public dev: 339 pairs / 247 connected source groups · all planned cases",
    )
    fig.text(
        0.06,
        0.035,
        "Text-support labels, not clinical truth. Full paired group intervals and failures accompany the report.",
        fontsize=9,
    )
    fig.tight_layout(rect=(0.03, 0.09, 0.98, 0.83))
    save(fig, "v07-fixed-verifiers")

    cal = read(OUT / "calibration-final.json")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    bins = [b for b in cal["reliability_bins"] if b["n"]]
    axes[0].plot([0, 1], [0, 1], linestyle="--", color="#959e98", label="Reference line")
    axes[0].scatter(
        [b["mean_score"] for b in bins],
        [b["observed_support"] for b in bins],
        s=[b["n"] * 4 for b in bins],
        color=COLORS[0],
        alpha=0.8,
    )
    for b in bins:
        axes[0].annotate(
            str(b["n"]),
            (b["mean_score"], b["observed_support"]),
            xytext=(5, 4),
            textcoords="offset points",
            fontsize=8,
        )
    axes[0].set(
        xlabel="Mapped support score",
        ylabel="Observed supported fraction",
        title="Final reliability bins · labels = pair counts",
        xlim=(-0.02, 1.05),
        ylim=(-0.02, 1.08),
    )
    curve = [r for r in cal["risk_coverage_curve"] if r["risk"] is not None]
    axes[1].plot(
        [r["coverage"] for r in curve], [r["risk"] for r in curve], color=COLORS[1], linewidth=2
    )
    axes[1].axhline(0.05, linestyle="--", color="#959e98", label="5% selection target")
    axes[1].set(
        xlabel="Accepted / all planned pairs",
        ylabel="Non-support / accepted pairs",
        title="Final risk–coverage · descriptive only",
        xlim=(-0.02, 1.02),
        ylim=(0, 1),
    )
    axes[1].legend(frameon=False, fontsize=8)
    for ax in axes:
        ax.grid(alpha=0.6)
        ax.xaxis.set_major_formatter(PercentFormatter(1))
        ax.yaxis.set_major_formatter(PercentFormatter(1))
    fig.suptitle(
        "Calibration did not yield a usable acceptance policy", fontsize=16, x=0.07, ha="left"
    )
    fig.text(
        0.07,
        0.035,
        "Fit: 87 pairs. Select: 91 pairs. No eligible threshold; the final curve is not used to choose a new one.",
        fontsize=9,
    )
    fig.tight_layout(rect=(0.03, 0.09, 0.98, 0.89))
    save(fig, "v07-calibration")

    if fixed_only:
        print("Rendered the completed fixed-verifier and calibration studies")
        return

    report = read(V07 / "final-metrics.json")
    names = ["Read all", "Autonomous tools", "Structured"]
    methods = ["direct_reader", "autonomous_tools", "structured_workflow"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.8))
    for i, method in enumerate(methods):
        r = report["methods"][method]
        c = r["accepted"]["counts"]
        w = r["workflow_counts"]
        axes[0].bar(i, c["correct"] / c["total"], color=COLORS[i], width=0.6)
        axes[0].text(
            i, c["correct"] / c["total"] + 0.025, f"{c['correct']}/{c['total']}", ha="center"
        )
        for ax, key in zip(axes[1:], ("model_calls", "reported_tokens")):
            value = w[key] / c["total"]
            ax.bar(i, value, color=COLORS[i], width=0.6)
            ax.annotate(
                f"{value:,.1f}", (i, value), xytext=(0, 5), textcoords="offset points", ha="center"
            )
    axes[0].set(ylim=(0, 1.15), title="Correct accepted binary decisions")
    axes[0].yaxis.set_major_formatter(PercentFormatter(1))
    axes[1].set_title("Mean model calls / query")
    axes[2].set_title("Mean reported tokens / query")
    for ax in axes:
        ax.set(xticks=range(3), xticklabels=names)
        ax.tick_params(axis="x", labelsize=8)
        ax.grid(axis="y")
        ax.margins(y=0.2)
    fig.suptitle(
        "Does a fixed workflow help on named-paper fact queries?", fontsize=17, x=0.06, ha="left"
    )
    fig.text(
        0.06,
        0.865,
        "40 final source groups · same Flash profile and 8-paper corpus · failures/review included",
    )
    fig.text(
        0.06,
        0.035,
        "This bounded experiment does not establish superiority of the historical Ask graph or clinical reasoning.",
        fontsize=9,
    )
    fig.tight_layout(rect=(0.03, 0.09, 0.98, 0.83))
    save(fig, "v07-workflow-comparison")
    print("Rendered three PNG/SVG research figures from frozen metric files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed-only", action="store_true")
    main(parser.parse_args().fixed_only)
