"""
Shared helper utilities for all API routes.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

from medrag.api.models import ChunkOut
from medrag.config import COLLECTION_NAME, get_qdrant_client

_COLLECTION = COLLECTION_NAME


@lru_cache(maxsize=1)
def get_qdrant() -> QdrantClient:
    return get_qdrant_client()


# ── Payload → ChunkOut ───────────────────────────────────────────────────────

def payload_to_chunk(payload: dict[str, Any], score: float | None = None) -> ChunkOut:
    """Convert a Qdrant point payload dict into a ChunkOut model."""
    source = payload.get("source", "pubmed")
    doc_id = payload.get("doc_id", "")
    pmid = payload.get("pmid") or None

    chunk_id = payload.get("chunk_id", "")
    chunk_idx = int(payload.get("chunk_idx", 0))
    total_chunks = int(payload.get("total_chunks", 1))
    title = payload.get("title", "")
    section = payload.get("section") or None
    text = payload.get("text", "")

    # Build a normalised citation string
    if source == "pubmed" and pmid:
        citation = f"PMID:{pmid}"
    else:
        citation = f"PMC:{doc_id}"

    ext_url = external_url(source, doc_id, pmid)

    # Bibliographic metadata stored by chunker (PubMed only)
    raw_authors = payload.get("authors")
    if isinstance(raw_authors, list):
        authors: str | None = ", ".join(str(a) for a in raw_authors) or None
    elif isinstance(raw_authors, str):
        authors = raw_authors or None
    else:
        authors = None

    journal: str | None = payload.get("journal") or None

    raw_year = payload.get("year")
    year: int | None = int(raw_year) if raw_year is not None else None

    return ChunkOut(
        chunk_id=chunk_id,
        citation=citation,
        source=source,
        doc_id=doc_id,
        title=title,
        section=section,
        pmid=pmid,
        chunk_idx=chunk_idx,
        total_chunks=total_chunks,
        text=text,
        score=score,
        highlight_ranges=[],
        external_url=ext_url,
        authors=authors,
        journal=journal,
        year=year,
    )


def external_url(source: str, doc_id: str, pmid: str | None) -> str:
    if source == "pubmed" and pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    if source == "pmc":
        if re.fullmatch(r"PMC\d+", doc_id):
            return f"https://pmc.ncbi.nlm.nih.gov/articles/{doc_id}/"
        return f"https://www.ncbi.nlm.nih.gov/pmc/search/?term={doc_id}"
    return ""


# ── Qdrant helpers ───────────────────────────────────────────────────────────

def scroll_by_chunk_ids(chunk_ids: list[str]) -> list[dict]:
    """Fetch specific chunks by chunk_id values."""
    q = get_qdrant()
    results, _ = q.scroll(
        collection_name=_COLLECTION,
        scroll_filter=Filter(
            must=[FieldCondition(key="chunk_id", match=MatchAny(any=chunk_ids))]
        ),
        limit=len(chunk_ids) + 5,
        with_payload=True,
    )
    return [p.payload for p in results]


def scroll_by_doc_id(doc_id: str, source: str) -> list[dict]:
    """Fetch all chunks belonging to a document, ordered by chunk_idx."""
    q = get_qdrant()
    all_points: list = []
    next_offset = None
    while True:
        pts, next_offset = q.scroll(
            collection_name=_COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
                    FieldCondition(key="source", match=MatchValue(value=source)),
                ]
            ),
            limit=100,
            offset=next_offset,
            with_payload=True,
        )
        all_points.extend(p.payload for p in pts)
        if next_offset is None:
            break
    all_points.sort(key=lambda p: int(p.get("chunk_idx", 0)))
    return all_points
