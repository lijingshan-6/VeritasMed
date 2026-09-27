"""Narrow cohort and protocol guards; these are not clinical evidence grades."""
from __future__ import annotations

import re
from .models import normalized


def _has_population_count(text: str) -> bool:
    return bool(re.search(
        r"\b\d[\d,]*\s+(?:[\w-]+\s+){0,3}(?:patients?|participants?|controls?|veterans?|subjects?|women|men|children|volunteers?|births|images|examinations|animals?|mice|rats)\b",
        normalized(text),
    ))


_COHORT_ROLES = {
    "development": r"\b(develop\w*|train\w*)\b",
    "calibration": r"\bcalibrat\w*\b",
    "validation": r"\bvalidat\w*\b",
    "test": r"\btest(?:ed|ing)?\b",
}


def _population_counts(text: str) -> set[str]:
    return {m.replace(",", "") for m in re.findall(
        r"\b(\d[\d,]*)\s+(?:[\w-]+\s+){0,3}(?:patients?|participants?|controls?|veterans?|subjects?|women|men|children|volunteers?|births|images|examinations|animals?|mice|rats)\b",
        normalized(text),
    )}


def population_scope_issue(text: str, component: dict) -> bool:
    """A cohort count cannot lose its explicit development/test/etc. role.

    This is a narrow guard for plainly labelled populations, not an entailment
    score. Ambiguous sentences with several roles still need semantic review.
    """
    if text.startswith('The study reports: "') and text.endswith('"'):
        quoted = normalized(text[len('The study reports: "'):-1])
        if any(quoted == normalized(s["quote"]) for s in component["evidence"]):
            return False  # An exact sentence has not paraphrased a cohort's role.
    counts = _population_counts(text)
    cohort_alias = r"\b(?:same|entire|whole|full|separate|independent|external|distinct|held[ -]out)\b[^.!?]{0,45}\b(?:data(?:set)?|set|cohort|population|patients|images)\b"
    # An anaphor can reassign a development population without repeating its
    # count. Neither shared nor independent validation data can be inferred
    # just from 'multicenter validation'.
    if (re.search(r"\b(?:validat\w*|test(?:ed|ing)?)\b", normalized(text))
            and re.search(cohort_alias, normalized(text))
            and not any(re.search(cohort_alias, normalized(s["quote"]))
                        and re.search(r"\b(?:validat\w*|test(?:ed|ing)?)\b", normalized(s["quote"]))
                        for s in component["evidence"])):
        return True
    for span in component["evidence"]:
        quote = normalized(span["quote"])
        if not counts.intersection(_population_counts(quote)):
            continue
        roles = [role for role, pattern in _COHORT_ROLES.items() if re.search(pattern, quote)]
        if len(roles) == 1 and not re.search(_COHORT_ROLES[roles[0]], normalized(text)):
            return True
    return False


def _bounded_gap(requirement: str, basis: str = "") -> str:
    # The missing component, not a free-form story about the underlying study,
    # names the evidence gap. In particular no invented design/data rationale.
    subject = re.sub(r"^(?:report\s+)?whether\s+|^report\s+", "", requirement, flags=re.I).rstrip('.?')
    statement = re.sub(r"^(?:does|do|did|can|could|has|have)\s+.+?\s+(?:establish|show|demonstrate|prove|confirm|support)\s+(?:that\s+)?", "", subject, flags=re.I)
    if statement != subject:
        if basis == "comparison":
            return f"The retrieved evidence does not provide the comparative data needed to establish that {statement}."
        if basis == "outcome":
            return f"The retrieved evidence does not provide outcome data establishing that {statement}."
        return f"The retrieved evidence does not establish that {statement}."
    if basis == "outcome":
        return f"The retrieved evidence does not provide outcome data establishing: {subject}."
    if basis == "comparison":
        return f"The retrieved evidence does not provide the required comparative data for: {subject}."
    return f"The retrieved evidence does not establish: {subject}."


def component_gap(component: dict, missing_outcome: str = "", basis: str = "") -> str:
    """Name only the absent part; a partial answer is not a blanket refusal."""
    phrase = missing_outcome.strip() if isinstance(missing_outcome, str) else ""
    safe_phrase = (5 <= len(phrase) <= 300 and not re.search(
        r"\b(because|due to|there were|there was)\b|^(?:no |identify |explain |what |which )", phrase, re.I))
    if basis:
        return _bounded_gap(component["requirement"], basis)
    if safe_phrase:
        return _bounded_gap(phrase)
    if component["status"] == "partial":
        return f"The retrieved passages only partly cover this requested aspect: {component['requirement'].rstrip('.?')}."
    return _bounded_gap(component["requirement"])


def _details(value: object) -> list[str]:
    """A single detail is one string, never an iterable of individual digits."""
    return [value] if isinstance(value, str) else [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def protocol_scope_issue(text: str, component: dict) -> bool:
    """Do not turn a design label into an unreported acquisition schedule.

    This narrow guard supplements semantic review, like the cohort-role guard.
    It does not decide whether a design or an inference is generally valid.
    """
    timing = r"\b(simultaneously|concurrent(?:ly)?|at the same time|at a single time point|at one time point)\b"
    if not re.search(timing, normalized(text)):
        return False
    evidence = " ".join(normalized(s["quote"]) for s in component["evidence"])
    return not re.search(timing + r"|\b(same visit|single visit|one visit)\b", evidence)


def repair_design_scope(components: list[dict], claims: list[dict]) -> list[dict]:
    """Repair a timing-based causal explanation from a bound design statement.

    A cross-sectional label licenses an association-versus-intervention limit,
    not an acquisition schedule. For that narrow failure, keep the actual design
    quotation and a bounded inference instead of asking for another timing synonym.
    Other designs, mixed studies and safe explanations retain normal model review.
    """
    result = list(claims)
    for component in components:
        own = [c for c in result if c.get("component_id") == component["id"]]
        if component["status"] != "supported" or not re.search(
            r"\b(causal\w*|limitation\w*|cannot|can not)\b", normalized(component["requirement"])
        ):
            continue
        designs = [s for s in component["evidence"]
                   if re.search(r"\bcross[ -]sectional\b", normalized(s["quote"]))]
        if (not designs or len({s["citation"] for s in component["evidence"]}) != 1
                or not any(protocol_scope_issue(c.get("text", ""), component) for c in own)):
            continue
        design = designs[0]
        replacement = {
            "component_id": component["id"],
            "text": (f'The study reports: "{design["quote"]}". '
                     "This cross-sectional association alone neither establishes causal direction "
                     "nor demonstrates that changing the exposure improves outcomes."),
            "cite": [design["citation"]],
        }
        result = [c for c in result if c.get("component_id") != component["id"]] + [replacement]
    return result
