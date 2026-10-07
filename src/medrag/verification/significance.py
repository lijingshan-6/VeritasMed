"""Advisory flag: a non-significant result stated as "no difference" or "no effect".

A non-significant comparison means the study could not show a difference, not that there is
none. Model checkers often accept "X was not better than Y" for a source that reports
"no significant difference (p = 0.33)"; in Experiment A this was the most common overstatement
the Direct audit caught and a general model judge missed. This rule is lexical, looks only at a
claim and the evidence bound to it, and never changes the model's relation.
"""
from __future__ import annotations

import re

# The claim asserts absence of a difference or effect ...
ABSENCE = re.compile(
    r"\bno (?:statistically )?(?:difference|differences|effect|impact|influence|association|role|benefit|advantage)\b"
    r"|\b(?:did|does|do|was|were|is|are|had|has) not (?:differ|affect|influence|change|alter|improve|reduce|increase|decrease"
    r"|matter|predict|worsen|help|benefit)\b"
    r"|\b(?:not|no) (?:more|less) \w+|\b(?:not|no) (?:noisier|louder|quieter|safer|riskier|higher|lower|greater|smaller"
    r"|larger|faster|slower|shorter|better|worse|superior|inferior|different)\b"
    r"|\bnot (?:associated|related|linked)\b"
    r"|\b(?:equivalent|equally \w+|did not make a difference)\b",
    re.I,
)
# ... unless it already says the result was non-significant or not shown.
HEDGED = re.compile(
    r"\b(?:not|no) (?:statistically )?significant(?:ly)?\b|\bno evidence (?:of|that|for)\b"
    r"|\bnot (?:shown|demonstrated|established|detected|proven)\b|\bfailed to (?:show|detect|find|demonstrate)\b"
    r"|\bdid not (?:find|detect|show|reach|demonstrate)\b|\bnon-?significant\b|\b(?:significantly|statistically)\b",
    re.I,
)
# The bound evidence reports a non-significant comparison.
NONSIGNIFICANT = re.compile(
    r"\b(?:not|no) (?:statistically )?significant(?:ly)?\b|\bnon-?significant\b|\bno evidence of (?:a )?difference\b"
    r"|\bdid not reach (?:statistical )?significance\b|\bp\s*=\s*n\.?s\b|\(n\.?s\.?\)"
    r"|\bp\s*[>≥]\s*0?\.05\b|\bp\s*=\s*0?\.(?:0[5-9]|[1-9])\d*\b",
    re.I,
)
NOTE = ("The source reports a non-significant result, and this claim states it as no difference or no effect. "
        "A non-significant result means the study could not show a difference, not that there is none.")


def nonsignificance_diagnostic(claim: str, evidence: list[str]) -> dict:
    base = {"status": "not_applicable", "overrides_relation": False,
            "scope": "Lexical rule on the claim and its bound evidence; advisory only"}
    absence = ABSENCE.search(claim or "")
    if not absence or HEDGED.search(claim) or not evidence:
        return base
    for text in evidence:
        found = NONSIGNIFICANT.search(text or "")
        if found:
            return {**base, "status": "flagged", "claim_phrase": absence.group(0),
                    "evidence_phrase": found.group(0), "note": NOTE}
    return base
