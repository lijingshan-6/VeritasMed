"""Bind answer components and claims to supplied source passages."""
from __future__ import annotations

import re
from pydantic import ValidationError
from medrag.retrieval.retriever import RetrievedChunk
from .models import AnswerComponent, EvidenceSpan, normalized, source_spans
from .scope import _details, _has_population_count, component_gap, population_scope_issue, protocol_scope_issue
from .restoration import _METHOD_STEPS


def bind_components(
    raw: object, requirements: list[str], chunks: list[RetrievedChunk], study_context: object = None,
) -> list[dict]:
    """Accept only quotations that exist in the declared retrieved chunk.

    This validates provenance, not whether the quoted finding answers the question.
    Citation keys come from the chunk rather than the model's proposed reference.
    """
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    spans = source_spans(chunks)
    span_keys = list(spans)
    components = []
    for value in raw if isinstance(raw, list) else []:
        missing_basis = value.get("missing_basis", "") if isinstance(value, dict) else ""
        missing_outcome = value.get("missing_outcome", "") if isinstance(value, dict) else ""
        if isinstance(value, dict):
            value = {**value, "required_details": _details(value.get("required_details"))}
        if isinstance(value, dict) and "evidence_ids" in value:
            ids = value["evidence_ids"] if isinstance(value["evidence_ids"], list) else []
            chosen = [key for key in ids if isinstance(key, str) and key in spans]
            reference_details = []
            # "Comparable" can refer to values in the preceding sentence. Only
            # bring that sentence in when no explicit comparator is given here;
            # an unrelated preceding numeric result is not a required detail.
            for key in list(chosen):
                index = span_keys.index(key)
                current = spans[key]
                comparison = normalized(current["quote"])
                if index and re.search(r"\bcomparab\w*\b", comparison) and not re.search(r"\b(vs|versus|compared)\b", comparison):
                    previous_key = span_keys[index - 1]
                    previous = spans[previous_key]
                    if previous["chunk_id"] == current["chunk_id"] and re.search(r"\d", previous["quote"]):
                        if previous_key not in chosen:
                            chosen.append(previous_key)
                        reference_details.append(previous["quote"])
            value = {**value, "evidence": [spans[key] for key in chosen],
                     "required_details": [*(value.get("required_details") or []), *reference_details]}
        try:
            component = AnswerComponent.model_validate(value)
        except (ValidationError, TypeError):
            continue
        if not component.requirement.strip():
            continue
        component.id = f"C{len(components) + 1}"
        valid = []
        for span in component.evidence:
            chunk = by_id.get(span.chunk_id)
            if chunk and normalized(span.quote) and normalized(span.quote) in normalized(chunk.text):
                if span.citation and span.citation != chunk.citation:
                    continue
                valid.append(span.model_copy(update={"citation": chunk.citation}))
        lost_evidence = len(valid) != len(component.evidence)
        # A 'how does this method address the problem' component needs actual
        # method steps, not only the introductory purpose statement. Select
        # method sentences from the same already-bound source, never another study.
        method_requirement = re.search(r"\b(method\w*|technique\w*|reconstruction|filter\w*)\b", normalized(component.requirement))
        outcome_requirement = re.search(r"\b(result\w*|validation|performance)\b", normalized(component.requirement))
        if component.status != "missing" and method_requirement and not outcome_requirement:
            bound_chunks = {s.chunk_id for s in valid}
            for method_span in spans.values():
                if method_span["chunk_id"] in bound_chunks and _METHOD_STEPS.search(normalized(method_span["quote"])):
                    extra = EvidenceSpan.model_validate(method_span)
                    if extra not in valid:
                        valid.append(extra)
        component.evidence = valid
        # Required verbatim details must themselves be present in a bound quote.
        component.required_details = [
            detail for detail in component.required_details
            if normalized(detail) and any(normalized(detail) in normalized(s.quote) for s in valid)
        ]
        if value.get("required_details") and not component.required_details:
            # If proposed excerpts are paraphrases, keep the actual selected
            # source sentences as the contract instead of silently losing it.
            component.required_details = [span.quote for span in valid]
        for span in valid:
            # Preserve a whole selected contrast, including its null result.
            # A short positive half alone can reverse the meaning of a study.
            contrast = re.search(r"\b(whereas|while|but|versus)\b", normalized(span.quote))
            methods = (re.search(r"\b(how|method\w*|technique\w*|reconstruction|filter\w*)\b", normalized(component.requirement))
                       and _METHOD_STEPS.search(normalized(span.quote)))
            if (contrast or methods) and span.quote not in component.required_details:
                component.required_details.append(span.quote)
        if not valid:
            if component.status != "missing":
                component.gap = f"A source passage could not be bound reliably for: {component.requirement.rstrip('.?')}."
            component.status = "missing"
        elif lost_evidence and component.status == "supported":
            component.status = "partial"
        if component.status != "supported":
            component.gap = component_gap(component.model_dump(), missing_outcome, missing_basis)
        if component.status == "supported":
            component.gap = ""
        component.answer = ""
        components.append(component.model_dump())
    if not components:
        components = [AnswerComponent(
            id=f"C{i + 1}", requirement=requirement,
            gap=f"No source-bound evidence was identified for: {requirement.rstrip('.?')}.",
        ).model_dump() for i, requirement in enumerate(requirements)]
    # Preserve plainly stated cohort counts even when the outline model forgets
    # its population field. This selects a verbatim methods sentence, not a
    # number inferred from a percentage or a benchmark-specific sample size.
    explicit_populations = [
        {**span, "required_details": [span["quote"]]}
        for span in spans.values()
        if _has_population_count(span["quote"])
        and re.search(r"\b(included|enrolled|recruited|analy[sz]ed|randomi[sz]ed|using|underwent|comprised)\b", normalized(span["quote"]))
    ]
    contexts = [*(study_context if isinstance(study_context, list) else []), *explicit_populations]
    # Study population belongs with the first supported result from that study,
    # not in an unbound global summary or repeated under every component.
    for value in contexts:
        if isinstance(value, dict) and "evidence_id" in value:
            value = {**value, **spans.get(value["evidence_id"], {})}
        try:
            span = EvidenceSpan.model_validate(value)
        except (ValidationError, TypeError):
            continue
        if not _has_population_count(span.quote):
            continue
        source = by_id.get(span.chunk_id)
        if not source or not normalized(span.quote) or normalized(span.quote) not in normalized(source.text):
            continue
        if span.citation and span.citation != source.citation:
            continue
        span.citation = source.citation
        for component in components:
            if component["status"] != "missing" and any(s["citation"] == source.citation for s in component["evidence"]):
                if span.model_dump() not in component["evidence"]:
                    component["evidence"].append(span.model_dump())
                for detail in _details(value.get("required_details")):
                    if isinstance(detail, str) and normalized(detail) and normalized(detail) in normalized(span.quote):
                        if detail not in component["required_details"]:
                            component["required_details"].append(detail)
                break
    return components


def outline_status(components: list[dict]) -> tuple[str, str]:
    if not components:
        return "insufficient", "No source-bound evidence was identified."
    gaps = list(dict.fromkeys(c["gap"] for c in components if c.get("gap")))
    if all(c["status"] == "supported" for c in components):
        return "complete", ""
    useful = any(c["status"] in {"supported", "partial"} and c["evidence"] for c in components)
    return ("partial" if useful else "insufficient"), " ".join(gaps)


def repair_gaps(components: list[dict], repairs: object, repair_ids: list[str]) -> list[dict]:
    """Keep the question-bound gap; free prose cannot add an unrequested outcome.

    Kept as a compatibility helper for stored generation responses. Source
    review can revise a component's evidence status, but generator gap_repairs
    cannot silently change the question that the component is answering.
    """
    return [dict(component) for component in components]


def bind_claims(claims: list[dict], components: list[dict]) -> tuple[list[dict], list[str]]:
    """Reject claims whose citations do not belong to their requested component."""
    by_id = {c["id"]: c for c in components}
    accepted, issues = [], []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        text = str(claim.get("text", ""))
        if not text.startswith('The study reports: "'):
            text = re.sub(r"\bwe\b", "the authors", text, flags=re.I)
            text = re.sub(r"\bour\b", "their", text, flags=re.I)
            claim = {**claim, "text": text}
        component = by_id.get(claim.get("component_id"))
        if component and component["status"] == "missing":
            # Missing components are rendered as explicit gaps, never as adjacent
            # result claims. Discarding such a claim needs no regeneration loop.
            continue
        allowed = {s["citation"] for s in component["evidence"]} if component else set()
        citations = claim.get("cite", [])
        if (not component or component["status"] == "missing" or not citations
                or not isinstance(citations, list) or any(c not in allowed for c in citations)):
            issues.append(f"A claim has no matching component/source binding: {claim.get('text', '')}")
            continue
        if population_scope_issue(claim.get("text", ""), component):
            issues.append(f"{component['id']}: preserve the population's development/calibration/test/validation role. Report validation as stated without claiming shared, separate, independent or held-out data unless the source establishes that relationship.")
            continue
        if protocol_scope_issue(claim.get("text", ""), component):
            issues.append(f"{component['id']}: remove the unreported timing assertion, including 'at a single time point', 'at the same time' and 'simultaneously'. Keep the explanation that association does not establish the effect of an intervention, without describing when measurements occurred. Rejected draft: {claim.get('text', '')}")
            continue
        accepted.append(claim)
    for component in components:
        if component["status"] != "missing" and component["evidence"]:
            if not any(c.get("component_id") == component["id"] for c in accepted):
                issues.append(f"{component['id']}: answer omitted {component['requirement']}")
    return accepted, issues


def bind_additional_evidence(
    claims: list[dict], components: list[dict], chunks: list[RetrievedChunk],
) -> list[dict]:
    """Let generation recover a missed sentence, within the same bound study.

    Global sentence IDs resolve only to retrieved text. A generator cannot use
    them to upgrade a missing outcome or move another paper's result into this
    component. Semantic relevance remains the source reviewer's responsibility.
    """
    spans = source_spans(chunks)
    updated = [AnswerComponent.model_validate(c).model_dump() for c in components]
    by_id = {c["id"]: c for c in updated}
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        component = by_id.get(claim.get("component_id"))
        if not component or component["status"] == "missing":
            continue
        allowed = {s["citation"] for s in component["evidence"]}
        citations = claim.get("cite", [])
        ids = claim.get("evidence_ids", [])
        if not isinstance(ids, list) or not isinstance(citations, list):
            continue
        for key in ids:
            span = spans.get(key) if isinstance(key, str) else None
            if span and span["citation"] in allowed and span["citation"] in citations:
                if span not in component["evidence"]:
                    component["evidence"].append(dict(span))
                    if span["quote"] not in component["required_details"]:
                        component["required_details"].append(span["quote"])
    return updated
