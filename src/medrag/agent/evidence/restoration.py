"""Detect bound numbers that an answer omitted; repair happens in the check node."""
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
