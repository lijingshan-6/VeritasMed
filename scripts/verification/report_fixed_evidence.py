"""Recompute saved pilot metrics offline, without loading API configuration."""
import argparse
import json
from pathlib import Path

from medrag.verification.scifact import object_hash, prepare_pilot, read_jsonl
from medrag.verification.scoring import score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path(".benchmark-runtime/scifact"))
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    cases, manifest = prepare_pilot(args.cache)
    settings = json.loads((args.run / "run.json").read_text(encoding="utf-8"))
    if object_hash(manifest) != settings["manifest_sha256"]:
        raise ValueError("Cached data/selection do not match the saved run")
    metrics = score(cases, read_jsonl(args.run / "predictions.jsonl"))
    saved = args.run / "metrics.json"
    if saved.exists() and json.loads(saved.read_text(encoding="utf-8")) != metrics:
        raise ValueError("Recomputed metrics differ from the saved results")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
