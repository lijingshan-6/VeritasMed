"""Embed the PubMedQA corpus with BGE-M3 (dense + sparse) into an embedded Qdrant store.

No model calls. Run with a CUDA-enabled Python; about 5-10 minutes on an 8 GB laptop GPU.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pyarrow  # noqa: F401  -- native runtimes must load before Qdrant on Windows
import sentence_transformers  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from medrag.index.embedder import BGEM3Embedder  # noqa: E402
from medrag.index.indexer import index_chunks  # noqa: E402
from medrag.index.qdrant_setup import create_collection  # noqa: E402
from medrag.ingest.chunker import Chunk  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402

RUNTIME = ROOT / ".exp-runtime" / "pubmedqa"
COLLECTION = "pubmedqa_exp"
BLOCK = 2048


def main() -> None:
    rows = [json.loads(line) for line in (RUNTIME / "corpus.jsonl").read_text(encoding="utf8").splitlines()]
    embedder = BGEM3Embedder(device="cuda", use_fp16=True)
    client = QdrantClient(path=str(RUNTIME / "qdrant"), force_disable_check_same_thread=True)
    create_collection(client, COLLECTION)
    started = time.time()
    for start in range(0, len(rows), BLOCK):
        block = rows[start:start + BLOCK]
        chunks = [Chunk(chunk_id=r["chunk_id"], source="pubmed", doc_id=r["doc_id"], text=r["text"],
                        metadata={k: v for k, v in r.items() if k not in {"chunk_id", "doc_id", "text", "source"}})
                  for r in block]
        encoded = embedder.encode([c.text for c in chunks], return_sparse=True, batch_size=32)
        index_chunks(client, chunks, encoded["dense"], encoded["sparse"], collection=COLLECTION)
        done = start + len(block)
        print(f"{done}/{len(rows)} passages · {time.time() - started:.0f}s", flush=True)
    print("indexed", client.count(COLLECTION).count)
    client.close()


if __name__ == "__main__":
    main()
