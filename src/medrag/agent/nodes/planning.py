"""Interpret the question and rewrite retrieval queries."""
from __future__ import annotations

import logging
import re
from langchain_core.messages import HumanMessage, SystemMessage
from medrag.agent.llms import make_llm_fast, make_llm_think
from medrag.agent.prompts import REWRITE_SYSTEM, REWRITE_USER, ROUTER_SYSTEM, ROUTER_USER
from medrag.agent.state import AgentState
from .common import _format_requirements, _invoke_json_with_retry, _invoke_with_retry, _unique_texts

logger = logging.getLogger("medrag.agent.nodes")


_REQUIREMENT_STOPWORDS = {
    "and",
    "about",
    "after",
    "answer",
    "between",
    "does",
    "evidence",
    "from",
    "for",
    "general",
    "include",
    "including",
    "question",
    "report",
    "reported",
    "result",
    "results",
    "specific",
    "study",
    "supplied",
    "the",
    "that",
    "their",
    "these",
    "this",
    "using",
    "what",
    "when",
    "where",
    "which",
    "with",
    "or",
}


def _content_terms(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) >= 3 and token not in _REQUIREMENT_STOPWORDS
    }


def _filter_requirements_for_query(query: str, requirements: list[str]) -> list[str]:
    """Drop planner details with no lexical connection to the user question."""

    # Planner examples are not new user requirements. Remove an invented
    # parenthetical expansion unless all its substantive terms are requested.
    query_terms = _content_terms(query)
    requirements = [re.sub(r"\s*\(([^()]*)\)",
                           lambda m: m.group(0) if _content_terms(m.group(1)) <= query_terms else "",
                           item) for item in requirements]
    if not query_terms:
        return requirements
    asks_for_boundary = bool(
        re.search(
            r"\b(why|limitation|limitations|boundary|boundaries|unanswered|untested|"
            r"unknown|unclear|establish|establishes|prove|proves|causal|causality)\b",
            query,
            re.IGNORECASE,
        )
    )
    filtered = [
        item
        for item in requirements
        if query_terms.intersection(_content_terms(item))
        and (
            asks_for_boundary
            or not re.search(
                r"\b(evidence boundar(?:y|ies)|limitations?)\b",
                item,
                re.IGNORECASE,
            )
        )
    ]
    return filtered or requirements


def _targets_one_named_source(query: str) -> bool:
    """Detect common one-study questions that a small router may over-split.

    A question can ask for methods plus results, or findings plus an evidence gap,
    without requiring a second paper. Keeping that distinction deterministic prevents
    a topically similar article from filling a missing component.
    """

    text = " ".join(query.casefold().split())
    repeated_study = bool(
        re.search(r"\b(study|trial|cohort)\b.*\band\b.*\b\1\b", text)
    )
    plural_sources = bool(
        re.search(r"\b(studies|trials|cohorts|papers|sources)\b", text)
    )
    named_study = bool(
        re.search(r"\b(study|trial|cohort|pilot|nomogram)\b", text)
    )
    one_model_build = bool(re.match(r"^how was .+\bbuilt and validated\b", text))
    unanswered_followup = bool(
        re.search(r"\bremains? (?:untested|unanswered|unknown|unclear)\b", text)
    )
    return (named_study and not repeated_study and not plural_sources) or (
        one_model_build or unanswered_followup
    )


def route_query(state: AgentState) -> dict:
    """Classify the query as factual / synthesis / multihop.

    Uses the generation role for classification; reasoning is backend-configured.
    Result stored in state but not used for routing in the graph edges;
    it is preserved for audit / downstream use.
    """
    llm = make_llm_fast(structured=True)
    query = state.get("original_query") or state["query"]

    _, parsed = _invoke_json_with_retry(llm, [
        SystemMessage(content=ROUTER_SYSTEM),
        HumanMessage(content=ROUTER_USER.format(query=query)),
    ], required_keys=("type",))

    query_type = parsed.get("type", "factual")
    search_queries = _unique_texts(parsed.get("search_queries", []), limit=3)
    answer_requirements = _unique_texts(
        parsed.get("answer_requirements", []),
        limit=4,
    )
    if not search_queries:
        search_queries = [query]
    if not answer_requirements:
        answer_requirements = [query]
    source_scope = str(parsed.get("source_scope", "")).strip().lower()
    if source_scope not in {"single_study", "multi_source", "general"}:
        if "supplied" in query.casefold():
            source_scope = "single_study"
        elif query_type in {"synthesis", "multihop"} and len(search_queries) > 1:
            source_scope = "multi_source"
        else:
            source_scope = "general"
    if source_scope == "multi_source" and _targets_one_named_source(query):
        source_scope = "single_study"
    answer_mode = str(parsed.get("answer_mode", "")).strip().lower()
    evidence_boundary = bool(
        re.match(r"^\s*(does|do|did|has|have|can|is|are)\b", query, re.IGNORECASE)
        and re.search(r"\b(study|evidence|documents?|paper|trial)\b", query, re.IGNORECASE)
    )
    if evidence_boundary:
        answer_mode = "evidence_boundary"
    elif answer_mode == "evidence_boundary":
        answer_mode = "compare" if source_scope == "multi_source" else "direct"
    elif answer_mode not in {"direct", "compare"}:
        answer_mode = "compare" if source_scope == "multi_source" else "direct"
    answer_requirements = _filter_requirements_for_query(query, answer_requirements)
    if answer_mode == "evidence_boundary":
        # Keep the requested comparator attached to the outcomes. Splitting it
        # into an isolated "specify comparator" item loses the actual question.
        answer_requirements = [query]
    logger.info("[route] query_type=%s  reason=%s", query_type, parsed.get("reason", ""))

    # Preserve the original query before any rewrites happen; used by append_history
    # to record what the user actually asked regardless of query reformulations.
    return {
        "query": query,
        "original_query": query,
        "query_type": query_type,
        "source_scope": source_scope,
        "answer_mode": answer_mode,
        "search_queries": search_queries,
        "answer_requirements": answer_requirements,
        "iterations": state.get("iterations", 0),
        "regen_count": state.get("regen_count", 0),
    }


def rewrite_query(state: AgentState) -> dict:
    """Rewrite a failed query to improve retrieval.

    Uses the review role. Increments the iterations counter.
    Also appends the old query to rewritten_queries for audit.
    """
    llm = make_llm_think()
    original_query = state.get("original_query") or state["query"]
    previous_rewrites = state.get("rewritten_queries", [])
    reason = state.get("grade_reason", "")
    hint   = state.get("rewrite_hint", "")
    requirements = _format_requirements(
        state.get("answer_requirements", []),
        original_query,
    )

    raw = _invoke_with_retry(llm, [
        SystemMessage(content=REWRITE_SYSTEM),
        HumanMessage(content=REWRITE_USER.format(
            query=original_query,
            requirements=requirements,
            previous_rewrites=", ".join(previous_rewrites) or "none",
            reason=reason,
            hint=hint,
        )),
    ])
    new_query = raw.strip().strip('"').strip("'")

    iterations = state.get("iterations", 0) + 1
    logger.info("[rewrite] iter=%d  new_query=%s", iterations, new_query[:80])

    return {
        "query": new_query,
        "rewritten_queries": [new_query],   # Annotated[list, add] — appends
        "iterations": iterations,
    }
