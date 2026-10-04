"""Restore omitted numbers and result context from bound quotations."""
from __future__ import annotations

import re
from decimal import Decimal
from .models import normalized


_METHOD_STEPS = re.compile(r"\b(combin(?:ed|es)|incorporat(?:e|ed|es)|us(?:e|ed|es)|calculated|optimi[sz]ed|applied)\b")


def missing_numeric_details(components: list[dict], claims: list[dict]) -> dict[str, list[str]]:
    """Catch omitted bound numbers; semantic support still needs source review."""
    def numbers(text: str) -> set[Decimal]:
        text = normalized(text)
        text = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", text)
        return {Decimal(n) for n in re.findall(r"(?<![\w.])(?:\d*\.\d+|\d+)(?!\w)", text)}

    missing = {}
    for component in components:
        if component["status"] == "missing":
            continue
        citations = {span["citation"] for span in component["evidence"]}
        # A finding already explained under another component of the same study
        # need not be quoted twice. Other papers cannot satisfy this requirement.
        rendered = " ".join(c.get("text", "") for c in claims
                            if c.get("component_id") == component["id"]
                            or (c.get("cite") and set(c["cite"]) <= citations))
        absent = [d for d in component["required_details"] if numbers(d) - numbers(rendered)]
        if absent:
            missing[component["id"]] = absent
    return missing


def restore_numeric_quotes(components: list[dict], claims: list[dict]) -> list[dict]:
    """Restore omitted bound numbers without another generative call.

    Prefer a full source sentence over a disconnected number or an invented
    paraphrase. This does not infer an outcome or repair semantic contradictions.
    """
    missing = missing_numeric_details(components, claims)
    for component in components:
        if component["status"] == "missing":
            continue
        rendered = normalized(" ".join(c.get("text", "") for c in claims if c.get("component_id") == component["id"]))
        for detail in component["required_details"]:
            # A vague 'used sampling' must not replace the actual method. Allow
            # concise paraphrases; quote only substantial lexical omissions.
            terms = set(re.findall(r"\b[a-z][a-z0-9-]{4,}\b", normalized(detail)))
            if (_METHOD_STEPS.search(normalized(detail)) and terms
                    and sum(term in rendered for term in terms) / len(terms) < 0.5):
                if detail not in missing.setdefault(component["id"], []):
                    missing[component["id"]].append(detail)
            # Preserve a selected contrast even if its second arm has no number.
            # This lexical fallback may quote a valid paraphrase unnecessarily;
            # it does not claim to establish semantic equivalence.
            contrast = re.search(r"\b(?:whereas|while|but)\b(.+)", normalized(detail))
            if contrast:
                tail_terms = set(re.findall(r"\b[a-z][a-z0-9-]{3,}\b", contrast[1])) - {
                    "with", "that", "this", "were", "remained", "substantially", "significantly",
                }
                if tail_terms and sum(t in rendered for t in tail_terms) / len(tail_terms) < 0.75:
                    if detail not in missing.setdefault(component["id"], []):
                        missing[component["id"]].append(detail)
    result = list(claims)
    for component in components:
        used = set()
        for detail in missing.get(component["id"], []):
            span = next((s for s in component["evidence"] if normalized(detail) in normalized(s["quote"])), None)
            if span and span["quote"] not in used:
                result.append({"component_id": component["id"],
                               "text": f'The study reports: "{span["quote"]}"',
                               "cite": [span["citation"]]})
                used.add(span["quote"])
    return result


def preserve_result_context(components: list[dict], claims: list[dict]) -> list[dict]:
    """Keep actors, denominators and qualifiers together in critical results.

    A paraphrase containing all the digits can still change whose performance
    was measured. For numerical/method components render the selected complete
    source sentences. Other components retain their generated explanation.
    This is extractive presentation, not an additional semantic judgment.

    A sentence already rendered for another component is not rendered again:
    a second copy is deduplicated away and would erase this component's own
    answer (e.g. "state whether that sentence reports five-year mortality").
    """
    projected_ids = {component["id"] for component in components}
    rendered = {c.get("text") for c in claims if c.get("component_id") not in projected_ids}
    result = []
    for component in components:
        own = [c for c in claims if c.get("component_id") == component["id"]]
        if component["status"] == "missing":
            continue
        if re.search(r"\b(causal\w*|limitation\w*|why|prevent\w*|cannot)\b", normalized(component["requirement"])):
            # A design quotation supports an explanation but cannot replace it.
            # The semantic checker still reviews that generated explanation.
            result.extend(own)
            continue
        critical = any(re.search(r"\d", d) or _METHOD_STEPS.search(normalized(d))
                       for d in component["required_details"])
        if not critical:
            result.extend(own)
            continue
        selected = []
        for span in component["evidence"]:
            if any(normalized(d) in normalized(span["quote"]) for d in component["required_details"]):
                if span not in selected:
                    selected.append(span)
        # Preserve the source's text (including "we") inside explicit quotation
        # marks. The answer therefore does not impersonate the study authors.
        quotes = [{"component_id": component["id"],
                   "text": f'The study reports: "{span["quote"]}"',
                   "cite": [span["citation"]]} for span in selected]
        quotes = [q for q in quotes if q["text"] not in rendered]
        if not quotes:
            result.extend(own)
            continue
        rendered.update(q["text"] for q in quotes)
        result.extend(quotes)
    return result
