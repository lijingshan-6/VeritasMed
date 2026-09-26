"""Same frozen atom table, controlled slot ablation and standalone-checker comparison."""

import argparse
from datetime import datetime, timezone
import json

from medrag.verification.atomic_audit import audit_atomic
from medrag.verification.schema import EvidenceDocument, VerificationInput
from medrag.verification.verifier import verify
from medrag.verification.scifact import object_hash, read_jsonl
from v06_prepare import OUT, SEED
from v06_fixed import dump
from v06_whole import load_cases


def prepare():
    rows = read_jsonl(OUT / "whole/medical_development/predictions.jsonl")
    cases = {c["id"]: c for c in load_cases("medical_development")}
    # Source selection depends only on frozen IDs, never on method behavior.
    selected_groups = sorted(
        {c["group_id"] for c in cases.values()}, key=lambda g: object_hash([SEED, "ablation", g])
    )[:3]
    selected = [
        r
        for r in rows
        if r["method"] == "atomic_v1" and cases[r["case_id"]]["group_id"] in selected_groups
    ]
    if len(selected) != 12:
        raise ValueError("Finish all medical development first")
    manifest = {
        "selected_groups": selected_groups,
        "selection": "3 source groups by seed; all four variants; no output selection",
        "rows": selected,
        "source_run_sha256": object_hash(rows),
        "E2_contract": "Both checkers receive the identical frozen standalone normalized claim plus same complete supplied source view; neither receives answer as evidence. This is conditional on extraction, not fidelity validation.",
        "E4_contract": "Same extracted table, answer and sources; remove explicit slots only in the verification call. Missing/failed extraction remains a failure in denominator.",
    }
    directory = OUT / "ablations"
    directory.mkdir(parents=True, exist_ok=False)
    dump(directory / "manifest.json", manifest)
    print("Frozen 12 same-table development ablations")


def run(method):
    manifest = json.loads((OUT / "ablations/manifest.json").read_text(encoding="utf8"))
    cases = {c["id"]: c for c in load_cases("medical_development")}
    path = OUT / "ablations" / f"{method}.jsonl"
    old = read_jsonl(path) if path.exists() else []
    done = {r["case_id"] for r in old}
    if method == "minicheck":
        from medrag.verification.minicheck_adapter import MiniCheckAdapter

        model = MiniCheckAdapter()
    else:
        from medrag.verification.gateway import FlashGateway

        model = FlashGateway()
        model.client = model.client.with_options(max_retries=0)
        model.settings["sdk_max_retries"] = 0
    for row in manifest["rows"]:
        if row["case_id"] in done:
            continue
        item = cases[row["case_id"]]["input"]
        extraction = row["audit"].get("extraction")
        result = {
            "case_id": row["case_id"],
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "settings": model.settings,
        }
        if extraction is None:
            result["status"] = "extraction_failed"
        elif method == "no_slots":
            result["audit"] = audit_atomic(
                item, model, with_slots=False, frozen_extraction=extraction
            )
        else:
            doc = EvidenceDocument(
                document_id=item.sources[0].id,
                title=item.sources[0].title,
                sentences=[item.sources[0].text],
            )
            result["facts"] = []
            for i, fact in enumerate(extraction["facts"]):
                target = VerificationInput(
                    case_id=f"{row['case_id']}-fact-{i + 1}",
                    claim=fact["normalized_claim"],
                    document=doc,
                )
                checked = model.verify(target) if method == "minicheck" else verify(target, model)
                result["facts"].append(
                    {
                        "input_sha256": object_hash(target.model_dump()),
                        "fact_index": i,
                        "result": checked,
                    }
                )
                if checked.get("http_status") in (401, 402, 403, 429):
                    break
        with path.open("a", encoding="utf8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
        print(row["case_id"], method, flush=True)
        checks = result.get("audit", {}).get("calls", []) + [
            f["result"] for f in result.get("facts", [])
        ]
        if any(c.get("http_status") in (401, 402, 403, 429) for c in checks):
            break


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["prepare", "no_slots", "flash", "minicheck"])
    a = p.parse_args()
    if a.action == "prepare":
        prepare()
    else:
        run(a.action)
