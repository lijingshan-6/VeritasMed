"""R1: replay every saved v0.6 Atomic extraction without any model calls."""
# Bootstrap src before local imports so the offline script also runs from a checkout.
# ruff: noqa: E402

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from medrag.verification.answer_audit import text_hash
from medrag.verification.atomic_schema import AtomicAuditRequest
from medrag.verification.parent_binding import BINDING_VERSION, bind_parent_fragments
from medrag.verification.quote_audit import locate_quote
from medrag.verification.scifact import object_hash, read_jsonl
from v06_whole import load_cases


def old_position_valid(parent, fragments):
    return (
        bool(fragments)
        and parent["status"] == "unique"
        and all(
            b["status"] == "unique"
            and parent["span"]["start"] <= b["span"]["start"]
            and b["span"]["end"] <= parent["span"]["end"]
            for b in fragments
        )
    )


def summarize(rows):
    counts = Counter(audits=len(rows))
    transitions, parents = Counter(), Counter()
    for row in rows:
        counts["audits_with_extraction"] += row["extraction_present"]
        counts["original_checked_facts"] += row["original_checked_facts"]
        counts["all_positions_valid_before"] += bool(row["facts"]) and all(
            f["before_valid"] for f in row["facts"]
        )
        counts["all_positions_valid_after"] += bool(row["facts"]) and all(
            f["after"]["position_valid"] for f in row["facts"]
        )
        for fact in row["facts"]:
            counts["facts"] += 1
            counts["valid_before"] += fact["before_valid"]
            counts["valid_after"] += fact["after"]["position_valid"]
            recovered = not fact["before_valid"] and fact["after"]["position_valid"]
            counts["recovered_positions"] += recovered
            counts["recovered_without_original_judgment"] += (
                recovered and fact["original_relation"] is None
            )
            counts["regressed_positions"] += (
                fact["before_valid"] and not fact["after"]["position_valid"]
            )
            parents[fact["after"]["parent_binding"]["status"]] += 1
            for old, new in zip(fact["before"], fact["after"]["answer_bindings"]):
                counts["fragments"] += 1
                transitions[f"{old['status']} -> {new['status']}"] += 1
                counts["unique_before"] += old["status"] == "unique"
                counts["unique_after"] += new["status"] == "unique"
                counts["global_unique_outside_parent"] += (
                    old["status"] == "unique" and new["status"] == "not_found"
                )
                if new["span"]:
                    p, s = fact["after"]["parent_binding"]["span"], new["span"]
                    if not (
                        p["start"] <= s["start"] <= s["end"] <= p["end"]
                        and row["answer"][s["start"] : s["end"]] == new["quote"]
                    ):
                        raise ValueError("Invalid rebinding offset")
    return {
        **counts,
        "parent_statuses": dict(parents),
        "fragment_transitions": dict(transitions),
        "incorrect_cross_parent_links_after": 0,
        "semantic_judgments_added": 0,
    }


def build():
    cases = {
        str(c["id"]): c
        for dataset in ("medical_development", "medical_transfer", "natural")
        for c in load_cases(dataset)
    }
    paths = sorted((ROOT / "data/verification/v06").rglob("*.jsonl"))
    rows, files, inputs = [], {}, []
    for path in paths:
        original = read_jsonl(path)
        selected = [
            (line, r)
            for line, r in enumerate(original, 1)
            if r.get("audit", {}).get("strategy") == "atomic_v1"
        ]
        if not selected:
            continue
        relative = path.relative_to(ROOT).as_posix()
        files[relative] = object_hash(original)
        dataset = "no_slots" if path.parent.name == "ablations" else path.parent.name
        for line, record in selected:
            inputs.append((relative, line, dataset, record, cases[str(record["case_id"])]["input"]))
    # These three audits are distinct model calls, not exports of JSONL runs.
    # Keep the single-paper demonstration as its own stratum.
    for path in sorted((ROOT / "data/demo/reliability").glob("*-atomic_v1.json")):
        saved = json.loads(path.read_text(encoding="utf-8"))
        relative = path.relative_to(ROOT).as_posix()
        files[relative] = object_hash(saved)
        inputs.append(
            (
                relative,
                1,
                "grade_demo",
                {"audit": saved["audit"], "case_id": path.stem.removesuffix("-atomic_v1")},
                AtomicAuditRequest.model_validate(saved["input"]),
            )
        )
    seen = set()
    for relative, line, dataset, record, item in inputs:
        audit = record["audit"]
        if audit["id"] in seen:
            raise ValueError("Duplicate saved audit; do not count an export as a new run")
        seen.add(audit["id"])
        if audit["answer_sha256"] != text_hash(item.answer) or audit["source_hashes"] != {
            s.id: text_hash(s.text) for s in item.sources
        }:
            raise ValueError(f"Saved input fingerprint mismatch: {relative}:{line}")
        extracted = (audit.get("extraction") or {}).get("facts", [])
        if len(extracted) != len(audit["claims"]):
            raise ValueError("Extraction/claim denominator mismatch")
        facts = []
        for raw, claim in zip(extracted, audit["claims"]):
            parent = locate_quote(item.answer, raw["parent_quote"])
            before = [locate_quote(item.answer, q) for q in raw["answer_quotes"]]
            if parent != claim["parent_binding"] or before != claim["answer_bindings"]:
                raise ValueError("Cannot reproduce historical global bindings")
            after = bind_parent_fragments(item.answer, raw["parent_quote"], raw["answer_quotes"])
            facts.append(
                {
                    "fact_id": claim["id"],
                    "parent_quote": raw["parent_quote"],
                    "normalized_claim": raw["normalized_claim"],
                    "original_status": claim["status"],
                    "original_relation": claim["relation"],
                    "decomposition_status": raw["decomposition_status"],
                    "before": before,
                    "before_valid": old_position_valid(parent, before),
                    "after": after,
                    "judgment_policy": "Original status/relation unchanged; recovered location is not a new verification.",
                }
            )
        rows.append(
            {
                "record_id": f"{relative}:{line}",
                "dataset": dataset,
                "case_id": record["case_id"],
                "attempt": record.get("attempt", 1),
                "audit_id": audit["id"],
                "original_audit_sha256": object_hash(audit),
                "answer": item.answer,
                "answer_sha256": audit["answer_sha256"],
                "source_hashes": audit["source_hashes"],
                "original_status": audit["status"],
                "original_checked_facts": sum(c["status"] == "ok" for c in audit["claims"]),
                "extraction_present": audit.get("extraction") is not None,
                "facts": facts,
            }
        )
    by_dataset = defaultdict(list)
    for row in rows:
        by_dataset[row["dataset"]].append(row)
    summary = {
        "schema": 1,
        "binding_version": BINDING_VERSION,
        "model_calls": 0,
        "scope": "All v06 JSONL atomic_v1 audit records, including repeats and no-slots ablation, plus the three distinct GRADE demo audits. Output fixed; strata reported separately.",
        "interpretation": "Exact localization only. Original claim extraction and semantic judgments are unchanged. Recovered unjudged facts are still not checked.",
        "input_files": files,
        "total": summarize(rows),
        "datasets": {name: summarize(group) for name, group in sorted(by_dataset.items())},
    }
    return rows, summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "data/verification/v08/r1-parent-binding")
    args = p.parse_args()
    rows, summary = build()
    protocol = {
        "schema": 1,
        "binding_version": BINDING_VERSION,
        "inputs": summary["input_files"],
        "source_hashes": {
            name: object_hash((ROOT / name).read_text(encoding="utf-8"))
            for name in (
                "src/medrag/verification/parent_binding.py",
                "scripts/verification/v08_rebind.py",
            )
        },
        "rules": [
            "No model calls",
            "No original output mutation",
            "No semantic promotion from repaired positions",
            "All rows and failures retained",
            "Global Unicode code-point offsets",
            "No fuzzy matching or first-match fallback",
        ],
    }
    outputs = {
        "protocol.json": json.dumps(protocol, ensure_ascii=False, indent=2) + "\n",
        "summary.json": json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        "records.jsonl": "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        "changes.jsonl": "".join(
            json.dumps(
                {
                    "record_id": row["record_id"],
                    "case_id": row["case_id"],
                    "dataset": row["dataset"],
                    "kind": "recovered" if fact["after"]["position_valid"] else "unresolved",
                    "fact": fact,
                },
                ensure_ascii=False,
            )
            + "\n"
            for row in rows
            for fact in row["facts"]
            if not fact["before_valid"] or not fact["after"]["position_valid"]
        ),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        target = args.output / name
        if target.exists() and target.read_text(encoding="utf-8") != content:
            raise ValueError("Existing replay differs; use a new output directory.")
        target.write_text(content, encoding="utf-8")
    print(
        json.dumps(
            {"total": summary["total"], "datasets": summary["datasets"]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
