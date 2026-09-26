"""Supplement saved medical atoms with a separate local checker, retaining original audits."""

import json
import time
from datetime import datetime, timezone

from medrag.verification.minicheck_adapter import MiniCheckAdapter
from medrag.verification.scifact import object_hash
from v06_prepare import ROOT
from v06_fixed import dump


def main():
    directory = ROOT / "data/demo/reliability"
    model = MiniCheckAdapter()
    for key in ("grade-original", "grade-arm-swap", "grade-evidence-gap"):
        source = directory / f"{key}-atomic_v1.json"
        if not source.exists():
            raise ValueError("Run Flash demo first")
        record = json.loads(source.read_text(encoding="utf8"))
        path = directory / f"{key}-minicheck.json"
        if path.exists():
            continue
        started = time.perf_counter()
        facts = []
        document = "\n\n".join(s["title"] + "\n" + s["text"] for s in record["input"]["sources"])
        for fact in record["audit"]["claims"]:
            score = model.score(document, fact["normalized_claim"])
            facts.append(
                {
                    "fact_id": fact["id"],
                    "normalized_claim_sha256": object_hash(fact["normalized_claim"]),
                    "result": score,
                }
            )
        dump(
            path,
            {
                "base_record_sha256": object_hash(record),
                "settings": model.settings,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "facts": facts,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "scope": "Supplemental standalone parsed-fact scoring; differs from contextual Flash audit. No aggregation, calibrated probability or independent gold.",
            },
        )
        print(key, len(facts), "supplemental local checks", flush=True)


if __name__ == "__main__":
    main()
