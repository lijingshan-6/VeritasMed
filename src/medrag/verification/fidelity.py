"""Mechanical extraction diagnostics, never a semantic or clinical guarantee."""

import re

from .parent_binding import bind_parent_fragments


def numbers(text):
    """Literal numeric tokens only; no clinical conversions or invented equivalence."""
    text = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", text).replace("·", ".")
    return set(re.findall(r"(?<![A-Za-z\d])\d+(?:\.\d+)?", text))


def bind_qualifiers(answer, qualifiers):
    result = []
    for qualifier in qualifiers:
        raw = qualifier.model_dump() if hasattr(qualifier, "model_dump") else qualifier
        bound = bind_parent_fragments(answer, raw["parent_quote"], [raw["quote"]])
        result.append(
            {
                **raw,
                "parent_binding": bound["parent_binding"],
                "binding": bound["answer_bindings"][0],
            }
        )
    return result


def fidelity_diagnostic(fact, qualifiers):
    flags = []
    if any(q["binding"]["status"] != "unique" for q in qualifiers):
        flags.append("unresolved_qualifier_anchor")
    texts = [*fact.answer_quotes, *(q["quote"] for q in qualifiers)]
    missing = sorted(numbers(" ".join(texts)) - numbers(fact.normalized_claim))
    if missing:
        flags.append("literal_number_absent_from_interpretation")
    if not qualifiers:
        flags.append("no_qualifier_anchors_declared")
    return {
        "status": "needs_review" if flags else "no_mechanical_issue_detected",
        "flags": flags,
        "numbers_absent_from_interpretation": missing,
        "scope": "Literal anchors and numeric tokens only. Paraphrases/conversions may trigger review; absence of a warning does not establish semantic fidelity or complete extraction.",
        "overrides_relation": False,
    }
