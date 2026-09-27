"""Review generated claims and select components for limited repair."""
from __future__ import annotations

import logging
import json
from langchain_core.messages import HumanMessage, SystemMessage
from medrag.agent.evidence import bind_claims, missing_numeric_details, outline_status, component_gap
from medrag.agent.llms import make_llm_think
from medrag.agent.prompts import BOUNDARY_CHECK_SYSTEM, CHECK_SYSTEM, CHECK_USER
from medrag.agent.state import AgentState
from medrag.agent.utils import build_answer_from_claims
from .common import _format_context, _format_outline, _format_requirements, _invoke_json_with_retry
from .constants import MAX_REGEN

logger = logging.getLogger("medrag.agent.nodes")


def _check_schema(components: list[dict]) -> dict | bool:
    """Require one actual decision per component, including missing outcomes."""
    if not components:
        return True
    row = {"type": "object", "properties": {
        "passed": {"type": "boolean"}, "correction": {"type": "string"},
        "unsupported_source_inference": {"type": "boolean"},
        "evidence_status": {"type": "string", "enum": ["supported", "partial", "missing"]},
        "gap": {"type": "string"}, "missing_outcome": {"type": "string"},
        "requirement_requested": {"type": "boolean"}},
        "required": ["passed", "correction", "unsupported_source_inference", "evidence_status", "gap", "missing_outcome", "requirement_requested"],
        "additionalProperties": False}
    properties = {key: {"type": "boolean"} for key in ("supported", "complete", "boundary_correct")}
    properties.update({"issues": {"type": "string"}, "component_checks": {
        "type": "object", "properties": {c["id"]: row for c in components},
        "required": [c["id"] for c in components], "additionalProperties": False}})
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def check_faithfulness(state: AgentState) -> dict:
    """Verify that every factual claim in the answer is grounded in context.

    Uses the review tier with a decision required for each component.
    Returns faithful (bool) and faithfulness_issues (str).
    """
    chunks = state.get("retrieved_chunks", [])
    answer = state.get("answer", "")
    query = state.get("original_query") or state.get("query", "")
    requirements = _format_requirements(state.get("answer_requirements", []), query)
    components = state.get("answer_components", [])
    if components:
        requirements += "\nSource-bound answer outline:\n" + _format_outline(components, include_quotes=False)
    evidence_status = state.get("evidence_status", "complete")
    evidence_gap = state.get("evidence_gap", "")
    source_scope = state.get("source_scope", "general")
    answer_mode = state.get("answer_mode", "direct")
    context = _format_context(chunks) if chunks else "(no context)"

    groups = [(query, chunks, components, answer, requirements)]
    decisions = []
    for group_query, group_chunks, group_components, group_answer, group_requirements in groups:
        boundary_only = group_components and all(c["status"] == "missing" for c in group_components)
        system = BOUNDARY_CHECK_SYSTEM if boundary_only else CHECK_SYSTEM
        schema = _check_schema(group_components)
        system += ("\nCheck ALL supplied components and the final answer together. Keep each result with its own study. "
                   "Do not add requirements such as unrequested loss functions, cross-validation splits, "
                   "pooled comparisons or superiority rankings. An exact quotation preserves the source's "
                   "speaker, including first-person pronouns inside quotation marks. "
                   "Return component_checks as an OBJECT keyed by every supplied C-ID, not an array. "
                   "For each ID give passed, correction, unsupported_source_inference, evidence_status, gap, "
                   "missing_outcome (only the actually absent requested part, a short noun phrase), and "
                   "requirement_requested (false only for an extra requirement not asked by the ORIGINAL user). "
                   "A correct explanation that a requested result is missing passes that component.\n")
        if isinstance(schema, dict):
            system += "Required output schema: " + json.dumps(schema)
        own_status, own_gap = outline_status(group_components) if group_components else (evidence_status, evidence_gap)
        _, decision = _invoke_json_with_retry(make_llm_think(structured=schema), [
            SystemMessage(content=system),
            HumanMessage(content=CHECK_USER.format(
                context=_format_context(group_chunks) if group_chunks else context,
                query=group_query, requirements=group_requirements,
                source_scope="single_study" if len(groups) > 1 else source_scope,
                answer_mode=answer_mode, evidence_status=own_status,
                evidence_gap=own_gap, answer=group_answer,
            )),
        ], required_keys=("supported", "complete", "boundary_correct"))
        if isinstance(decision.get("component_checks"), dict):
            decision["component_checks"] = [{"id": k, **v} for k, v in decision["component_checks"].items()]
        decisions.append(decision)
    parsed = {key: bool(decisions) and all(d.get(key, False) for d in decisions)
              for key in ("supported", "complete", "boundary_correct")}
    parsed["issues"] = " ".join(str(d.get("issues", "")) for d in decisions)
    parsed["component_checks"] = [c for d in decisions for c in d.get("component_checks", [])]

    supported = bool(parsed.get("supported", False))
    complete = bool(parsed.get("complete", False))
    boundary_correct = bool(parsed.get("boundary_correct", False))
    faithful = supported and complete and boundary_correct
    issues = str(parsed.get("issues", ""))
    if not faithful and not issues:
        failed = [
            label
            for label, passed in (
                ("claim support", supported),
                ("answer completeness", complete),
                ("evidence boundary", boundary_correct),
            )
            if not passed
        ]
        issues = f"Failed checks: {', '.join(failed)}."

    repairs = []
    checks = parsed.get("component_checks", [])
    revised_components = []
    for component in components:
        component = dict(component)
        check = next((c for c in checks if isinstance(c, dict) and c.get("id") == component["id"]), {})
        if check.get("requirement_requested") is False:
            # The planner is not allowed to expand the original user's task.
            # Removing that extra component also removes its invented gap.
            continue
        revised_status = check.get("evidence_status")
        if revised_status == "supported" and component["evidence"]:
            component.update(status="supported", gap="", missing_outcome="")
        if (check.get("unsupported_source_inference") is True
                and revised_status in {"partial", "missing"}
                and revised_status != component["status"] and check.get("gap")):
            component["status"] = revised_status
            component["missing_outcome"] = check.get("missing_outcome", "")
            component["gap"] = component_gap(component, component["missing_outcome"])
            if revised_status == "missing":
                component["answer"] = ""
            check = {**check, "passed": False}
        elif answer_mode != "evidence_boundary" and revised_status in {"partial", "missing"} and revised_status == component["status"] and check.get("missing_outcome"):
            component["missing_outcome"] = check["missing_outcome"]
            component["gap"] = component_gap(component, component["missing_outcome"])
        revised_components.append(component)
        if check.get("passed") is not True:
            repairs.append(component["id"])
            correction = str(check.get("correction", "Compare this component with every bound detail and gap."))
            issues += f" {component['id']}: {correction}"
    if repairs:
        complete = False
    if components and not revised_components:
        revised_components = components
        supported = complete = False
        issues += " The review discarded every requested component; the original question still needs an answer."
    for component_id, details in missing_numeric_details(revised_components, state.get("answer_claims", [])).items():
        if component_id not in repairs:
            repairs.append(component_id)
        complete = False
        issues += f" {component_id}: preserve the missing numerical detail(s): {'; '.join(details)}."
    if state.get("binding_issues"):
        supported = False
        issues += " " + " ".join(state["binding_issues"])
    faithful = supported and complete and boundary_correct
    if not faithful and not repairs:
        repairs = [c["id"] for c in components]
    # Keep evidence gaps visible even when a repair cannot finish within the budget.
    status = state.get("evidence_status", "insufficient")
    if not faithful and status == "complete":
        status = "partial"
    gap = state.get("evidence_gap", "")
    if not faithful and state.get("regen_count", 0) >= MAX_REGEN and not gap:
        gap = "Some requested details could not be verified in this answer; inspect the source passages."
    rendered_update = {}
    if revised_components != components:
        # A newly rejected source inference must not remain in the visible answer
        # even when the final check has exhausted the regeneration budget.
        kept, _ = bind_claims(state.get("answer_claims", []), revised_components)
        status, gap = outline_status(revised_components)
        answer, citations = build_answer_from_claims(kept)
        if status == "insufficient":
            status, answer, citations, kept = "insufficient", gap, [], []
        elif status == "partial":
            answer = f"{answer} {gap}" if kept else gap
        rendered_update = {"answer": answer, "citations": citations, "answer_claims": kept}
    logger.info("[check] faithful=%s", faithful)
    return {
        **rendered_update,
        "answer_components": revised_components,
        "evidence_status": status,
        "evidence_gap": gap,
        "repair_component_ids": repairs,
        "repair_history": [{"attempt": state.get("regen_count", 0), "component_ids": repairs, "issues": issues.strip()}],
        "faithful": faithful,
        "faithfulness_issues": issues,
        "answer_supported": supported,
        "answer_complete": complete,
        "boundary_correct": boundary_correct,
    }


def increment_regen(state: AgentState) -> dict:
    """Increment the regen counter before looping back to generate.

    Separated from check_faithfulness so the counter update is persisted
    correctly by the LangGraph checkpointer (edge functions are read-only).
    """
    new_count = state.get("regen_count", 0) + 1
    logger.info("[regen] regen_count → %d", new_count)
    return {"regen_count": new_count}
