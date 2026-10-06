"""LangGraph AgentState definition for VeritasMed.

The graph has checkpoint/history reducers for explicit programmatic reuse.
The Ask API deliberately starts a fresh checkpoint per request; conversation
intent comes from bounded browser snapshots, not shared history or summaries.
"""
from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict

from medrag.retrieval.retriever import RetrievedChunk


class AgentState(TypedDict):
    # ── Core query ────────────────────────────────────────────────────────────
    query: str
    """Current (possibly rewritten) query sent to the retriever."""

    original_query: str
    """The user's original query before any rewrites.
    Set by route_query and preserved through the loop; used by append_history
    so conversation history records what the user actually asked."""

    query_type: str
    """Router classification: 'factual' | 'synthesis' | 'multihop'.
    Used by grade_relevance for dynamic threshold selection."""

    source_scope: str
    """Whether evidence must stay within one study, combine sources, or is general."""

    selected_sources: list[str]
    """Studies matched to the original question before constructing the outline."""

    unmatched_source_queries: list[str]
    """Requested source searches with no matching candidate; trigger bounded retrieval repair."""

    source_queries: dict[str, list[str]]
    """Focused question parts matched to each study, for separate evidence review."""

    answer_mode: str
    """Direct answer, cross-source comparison, or evidence-boundary decision."""

    search_queries: list[str]
    """Focused retrieval queries produced by the router for multi-part questions."""

    answer_requirements: list[str]
    """Explicit components that a complete answer must cover."""

    answer_components: list[dict]
    """Question components bound to exact retrieved spans, qualifiers and gaps."""

    answer_claims: list[dict]
    """Generated claims with component IDs, retained for targeted repair."""

    binding_issues: list[str]
    repair_component_ids: list[str]
    repair_history: Annotated[list[dict], add]

    rewritten_queries: Annotated[list[str], add]
    """Accumulates each query rewrite for audit / tracing."""

    # ── Retrieval ─────────────────────────────────────────────────────────────
    retrieved_chunks: list[RetrievedChunk]
    """Top-k chunks after reranking, ready for the generator."""

    retrieval_groups: list[dict]
    """Per-query candidate groups retained for coverage-aware reranking."""

    # ── Grading ──────────────────────────────────────────────────────────────
    relevance_score: float
    """0-1 score from the grade node; < threshold triggers a rewrite."""

    relevant: bool
    """LLM's boolean relevance judgment from the grade node.
    Used by evaluate_query and for audit; routing uses relevance_score."""

    grade_reason: str
    """Human-readable explanation from the grade node (for audit log)."""

    rewrite_hint: str
    """Hint produced by grade node to guide the rewrite."""

    iterations: int
    """Rewrite counter. Starts at 0; incremented inside rewrite node.
    Hard cap: MAX_REWRITES = 2 (3 retrieval attempts total)."""

    # ── Generation ────────────────────────────────────────────────────────────
    answer: str
    """Final answer string (thinking tags already stripped)."""

    citations: list[str]
    """List of PMID / PMCID strings cited inline in the answer."""

    confidence: float
    """Self-reported confidence 0-1 from the generate node."""

    evidence_status: str
    """Generator decision: complete, partial, or insufficient."""

    evidence_gap: str
    """Explicit boundary statement when requested evidence is missing."""

    # ── Faithfulness check ───────────────────────────────────────────────────
    faithful: bool
    """True only when support, completeness, and evidence boundary all pass."""

    answer_supported: bool
    """Whether every material answer claim is supported by retrieved context."""

    answer_complete: bool
    """Whether every requested answer component is covered or bounded."""

    boundary_correct: bool
    """Whether the answer refuses or qualifies unsupported requests correctly."""

    faithfulness_issues: str
    """Description of hallucinated claims (empty if faithful)."""

    regen_count: int
    """Re-generation counter. Hard cap: MAX_REGEN = 2."""

    # ── Memory ───────────────────────────────────────────────────────────────
    history: Annotated[list[dict], add]
    """Append-only conversation history (query + answer pairs)."""

    summary: str
    """Rolling summarization of older turns (L2 memory)."""
