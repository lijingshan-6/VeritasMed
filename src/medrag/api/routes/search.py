"""
GET /api/search — standalone hybrid retrieval (no agent loop).

Uses the same singleton retriever/reranker as the agent graph so only one
BGE-M3 instance is ever loaded per process.
"""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Query

from medrag.agent.nodes.retrieval import _get_retriever, _get_reranker
from medrag.api._helpers import compute_highlights, payload_to_chunk
from medrag.api.models import ChunkOut, SearchResponse

router = APIRouter()


@router.get("/api/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=500),
    k: int = Query(default=5, ge=1, le=20),
    pipeline: str = Query(default="p2", pattern="^p[23]$"),
    highlight: bool = Query(default=True),
) -> SearchResponse:
    t0 = time.perf_counter()

    candidate_k = 20 if pipeline == "p3" else k

    # Run heavy retrieval in a worker thread so that:
    # (a) the event loop isn't blocked during model loading / inference
    # (b) CUDA initialisation happens in a thread, not the asyncio loop
    #     (avoids STATUS_ACCESS_VIOLATION crash on Windows + ProactorEventLoop)
    def _retrieve() -> list:
        raw = _get_retriever().retrieve(q, k=candidate_k)
        if pipeline == "p3":
            raw = _get_reranker().rerank(q, raw, top_k=k)
        else:
            raw = raw[:k]
        return raw

    raw_chunks = await asyncio.to_thread(_retrieve)

    chunks_out: list[ChunkOut] = []
    for rc in raw_chunks:
        payload = rc.payload if hasattr(rc, "payload") else rc
        score = getattr(rc, "score", None)
        co = payload_to_chunk(payload, score=score)
        if highlight:
            co.highlight_ranges = compute_highlights(co.text, q)
        chunks_out.append(co)

    latency = round((time.perf_counter() - t0) * 1000, 1)
    return SearchResponse(query=q, pipeline=pipeline, latency_ms=latency, chunks=chunks_out)
