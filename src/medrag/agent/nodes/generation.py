"""Generate claims and apply bounded source-based repairs."""
from __future__ import annotations

import logging
import json
from langchain_core.messages import HumanMessage, SystemMessage
from medrag.agent.evidence import bind_claims, outline_status, repair_gaps, bind_additional_evidence, repair_design_scope, source_spans
from medrag.agent.llms import make_llm_fast
from medrag.agent.prompts import GENERATE_SYSTEM, GENERATE_USER, REGEN_SYSTEM, REGEN_USER
from medrag.agent.state import AgentState
from medrag.agent.utils import build_answer_from_claims, validate_citations
from .common import _boundary_sentence, _format_context, _format_outline, _format_requirements, _invoke_json_with_retry

logger = logging.getLogger("medrag.agent.nodes")


def generate_answer_node(state: AgentState) -> dict:
    """Generate a citation-grounded answer from retrieved context.

    Uses the generation role; reasoning is configured by the selected backend.

    Pipeline:
      1. LLM outputs {"claims": [{"text":…, "cite":[…]}], "confidence":…}
      2. validate_citations() filters out claims whose cite keys are not in
         the current retrieval context (prevents hallucinated references).
      3. build_answer_from_claims() reconstructs a readable answer string
         with inline [PMID:xxx] / [PMC:xxx] markers.
      4. If 0 claims survive validation, the answer is set to a disclaimer
         and confidence=0.0; check_faithfulness will mark it unfaithful,
         triggering one regen attempt via the graph's inc_regen path.
    """
    llm = make_llm_fast(structured=True)
    query = state.get("original_query") or state["query"]
    chunks = state.get("retrieved_chunks", [])
    context = _format_context(chunks) if chunks else "(no context available)"
    requirements = _format_requirements(state.get("answer_requirements", []), query)
    components = state.get("answer_components", [])
    if components:
        spans = source_spans(chunks)
        requirements += "\nSource-bound answer outline (cover each ID):\n" + _format_outline(components, include_quotes=False, all_spans=spans)
        context = "\n".join(f"[{key}] [{span['citation']}]: {span['quote']}" for key, span in spans.items())
    repair_ids = state.get("repair_component_ids", [])
    source_scope = state.get("source_scope", "general")
    answer_mode = state.get("answer_mode", "direct")
    regen_count = state.get("regen_count", 0)
    faith_issues = state.get("faithfulness_issues", "")

    # Use REGEN prompt if this is a re-generation attempt
    if regen_count > 0 and faith_issues:
        system_prompt = REGEN_SYSTEM.format(faithfulness_issues=faith_issues)
        user_prompt = REGEN_USER.format(
            query=query,
            requirements=requirements,
            source_scope=source_scope,
            answer_mode=answer_mode,
            context=context,
            faithfulness_issues=faith_issues,
        )
        logger.info("[generate] regen attempt #%d — using REGEN prompt", regen_count)
    else:
        system_prompt = GENERATE_SYSTEM
        user_prompt = GENERATE_USER.format(
            query=query,
            requirements=requirements,
            source_scope=source_scope,
            answer_mode=answer_mode,
            context=context,
        )

    if components and regen_count > 0:
        user_prompt += (
            "\nPrevious claims: " + json.dumps(state.get("answer_claims", []), ensure_ascii=False)
            + "\nRepair ONLY these component IDs: " + json.dumps(repair_ids)
            + ". Return replacement claims for those IDs only. Other components will be preserved."
        )

    raw, parsed = _invoke_json_with_retry(llm, [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ], required_keys=("claims", "evidence_status"))
    if not raw.strip():
        logger.warning("[generate] LLM returned completely empty response after retry")
    else:
        logger.debug("[generate] raw response (%d chars): %s", len(raw), raw[:300])
    # ── Citation-grounded validation ──────────────────────────────────────
    claims_raw: list[dict] = parsed.get("claims", [])
    confidence: float = float(parsed.get("confidence", 0.5))
    evidence_status = str(parsed.get("evidence_status", "complete")).strip().lower()
    if evidence_status not in {"complete", "partial", "insufficient"}:
        evidence_status = "complete"
    evidence_gap = str(parsed.get("evidence_gap", "")).strip()

    if not claims_raw:
        # LLM returned old-style {answer, citations} or empty claims
        # Graceful fallback: wrap entire answer as a single unverified claim
        legacy_answer = str(parsed.get("answer", raw))
        legacy_cites  = list(parsed.get("citations", []))
        if legacy_answer and legacy_cites:
            claims_raw = [{"text": legacy_answer, "cite": legacy_cites}]
            logger.info("[generate] legacy answer format detected, wrapping as single claim")
        else:
            logger.warning("[generate] LLM returned no claims and no legacy answer")

    binding_issues = []
    design_repairs = []
    if components:
        if regen_count > 0:
            components = repair_gaps(components, parsed.get("gap_repairs"), repair_ids)
        if regen_count > 0 and repair_ids:
            retained = [c for c in state.get("answer_claims", []) if c.get("component_id") not in repair_ids]
            claims_raw = retained + [c for c in claims_raw if isinstance(c, dict) and c.get("component_id") in repair_ids]
        components = bind_additional_evidence(claims_raw, components, chunks)
        repair_scope = [c for c in components if not regen_count or c["id"] in repair_ids]
        scoped = repair_design_scope(repair_scope, claims_raw)
        design_repairs = [c for c in scoped if c not in claims_raw]
        claims_raw, binding_issues = bind_claims(scoped, components)
        evidence_status, evidence_gap = outline_status(components)

    # Answers are written in the model's own words; the bound source sentences stay
    # attached to each component as evidence. Omitted numbers are caught by the
    # check node (missing_numeric_details) and repaired there, not pasted in.
    validated_claims = validate_citations(claims_raw, chunks)
    component_order = {component["id"]: index for index, component in enumerate(components)}
    validated_claims.sort(key=lambda claim: component_order.get(claim.get("component_id"), len(components)))
    answer, citations = build_answer_from_claims(validated_claims)

    if not components and answer_mode == "evidence_boundary" and evidence_status != "complete":
        evidence_status = "insufficient"
        evidence_gap = _boundary_sentence(
            evidence_gap,
            "The retrieved documents do not establish the requested outcome",
        )
        answer = evidence_gap
        citations = []
        confidence = 0.0
    elif evidence_status == "insufficient":
        evidence_gap = _boundary_sentence(
            evidence_gap,
            "The retrieved documents do not provide enough information to answer the requested question",
        )
        answer = evidence_gap
        citations = []
        confidence = 0.0
    elif evidence_status == "partial":
        evidence_gap = _boundary_sentence(
            evidence_gap,
            "The retrieved documents do not support every requested answer component",
        )
        answer = f"{answer} {evidence_gap}" if validated_claims else evidence_gap
        if not validated_claims:
            confidence = 0.0
    elif not validated_claims:
        # All claims failed citation validation — signal to check node
        evidence_status = "insufficient"
        evidence_gap = _boundary_sentence(
            evidence_gap,
            "The retrieved documents do not contain sufficient cited evidence to answer this question",
        )
        answer = evidence_gap
        confidence = 0.0
        logger.warning("[generate] all claims failed citation validation — answer set to disclaimer")

    logger.info("[generate] confidence=%.2f  valid_claims=%d  citations=%s",
                confidence, len(validated_claims), citations)
    rendered_components = []
    for component in components:
        component = dict(component)
        own_claims = [c for c in validated_claims if c.get("component_id") == component["id"]]
        component["answer"] = build_answer_from_claims(own_claims)[0] if own_claims else ""
        rendered_components.append(component)
    return {
        "repair_history": ([{"attempt": regen_count, "kind": "design_scope",
                             "component_ids": list(dict.fromkeys(c["component_id"] for c in design_repairs)),
                             "issues": "Replaced unsupported measurement timing with the bound design and an association-versus-intervention limit."}]
                           if design_repairs else []),
        "answer_components": rendered_components,
        "answer_claims": validated_claims,
        "binding_issues": binding_issues,
        "answer": answer,
        "citations": citations,
        "confidence": confidence,
        "evidence_status": evidence_status,
        "evidence_gap": evidence_gap,
    }
