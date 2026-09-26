"""Denominator-explicit metrics. Failures and abstentions never become correct negatives."""

from collections import Counter
import math
import random


def ratio(a, b):
    return a / b if b else None


def fixed_metrics(entries, predictions):
    by_id = {r["case_id"]: r for r in predictions}
    if len(by_id) != len(predictions) or not set(by_id) <= set(e["case_id"] for e in entries):
        raise ValueError("Duplicate/unknown predictions")
    c = Counter()
    details = []
    for e in entries:
        row = by_id.get(e["case_id"], {})
        prediction = row.get("binary_prediction") if row.get("status") == "ok" else None
        truth = int(e["relation"] == "supported")
        c.update(
            total=1,
            completed=prediction is not None,
            support=truth,
            nonsupport=1 - truth,
            correct=prediction is not None and prediction == truth,
            false_accept=prediction == 1 and truth == 0,
            true_accept=prediction == 1 and truth == 1,
            true_reject=prediction == 0 and truth == 0,
            predicted_support=prediction == 1,
        )
        details.append(
            {
                "case_id": e["case_id"],
                "group_id": e["group_id"],
                "gold": truth,
                "prediction": prediction,
            }
        )
    recall = ratio(c["true_accept"], c["support"])
    specificity = ratio(c["true_reject"], c["nonsupport"])
    return {
        "counts": dict(c),
        "group_count": len(set(e["group_id"] for e in entries)),
        "completion": ratio(c["completed"], c["total"]),
        "all_case_accuracy": ratio(c["correct"], c["total"]),
        "false_acceptance_rate": ratio(c["false_accept"], c["nonsupport"]),
        "support_precision": ratio(c["true_accept"], c["predicted_support"]),
        "support_recall": recall,
        "balanced_accuracy": (recall + specificity) / 2
        if recall is not None and specificity is not None
        else None,
        "interpretation": "Missing/failed/review decisions reduce completion and useful-decision accuracy; never count as correct non-support.",
        "details": details,
    }


def paired_intervals(left, right, seed=260926, replicates=2000):
    """Right minus left. Resample source groups, retaining all their dependent pairs."""
    a = {r["case_id"]: r for r in left["details"]}
    b = {r["case_id"]: r for r in right["details"]}
    if set(a) != set(b):
        raise ValueError("Paired comparison requires identical planned cases")
    groups = {
        g: [k for k, v in a.items() if v["group_id"] == g]
        for g in sorted({v["group_id"] for v in a.values()})
    }
    samples = {"false_acceptance_rate": [], "support_recall": []}
    rng = random.Random(seed)

    def measure(rows, which):
        rows = [r for r in rows if r["gold"] == (0 if which == "false_acceptance_rate" else 1)]
        return ratio(sum(r["prediction"] == 1 for r in rows), len(rows))

    for _ in range(replicates):
        ids = [k for g in rng.choices(list(groups), k=len(groups)) for k in groups[g]]
        for metric in samples:
            x, y = measure([a[k] for k in ids], metric), measure([b[k] for k in ids], metric)
            if x is not None and y is not None:
                samples[metric].append(y - x)
    out = {
        "direction": "right minus left",
        "source_groups": len(groups),
        "replicates": replicates,
        "seed": seed,
    }
    for metric, values in samples.items():
        values.sort()
        ci = [values[int((len(values) - 1) * q)] for q in (0.025, 0.975)] if values else None
        out[metric] = {
            "difference": right[metric] - left[metric]
            if right[metric] is not None and left[metric] is not None
            else None,
            "ci95": ci,
            "degenerate": bool(ci and ci[0] == ci[1]),
            "valid_replicates": len(values),
        }
    return out


def wilson(errors, total, z=1.959963984540054):
    if not total:
        return None
    p = errors / total
    d = 1 + z * z / total
    mid = (p + z * z / (2 * total)) / d
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return [max(0, mid - half), min(1, mid + half)]
