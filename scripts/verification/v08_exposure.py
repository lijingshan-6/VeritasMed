"""Offline source exposure inventory; no inference or reserved-test text review."""
# Bootstrap src before local imports so the offline script also runs from a checkout.
# ruff: noqa: E402

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from medrag.verification.scifact import FILES, adapt_pairs, document_ids, object_hash, read_jsonl
from medrag.verification.ragtruth import HASHES as RAGTRUTH_HASHES

OUT = ROOT / "data/verification/v08/exposure"


def norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def walk(value):
    if isinstance(value, dict):
        yield value
        for key, child in value.items():
            if key not in {
                "reserved_official_test",
                "code_hashes",
                "source_file_hashes",
                "frozen_source",
            }:
                yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def json_file(path):
    return (
        read_jsonl(path)
        if path.suffix == ".jsonl"
        else json.loads(path.read_text(encoding="utf-8"))
    )


def artifact_paths(include_local):
    roots = [
        ROOT / name for name in ("data/verification", "data/demo", "data/benchmark", "docs/assets")
    ]
    if include_local:
        roots += [ROOT / "output", ROOT / ".benchmark-runtime/diagnostics"]
    paths = {
        p
        for root in roots
        if root.exists()
        for p in root.rglob("*")
        if p.suffix in {".json", ".jsonl"}
    }
    if include_local:
        paths |= {
            p
            for p in (ROOT / ".benchmark-runtime").glob("*.json*")
            if p.is_file() and p.suffix in {".json", ".jsonl"}
        }
    # Split membership alone is not use. Generated inventory/replay files and
    # archived source code cannot bootstrap themselves into additional exposure.
    return sorted(
        p
        for p in paths
        if p.name
        not in {
            "splits.json",
            "frozen-source.json",
            "frozen-source-v2.json",
            "tsconfig.json",
            "openapi.json",
        }
        and not any(part == "exposure" or part.startswith("r1-") for part in p.parts)
    )


def build(include_local=False):
    cache = ROOT / ".benchmark-runtime/scifact"
    corpus, train, dev = [read_jsonl(cache / name) for name in FILES]
    docs = {str(d["doc_id"]): d for d in corpus}
    old = json_file(ROOT / "data/verification/v06/splits.json")
    if {f: object_hash(read_jsonl(cache / f)) for f in FILES} != old["source_file_hashes"]:
        raise ValueError("Pinned SciFact files changed")
    parent = {d: d for d in docs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for claim in train + dev:
        ids = sorted(document_ids(claim))
        for other in ids[1:]:
            parent[find(other)] = find(ids[0])
    members = defaultdict(list)
    for doc in docs:
        members[find(doc)].append(doc)
    groups = {doc: object_hash(sorted(group))[:16] for group in members.values() for doc in group}
    if any(groups[e["document_id"]] != e["group_id"] for e in old["entries"]):
        raise ValueError("Source grouping no longer matches historical partitions")

    exposure, rag_exposure = defaultdict(set), defaultdict(set)
    records = {}

    def mark(doc, reason):
        if str(doc) in docs:
            exposure[str(doc)].add(reason)

    for doc in old["exposure"]["prior_document_ids"]:
        mark(doc, "v06-inherited-prior-exposure")
    old_titles = set()
    for name in (
        "data/raw/pubmed/abstracts.jsonl",
        "data/raw/pmc/full_texts.jsonl",
        "data/demo/medical/corpus.jsonl",
    ):
        path = ROOT / name
        if not path.exists():
            raise ValueError(f"Missing old corpus exposure input: {name}")
        raw = json_file(path)
        records[name] = object_hash(raw)
        old_titles.update(norm(r["title"]) for r in walk(raw) if isinstance(r.get("title"), str))
    title_docs = defaultdict(set)
    for doc, record in docs.items():
        title_docs[norm(record["title"])].add(doc)
        if norm(record["title"]) in old_titles:
            mark(doc, "old-medical-corpus-title")

    # All supplied distractors count, even if one tool agent did not open them:
    # other arms read the same pack and search displayed titles.
    v07 = json_file(ROOT / "data/verification/v07/manifest.json")
    targets = {str(c["document_id"]) for c in v07["cases"]}
    distractors = {
        str(d) for c in v07["cases"] for d in c["document_ids"] if str(d) != str(c["document_id"])
    }
    for doc in targets:
        mark(doc, "v07-target")
    for doc in distractors:
        mark(doc, "v07-supplied-distractor")

    rag_cache = ROOT / ".benchmark-runtime/ragtruth"
    rag_hashes = {
        name: hashlib.sha256((rag_cache / name).read_bytes()).hexdigest()
        for name in RAGTRUTH_HASHES
    }
    if rag_hashes != RAGTRUTH_HASHES:
        raise ValueError("Pinned RAGTruth files changed")
    rag_rows = read_jsonl(rag_cache / "response.jsonl")
    response_source = {str(r["id"]): str(r["source_id"]) for r in rag_rows}
    test_sources = {str(r["source_id"]) for r in rag_rows if r["split"] == "test"}
    # Parse the JSON file, but do not consume test source text or annotations.
    rag_source_meta = {}
    for r in read_jsonl(rag_cache / "source_info.jsonl"):
        source = str(r["source_id"])
        rag_source_meta[source] = {"task_type": r["task_type"]}
        if source not in test_sources:
            rag_source_meta[source]["length"] = (
                len(r["source_info"]) if isinstance(r["source_info"], str) else None
            )
    reserve = json_file(ROOT / "data/verification/ragtruth_v1/run01/manifest.json")[
        "reserved_official_test"
    ]
    reserved_ids = {str(r["source_id"]) for r in reserve}
    split_case = {e["case_id"]: e["document_id"] for e in old["entries"]}
    parse_failures = []
    for path in artifact_paths(include_local):
        relative = path.relative_to(ROOT).as_posix()
        try:
            value = json_file(path)
        except (ValueError, UnicodeError):
            parse_failures.append(relative)
            continue
        records[relative] = object_hash(value)
        rag_path = any(
            s in relative
            for s in (
                "ragtruth_v1/",
                "context_v1/",
                "quote_v2/",
                "whole/natural/",
                "whole/repeat/",
                "v06/natural.json",
            )
        )
        for record in walk(value):
            case = record.get("case_id")
            if isinstance(case, str) and case in split_case:
                mark(split_case[case], relative + ":case")
            if "document_id" in record:
                mark(record["document_id"], relative + ":document")
            for doc in record.get("read_document_ids", []):
                mark(doc, relative + ":tool-read")
            for doc in record.get("document_ids", []):
                mark(doc, relative + ":supplied-pack")
            title = record.get("title")
            if isinstance(title, str):
                for doc in title_docs.get(norm(title), []):
                    mark(doc, relative + ":title")
            # Fingerprint keys describe actual inputs, not only target identifiers.
            hashes = record.get("source_hashes", {})
            if isinstance(hashes, dict):
                for source in hashes:
                    if not rag_path:
                        mark(source, relative + ":audit-source")
                    if rag_path and str(source) in rag_source_meta:
                        rag_exposure[str(source)].add(relative + ":audit-source")
            source = record.get("source_id")
            if rag_path and str(source) in rag_source_meta:
                rag_exposure[str(source)].add(relative + ":source")
            response = record.get("response_id")
            if response is not None and str(response) in response_source:
                rag_exposure[response_source[str(response)]].add(relative + ":response")
    if parse_failures:
        raise ValueError(f"Cannot inventory unparsed artifacts: {parse_failures}")

    used_groups = {groups[doc] for doc in exposure}
    labelled = adapt_pairs(corpus, train, "train") + adapt_pairs(corpus, dev, "dev")
    fresh_pairs = [p for p in labelled if groups[p.input.document.document_id] not in used_groups]
    fresh_pair_groups = {groups[p.input.document.document_id] for p in fresh_pairs}
    candidates = []
    for doc, record in docs.items():
        if groups[doc] in used_groups:
            continue
        numeric_sentences = sum(bool(re.search(r"\d", s)) for s in record["abstract"])
        medical_words = bool(
            re.search(
                r"\b(patient|trial|participants|women|men|adults|children|cohort|randomized)\b",
                " ".join(record["abstract"]),
                re.I,
            )
        )
        if numeric_sentences >= 2 and medical_words:
            candidates.append(
                {
                    "document_id": doc,
                    "group_id": groups[doc],
                    "numeric_sentences": numeric_sentences,
                }
            )
    rag_candidates = []
    for row in rag_rows:
        source = str(row["source_id"])
        if row["split"] != "train" or source in test_sources or source in rag_exposure:
            continue
        meta = rag_source_meta[source]
        if (
            row["quality"] != "good"
            or meta["task_type"] != "Summary"
            or meta["length"] is None
            or meta["length"] > 50000
            or len(row["response"]) > 12000
        ):
            continue
        rag_candidates.append(
            {
                "response_id": str(row["id"]),
                "source_id": source,
                "has_marked_error": bool(row["labels"]),
            }
        )
    counts = {
        "scifact": {
            "corpus_documents": len(docs),
            "source_connected_groups": len(members),
            "directly_exposed_documents": len(exposure),
            "exposed_groups": len(used_groups),
            "excluded_documents_after_group_closure": sum(groups[d] in used_groups for d in docs),
            "v07_target_documents": len(targets),
            "v07_distractor_documents": len(distractors),
            "fresh_public_label_pairs": len(fresh_pairs),
            "fresh_public_label_groups": len(fresh_pair_groups),
            "fresh_public_label_counts": dict(Counter(p.relation.value for p in fresh_pairs)),
            "mechanically_screened_medical_numeric_documents": len(candidates),
            "mechanically_screened_medical_numeric_groups": len(
                {c["group_id"] for c in candidates}
            ),
        },
        "ragtruth": {
            "exposed_source_groups": len(rag_exposure),
            "reserved_official_test_groups": len(reserved_ids),
            "reserved_test_groups_with_recorded_exposure": len(reserved_ids & set(rag_exposure)),
            "fresh_train_summary_sources": len({r["source_id"] for r in rag_candidates}),
            "fresh_train_summary_responses": len(rag_candidates),
            "fresh_sources_with_marked_response": len(
                {r["source_id"] for r in rag_candidates if r["has_marked_error"]}
            ),
            "fresh_sources_with_unmarked_response": len(
                {r["source_id"] for r in rag_candidates if not r["has_marked_error"]}
            ),
        },
    }
    return {
        "schema": 1,
        "scope": "Repository artifact exposure; optional local saved diagnostics. Not proof against pretraining, unsaved conversations or unlogged calls.",
        "policy": "Close exposure over cited/evidence-related SciFact documents; include all supplied v07 distractors. Split assignment alone is not exposure. Inherit v06 normalized title/text/DOI exclusions. Official RAGTruth test text/labels not used.",
        "local_artifacts_included": include_local,
        "scan_roots": ["data/verification", "data/demo", "data/benchmark", "docs/assets"]
        + (
            ["output", ".benchmark-runtime/diagnostics", ".benchmark-runtime/*.json* (top level)"]
            if include_local
            else []
        ),
        "scan_exclusions": [
            "split membership files",
            "frozen code dumps",
            "generated exposure/R1 outputs",
            "tsconfig.json and openapi.json (compiler/API schemas, not saved task inputs)",
        ],
        "dataset_hashes": {
            "scifact_canonical": old["source_file_hashes"],
            "ragtruth_bytes": rag_hashes,
        },
        "counts": counts,
        "inputs": records,
        "scifact_exposed": [
            {"document_id": doc, "group_id": groups[doc], "reasons": sorted(reasons)}
            for doc, reasons in sorted(exposure.items())
        ],
        "ragtruth_exposed": [
            {"source_id": source, "reasons": sorted(reasons)}
            for source, reasons in sorted(rag_exposure.items())
        ],
        "fresh_public_label_pairs": [
            {
                "case_id": p.input.case_id,
                "document_id": p.input.document.document_id,
                "group_id": groups[p.input.document.document_id],
                "relation": p.relation.value,
                "original_split": p.original_split,
            }
            for p in fresh_pairs
        ],
        "construction_candidates": candidates,
        "natural_candidates": rag_candidates,
        "reserved_official_test": reserve,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--include-local", action="store_true")
    p.add_argument("--output", type=Path, default=OUT / "inventory.json")
    args = p.parse_args()
    result = build(args.include_local)
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and args.output.read_text(encoding="utf-8") != content:
        raise ValueError(
            "Exposure changed; write a separately named snapshot, do not overwrite history."
        )
    args.output.write_text(content, encoding="utf-8")
    print(json.dumps(result["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
