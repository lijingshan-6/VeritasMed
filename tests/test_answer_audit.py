"""Direct audit: exact anchors, explicit uncovered text and failures, with no live model calls."""
import json
from types import SimpleNamespace

import pytest

from medrag.verification.answer_audit import Anchor, AuditRequest, audit_answer, resolve_anchor
from medrag.verification.numeric_checks import numeric_diagnostic


class Stub:
    def __init__(self, outputs):
        self.outputs = iter(outputs)

    def invoke(self, messages):
        value = next(self.outputs)
        if isinstance(value, Exception):
            raise value
        return SimpleNamespace(content=json.dumps(value), usage_metadata=None, response_metadata={})


def item():
    return AuditRequest(answer="A 😀. B is false.", sources=[{"id": "s1", "title": "Source", "text": "A 😀. B is true."}])


def claim(quote="A 😀.", evidence="A 😀."):
    return {"quote": quote, "occurrence": 0, "relation": "supported", "evidence": [
        {"source_id": "s1", "quote": evidence, "occurrence": 0}], "explanation": "Source says this."}


def test_unicode_and_duplicate_anchors():
    span = resolve_anchor("😀 x 😀 x", Anchor(quote="😀 x", occurrence=1))
    assert (span["start"], span["end"]) == (4, 7)
    with pytest.raises(ValueError):
        resolve_anchor("x", Anchor(quote="invented", occurrence=0))


def test_unextracted_text_stays_visible():
    audit = audit_answer(item(), Stub([{"claims": [claim()]}]))
    assert audit["status"] == "ok"
    assert audit["checked_coverage"]["uncovered"][0]["text"] == " B is false."


def test_invalid_source_is_not_a_pass():
    audit = audit_answer(item(), Stub([{"claims": [claim(evidence="Invented sentence")]}]))
    assert audit["status"] == "partial_error"
    assert audit["summary"]["supported"] == 0
    assert audit["claims"][0]["status"] == "invalid_reference"
    assert audit["checked_coverage"]["covered_nonspace_characters"] == 0


def test_provider_failure_is_recorded_without_exposing_body():
    class Failed(Exception):
        status_code = 402
    audit = audit_answer(item(), Stub([Failed("secret provider body")]))
    assert audit["status"] == "partial_error"
    assert audit["calls"][0]["status"] == "execution_error"
    assert audit["calls"][0]["http_status"] == 402
    assert "secret" not in json.dumps(audit)


def test_invalid_schema_is_not_no_claims():
    audit = audit_answer(item(), Stub([{"claims": [{"quote": "A 😀."}]}]))
    assert audit["status"] == "partial_error"
    assert audit["calls"][0]["error_type"] == "InvalidAuditSchema"


def test_contradiction_keeps_its_evidence():
    faulty = claim("B is false.", "B is true.")
    faulty["relation"] = "contradicted"
    audit = audit_answer(item(), Stub([{"claims": [faulty]}]))
    assert audit["summary"]["contradicted"] == 1
    evidence = audit["claims"][0]["evidence"][0]
    assert item().sources[0].text[evidence["start"]:evidence["end"]] == "B is true."


def test_numeric_absence_and_multi_arm_remain_unknown():
    slots = {"subject": "drug A", "outcome": "response"}
    claim_text = "drug A response was 40%"
    assert numeric_diagnostic("no number here", [], slots)["status"] == "not_applicable"
    two = [{"text": "drug A response 40%"}, {"text": "placebo 20%"}]
    assert numeric_diagnostic(claim_text, two, slots)["status"] == "unresolved"
    mismatch = numeric_diagnostic(claim_text, [{"text": "drug A response was 30%"}], slots)
    assert mismatch["status"] == "possible_mismatch" and mismatch["overrides_relation"] is False
    same = numeric_diagnostic(claim_text, [{"text": "drug A response was 40%"}], slots)
    assert same["status"] == "equivalent"
