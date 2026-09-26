"""Offline-only fixed-target metrics and calibrated acceptance research."""

import argparse
from collections import Counter
import json
from statistics import median

from medrag.verification.research_metrics import fixed_metrics, paired_intervals, wilson
from medrag.verification.scifact import object_hash, read_jsonl
from v06_fixed import dump
from v06_prepare import OUT, load_cases


def entries_for(manifest, split):
    return [
        e
        for e in manifest["entries"]
        if (e["case_id"] in manifest["pilot_ids"] if split == "pilot" else e["split"] == split)
    ]


def fixed_report(split):
    manifest = json.loads((OUT / "splits.json").read_text(encoding="utf8"))
    entries = entries_for(manifest, split)
    results = {}
    predictions = {}
    for method in ("flash", "minicheck"):
        path = OUT / "fixed" / f"{split}-{method}" / "predictions.jsonl"
        if path.exists():
            predictions[method] = read_jsonl(path)
            results[method] = fixed_metrics(entries, predictions[method])
            rows = predictions[method]
            usages = [(r.get("usage") or {}).get("total_tokens") for r in rows]
            results[method]["runtime"] = {
                "statuses": dict(Counter(r["status"] for r in rows)),
                "reported_tokens": sum(t for t in usages if t is not None),
                "records_without_token_usage": sum(t is None for t in usages),
                "median_seconds": median(r["elapsed_seconds"] for r in rows) if rows else None,
                "sum_elapsed_seconds": sum(r["elapsed_seconds"] for r in rows),
                "response_models": dict(
                    Counter(r.get("response_model", r.get("model", "unavailable")) for r in rows)
                ),
                "note": "MiniCheck is local single-pass scoring; missing API token usage does not mean zero compute. Latency excludes model loading and is not batch wall time.",
            }
            if method == "flash":
                # A secondary label-only view separates semantic labels from the extra citation contract.
                parsed = []
                for row in rows:
                    relation = (row.get("decision") or {}).get("relation")
                    usable = row.get("status") in (
                        "ok",
                        "invalid_evidence_reference",
                    ) and relation in ("supported", "contradicted", "insufficient")
                    parsed.append(
                        {
                            "case_id": row["case_id"],
                            "status": "ok" if usable else row["status"],
                            "binary_prediction": int(relation == "supported") if usable else None,
                        }
                    )
                results[method]["parsed_relation_diagnostic"] = {
                    **fixed_metrics(entries, parsed),
                    "scope": "Post-hoc label-only diagnostic, declared after E2 development reference failures while fixed final inference was running. Ignores invalid evidence references only; never replaces the primary full-contract score or changes a frozen method/threshold/default. MiniCheck has no evidence-reference output contract.",
                }
                by = {r["case_id"]: r for r in rows}
                gold_cases = load_cases()
                matrix = Counter()
                rationale = Counter()
                for e in entries:
                    row = by.get(e["case_id"], {})
                    decision = row.get("decision") or {}
                    prediction = (
                        decision.get("relation")
                        if row.get("status") == "ok"
                        else row.get("status", "not_run")
                    )
                    matrix[(e["relation"], prediction)] += 1
                    sets = [set(ids) for ids in gold_cases[e["case_id"]].rationale_sets]
                    if not sets:
                        continue
                    cited = (
                        set(decision.get("sentence_ids", []))
                        if row.get("status") == "ok"
                        else set()
                    )
                    correct = prediction == e["relation"]
                    rationale.update(
                        annotated_pairs=1,
                        exact_one_annotation=any(cited == s for s in sets),
                        covers_one_annotation=any(s <= cited for s in sets),
                        correct_relation_and_covers=correct and any(s <= cited for s in sets),
                    )
                results[method]["three_class_matrix"] = [
                    {"gold": g, "prediction": p, "n": n} for (g, p), n in matrix.items()
                ]
                results[method]["rationale_annotation_comparison"] = {
                    "counts": dict(rationale),
                    "note": "Matching one public rationale set is not independent semantic adjudication; alternative valid evidence may not be annotated. No-rationale insufficient pairs excluded only from this secondary table.",
                }
    if len(results) == 2:
        results["minicheck_minus_flash"] = paired_intervals(results["flash"], results["minicheck"])
        common = {r["case_id"] for r in predictions["flash"] if r["status"] == "ok"} & {
            r["case_id"] for r in predictions["minicheck"] if r["status"] == "ok"
        }
        results["common_success"] = {
            m: fixed_metrics(
                [e for e in entries if e["case_id"] in common],
                [r for r in rows if r["case_id"] in common],
            )
            for m, rows in predictions.items()
        }
    dump(OUT / f"fixed-{split}-metrics.json", results)
    print(
        json.dumps(
            {
                k: {
                    x: v[x]
                    for x in (
                        "counts",
                        "false_acceptance_rate",
                        "support_recall",
                        "all_case_accuracy",
                    )
                    if x in v
                }
                for k, v in results.items()
            },
            indent=2,
        )
    )


def calibrate():
    import numpy as np
    from sklearn.linear_model import LogisticRegression

    manifest = json.loads((OUT / "splits.json").read_text(encoding="utf8"))

    def load(split):
        es = entries_for(manifest, split)
        rows = read_jsonl(OUT / "fixed" / f"{split}-minicheck" / "predictions.jsonl")
        by = {r["case_id"]: r for r in rows}
        valid = [e for e in es if by.get(e["case_id"], {}).get("status") == "ok"]
        scores = np.array([by[e["case_id"]]["raw_support_score"] for e in valid])
        return (
            es,
            valid,
            np.log(np.clip(scores, 1e-6, 1 - 1e-6) / (1 - np.clip(scores, 1e-6, 1 - 1e-6))).reshape(
                -1, 1
            ),
            np.array([e["relation"] == "supported" for e in valid], dtype=int),
        )

    _, fit, x, y = load("score_fit")
    model = LogisticRegression(C=1.0, random_state=260926, max_iter=1000).fit(x, y)
    _, select, sx, sy = load("threshold_select")
    scores = model.predict_proba(sx)[:, 1]
    thresholds = [i / 200 for i in range(201)]
    curve = []
    for t in thresholds:
        mask = scores >= t
        accepted = int(sum(mask))
        errors = int(sum(sy[mask] == 0))
        groups = len({e["group_id"] for e, keep in zip(select, mask) if keep})
        curve.append(
            {
                "threshold": t,
                "accepted": accepted,
                "source_groups": groups,
                "errors": errors,
                "risk": errors / accepted if accepted else None,
            }
        )
    eligible = [
        r for r in curve if r["accepted"] >= 20 and r["source_groups"] >= 10 and r["risk"] <= 0.05
    ]
    chosen = max(eligible, key=lambda r: (r["accepted"], -r["threshold"])) if eligible else None
    result = {
        "method": "logistic on clipped raw-score logit, C=1, max_iter=1000",
        "coefficient": float(model.coef_[0, 0]),
        "intercept": float(model.intercept_[0]),
        "fit_count": len(fit),
        "select_count": len(select),
        "threshold_rule": "max coverage with empirical risk <=5%, >=20 accepted pairs, >=10 source groups; not statistical guarantee",
        "selection_curve": curve,
        "chosen": chosen,
        "manifest_sha256": object_hash(manifest),
        "final_used": False,
    }
    path = OUT / "calibration.json"
    if path.exists() and json.loads(path.read_text(encoding="utf8")) != result:
        raise ValueError("Calibration already frozen")
    dump(path, result)
    print(json.dumps({"fit": len(fit), "select": len(select), "chosen": chosen}, indent=2))


def evaluate_calibration():
    import math

    manifest = json.loads((OUT / "splits.json").read_text(encoding="utf8"))
    cal = json.loads((OUT / "calibration.json").read_text(encoding="utf8"))
    rows = {r["case_id"]: r for r in read_jsonl(OUT / "fixed/final-minicheck/predictions.jsonl")}
    entries = entries_for(manifest, "final")
    values = []
    for e in entries:
        r = rows.get(e["case_id"], {})
        if r.get("status") != "ok":
            continue
        raw = max(1e-6, min(1 - 1e-6, r["raw_support_score"]))
        z = cal["intercept"] + cal["coefficient"] * math.log(raw / (1 - raw))
        p = 1 / (1 + math.exp(-z))
        values.append({**e, "raw": raw, "calibrated": p, "y": int(e["relation"] == "supported")})
    t = cal["chosen"]["threshold"] if cal["chosen"] else None

    def risk(items, threshold):
        accepted = [v for v in items if threshold is not None and v["calibrated"] >= threshold]
        errors = sum(v["y"] == 0 for v in accepted)
        return {
            "planned": len(items),
            "accepted": len(accepted),
            "errors": errors,
            "risk": errors / len(accepted) if accepted else None,
            "coverage": len(accepted) / len(items) if items else None,
            "wilson95": wilson(errors, len(accepted)),
        }

    # Representative ID chosen by seed before considering scores/labels, even if that run failed.
    representative_ids = {
        min(
            [e for e in entries if e["group_id"] == g],
            key=lambda e: object_hash(["v06-risk-representative", e["case_id"]]),
        )["case_id"]
        for g in {e["group_id"] for e in entries}
    }
    result = {
        "calibration_sha256": object_hash(cal),
        "threshold": t,
        "planned_pairs": len(entries),
        "completed": len(values),
        "brier_raw": sum((v["raw"] - v["y"]) ** 2 for v in values) / len(values),
        "brier_calibrated": sum((v["calibrated"] - v["y"]) ** 2 for v in values) / len(values),
        "all_pairs": risk(values, t),
        "independent_representatives": risk(
            [v for v in values if v["case_id"] in representative_ids], t
        ),
        "representative_planned": len(representative_ids),
        "risk_coverage_curve": [
            {"threshold": i / 100, **risk(values, i / 100)} for i in range(101)
        ],
        "reliability_bins": [
            {
                "lower": i / 10,
                "n": len(vs),
                "mean_score": sum(v["calibrated"] for v in vs) / len(vs) if vs else None,
                "observed_support": sum(v["y"] for v in vs) / len(vs) if vs else None,
            }
            for i in range(10)
            for vs in [[v for v in values if i / 10 <= v["calibrated"] < (i + 1) / 10]]
        ],
        "note": "Uncertainty is source-population-specific. Pair Wilson interval is descriptive; group representatives address dependence. No selected policy if threshold null.",
    }
    result["all_pairs"]["coverage_among_completed"] = result["all_pairs"]["coverage"]
    result["all_pairs"]["planned"] = len(entries)
    result["all_pairs"]["coverage"] = result["all_pairs"]["accepted"] / len(entries)
    result["independent_representatives"]["coverage_among_completed"] = result[
        "independent_representatives"
    ]["coverage"]
    result["independent_representatives"]["planned"] = len(representative_ids)
    result["independent_representatives"]["coverage"] = result["independent_representatives"][
        "accepted"
    ] / len(representative_ids)
    for point in result["risk_coverage_curve"]:
        point["coverage_among_completed"] = point["coverage"]
        point["planned"] = len(entries)
        point["coverage"] = point["accepted"] / len(entries)
    dump(OUT / "calibration-final.json", result)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in ("risk_coverage_curve", "reliability_bins")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["pilot", "final", "calibrate", "calibration_final"])
    args = p.parse_args()
    if args.action == "calibrate":
        calibrate()
    elif args.action == "calibration_final":
        evaluate_calibration()
    else:
        fixed_report(args.action)
