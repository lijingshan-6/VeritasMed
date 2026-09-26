"""Index the bundled demonstration summaries without touching research data."""
from __future__ import annotations

import argparse
from pathlib import Path

import pyarrow  # noqa: F401 -- Arrow must precede the ML/native runtime on Windows
import sentence_transformers  # noqa: F401 -- native runtime must load before Qdrant

from medrag.config import get_qdrant_client
from medrag.demo import bootstrap
from medrag.index.embedder import BGEM3Embedder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--medical", action="store_true", help="Use original GRADE trial abstract passages")
    args = parser.parse_args()
    embedder = BGEM3Embedder(device=args.device)
    client = get_qdrant_client()
    try:
        collection = "medrag_medical_demo" if args.medical else "medrag_demo"
        path = "data/demo/medical/corpus.jsonl" if args.medical else "data/demo/corpus.jsonl"
        count = bootstrap(client, embedder, Path(__file__).resolve().parent.parent / path, collection=collection)
        kind = "original article passages" if args.medical else "authored demonstration summaries"
        print(f"Ready: {collection} contains {count} {kind}.")
        print(f"Start the API with QDRANT_COLLECTION={collection}.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
