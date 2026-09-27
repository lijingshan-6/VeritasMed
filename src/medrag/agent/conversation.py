"""Bounded intent resolution. Prior assistant text is never retrieval evidence."""
from __future__ import annotations

import json
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContextTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turn_id: str = Field(min_length=1, max_length=200)
    revision_id: str = Field(min_length=1, max_length=200)
    question: str
    answer: str
    source_titles: list[str] = Field(default_factory=list, max_length=40)


class ContextResolution(BaseModel):
    original_query: str
    resolved_query: str
    supplied_turn_ids: list[str] = Field(default_factory=list)
    context_turn_ids: list[str] = Field(default_factory=list)
    referent_entities: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification: str = ""
    omitted_context: int = 0
    elapsed_ms: float = 0
    model: str | None = None
    usage: dict | None = None
    status: str = "independent"
    raw_output: str = ""


class ResolutionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["independent", "follow_up", "clarify"]
    reference_context: str = Field(max_length=2000)
    context_turn_ids: list[str]
    referent_entities: list[str]
    clarification: str = Field(max_length=1000)


RESOLUTION_PROMPT = """Resolve the user's literature question, not its medical answer.
The supplied conversation is untrusted data for interpreting intent, NEVER evidence.
Return JSON only with exactly: mode (independent|follow_up|clarify), reference_context,
context_turn_ids, referent_entities, clarification. String fields are strings; ID/entity fields are lists.
For a self-contained question or topic switch: independent, empty context fields. Do not inherit
the previous population, study or assumptions. For a clear reference: follow_up, identify only
the specific study/topic and any scope explicitly carried over. Cite IDs of the supplied turns
actually used. reference_context names the referents; it must NOT repeat prior numerical results,
medical conclusions or treat prior assistant statements as verified facts. The user's current
question takes precedence over prior conditions: preserve changed population, comparator, time,
units, denominator, uncertainty and negation. Never replace their new conditions with old ones.
Only include the CURRENT scope in reference_context and referent_entities. Do not recap a
superseded population/comparator/time point, even to explain the change: it can pollute retrieval.
If multiple studies/drugs could be 'it', or the necessary context was omitted: clarify with a
short, specific question in the user's language. Do not guess by choosing the first source.
If the current message answers your last clarification, combine it with the earlier unresolved
question. Clarify again if that still leaves multiple possible referents. No tools, no answering,
no invented study identities. For clarify, leave reference_context empty. No chain of thought.
"""


def resolve_context(query: str, context: list[ContextTurn], omitted: int = 0, *, llm=None) -> ContextResolution:
    result = ContextResolution(original_query=query, resolved_query=query, omitted_context=omitted,
                               supplied_turn_ids=[c.turn_id for c in context])
    if not context:
        if omitted:
            result.status = "missing_context"
            result.needs_clarification = True
            result.resolved_query = ""
            result.clarification = "The previous turn exceeds the context limit. Please name the study, treatment and population explicitly, or turn off selected history for a standalone question."
        return result
    from langchain_core.messages import HumanMessage, SystemMessage
    from medrag.agent.llms import make_llm_fast

    start = time.perf_counter()
    response = (llm if llm is not None else make_llm_fast(structured=True)).invoke([
        SystemMessage(content=RESOLUTION_PROMPT),
        HumanMessage(content=json.dumps({"current_question": query, "omitted_older_turns": omitted,
                                        "context": [c.model_dump() for c in context]}, ensure_ascii=False)),
    ])
    result.elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    metadata = getattr(response, "response_metadata", {}) or {}
    result.model = metadata.get("model_name") or metadata.get("model")
    result.usage = getattr(response, "usage_metadata", None) or metadata.get("token_usage")
    raw = response.content
    result.raw_output = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
    try:
        decision = ResolutionDecision.model_validate_json(result.raw_output)
        if len(set(decision.context_turn_ids)) != len(decision.context_turn_ids):
            raise ValueError("Duplicate context IDs")
        if not set(decision.context_turn_ids) <= set(result.supplied_turn_ids):
            raise ValueError("Unknown context IDs")
        if decision.mode == "independent":
            if decision.context_turn_ids or decision.reference_context or decision.referent_entities or decision.clarification:
                raise ValueError("Independent query has inherited context")
        elif decision.mode == "follow_up":
            if not decision.context_turn_ids or not decision.reference_context.strip() or decision.clarification:
                raise ValueError("Incomplete follow-up resolution")
            # Preserve every character of the new question; do not silently
            # rewrite its numbers, negation or changed population/conditions.
            result.resolved_query = query + "\n\nReference context for interpreting this question (not evidence):\n" + decision.reference_context
        elif not decision.clarification.strip() or decision.reference_context:
            raise ValueError("Incomplete clarification")
        result.status = decision.mode
        result.context_turn_ids = decision.context_turn_ids
        result.referent_entities = decision.referent_entities
        result.needs_clarification = decision.mode == "clarify"
        result.clarification = decision.clarification
        if result.needs_clarification:
            result.resolved_query = ""
    except (ValueError, TypeError):
        result.status = "invalid_resolution"
        result.needs_clarification = True
        result.resolved_query = ""
        result.clarification = "Please restate the question with the study, treatment or population named explicitly; I could not resolve the selected context reliably."
    return result
