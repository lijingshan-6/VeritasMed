"""LangGraph StateGraph assembly for MedRAG-Agent.

Graph topology
──────────────
                     ┌──────────┐
              ┌─────►│  rewrite │◄──────────────────────┐
              │      └────┬─────┘                        │
              │           │                              │
  START ──► route ──► retrieve ──► rerank ──► grade ─── ┤
                                                         │
                                          (relevant) ►  generate ──► check ──► END
                                                                         │
                                    (unfaithful + regen<MAX) ──► inc_regen ──► generate
                                                                         │
                                          (unfaithful + cap) ──► END

Conditional edges
─────────────────
  after grade   : score ≥ threshold (0.6/0.75/0.8 by query type) → generate
                                            |  else → rewrite (or generate if MAX hit)
  after check   : faithful → append_history |  regen_count < MAX_REGEN → inc_regen → generate
                                            |  cap hit → append_history (faithful=False, issues kept)

Memory
──────
  SqliteSaver retains graph execution state; web/MCP requests use a fresh ID.
  Browser conversation context is explicitly resolved before graph invocation.
  summarize_history remains for programmatic callers reusing a checkpoint.

Usage
─────
    from medrag.agent.graph import app

    from uuid import uuid4
    from medrag.agent.invocation import build_initial_state
    config = {"configurable": {"thread_id": str(uuid4())}}
    result = app.invoke(build_initial_state("What is the mechanism of aspirin?"), config=config)
    print(result["answer"])
"""
from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from medrag.agent.nodes import (
    MAX_REGEN,
    MAX_REWRITES,
    GRADE_THRESHOLD,
    _GRADE_THRESHOLDS,
    HISTORY_SUMMARIZE_EVERY,
    append_history,
    check_faithfulness,
    generate_answer_node,
    grade_relevance,
    hybrid_retrieve,
    increment_regen,
    rerank_chunks,
    rewrite_query,
    route_query,
    summarize_history,
)
from medrag.agent.state import AgentState

logger = logging.getLogger(__name__)

# ── Checkpointer ───────────────────────────────────────────────────────────────

_DB_DIR  = Path(os.environ.get("MEDRAG_DATA_DIR", "data")) / "checkpoints"
_DB_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = str(_DB_DIR / "agent.db")

# SqliteSaver requires a live sqlite3 connection.
# check_same_thread=False is required for LangGraph's internal threading.
_conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
_checkpointer = SqliteSaver(_conn)
logger.info("[graph] SqliteSaver at %s", _DB_PATH)

# ── Conditional edge predicates ────────────────────────────────────────────────

def _after_grade(state: AgentState) -> str:
    """Route after grade_relevance:
      - If score ≥ dynamic threshold → proceed to generate
      - If iterations < MAX_REWRITES → rewrite
      - Otherwise (cap hit) → generate anyway (best-effort)
    """
    score      = state.get("relevance_score", 0.0)
    iterations = state.get("iterations", 0)
    query_type = state.get("query_type", "synthesis")
    threshold  = _GRADE_THRESHOLDS.get(query_type, GRADE_THRESHOLD)

    if score >= threshold:
        return "generate"
    if iterations < MAX_REWRITES:
        return "rewrite"
    logger.warning("[graph] max rewrites hit — generating anyway")
    return "generate"


def _after_check(state: AgentState) -> str:
    """Route after check_faithfulness:
      - faithful → END (via summarize gate)
      - regen_count < MAX_REGEN → increment counter then re-generate
      - cap hit → END (faithful=False + faithfulness_issues preserved as warning)

    NOTE: The former "smart gate" (confidence ≥ 0.3 bypass) has been removed.
    Self-reported LLM confidence is unreliable and the 0.3 threshold was too low
    to be a meaningful safety bar for medical answers.  If the faithfulness
    checker has genuine false-positive issues, fix the checker prompt instead.
    """
    faithful    = state.get("faithful", False)
    regen_count = state.get("regen_count", 0)

    if faithful:
        return "end"

    if regen_count < MAX_REGEN:
        logger.warning("[graph] unfaithful — re-generating (regen_count=%d)", regen_count)
        return "regenerate"

    logger.warning(
        "[graph] max regen hit (%d) — ending with unfaithful answer; "
        "issues preserved in faithfulness_issues field",
        regen_count,
    )
    return "end"


def _maybe_summarize(state: AgentState) -> str:
    """After appending a new turn to history, decide whether to compress."""
    history = state.get("history", [])
    if len(history) > 0 and len(history) % HISTORY_SUMMARIZE_EVERY == 0:
        return "summarize"
    return "end"


# ── Graph assembly ─────────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    # Register all nodes
    g.add_node("route",           route_query)
    g.add_node("retrieve",        hybrid_retrieve)
    g.add_node("rerank",          rerank_chunks)
    g.add_node("grade",           grade_relevance)
    g.add_node("rewrite",         rewrite_query)
    g.add_node("generate",        generate_answer_node)
    g.add_node("check",           check_faithfulness)
    g.add_node("inc_regen",       increment_regen)
    g.add_node("append_history",  append_history)     # persists Q&A to history
    g.add_node("summarize_gate",  lambda state: {})   # no-op passthrough
    g.add_node("summarize",       summarize_history)

    # Linear backbone: START → route → retrieve → rerank → grade
    g.add_edge(START,       "route")
    g.add_edge("route",     "retrieve")
    g.add_edge("retrieve",  "rerank")
    g.add_edge("rerank",    "grade")

    # After grade: conditional — rewrite or generate
    g.add_conditional_edges(
        "grade",
        _after_grade,
        {"generate": "generate", "rewrite": "rewrite"},
    )

    # After rewrite: loop back to retrieve
    g.add_edge("rewrite", "retrieve")

    # After generate: faithfulness check
    g.add_edge("generate", "check")

    # After check: conditional — end (via history append) or re-generate
    g.add_conditional_edges(
        "check",
        _after_check,
        {"end": "append_history", "regenerate": "inc_regen"},
    )

    # Increment regen counter, then loop back to generate
    g.add_edge("inc_regen", "generate")

    # Persist the completed Q&A turn, then decide whether to compress history
    g.add_edge("append_history", "summarize_gate")

    # Summarize gate: decide whether to compress history before ending
    g.add_conditional_edges(
        "summarize_gate",
        _maybe_summarize,
        {"summarize": "summarize", "end": END},
    )
    g.add_edge("summarize", END)

    return g


# ── Compile ────────────────────────────────────────────────────────────────────

_graph = _build_graph()
app = _graph.compile(checkpointer=_checkpointer)

__all__ = ["app"]
