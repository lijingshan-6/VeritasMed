"""Small, separately named demonstration corpus; never resets research data."""
from __future__ import annotations

import json
from pathlib import Path

from medrag.index.indexer import index_chunks
from medrag.index.qdrant_setup import create_collection
from medrag.ingest.chunker import Chunk


def bootstrap(client, embedder, corpus: Path | None = None, *, collection: str = "medrag_demo") -> int:
    """Upsert a bundled demo corpus into its separately named collection."""
    if collection not in {"medrag_demo", "medrag_medical_demo", "medrag_conversation_demo"}:
        raise ValueError("Demo indexing is restricted to demonstration collections")
    corpus = corpus or Path(__file__).resolve().parents[2] / "data/demo/corpus.jsonl"
    rows = [json.loads(line) for line in corpus.read_text(encoding="utf-8").splitlines() if line.strip()]
    chunks = [Chunk(
        chunk_id=row["chunk_id"], source="pmc", doc_id=row["doc_id"],
        text=row["text"], metadata={key: value for key, value in row.items()
                                   if key not in {"chunk_id", "doc_id", "text"}},
    ) for row in rows]
    encoded = embedder.encode([chunk.text for chunk in chunks], return_sparse=True)
    create_collection(client, collection)
    index_chunks(client, chunks, encoded["dense"], encoded["sparse"], collection=collection)
    return client.count(collection).count
