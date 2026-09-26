"""SciFact pair adapter and predeclared, source-disjoint train pilot."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from .schema import EvidenceDocument, GoldCase, Relation, VerificationInput

ARCHIVE_URL = "https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz"
ARCHIVE_SHA256 = "11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be"
FILES = ("corpus.jsonl", "claims_train.jsonl", "claims_dev.jsonl")
PILOT_SEED = "veritasmed-v0.5-scifact-pilot-2026-09-24"


def read_jsonl(path: Path) -> list[dict]:
    # Unicode paragraph/line separators may occur inside valid JSON strings.
    # splitlines() treats those characters as record boundaries; file iteration does not.
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def object_hash(value) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def document_ids(claim: dict) -> set[str]:
    return {str(i) for i in claim["cited_doc_ids"]} | set(claim["evidence"])


def adapt_pairs(corpus: list[dict], claims: list[dict], split: str) -> list[GoldCase]:
    documents = {str(row["doc_id"]): EvidenceDocument(
        document_id=str(row["doc_id"]), title=row["title"], sentences=row["abstract"],
    ) for row in corpus}
    mapping = {"SUPPORT": Relation.SUPPORTED, "CONTRADICT": Relation.CONTRADICTED}
    cases = []
    for claim in claims:
        related = sorted(document_ids(claim))
        for document_id in related:
            annotations = claim["evidence"].get(document_id, [])
            labels = {mapping[a["label"]] for a in annotations}
            if len(labels) > 1:
                raise ValueError(f"Conflicting official labels: {claim['id']}/{document_id}")
            rationales = [sorted(set(a["sentences"])) for a in annotations]
            document = documents[document_id]
            if any(not ids or any(i < 0 or i >= len(document.sentences) for i in ids)
                   for ids in rationales):
                raise ValueError("Invalid official rationale")
            cases.append(GoldCase(
                input=VerificationInput(case_id=f"scifact-{split}-{claim['id']}-{document_id}",
                                        claim=claim["claim"], document=document),
                relation=next(iter(labels)) if labels else Relation.INSUFFICIENT,
                rationale_sets=rationales, original_split=split, claim_id=claim["id"],
                related_document_ids=related,
            ))
    return cases


def select_pilot(train: list[GoldCase], dev_claims: list[dict], per_label: int = 10,
                 seed: str = PILOT_SEED) -> tuple[list[GoldCase], dict]:
    dev_documents = set().union(*(document_ids(c) for c in dev_claims))
    eligible = [c for c in train if not dev_documents.intersection(c.related_document_ids)]
    ordered = sorted(eligible, key=lambda c: object_hash([seed, c.input.case_id]))
    counts = Counter()
    used_claims, used_documents = set(), set()
    selected = []
    for case in ordered:
        if (counts[case.relation] >= per_label or case.claim_id in used_claims
                or used_documents.intersection(case.related_document_ids)):
            continue
        selected.append(case)
        counts[case.relation] += 1
        used_claims.add(case.claim_id)
        used_documents.update(case.related_document_ids)
    if any(counts[label] != per_label for label in Relation):
        raise ValueError(f"Cannot satisfy the predeclared selection: {dict(counts)}")
    return selected, {
        "seed": seed, "per_label": per_label, "train_pairs": len(train),
        "eligible_pairs_after_dev_document_exclusion": len(eligible),
        "dev_document_count": len(dev_documents), "selected_counts": dict(counts),
        "rule": "SHA256 sorted; official train only; all related docs disjoint from dev and other selected claims",
    }


def prepare_pilot(cache: Path) -> tuple[list[GoldCase], dict]:
    corpus, train, dev = [read_jsonl(cache / name) for name in FILES]
    cases, selection = select_pilot(adapt_pairs(corpus, train, "train"), dev)
    manifest = {
        "dataset": "SciFact", "purpose": "development pilot, not held-out evaluation",
        "archive_url": ARCHIVE_URL, "archive_sha256": ARCHIVE_SHA256,
        "file_sha256": {name: hashlib.sha256((cache / name).read_bytes()).hexdigest()
                        for name in FILES},
        "selection": selection,
        "cases": [{"case_id": c.input.case_id, "claim_id": c.claim_id,
                   "document_id": c.input.document.document_id,
                   "relation": c.relation, "input_sha256": object_hash(c.input.model_dump()),
                   "rationale_sets": c.rationale_sets} for c in cases],
    }
    return cases, manifest
