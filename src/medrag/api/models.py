"""
Pydantic data models for the VeritasMed API.

This file is the single source of truth for the API contract.
REST types are exposed via FastAPI's /openapi.json endpoint.
WebSocket event types (AgentEvent variants) are defined here
and mirrored in frontend/src/types/ws.ts (see that file for the TS side).
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, model_validator

from medrag.agent.evidence import AnswerComponent
from medrag.agent.conversation import ContextTurn, ContextResolution


# ── Shared ──────────────────────────────────────────────────────────────────

class ChunkOut(BaseModel):
    chunk_id: str = Field(description="e.g. 'pubmed:12345:0' or 'pmc:doc196:3'")
    citation: str = Field(description="e.g. 'PMID:12345' or 'PMC:doc196'")
    source: str = Field(description="'pubmed' or 'pmc'")
    doc_id: str
    title: str
    section: str | None = None
    pmid: str | None = None
    chunk_idx: int
    total_chunks: int
    text: str
    score: float | None = None
    highlight_ranges: list[tuple[int, int]] = Field(default_factory=list)
    external_url: str = ""
    # Bibliographic metadata (populated from Qdrant payload; PubMed only)
    authors: str | None = None
    journal: str | None = None
    year: int | None = None


# ── WebSocket event stream ───────────────────────────────────────────────────
# Each event is a distinct Pydantic model discriminated by the `event` field.
# ask.py constructs specific event types directly; AgentEvent is the union alias.

class NodeStartEvent(BaseModel):
    event: Literal["node_start"] = "node_start"
    node: str


class NodeEndData(BaseModel):
    """Merged payload for all node_end events — fields are node-specific."""
    # retrieve / rerank
    count: int | None = None
    # grade
    relevance_score: float | None = None
    relevant: bool | None = None
    reason: str | None = None
    rewrite_hint: str | None = None
    # rewrite
    new_query: str | None = None
    rewritten_queries: list[str] | None = None
    # generate
    answer_preview: str | None = None
    # check
    faithful: bool | None = None
    issues: str | None = None
    confidence: float | None = None
    # route
    route: str | None = None


class NodeEndEvent(BaseModel):
    event: Literal["node_end"] = "node_end"
    node: str
    data: NodeEndData = Field(default_factory=NodeEndData)


class ChunkRetrievedData(BaseModel):
    chunk_id: str
    citation: str
    title: str
    score: float | None = None
    text_snippet: str
    source: str
    external_url: str


class ChunkRetrievedEvent(BaseModel):
    event: Literal["chunk_retrieved"] = "chunk_retrieved"
    node: str
    data: ChunkRetrievedData


class ErrorData(BaseModel):
    message: str


class ErrorEvent(BaseModel):
    event: Literal["error"] = "error"
    node: None = None
    data: ErrorData


# ── WS request ──────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=12000)
    thread_id: str = "default"
    context: list[ContextTurn] = Field(default_factory=list, max_length=6)
    omitted_context: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def bounded_context(self):
        if not self.query.strip():
            raise ValueError("Question is empty")
        if sum(len(c.question) + len(c.answer) + sum(map(len, c.source_titles)) for c in self.context) > 12000:
            raise ValueError("Context exceeds 12000 characters; retain whole turns")
        if len({c.turn_id for c in self.context}) != len(self.context):
            raise ValueError("Context must contain distinct turns")
        return self


# ── Full answer (inside "done" event data) ──────────────────────────────────

class AnswerOut(BaseModel):
    conversation_context: ContextResolution | None = None
    evidence_status: Literal["complete", "partial", "insufficient"] | None = None
    evidence_gap: str = ""
    answer_components: list[AnswerComponent] = Field(default_factory=list)
    answer: str
    citations: list[str]
    confidence: float
    faithful: bool
    faithfulness_issues: str
    iterations: int
    regen_count: int
    rewritten_queries: list[str]
    chunks: list[ChunkOut]
    thread_id: str
    latency_ms: float


class DoneEvent(BaseModel):
    event: Literal["done"] = "done"
    node: None = None
    data: AnswerOut


# Discriminated union — the canonical AgentEvent type.
# Used in OpenAPI schema and TypeScript ws.ts mirror.
AgentEvent = Annotated[
    Union[NodeStartEvent, NodeEndEvent, ChunkRetrievedEvent, DoneEvent, ErrorEvent],
    Field(discriminator="event"),
]


# ── /api/document/{citation} ─────────────────────────────────────────────────

class DocumentChunkSlim(BaseModel):
    chunk_id: str
    chunk_idx: int
    section: str | None = None
    text: str


class DocumentResponse(BaseModel):
    citation: str
    source: str
    doc_id: str
    title: str
    pmid: str | None
    external_url: str
    total_chunks: int
    chunks: list[DocumentChunkSlim]


# ── /api/chunk/{chunk_id} ────────────────────────────────────────────────────

class ChunkSlim(BaseModel):
    chunk_id: str
    text: str
    score: float | None = None


class ChunkContextResponse(BaseModel):
    chunk: ChunkSlim
    prev_chunk: ChunkSlim | None = None
    next_chunk: ChunkSlim | None = None
    document: dict  # {title, citation, external_url}


# ── /api/corpus/stats ────────────────────────────────────────────────────────

class CorpusStats(BaseModel):
    total_chunks: int
    pubmed_chunks: int
    pmc_chunks: int
    collection: str
    embedding_model: str


# ── /api/health ──────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    qdrant: str
    llm: str
