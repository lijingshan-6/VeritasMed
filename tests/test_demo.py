import numpy as np
import pytest
from qdrant_client import QdrantClient

from medrag.demo import bootstrap
from medrag.index.qdrant_setup import create_collection


class TinyEmbedder:
    def encode(self, texts, **kwargs):
        dense = np.zeros((len(texts), 1024), dtype=np.float32)
        dense[:, 0] = 1
        return {"dense": dense, "sparse": [{"1": 1.0} for _ in texts]}


def test_bootstrap_is_idempotent_and_does_not_touch_research_collection():
    client = QdrantClient(":memory:")
    try:
        create_collection(client, "medrag_text")
        first = bootstrap(client, TinyEmbedder())
        second = bootstrap(client, TinyEmbedder())
        assert first == second == 15
        assert client.count("medrag_text").count == 0
        rows, _ = client.scroll("medrag_conversation_demo", with_payload=True, limit=20)
        assert {row.payload["doc_id"] for row in rows} == {"PMC11567630", "PMC4890770", "PMC3594238"}
    finally:
        client.close()


def test_bootstrap_refuses_other_collections():
    with pytest.raises(ValueError):
        bootstrap(QdrantClient(":memory:"), TinyEmbedder(), collection="medrag_text")
