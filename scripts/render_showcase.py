"""Render documentation figures from code paths and saved outputs; no model calls.

Optional dependencies: matplotlib. Run from any directory with Python 3.12.
"""

from pathlib import Path
import hashlib
import json
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets/showcase"
INK, TEAL, GOLD, BLUE, BG = "#223a37", "#23685f", "#aa702a", "#556ba0", "#faf9f5"
SOURCES = {}


def read(path):
    p = ROOT / path
    SOURCES[path] = hashlib.sha256(p.read_bytes()).hexdigest()
    return json.loads(p.read_text(encoding="utf8"))


def save(fig, name):
    for ext in ("svg", "png"):
        fig.savefig(
            OUT / f"{name}.{ext}",
            dpi=135,
            facecolor=BG,
            metadata={"Date": None} if ext == "svg" else None,
        )
    plt.close(fig)


def canvas(title, subtitle, footer, height=8):
    fig, ax = plt.subplots(figsize=(14, height))
    fig.subplots_adjust(left=0.025, right=0.975, top=0.80, bottom=0.13)
    ax.set(xlim=(0, 100), ylim=(0, 100))
    ax.axis("off")
    fig.text(0.04, 0.94, "VERITASMED / v0.8", size=11, color=TEAL, weight="bold")
    fig.text(0.04, 0.885, title, size=24, weight="bold")
    fig.text(0.04, 0.83, subtitle, size=12)
    fig.text(0.04, 0.05, footer, size=11)
    return fig, ax


def box(ax, x, y, w, h, title, body, color=TEAL):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.6,rounding_size=1.5",
            facecolor="white",
            edgecolor=color,
            linewidth=1.5,
        )
    )
    ax.text(x + 2, y + h - 5, title, fontsize=14, weight="bold", va="top", color=color)
    ax.text(x + 2, y + h - 15, body, fontsize=11.5, va="top", linespacing=1.55)


def arrow(ax, start, end, label=None, color=TEAL, rad=0):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=16,
            linewidth=1.4,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
        )
    )
    if label:
        ax.text(
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2 + 3,
            label,
            fontsize=10,
            ha="center",
            color=color,
            bbox={"facecolor": BG, "edgecolor": "none", "pad": 2},
        )


def diagrams():
    fig, ax = canvas(
        "One conversation, inspectable evidence",
        "Ask is the product entrance. Audit belongs to an answer. Research is a separate experiment.",
        "Full Ask uses fresh evidence. Replay reads saved outputs and invokes no models.",
    )
    box(
        ax,
        2,
        61,
        28,
        34,
        "Browser / React",
        "Ask + turn history\nAnswer versions + attached audits\nIndexedDB / JSON import-export",
    )
    box(
        ax,
        37,
        61,
        28,
        34,
        "Ask / FastAPI + LangGraph",
        "Resolve references from history\nRetrieve, rerank, grade, generate\nInternal check + bounded repair",
    )
    box(
        ax,
        72,
        61,
        26,
        34,
        "Literature / Qdrant",
        "BGE-M3 dense + sparse\nRRF + reranking\nSource identity + passages",
    )
    arrow(ax, (30.8, 78), (36.2, 78))
    arrow(ax, (65.8, 78), (71.2, 78))
    box(
        ax,
        2,
        7,
        28,
        36,
        "Saved replay",
        "Actual committed Ask + audit runs\nThree papers / nine turns\nSame conversation interface",
        BLUE,
    )
    box(
        ax,
        37,
        7,
        28,
        36,
        "Independent Audit",
        "Unchanged answer + supplied text\nDirect Flash default / v2 experiment\nClaims, quotes, flags, fingerprints",
        GOLD,
    )
    box(
        ax,
        72,
        7,
        26,
        36,
        "Research workspace",
        "Eight fixed candidate abstracts\nDirect / autonomous / structured\nSaved traces + external labels",
        BLUE,
    )
    arrow(ax, (16, 60), (16, 44), "replay mode", BLUE)
    arrow(ax, (51, 60), (51, 44), "user opens Audit", GOLD)
    arrow(ax, (71, 25), (66, 25), "transfer", BLUE)
    save(fig, "system-overview")

    fig, ax = canvas(
        "How the Ask Agent reaches an answer",
        "Current graph: src/medrag/agent/graph.py. The internal check and the opened Audit panel are separate.",
        "At the limits: preserve gaps or failed checks. Opening Audit does not trigger automatic answer repair.",
        9,
    )
    steps = [
        ("Resolve + route", "History clarifies intent;\nprior answers are not evidence."),
        ("Retrieve + rerank", "Fresh dense/sparse search;\nbind requested study identity."),
        ("Grade evidence", "Query-type threshold;\nassess retrieved evidence."),
        (
            "Generate + check",
            "Cited answer components;\nmodel faithfulness check;\nfailed check: regenerate ≤2.",
        ),
    ]
    for i, (t, b) in enumerate(steps):
        box(ax, 2 + i * 25, 64, 22, 30, t, b)
    for i in range(3):
        arrow(ax, (24 + i * 25, 80), (26 + i * 25, 80))
    box(ax, 27, 17, 22, 30, "Rewrite query", "Low grade + budget left\nAt most two rewrites", GOLD)
    box(
        ax,
        77,
        17,
        21,
        30,
        "Return answer",
        "Pass OR repair limit hit\nPreserve unresolved issues",
        BLUE,
    )
    arrow(ax, (62, 63), (48, 46), "low grade", GOLD)
    arrow(ax, (37, 48), (37, 63), "retrieve again", GOLD)
    arrow(ax, (88, 63), (88, 48), "pass / exhausted", BLUE)
    ax.text(
        52,
        30,
        "After rewrite limit:\ngenerate best effort\nwith available evidence.",
        fontsize=12,
        va="center",
    )
    save(fig, "agent-workflow")

    case = read("data/demo/conversations/run01/v08-grade-follow-up-turn-1-atomic_v2.json")
    c = case["audit"]["claims"][0]
    fig, ax = canvas(
        "From answer fragment to source passage",
        "Illustrated from saved GRADE fact-1; this is a data diagram, not a mock product screenshot.",
        "Unique text binding proves location. 'Supported' is a model judgment. Neither is a calibrated confidence score.",
        10,
    )
    box(
        ax,
        2,
        62,
        45,
        33,
        "01 / Unchanged answer fragments",
        '"'
        + c["quote"]
        + '"\n"'
        + c["answer_spans"][1]["text"]
        + '"\nOffsets: 79–120 and 266–301; end exclusive.',
    )
    box(
        ax,
        53,
        62,
        45,
        33,
        "02 / Explicit condition anchor",
        textwrap.fill('"' + c["qualifier_anchors"][0]["quote"] + '"', 57)
        + "\nUnique parent-scoped match: 20–77.",
        GOLD,
    )
    box(
        ax,
        2,
        7,
        45,
        39,
        "03 / Model-parsed interpretation",
        textwrap.fill(c["normalized_claim"], 58) + "\n\nRelation: supported  |  Fact status: ok",
        TEAL,
    )
    source = c["evidence"][0]
    box(
        ax,
        53,
        7,
        45,
        39,
        "04 / Source passage + fingerprint",
        "PMC11567630 / Abstract / Results\nevidence-1: 0–349; supplied text\n"
        + source["source_sha256"][:26]
        + "…\n\nWhole run: partial_error\nFour other facts need parsing review.",
        BLUE,
    )
    arrow(ax, (24, 61), (24, 47))
    arrow(ax, (75, 61), (75, 47), color=GOLD)
    arrow(ax, (48, 27), (52, 27), "compare")
    save(fig, "claim-evidence")


def research():
    fixed = read("data/verification/v06/fixed-final-metrics.json")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4))
    metrics = [
        ("Non-support accepted (lower is better)", "false_accept", "nonsupport"),
        ("Supported recalled (higher is better)", "true_accept", "support"),
    ]
    for ax, (title, num, den) in zip(axes, metrics):
        for i, m in enumerate(("flash", "minicheck")):
            c = fixed[m]["counts"]
            value = c[num] / c[den]
            ax.barh(1 - i, value, color=(TEAL, GOLD)[i], height=0.45)
            ax.text(value + 0.025, 1 - i, f"{c[num]}/{c[den]} = {value:.1%}", va="center", size=12)
        ax.set(yticks=[1, 0], yticklabels=["Flash", "MiniCheck"], xlim=(0, 1.04), title=title)
        ax.xaxis.set_major_formatter(PercentFormatter(1))
        ax.grid(axis="x", alpha=0.4)
    fig.suptitle(
        "Fixed claims with external text-support labels", x=0.07, ha="left", size=22, weight="bold"
    )
    fig.text(
        0.07,
        0.87,
        "SciFact public dev · 339 pairs / 247 connected source groups · v0.6 frozen evaluation",
        size=12,
    )
    fig.text(
        0.07,
        0.04,
        "Not whole-answer or clinical accuracy. Paired intervals and the failed calibration policy remain in the report.",
        size=11,
    )
    fig.tight_layout(rect=(0.025, 0.1, 0.98, 0.83))
    save(fig, "research-verifiers")

    r = read("data/verification/v07/final-metrics.json")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4))
    names = ["Read all", "Autonomous tools", "Structured"]
    for i, m in enumerate(("direct_reader", "autonomous_tools", "structured_workflow")):
        c = r["methods"][m]["accepted"]["counts"]
        w = r["methods"][m]["workflow_counts"]
        v = c["correct"] / c["total"]
        axes[0].barh(2 - i, v, color=(TEAL, GOLD, BLUE)[i], height=0.5)
        axes[0].text(v + 0.02, 2 - i, f"{c['correct']}/{c['total']}", va="center")
        v = w["model_calls"] / c["total"]
        axes[1].barh(2 - i, v, color=(TEAL, GOLD, BLUE)[i], height=0.5)
        axes[1].text(v + 0.08, 2 - i, f"{v:.1f}", va="center")
    axes[0].set(xlim=(0, 1.1), title="Correct accepted binary decisions")
    axes[0].xaxis.set_major_formatter(PercentFormatter(1))
    axes[1].set(xlim=(0, 4), title="Mean actual model calls per query")
    for ax in axes:
        ax.set(yticks=[2, 1, 0], yticklabels=names)
        ax.grid(axis="x", alpha=0.4)
    fig.suptitle(
        "The prescribed workflow did not improve this task",
        x=0.07,
        ha="left",
        size=22,
        weight="bold",
    )
    fig.text(
        0.07,
        0.87,
        "40 final source groups · named-paper claims · eight fixed abstracts · same Flash profile",
        size=12,
    )
    fig.text(
        0.07,
        0.04,
        "All arms accepted 2/19 non-supports. Four structured outputs retained for review. Not a test of full Ask superiority.",
        size=11,
    )
    fig.tight_layout(rect=(0.025, 0.1, 0.98, 0.83))
    save(fig, "research-workflows")

    r = read("data/verification/v08/r2/summary.json")["phases"]["final"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 6))
    ms = ("direct", "atomic_v1", "atomic_v2")
    colors = (TEAL, GOLD, BLUE)
    for ax, (num, den, title) in zip(
        axes,
        [
            ("completed_answers", "answers", "Fully completed audits"),
            ("joint_targets", "targets", "All anchors in one claim"),
            ("literal_preserved", "literal_targets", "Number + conditions retained"),
        ],
    ):
        for i, m in enumerate(ms):
            c = r["methods"][m]
            v = c[num] / c[den]
            ax.bar(i, v, color=colors[i], width=0.6)
            ax.text(i, v + 0.03, f"{c[num]}/{c[den]}", ha="center", size=12)
        ax.set(
            xticks=range(3),
            xticklabels=["Direct", "Atomic v1", "Atomic v2"],
            ylim=(0, 1.15),
            title=title,
        )
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.grid(axis="y", alpha=0.4)
    fig.suptitle(
        "More inspectable conditions, more incomplete audits",
        x=0.07,
        ha="left",
        size=22,
        weight="bold",
    )
    fig.text(
        0.07,
        0.88,
        "v0.8 R2 · final 12 source groups / 48 AI-constructed answers · completion contracts differ",
        size=12,
    )
    fig.text(
        0.07,
        0.035,
        "Mechanical diagnostics, not semantic accuracy. Partial runs contribute to extraction counts; completed-only counts are in the report.",
        size=10.5,
    )
    fig.tight_layout(rect=(0.025, 0.1, 0.98, 0.83))
    save(fig, "research-qualifiers")

    fig, ax = plt.subplots(figsize=(14, 5.3))
    intervals = r["paired_source_intervals"]["atomic_v2"]
    for y, (key, label) in enumerate(
        [
            ("joint_targets", "All anchors in one claim"),
            ("literal_preserved", "Number + conditions retained"),
            ("completed_joint_targets", "All anchors + completed judgment"),
        ]
    ):
        c = intervals[key]
        v = c["candidate_minus_direct"] * 100
        lo, hi = [x * 100 for x in c["percentile_95"]]
        ax.errorbar(v, 2 - y, xerr=[[v - lo], [hi - v]], fmt="o", color=TEAL, capsize=6, ms=8, lw=2)
        ax.text(29, 2 - y, f"{v:+.1f} pp [{lo:+.1f}, {hi:+.1f}]", va="center", size=12)
    ax.axvline(0, color=INK, lw=1, linestyle="--")
    ax.set(
        yticks=[2, 1, 0],
        yticklabels=[
            "All anchors in one claim",
            "Number + conditions retained",
            "All anchors + completed judgment",
        ],
        xlim=(-30, 52),
        ylim=(-0.6, 2.6),
        xlabel="Atomic v2 minus Direct / percentage points",
    )
    ax.set_xticks([-25, 0, 25])
    ax.grid(axis="x", alpha=0.4)
    fig.suptitle("The paired uncertainty matters", x=0.07, ha="left", size=23, weight="bold")
    fig.text(
        0.07,
        0.86,
        "Source-group mean differences · paired percentile 95% intervals · 12 final groups",
        size=12,
    )
    fig.text(
        0.07,
        0.04,
        "All three intervals include zero. Group-mean differences differ from pooled fractions shown in the previous chart.",
        size=11,
    )
    fig.tight_layout(rect=(0.025, 0.1, 0.98, 0.81))
    save(fig, "research-intervals")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "text.color": INK,
            "axes.labelcolor": INK,
            "axes.facecolor": BG,
            "figure.facecolor": BG,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": "#d8dfdc",
            "axes.axisbelow": True,
            "svg.fonttype": "none",
            "svg.hashsalt": "veritasmed-showcase-v08",
        }
    )
    diagrams()
    research()
    (OUT / "figure-sources.json").write_text(
        json.dumps(
            {
                "renderer": "scripts/render_showcase.py",
                "scope": "Saved results only; no new inference; diagram layout is explanatory.",
                "input_sha256": SOURCES,
            },
            indent=2,
        )
        + "\n",
        encoding="utf8",
    )
    print("Rendered three explanatory diagrams and four research figures (SVG + PNG).")


if __name__ == "__main__":
    main()
