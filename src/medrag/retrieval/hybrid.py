"""Hybrid retrieval: BGE-M3 dense + sparse with RRF fusion."""

from __future__ import annotations

from collections import defaultdict

from typing import TYPE_CHECKING

from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector

from medrag.retrieval.retriever import RetrievedChunk

if TYPE_CHECKING:
    from medrag.index.embedder import BGEM3Embedder


def _reciprocal_rank_fusion(
    rankings: list[list[str]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Merge multiple ranked lists via RRF.

    k=60 is the value from the original Cormack et al. (2009) paper.
    Using rank position rather than raw scores makes fusion scale-independent:
    dense cosine similarities (~0-1) and sparse dot products (unbounded) fuse cleanly.
    """
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking):
            scores[chunk_id] += 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


def _to_sparse_vec(weights: dict) -> SparseVector:
    if not weights:
        return SparseVector(indices=[0], values=[0.0])
    return SparseVector(
        indices=[int(k) for k in weights],
        values=[float(v) for v in weights.values()],
    )


class HybridRetriever:
    def __init__(
        self,
        qdrant: QdrantClient,
        embedder: BGEM3Embedder,
        collection: str = "medrag_text",
        rrf_k: int = 60,
        candidate_k: int = 20,
    ):
        self.qdrant = qdrant
        self.embedder = embedder
        self.collection = collection
        self.rrf_k = rrf_k
        self.candidate_k = candidate_k

    def retrieve(self, query: str, k: int = 5) -> list[RetrievedChunk]:
        enc = self.embedder.encode([query], return_sparse=True)
        dense_vec: list[float] = enc["dense"][0].tolist()
        sparse_weights: dict = (enc.get("sparse") or [{}])[0]

        # Dense retrieval → top candidate_k
        dense_result = self.qdrant.query_points(
            collection_name=self.collection,
            query=dense_vec,
            using="dense",
            limit=self.candidate_k,
            with_payload=True,
        )

        id_to_point: dict[str, object] = {}
        dense_ranking: list[str] = []
        for p in dense_result.points:
            cid = p.payload["chunk_id"]
            dense_ranking.append(cid)
            id_to_point[cid] = p

        rankings = [dense_ranking]

        # Sparse retrieval only when sparse weights are available
        if sparse_weights:
            sparse_result = self.qdrant.query_points(
                collection_name=self.collection,
                query=_to_sparse_vec(sparse_weights),
                using="sparse",
                limit=self.candidate_k,
                with_payload=True,
            )
            sparse_ranking: list[str] = []
            for p in sparse_result.points:
                cid = p.payload["chunk_id"]
                sparse_ranking.append(cid)
                if cid not in id_to_point:
                    id_to_point[cid] = p
            rankings.append(sparse_ranking)

        # RRF fusion
        fused = _reciprocal_rank_fusion(rankings, k=self.rrf_k)

        # Rebuild top-k RetrievedChunk from cached payloads
        results: list[RetrievedChunk] = []
        for chunk_id, rrf_score in fused[:k]:
            p = id_to_point.get(chunk_id)
            if p is None:
                continue
            results.append(RetrievedChunk(
                chunk_id=chunk_id,
                text=p.payload["text"],
                score=rrf_score,
                payload=p.payload,
            ))
        return results

    def document_passages(self, doc_id: str) -> list[RetrievedChunk]:
        """Every indexed passage of one document, in reading order."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        points, _ = self.qdrant.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]),
            limit=64, with_payload=True,
        )
        points.sort(key=lambda p: p.payload.get("chunk_idx", 0))
        return [RetrievedChunk(chunk_id=p.payload["chunk_id"], text=p.payload["text"], score=0.0, payload=p.payload)
                for p in points]


__all__ = ["HybridRetriever", "_reciprocal_rank_fusion"]
