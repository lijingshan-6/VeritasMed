"""Freeze source-connected partitions before any v0.6/v0.7 model inference."""

from collections import Counter, defaultdict
import json
from pathlib import Path
import re

from medrag.verification.scifact import FILES, adapt_pairs, document_ids, object_hash, read_jsonl

ROOT = Path(__file__).resolve().parents[2]
SEED = "veritasmed-v06-v07-2026-09-26"
OUT = ROOT / "data/verification/v06"
CACHE = ROOT / ".benchmark-runtime/scifact"


def norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def build():
    corpus, train, dev = [read_jsonl(CACHE / name) for name in FILES]
    parent = {str(d["doc_id"]): str(d["doc_id"]) for d in corpus}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for c in train + dev:
        ids = sorted(document_ids(c))
        for other in ids[1:]:
            parent[find(other)] = find(ids[0])
    groups = defaultdict(list)
    for doc in parent:
        groups[find(doc)].append(doc)
    group_ids = {doc: object_hash(sorted(group))[:16] for group in groups.values() for doc in group}
    used = set()
    for path in [
        ROOT / "data/verification/scifact_pilot/selection.json",
        ROOT / "data/verification/controlled_v1/families.json",
    ]:
        for row in walk(json.loads(path.read_text(encoding="utf8"))):
            if "document_id" in row:
                used.add(str(row["document_id"]))
    # Conservatively exclude the entire old medical corpus, not only documents cited in answers.
    old_titles, old_texts, old_dois = set(), set(), set()
    exposure_paths = [
        ROOT / "data/raw/pubmed/abstracts.jsonl",
        ROOT / "data/raw/pmc/full_texts.jsonl",
        ROOT / "data/demo/medical/corpus.jsonl",
    ]
    for path in exposure_paths:
        if not path.exists():
            raise ValueError(f"Exposure inventory missing: {path}")
        # JSON strings may legally contain U+2028; splitlines would corrupt those records.
        with path.open(encoding="utf8") as stream:
            exposure_docs = [json.loads(line) for line in stream if line.strip()]
        for doc in exposure_docs:
            for row in walk(doc):
                if row.get("title"):
                    old_titles.add(norm(row["title"]))
                for key in ("abstract", "text", "content"):
                    if isinstance(row.get(key), str) and len(row[key]) > 100:
                        old_texts.add(norm(row[key]))
                if row.get("doi"):
                    old_dois.add(norm(row["doi"]))
    overlap = [
        str(d["doc_id"])
        for d in corpus
        if norm(d["title"]) in old_titles
        or norm(" ".join(d["abstract"])) in old_texts
        or (d.get("doi") and norm(d["doi"]) in old_dois)
    ]
    used.update(overlap)
    used_groups = {group_ids[d] for d in used}
    dev_groups = {group_ids[d] for c in dev for d in document_ids(c)}
    pairs = adapt_pairs(corpus, train, "train") + adapt_pairs(corpus, dev, "dev")
    by_group = defaultdict(list)
    for pair in pairs:
        by_group[group_ids[pair.input.document.document_id]].append(pair)
    eligible = sorted(
        set(by_group) - used_groups - dev_groups, key=lambda g: object_hash([SEED, g])
    )
    # Reserve constructions by source, not by model behavior. Only train medical/numeric abstracts.
    medical = []
    for g in eligible:
        docs = {p.input.document.document_id: p.input.document for p in by_group[g]}
        if any(
            re.search(
                r"\b(patient|trial|participants|women|men|adults|children|cohort|randomized)\b",
                d.canonical_text,
                re.I,
            )
            and sum(bool(re.search(r"\d", s)) for s in d.sentences) >= 2
            for d in docs.values()
        ):
            medical.append(g)
    diagnostic = medical[:24]
    remaining = [g for g in eligible if g not in diagnostic]
    if len(diagnostic) < 24 or len(remaining) < 120:
        raise ValueError("Insufficient independent groups for the declared experiment")
    v07dev, v07final = remaining[:20], remaining[20:60]
    remaining = remaining[60:]
    n = len(remaining)
    assignments = {
        "medical_development": diagnostic[:16],
        "medical_transfer": diagnostic[16:],
        "v07_development": v07dev,
        "v07_final": v07final,
        "development": remaining[: n // 2],
        "score_fit": remaining[n // 2 : n * 3 // 4],
        "threshold_select": remaining[n * 3 // 4 :],
        "final": sorted(dev_groups - used_groups),
    }
    entries = []
    for split, gs in assignments.items():
        for g in gs:
            for p in by_group[g]:
                if (split == "final") != (p.original_split == "dev"):
                    continue
                entries.append(
                    {
                        "case_id": p.input.case_id,
                        "group_id": g,
                        "split": split,
                        "document_id": p.input.document.document_id,
                        "relation": p.relation.value,
                        "input_sha256": object_hash(p.input.model_dump()),
                    }
                )
    pilot = sorted(
        [e for e in entries if e["split"] == "development"],
        key=lambda e: object_hash([SEED, "pilot", e["case_id"]]),
    )[:60]
    manifest = {
        "schema": 1,
        "seed": SEED,
        "source_file_hashes": {f: object_hash(read_jsonl(CACHE / f)) for f in FILES},
        "exposure": {
            "prior_document_ids": sorted(used),
            "old_corpus_overlap": overlap,
            "old_corpus_titles": len(old_titles),
            "doi_available": len(old_dois),
            "policy": "Exact normalized title/text/DOI plus source connected components; not proof of no pretraining contamination",
        },
        "counts": {
            s: {
                "groups": len(gs),
                "pairs": sum(e["split"] == s for e in entries),
                "labels": dict(Counter(e["relation"] for e in entries if e["split"] == s)),
            }
            for s, gs in assignments.items()
        },
        "entries": entries,
        "pilot_ids": [e["case_id"] for e in pilot],
    }
    return manifest


def load_cases():
    corpus, train, dev = [read_jsonl(CACHE / name) for name in FILES]
    return {
        p.input.case_id: p
        for p in adapt_pairs(corpus, train, "train") + adapt_pairs(corpus, dev, "dev")
    }


if __name__ == "__main__":
    manifest = build()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "splits.json"
    if path.exists() and json.loads(path.read_text(encoding="utf8")) != manifest:
        raise ValueError("Frozen partitions changed; preserve original and record an amendment")
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps(manifest["counts"], indent=2))
