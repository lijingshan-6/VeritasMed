"""Exact mappings and error denominators, with no live model calls."""
import json
from types import SimpleNamespace

import pytest

from medrag.verification.answer_audit import Anchor, AuditInput, audit_answer, resolve_anchor
from medrag.verification.ragtruth import score_answers


class Stub:
    def __init__(self, outputs):
        self.outputs = iter(outputs)

    def invoke(self, messages):
        assert "gold_spans" not in messages[1].content
        value = next(self.outputs)
        if isinstance(value, Exception):
            raise value
        return SimpleNamespace(content=json.dumps(value), usage_metadata=None, response_metadata={})


def item(strategy="direct"):
    return AuditInput(answer="A 😀. B is false.", sources=[{"id": "s1", "title": "Source", "text": "A 😀. B is true."}], strategy=strategy)


def claim(quote="A 😀.", evidence="A 😀."):
    return {"quote": quote, "occurrence": 0, "relation": "supported", "evidence": [
        {"source_id": "s1", "quote": evidence, "occurrence": 0}], "explanation": "Source says this."}


def test_unicode_and_duplicate_anchors():
    span = resolve_anchor("😀 x 😀 x", Anchor(quote="😀 x", occurrence=1))
    assert (span["start"], span["end"]) == (4, 7)
    with pytest.raises(ValueError):
        resolve_anchor("x", Anchor(quote="invented", occurrence=0))


@pytest.mark.parametrize("strategy", ["direct", "split"])
def test_unextracted_errors_stay_in_denominator(strategy):
    outputs = [{"claims": [claim()]}] if strategy == "direct" else [
        {"claims": [{"quote": "A 😀.", "occurrence": 0}]}, claim()]
    audit = audit_answer(item(strategy), Stub(outputs))
    assert audit["checked_coverage"]["uncovered"][0]["text"] == " B is false."
    cases = [{"id": "1", "source_id": "s1", "input": item(), "gold_spans": [
        {"start": 5, "end": 16, "text": "B is false."}]}]
    metrics = score_answers(cases, [{"case_id": "1", "audit": audit}])
    assert metrics["counts"]["gold_spans"] == 1
    assert metrics["gold_span_recall_any_overlap"] == 0
    assert metrics["gold_span_extraction_coverage"] == 0
    assert score_answers(cases, [])["counts"]["gold_spans"] == 1


def test_invalid_source_is_not_a_pass():
    audit = audit_answer(item(), Stub([{"claims": [claim(evidence="Invented sentence")]}]))
    assert audit["status"] == "partial_error"
    assert audit["summary"]["supported"] == 0
    assert audit["claims"][0]["status"] == "invalid_reference"
    assert audit["checked_coverage"]["covered_nonspace_characters"] == 0


def test_provider_failure_stops_subsequent_claims_without_exposing_body():
    class Failed(Exception):
        status_code = 402
    output = {"claims": [{"quote": "A 😀.", "occurrence": 0}, {"quote": "B is false.", "occurrence": 0}]}
    audit = audit_answer(item("split"), Stub([output, Failed("secret provider body")]))
    assert [c["status"] for c in audit["claims"]] == ["execution_error", "not_checked"]
    assert len(audit["calls"]) == 2
    assert "secret" not in json.dumps(audit)


def test_error_location_and_clean_false_positive_are_separate():
    faulty = claim("B is false.", "B is true.")
    faulty["relation"] = "contradicted"
    audit = audit_answer(item(), Stub([{"claims": [faulty]}]))
    cases = [{"id": "1", "source_id": "s1", "input": item(), "gold_spans": [
        {"start": 10, "end": 15, "text": "false"}]},
        {"id": "2", "source_id": "s2", "input": item(), "gold_spans": []}]
    metrics = score_answers(cases, [{"case_id": "1", "audit": audit}, {"case_id": "2", "audit": audit}])
    assert metrics["gold_span_recall_half_overlap"] == 1
    assert metrics["answer_error_precision"] == .5
    assert metrics["unmarked_answer_false_positive_rate"] == 1
    assert 0 < metrics["character_precision"] < 1
