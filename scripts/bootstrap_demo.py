"""Index the three bundled papers (original abstracts) for live Ask."""
from __future__ import annotations

import argparse

import pyarrow  # noqa: F401 -- Arrow must precede the ML/native runtime on Windows
import sentence_transformers  # noqa: F401 -- native runtime must load before Qdrant

from medrag.config import get_qdrant_client
from medrag.demo import DEMO_COLLECTION, bootstrap
from medrag.index.embedder import BGEM3Embedder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args()
    embedder = BGEM3Embedder(device=args.device)
    client = get_qdrant_client()
    try:
        count = bootstrap(client, embedder)
        print(f"Ready: {DEMO_COLLECTION} contains {count} original abstract passages.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
