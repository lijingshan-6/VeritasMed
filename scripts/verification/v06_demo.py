"""Run the unchanged real Ask answer and explicitly authored medical controls."""

import argparse
import json
from datetime import datetime, timezone

from medrag.verification.atomic_audit import audit_atomic
from medrag.verification.atomic_schema import AtomicAuditRequest
from medrag.verification.answer_audit import audit_answer
from medrag.verification.scifact import object_hash
from v06_prepare import ROOT
from v06_fixed import dump

OUT = ROOT / "data/demo/reliability"


def inputs():
    saved = json.loads((ROOT / "data/demo/medical/audit.json").read_text(encoding="utf8"))
    original = AtomicAuditRequest.model_validate(saved["input"])
    answer = original.answer.replace("10 (0.8%), 16 (1.3%)", "16 (1.3%), 10 (0.8%)", 1)
    if answer == original.answer:
        raise ValueError("Expected mutation anchor missing")
    return [
        (
            "grade-original",
            "GRADE · unchanged real Agent answer",
            original,
            "Unchanged actual v0.5 Ask answer and source excerpts; new audit only. Not an independently labelled medical evaluation.",
        ),
        (
            "grade-arm-swap",
            "GRADE · deliberately swapped arm values",
            original.model_copy(update={"answer": answer}),
            "Constructed diagnostic: glargine and glimepiride severe-hypoglycemia counts/percentages swapped. Other text unchanged. Not a natural Agent error.",
        ),
        (
            "grade-evidence-gap",
            "GRADE · result evidence deliberately removed",
            original.model_copy(update={"sources": [original.sources[3]]}),
            "Constructed diagnostic: only the original background excerpt remains. The answer is unchanged; result/method details are not supplied. Not a natural retrieval failure rate.",
        ),
    ]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["prepare", "run"])
    args = p.parse_args()
    cases = inputs()
    protocol = {
        "inputs": {key: object_hash(item.model_dump()) for key, _, item, _ in cases},
        "methods": ["direct", "atomic_v1"],
        "origin": "Seaquist et al. 2024, PMC11567630, CC0",
        "note": "Demonstration only; no selection from multiple attempts",
    }
    if args.action == "prepare":
        OUT.mkdir(parents=True, exist_ok=False)
        dump(OUT / "protocol.json", protocol)
        return
    if json.loads((OUT / "protocol.json").read_text(encoding="utf8")) != protocol:
        raise ValueError("Demo inputs changed")
    from medrag.verification.gateway import FlashGateway

    model = FlashGateway()
    model.client = model.client.with_options(max_retries=0)
    model.settings["sdk_max_retries"] = 0
    catalogue = []
    for key, label, item, note in cases:
        methods = {}
        for method in protocol["methods"]:
            path = OUT / f"{key}-{method}.json"
            if not path.exists():
                request = item.model_copy(update={"strategy": method})
                result = (
                    audit_atomic(request, model)
                    if method == "atomic_v1"
                    else audit_answer(request, model)
                )
                dump(
                    path,
                    {
                        "input": request.model_dump(),
                        "audit": result,
                        "mode": "saved",
                        "provenance": {
                            "note": note,
                            "paper": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11567630/",
                            "created_utc": datetime.now(timezone.utc).isoformat(),
                            "settings": model.settings,
                        },
                    },
                )
            record = json.loads(path.read_text(encoding="utf8"))
            methods[method] = record["audit"]["status"]
            print(f"{key} {method} {methods[method]}", flush=True)
            if any(c.get("http_status") in (401, 402, 403, 429) for c in record["audit"]["calls"]):
                return
        catalogue.append(
            {"id": key, "label": label, "requires_download": False, "strategies": methods}
        )
        dump(OUT / "catalogue.json", catalogue)


if __name__ == "__main__":
    main()
