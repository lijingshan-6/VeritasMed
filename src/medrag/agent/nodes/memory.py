"""Programmatic graph history; browser conversations live outside this state."""
from __future__ import annotations

import logging
from langchain_core.messages import HumanMessage, SystemMessage
from medrag.agent.llms import make_llm_fast
from medrag.agent.prompts import SUMMARIZE_SYSTEM, SUMMARIZE_USER
from medrag.agent.state import AgentState
from .common import _invoke_with_retry
from .constants import HISTORY_SUMMARIZE_EVERY

logger = logging.getLogger("medrag.agent.nodes")


def append_history(state: AgentState) -> dict:
    """Append the completed Q&A turn to conversation history.

    Called once per turn, just before summarize_gate.  Uses original_query
    (pre-rewrite) so history records what the user actually asked, not the
    internally reformulated query.
    """
    original = state.get("original_query") or state.get("query", "")
    answer   = state.get("answer", "")
    return {"history": [{"query": original, "answer": answer}]}


def summarize_history(state: AgentState) -> dict:
    """L2 memory: compress conversation history into a rolling summary.

    Triggered when len(history) is a multiple of HISTORY_SUMMARIZE_EVERY.
    Uses llm_fast (thinking=OFF) — compression, not reasoning.
    Returns updated summary; history list itself is NOT cleared here
    (LangGraph checkpointer preserves it for crash recovery).
    """
    history  = state.get("history", [])
    summary  = state.get("summary", "")

    if not history:
        return {}

    # Format new turns to incorporate
    turns_text = "\n".join(
        f"Q: {h.get('query', '')}\nA: {h.get('answer', '')}"
        for h in history[-(HISTORY_SUMMARIZE_EVERY):]
    )

    llm = make_llm_fast()
    raw = _invoke_with_retry(llm, [
        SystemMessage(content=SUMMARIZE_SYSTEM),
        HumanMessage(content=SUMMARIZE_USER.format(
            previous_summary=summary or "(none)",
            turns=turns_text,
        )),
    ])
    new_summary = raw.strip()
    logger.info("[summarize] updated summary (%d chars)", len(new_summary))
    return {"summary": new_summary}
