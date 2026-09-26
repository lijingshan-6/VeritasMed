"""Conservative numeric diagnostics; a missing number is never a contradiction."""

from decimal import Decimal
import re

QUANTITY = re.compile(
    r"(?<![\w.])(\d+(?:,\d{3})*(?:\.\d+)?)\s*(mg|kg|g|ml|l|%|percent|days?|weeks?|years?)\b|(?<![\w.])(\d+(?:\.\d+)?)\s*(%)",
    re.I,
)
FACTORS = {
    "mg": ("mass_g", Decimal(".001")),
    "g": ("mass_g", Decimal(1)),
    "kg": ("mass_g", Decimal(1000)),
    "ml": ("volume_l", Decimal(".001")),
    "l": ("volume_l", Decimal(1)),
    "%": ("percent", Decimal(1)),
    "percent": ("percent", Decimal(1)),
    "day": ("days", Decimal(1)),
    "days": ("days", Decimal(1)),
    "week": ("days", Decimal(7)),
    "weeks": ("days", Decimal(7)),
    "year": ("years", Decimal(1)),
    "years": ("years", Decimal(1)),
}


def quantities(text):
    result = []
    for m in QUANTITY.finditer(text):
        value, unit = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        dimension, factor = FACTORS[unit.lower()]
        result.append((dimension, Decimal(value.replace(",", "")) * factor))
    return result


def numeric_diagnostic(claim, evidence, slots):
    """Compare only single quantities in one quoted passage with explicit shared context.

    Even a discrepancy is an advisory flag, never a replacement semantic decision.
    Multi-arm, rounding, denominator and interval ambiguity deliberately remain unresolved.
    """
    base = {
        "status": "not_applicable",
        "overrides_relation": False,
        "scope": "Single explicit quantity with shared named subject/outcome/time; advisory only",
    }
    left = quantities(claim)
    if not left:
        return base
    if len(evidence) != 1 or len(left) != 1:
        return {
            **base,
            "status": "unresolved",
            "reason": "Multiple quantities or passages require semantic alignment",
        }
    text = evidence[0]["text"]
    right = quantities(text)
    if len(right) != 1 or left[0][0] != right[0][0]:
        return {
            **base,
            "status": "unresolved",
            "reason": "Missing or non-unique comparable quantity; absence is not contradiction",
        }
    context = [slots.get(k) for k in ("subject", "outcome", "time") if slots.get(k)]
    if len(context) < 2 or any(
        c.lower() not in text.lower() or c.lower() not in claim.lower() for c in context
    ):
        return {
            **base,
            "status": "unresolved",
            "reason": "Cannot establish identical explicit quantity context",
        }
    if re.search(r"\b(about|approximately|rounded|range|CI|between)\b", claim + " " + text, re.I):
        return {
            **base,
            "status": "unresolved",
            "reason": "Approximation or interval is outside this exact-value rule",
        }
    return {
        **base,
        "status": "equivalent" if left == right else "possible_mismatch",
        "claim_quantity": str(left[0][1]),
        "evidence_quantity": str(right[0][1]),
        "dimension": left[0][0],
    }
