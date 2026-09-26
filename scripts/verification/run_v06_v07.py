"""Continue the predeclared milestone experiments, stopping on incomplete/provider-failed runs.

Run only after the medical development batch. This dispatcher never starts more than one
API batch at a time; individual runners cap concurrency at three. Existing attempts stay intact.
"""

import argparse
import json
import subprocess
import sys

from medrag.verification.scifact import object_hash, read_jsonl
from v06_fixed import dump
from v06_prepare import OUT, ROOT


def command(script, *args, python=None):
    subprocess.run(
        [python or sys.executable, "-X", "utf8", f"scripts/verification/{script}.py", *args],
        cwd=ROOT,
        check=True,
    )


def complete(directory, field="schedule"):
    protocol = json.loads((directory / "protocol.json").read_text(encoding="utf8"))
    rows = (
        read_jsonl(directory / "predictions.jsonl")
        if (directory / "predictions.jsonl").exists()
        else []
    )
    if len(rows) != len(protocol[field]):
        raise RuntimeError(
            f"Incomplete run: {directory}; resolve provider access or execution before continuing"
        )
    return object_hash(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gpu-python", default=sys.executable)
    p.add_argument(
        "--workflow-only",
        action="store_true",
        help="Continue workflow development/final/demo after completed audit studies",
    )
    a = p.parse_args()
    if not a.workflow_only:
        complete(OUT / "whole/medical_development")
        if not (OUT / "ablations/manifest.json").exists():
            command("v06_ablations", "prepare")
        for method in ("no_slots", "flash", "minicheck"):
            command("v06_ablations", method, python=a.gpu_python if method == "minicheck" else None)
            rows = read_jsonl(OUT / "ablations" / f"{method}.jsonl")
            if len(rows) != 12:
                raise RuntimeError("Incomplete controlled ablation; stop")
            checks = [c for r in rows for c in r.get("audit", {}).get("calls", [])]
            checks += [f["result"] for r in rows for f in r.get("facts", [])]
            if any(c.get("http_status") in (401, 402, 403, 429) for c in checks):
                raise RuntimeError("Provider blocked during ablation; stop")
        for dataset in ("natural", "repeat"):
            if not (OUT / "whole" / dataset / "protocol.json").exists():
                command("v06_whole", "prepare", "--dataset", dataset)
            command("v06_whole", "run", "--dataset", dataset)
            complete(OUT / "whole" / dataset)
        command("v06_ablation_report")
        command("v06_whole_report")
        freeze = {
            "decision": "Keep Direct default; atomic_v1 remains experimental",
            "reason": "No independent whole-answer semantic gold; authored diagnostic and span coverage do not meet default-upgrade criteria. No prompt adjustment made.",
            "development_prediction_hashes": {
                s: complete(OUT / "whole" / s) for s in ("medical_development", "natural", "repeat")
            },
            "reserved_ragtruth_test": "60 source groups remain unopened; semantic scorer not validated",
            "transfer": "Run fixed methods once on all 8 constructed transfer groups; report as construction, not clinical validation",
        }
        if not (OUT / "method-freeze.json").exists():
            dump(OUT / "method-freeze.json", freeze)
        elif json.loads((OUT / "method-freeze.json").read_text(encoding="utf8")) != freeze:
            raise RuntimeError("Whole-answer freeze changed")
        for method in ("flash", "minicheck"):
            directory = OUT / "fixed" / f"final-{method}"
            if not (directory / "protocol.json").exists():
                command("v06_fixed", "prepare", "--split", "final", "--method", method)
            if (
                not (directory / "predictions.jsonl").exists()
                or len(read_jsonl(directory / "predictions.jsonl")) != 339
            ):
                command(
                    "v06_fixed",
                    "run",
                    "--split",
                    "final",
                    "--method",
                    method,
                    python=a.gpu_python if method == "minicheck" else None,
                )
            complete(directory)
        command("v06_report", "final")
        command("v06_report", "calibration_final", python=a.gpu_python)
        if not (OUT / "whole/medical_transfer/protocol.json").exists():
            command("v06_whole", "prepare", "--dataset", "medical_transfer")
        command("v06_whole", "run", "--dataset", "medical_transfer")
        complete(OUT / "whole/medical_transfer")
        command("v06_whole_report")
    v07 = ROOT / "data/verification/v07"
    if not (v07 / "development/protocol.json").exists():
        command("v07_benchmark", "prepare", "--split", "development")
    command("v07_benchmark", "run", "--split", "development")
    digest = complete(v07 / "development")
    command("v07_report", "development")
    freeze = {
        "decision": "Evaluate all three workflows with the v2 action adapter selected after retained first-round protocol failures; no final-set tuning or baseline exclusion",
        "development_predictions_sha256": digest,
        "final_queries": 40,
        "scope": "Named-paper fixed-candidate-corpus comparison, not historical Ask graph superiority",
    }
    if (v07 / "development-original/predictions.jsonl").exists():
        freeze["original_development_predictions_sha256"] = complete(v07 / "development-original")
        freeze["development_revision"] = (
            "Finish-contract clarification; recorded leading-JSON/DSML discard and bare-answer wrapping; all three arms rerun before final"
        )
    if not (v07 / "method-freeze.json").exists():
        dump(v07 / "method-freeze.json", freeze)
    elif json.loads((v07 / "method-freeze.json").read_text(encoding="utf8")) != freeze:
        raise RuntimeError("Workflow freeze changed")
    if not (v07 / "final/protocol.json").exists():
        command("v07_benchmark", "prepare", "--split", "final")
    command("v07_benchmark", "run", "--split", "final")
    complete(v07 / "final")
    command("v07_report", "final")
    if not (ROOT / "data/demo/reliability/protocol.json").exists():
        command("v06_demo", "prepare")
    command("v06_demo", "run")
    command("v06_demo_minicheck", python=a.gpu_python)
    print(
        "Research runs finished. Inspect results, finish UI/documentation and publication separately; no automatic claim of release.",
        flush=True,
    )


if __name__ == "__main__":
    main()
