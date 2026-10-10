"""Draw the Experiment A figures (light and dark) from the committed run files. No API calls.

    python experiments/pubmedqa/figures.py      # writes docs/assets/experiment-a/*.png

Each figure answers one question and its title states the answer. Colours follow a validated
two-slot palette (blue = VeritasMed / the measured quantity, orange = the failure being counted);
everything else is neutral ink so the eye lands on the comparison that matters.
"""
from __future__ import annotations

import json
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "docs" / "assets" / "experiment-a"
sys.path.insert(0, str(HERE))
import report  # noqa: E402

THEMES = {
    "light": {"surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781", "grid": "#e1e0d9",
              "axis": "#c3c2b7", "blue": "#2a78d6", "orange": "#eb6834", "neutral": "#b9b7af", "track": "#ecebe6"},
    "dark": {"surface": "#1a1a19", "ink": "#ffffff", "ink2": "#c3c2b7", "muted": "#898781", "grid": "#2c2c2a",
             "axis": "#383835", "blue": "#3987e5", "orange": "#d95926", "neutral": "#6b6a65", "track": "#2c2c2a"},
}
ARMS = {"A1": "Plain RAG", "A5": "Strict-prompt RAG", "A2": "VeritasMed", "A4": "Gold abstract given"}


def rows(arm: str) -> dict:
    run = HERE / "runs" / "main"
    ids = json.loads((HERE / "manifest.json").read_text())["splits"]["test_full"]
    return report.per_question(arm, report.load(run / f"test_full-{arm}.jsonl"), report.load(run / f"test_full-{arm}.judged.jsonl"),
                               report.load(run / f"test_full-{arm}.scored.jsonl"), report.flash_labels(arm), ids)


def ci(values: list[float], n: int = 4000, seed: int = 20261005) -> tuple[float, float, float]:
    rng = random.Random(seed)
    means = sorted(statistics.mean(rng.choice(values) for _ in values) for _ in range(n))
    return statistics.mean(values), means[int(0.025 * n)], means[int(0.975 * n) - 1]


def style(ax, t, grid_axis="y"):
    ax.set_facecolor(t["surface"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(t["axis"])
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=t["muted"], labelsize=9, length=0)
    ax.grid(axis=grid_axis, color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def title(fig, t, head, sub):
    fig.text(0.02, 0.965, head, fontsize=13.5, fontweight="bold", color=t["ink"], va="top")
    fig.text(0.02, 0.905, sub, fontsize=9.5, color=t["ink2"], va="top")


def fig_tradeoff(plt, t, data, closed):
    """Accuracy vs grounded conclusions: only VeritasMed is high on both."""
    fig, ax = plt.subplots(figsize=(8.6, 5.2), facecolor=t["surface"])
    fig.subplots_adjust(left=0.09, right=0.97, top=0.80, bottom=0.12)
    style(ax, t, "both")
    for arm, d in data.items():
        hero = arm == "A2"
        color = t["blue"] if hero else t["neutral"]
        (gx, glo, ghi), (ay, alo, ahi) = d["grounded"], d["acc"]
        ax.plot([glo, ghi], [ay, ay], color=color, lw=1.6, solid_capstyle="round", zorder=2)
        ax.plot([gx, gx], [alo, ahi], color=color, lw=1.6, solid_capstyle="round", zorder=2)
        ax.scatter([gx], [ay], s=90 if hero else 60, color=color, edgecolor=t["surface"], linewidth=2, zorder=3)
        dx, dy, ha = {"A1": (-1.5, -2.6, "right"), "A4": (1.5, 3.0, "left"), "A5": (-1.5, -2.4, "right"), "A2": (-1.5, -3.6, "right")}[arm]
        ax.annotate(f"{ARMS[arm]}\n{ay:.1f}% accurate · {gx:.0f}% grounded", (gx, ay), xytext=(gx + dx, ay + dy), ha=ha, va="center",
                    fontsize=9, color=t["ink"] if hero else t["ink2"], fontweight="bold" if hero else "normal")
    ax.axhline(closed, color=t["axis"], lw=1)
    ax.text(31, closed - 0.8, f"Closed-book (no retrieval): {closed:.1f}%", fontsize=8.5, color=t["muted"], va="top")
    ax.set_xlim(30, 100)
    ax.set_ylim(46, 72)
    ax.set_xlabel("Conclusions grounded: first sentence cited and supported by its passages (%)", color=t["ink2"], fontsize=9.5)
    ax.set_ylabel("Accuracy vs expert yes/no/maybe label (%)", color=t["ink2"], fontsize=9.5)
    title(fig, t, "Only VeritasMed is both decisive and grounded",
          "PubMedQA, 500 test questions, same model and retriever. Whiskers: 95% bootstrap intervals.")
    return fig


def fig_bottom_lines(plt, t, decomp):
    """Where conclusions fail: uncited vs cited-but-unsupported."""
    fig, ax = plt.subplots(figsize=(8.6, 3.9), facecolor=t["surface"])
    fig.subplots_adjust(left=0.2, right=0.97, top=0.70, bottom=0.14)
    style(ax, t, "x")
    order = ["A1", "A4", "A5", "A2"]
    for y, arm in enumerate(reversed(order)):
        rej, unc = decomp[arm]
        ax.barh(y, 100, height=0.56, color=t["track"], zorder=1)
        ax.barh(y, rej, height=0.56, color=t["orange"], zorder=2)
        ax.barh(y, unc, left=rej, height=0.56, color=t["blue"], zorder=2, edgecolor=t["surface"], linewidth=2)
        ax.text(rej + unc + 1.2, y, f"{rej + unc:.0f}%", va="center", fontsize=9.5, color=t["ink"], fontweight="bold" if arm == "A2" else "normal")
    ax.set_yticks(range(len(order)), [ARMS[a] for a in reversed(order)], color=t["ink"], fontsize=9.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of answers whose first sentence (the yes/no conclusion) fails (%)", color=t["ink2"], fontsize=9.5)
    title(fig, t, "Plain RAG's conclusions fail 40% of the time; VeritasMed's 16%",
          "Even with the right abstract handed over, 36% fail - the problem is generation, not retrieval.")
    fig.text(0.2, 0.80, "■", color=t["orange"], fontsize=11, va="center")
    fig.text(0.22, 0.80, "cited, but the passages do not support it", color=t["ink2"], fontsize=9, va="center")
    fig.text(0.56, 0.80, "■", color=t["blue"], fontsize=11, va="center")
    fig.text(0.58, 0.80, "no citation at all", color=t["ink2"], fontsize=9, va="center")
    return fig


def fig_audit(plt, t, planted):
    """Planted errors: detection by type, with the unwarranted-flag rate."""
    fig, ax = plt.subplots(figsize=(8.6, 4.1), facecolor=t["surface"])
    fig.subplots_adjust(left=0.27, right=0.97, top=0.72, bottom=0.14)
    style(ax, t, "x")
    labels = ["Changed number", "Reversed direction or significance", "Wrong population or comparator",
              "Overstated conclusion", "All material errors (adjudicated)"]
    for y, (name, k, n) in enumerate(reversed(list(zip(labels, *zip(*planted))))):
        lo, hi = report_wilson(k, n)
        hero = name.startswith("All")
        ax.barh(y, 100, height=0.5, color=t["track"], zorder=1)
        ax.barh(y, 100 * k / n, height=0.5, color=t["blue"] if hero else t["neutral"], zorder=2)
        ax.plot([100 * lo, 100 * hi], [y, y], color=t["ink2"], lw=1.2, zorder=3)
        ax.text(101.5, y, f"{100 * k / n:.0f}%  ({k}/{n})", va="center", fontsize=9, color=t["ink"],
                fontweight="bold" if hero else "normal")
    ax.set_yticks(range(len(labels)), list(reversed(labels)), color=t["ink"], fontsize=9.5)
    ax.set_xlim(0, 118)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Planted errors the audit flags (%), 95% Wilson interval", color=t["ink2"], fontsize=9.5)
    title(fig, t, "The audit catches 98% of planted errors and wrongly flags 2% of correct sentences",
          "200 VeritasMed answers, one error each. Grey bars: raw; blue bar: after adjudication removed 9 invalid or wording-only plants.")
    return fig


def fig_judges(plt, t, calib):
    """Calibration: which citation judge to trust."""
    fig, ax = plt.subplots(figsize=(8.6, 3.5), facecolor=t["surface"])
    fig.subplots_adjust(left=0.27, right=0.97, top=0.66, bottom=0.18)
    style(ax, t, "x")
    for y, (name, k, n, hero) in enumerate(reversed(calib)):
        ax.barh(y, 100, height=0.5, color=t["track"], zorder=1)
        ax.barh(y, 100 * k / n, height=0.5, color=t["blue"] if hero else t["orange"], zorder=2)
        ax.text(101.5, y, f"{100 * k / n:.1f}%", va="center", fontsize=9.5, color=t["ink"], fontweight="bold" if hero else "normal")
    ax.set_yticks(range(len(calib)), [c[0] for c in reversed(calib)], color=t["ink"], fontsize=9.5)
    ax.set_xlim(0, 112)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Agreement with blinded labels on 150 cited sentences (%)", color=t["ink2"], fontsize=9.5)
    title(fig, t, "The pre-registered judge failed calibration and was replaced",
          "MiniCheck rejects even verbatim sentences against full abstracts; its 'halved' result was withdrawn.")
    return fig


def density(np, values, grid):
    """Gaussian kernel density with Silverman's bandwidth, on log10 values."""
    v = np.log10(values)
    h = 1.06 * v.std() * len(v) ** -0.2
    return np.exp(-0.5 * ((grid[:, None] - v[None, :]) / h) ** 2).sum(axis=1) / (len(v) * h * (2 * np.pi) ** 0.5)


def fig_cost(plt, t, usage):
    """Per-question cost vs time, with the distribution of each on the margins."""
    import numpy as np

    fig = plt.figure(figsize=(8.6, 6.6), facecolor=t["surface"])
    ax = fig.add_axes([0.10, 0.09, 0.70, 0.62])
    top = fig.add_axes([0.10, 0.72, 0.70, 0.11], sharex=ax)
    side = fig.add_axes([0.81, 0.09, 0.14, 0.62], sharey=ax)
    style(ax, t, "both")
    xlim, ylim = (4, 320), (0.0004, 0.06)
    gx, gy = np.linspace(*np.log10(xlim), 300), np.linspace(*np.log10(ylim), 300)
    looks = {"A1": (t["neutral"], "-", 0.55), "A5": (t["muted"], (0, (4, 2)), 0.0), "A2": (t["blue"], "-", 0.30)}
    for arm, (color, dash, fill) in looks.items():
        sec, usd = (np.array(v) for v in usage[arm])
        hero = arm == "A2"
        ax.scatter(sec, usd, s=11, alpha=0.5, linewidths=0.6 if arm == "A5" else 0, zorder=3 if hero else 2,
                   facecolors="none" if arm == "A5" else color, edgecolors=color)
        mx, my = float(np.median(sec)), float(np.median(usd))
        ax.scatter([mx], [my], s=90 if hero else 60, color=color, edgecolor=t["surface"], linewidth=2, zorder=5)
        dx, dy, ha = {"A1": (1.55, 0.50, "left"), "A5": (0.92, 2.6, "right"), "A2": (1.25, 0.60, "left")}[arm]
        ax.annotate(f"{ARMS[arm]}\nmedian {mx:.0f} s · ${my:.4f}", (mx, my), xytext=(mx * dx, my * dy), ha=ha, va="center",
                    fontsize=9, color=t["ink"] if hero else t["ink2"], fontweight="bold" if hero else "normal", zorder=6)
        for margin, grid, values, horizontal in ((top, gx, sec, True), (side, gy, usd, False)):
            d = density(np, values, grid)
            d[d < 0.02] = np.nan
            if horizontal:
                margin.fill_between(10 ** grid, d, color=color, alpha=fill, linewidth=0)
                margin.plot(10 ** grid, d, color=color, lw=1.4, linestyle=dash)
            else:
                margin.fill_betweenx(10 ** grid, d, color=color, alpha=fill, linewidth=0)
                margin.plot(d, 10 ** grid, color=color, lw=1.4, linestyle=dash)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_xticks([5, 10, 20, 50, 100, 200], ["5", "10", "20", "50", "100", "200"])
    ax.set_yticks([0.001, 0.003, 0.01, 0.03], ["$0.001", "$0.003", "$0.01", "$0.03"])
    ax.minorticks_off()
    ax.set_xlabel("Seconds per question (log scale)", color=t["ink2"], fontsize=9.5)
    ax.set_ylabel("Model cost per question (log scale)", color=t["ink2"], fontsize=9.5)
    for margin in (top, side):
        margin.set_facecolor(t["surface"])
        margin.tick_params(length=0, labelbottom=False, labelleft=False)
        for s in margin.spines.values():
            s.set_visible(False)
    top.set_ylim(0)
    side.set_xlim(0)
    title(fig, t, "Checking costs about 1 cent and 50 seconds more per question",
          "Each dot is one of 500 questions; curves show how time and cost are spread. VeritasMed's long tail is its draft repairs.")
    return fig


def report_wilson(k: int, n: int) -> tuple[float, float]:
    z, p = 1.96, k / n
    c, h = (p + z * z / (2 * n)) / (1 + z * z / n), z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)
    return c - h, c + h


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]

    data, decomp = {}, {}
    for arm in ARMS:
        r = list(rows(arm).values())
        acc = ci([100 * x["correct"] for x in r])
        bl = [100 * (1 - x["bottom"]) for x in r if x["bottom"] is not None]
        data[arm] = {"acc": acc, "grounded": ci(bl)}
    # bottom-line decomposition, computed directly from the files
    for arm in ARMS:
        s = report.load(HERE / "runs" / "main" / f"test_full-{arm}.scored.jsonl")
        fl = report.flash_labels(arm)
        n = unc = rej = 0
        for p, r in s.items():
            if not r["sentences"] or r["sentences"][0]["absence"]:
                continue
            if not r["sentences"][0]["cites"]:
                n, unc = n + 1, unc + 1
            elif 0 in fl.get(p, {}):
                n, rej = n + 1, rej + (fl[p][0] == 0)
        decomp[arm] = (100 * rej / n, 100 * unc / n)
    closed = statistics.mean(100 * x["correct"] for x in rows("A0").values())

    planted_rows = [r for r in map(json.loads, (HERE / "runs" / "planted" / "test_full-planted.jsonl").read_text(encoding="utf8").splitlines())]
    by_type = {}
    for r in planted_rows:
        by_type.setdefault(r["type"], []).append(r["planted"]["flagged"])
    adj = json.loads((HERE / "runs" / "planted" / "summary.json").read_text())["adjudicated"]
    material = adj["material_plants"]
    planted = [(sum(by_type[k]), len(by_type[k])) for k in ("number", "direction", "population", "overreach")]
    planted.append((material - adj["true_misses"], material))

    labels = json.loads((HERE / "runs" / "agreement" / "calibration-labels.json").read_text(encoding="utf8"))["labels"]
    items = [json.loads(l) for l in (HERE / "runs" / "agreement" / "calibration-items.jsonl").read_text(encoding="utf8").splitlines()]
    hits = {"minicheck": 0, "flash": 0}
    for it in items:
        ag = report.load(HERE / "runs" / "agreement" / f"test_full-{it['arm']}.jsonl")[it["pmid"]]
        s = next(x for x in ag["sentences"] if x["id"] == it["sid"])
        for j in hits:
            hits[j] += s[j] == labels[it["item"]]
    calib = [("MiniCheck-Flan-T5 (pre-registered)", hits["minicheck"], len(items), False),
             ("Flash citation judge (adopted)", hits["flash"], len(items), True)]

    usage = {}
    for arm in ("A1", "A5", "A2"):
        r = report.load(HERE / "runs" / "main" / f"test_full-{arm}.jsonl").values()
        usage[arm] = ([x["seconds"] for x in r], [x["usd"] for x in r])

    OUT.mkdir(parents=True, exist_ok=True)
    for theme, t in THEMES.items():
        for name, fn, arg in [("tradeoff", fig_tradeoff, (data, closed)), ("bottom-lines", fig_bottom_lines, (decomp,)),
                              ("audit", fig_audit, (planted,)), ("judges", fig_judges, (calib,)), ("cost", fig_cost, (usage,))]:
            fig = fn(plt, t, *arg)
            fig.savefig(OUT / f"{name}-{theme}.png", dpi=170, facecolor=t["surface"])
            plt.close(fig)
    print(json.dumps({"tradeoff": {a: {k: [round(v, 1) for v in d[k]] for k in d} for a, d in data.items()},
                      "bottom_lines_rejected_uncited": {a: [round(v, 1) for v in d] for a, d in decomp.items()},
                      "planted": planted, "calibration": [(c[0], c[1], c[2]) for c in calib], "closed_book": round(closed, 1)}, indent=1))


if __name__ == "__main__":
    main()
