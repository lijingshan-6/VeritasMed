"""Download PubMedQA, freeze the question splits and build the retrieval corpus.

No model calls. Writes the frozen manifest to experiments/pubmedqa/manifest.json and the
raw/derived data to .exp-runtime/pubmedqa/ (ignored by Git).

Splits (fixed seed, decided before any model output exists):
  test_full  all 500 questions of the official PQA-L test set (the main evaluation)
  test  200 questions drawn from that test set, stratified by label (the original, smaller plan)
  dev    50 questions from the other 500 PQA-L questions (pilot = first 10 of dev)
Corpus: every PQA-L abstract (1,000) + 10,000 unlabeled PQA-U abstracts as distractors.
Each abstract section becomes one passage. The question (derived from the paper title) and the
conclusion ("long answer") are never indexed, as in the PubMedQA setup.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNTIME = ROOT / ".exp-runtime" / "pubmedqa"
SEED = 20261005
SOURCES = {
    "ori_pqal.json": "https://raw.githubusercontent.com/pubmedqa/pubmedqa/master/data/ori_pqal.json",
    "test_ground_truth.json": "https://raw.githubusercontent.com/pubmedqa/pubmedqa/master/data/test_ground_truth.json",
    "pqa_unlabeled.parquet": "https://huggingface.co/datasets/qiaojin/PubMedQA/resolve/main/pqa_unlabeled/train-00000-of-00001.parquet",
}
N_TEST, N_DEV, N_PILOT, N_DISTRACTORS = 200, 50, 10, 10_000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download() -> dict[str, str]:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, url in SOURCES.items():
        path = RUNTIME / name
        if not path.exists():
            with httpx.stream("GET", url, follow_redirects=True, timeout=300) as r:
                r.raise_for_status()
                with path.open("wb") as f:
                    for block in r.iter_bytes():
                        f.write(block)
        hashes[name] = sha256(path)
    return hashes


def stratified(ids_by_label: dict[str, list[str]], n: int, rng: random.Random) -> list[str]:
    total = sum(len(v) for v in ids_by_label.values())
    picked = []
    labels = sorted(ids_by_label)
    quotas = {lab: round(n * len(ids_by_label[lab]) / total) for lab in labels}
    quotas[labels[0]] += n - sum(quotas.values())  # keep the exact total
    for lab in labels:
        pool = sorted(ids_by_label[lab])
        picked += rng.sample(pool, quotas[lab])
    return sorted(picked)


def passages(pmid: str, contexts: list[str], labels: list[str], origin: str) -> list[dict]:
    return [{"chunk_id": f"pubmed:{pmid}:{i}", "doc_id": pmid, "pmid": pmid, "source": "pubmed",
             "title": f"PubMed {pmid}", "section": (labels[i] if i < len(labels) else "").title(),
             "chunk_idx": i, "total_chunks": len(contexts), "text": " ".join(text.split()),
             "corpus_origin": origin}
            for i, text in enumerate(contexts) if text.strip()]


def main() -> None:
    hashes = download()
    pqal = json.loads((RUNTIME / "ori_pqal.json").read_text(encoding="utf8"))
    test_truth = json.loads((RUNTIME / "test_ground_truth.json").read_text(encoding="utf8"))
    rng = random.Random(SEED)

    test_by_label, other_by_label = defaultdict(list), defaultdict(list)
    for pmid, row in pqal.items():
        (test_by_label if pmid in test_truth else other_by_label)[row["final_decision"]].append(pmid)
    test = stratified(test_by_label, N_TEST, rng)
    dev = stratified(other_by_label, N_DEV, rng)
    pilot = sorted(rng.sample(dev, N_PILOT))

    import pyarrow.parquet as pq
    unlabeled = pq.read_table(RUNTIME / "pqa_unlabeled.parquet").to_pylist()
    candidates = sorted((r for r in unlabeled if str(r["pubid"]) not in pqal), key=lambda r: r["pubid"])
    distractors = rng.sample(candidates, N_DISTRACTORS)

    corpus = []
    for pmid, row in sorted(pqal.items()):
        corpus += passages(pmid, row["CONTEXTS"], row["LABELS"], "pqa_labeled")
    for row in distractors:
        corpus += passages(str(row["pubid"]), row["context"]["contexts"], row["context"]["labels"], "pqa_unlabeled")
    corpus_path = RUNTIME / "corpus.jsonl"
    corpus_path.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in corpus), encoding="utf8")

    questions = {pmid: {"pmid": pmid, "question": pqal[pmid]["QUESTION"], "label": pqal[pmid]["final_decision"],
                        "gold_contexts": pqal[pmid]["CONTEXTS"], "gold_labels": pqal[pmid]["LABELS"]}
                 for pmid in sorted(set(test_truth) | set(dev))}
    (RUNTIME / "questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=1), encoding="utf8")

    manifest = {
        "dataset": "PubMedQA (Jin et al., EMNLP 2019), MIT license",
        "seed": SEED, "source_files": {n: {"url": SOURCES[n], "sha256": h} for n, h in hashes.items()},
        "splits": {"test_full": sorted(test_truth), "test": test, "dev": dev, "pilot": pilot},
        "label_counts": {s: dict(Counter(pqal[p]["final_decision"] for p in ids)) for s, ids in
                         {"test_full": sorted(test_truth), "test": test, "dev": dev, "pilot": pilot}.items()},
        "corpus": {"abstracts_labeled": len(pqal), "abstracts_distractor": len(distractors), "passages": len(corpus),
                   "sha256": sha256(corpus_path)},
        "questions_sha256": sha256(RUNTIME / "questions.json"),
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf8")
    print(json.dumps({k: manifest[k] for k in ("label_counts", "corpus")}, indent=1))


if __name__ == "__main__":
    main()
