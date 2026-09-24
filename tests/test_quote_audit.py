import json
from types import SimpleNamespace

from medrag.verification.quote_audit import QuoteAuditRequest, audit_quotes, locate_quote


class Fake:
    def __init__(self, output):
        self.output = output

    def invoke(self, _):
        return SimpleNamespace(content=json.dumps(self.output), usage_metadata=None, response_metadata={})


def test_unique_unicode_and_overlapping_ambiguity():
    assert locate_quote("😀First.\nSecond.", "Second.")["span"]["start"] == 8
    binding = locate_quote("aaa", "aa")
    assert binding["status"] == "ambiguous" and binding["span"] is None
    assert [s["start"] for s in binding["candidates"]] == [0, 1]
    assert locate_quote("A drug.", "a drug.")["status"] == "not_found"


def test_context_is_derived_and_all_invalid_evidence_is_visible():
    item = QuoteAuditRequest(answer="Intro.\nA\nB", sources=[{"id": "s", "title": "S", "text": "Yes. Yes."}])
    result = audit_quotes(item, Fake({"claims": [{"quote": "A\nB", "relation": "supported", "explanation": "Claim.",
        "evidence": [{"source_id": "s", "quote": "Yes."}, {"source_id": "missing", "quote": "No."}]}], "meta_text": []}))
    claim = result["claims"][0]
    assert claim["status"] == "ambiguous_reference" and result["summary"]["supported"] == 0
    assert len(claim["context_spans"]) == 2 and claim["context_span"]["text"] == "A\nB"
    assert claim["binding_failures"] == ["ambiguous", "unknown_source"]
    assert result["checked_coverage"]["covered_nonspace_characters"] == 0


def test_repeated_answer_is_not_silently_bound_and_meta_cannot_hide_it():
    item = QuoteAuditRequest(answer="Fact. Fact.", sources=[{"id": "s", "title": "S", "text": "Fact."}])
    result = audit_quotes(item, Fake({"claims": [{"quote": "Fact.", "relation": "insufficient", "evidence": [], "explanation": "Missing."}],
                                     "meta_text": [{"quote": "Fact.", "kind": "introduction", "explanation": "Intro."}]}))
    assert result["claims"][0]["answer_span"] is None
    assert result["meta_text"][0]["status"] == "ambiguous_reference"
    assert result["status"] == "partial_error"


def test_fixed_target_cannot_change_and_meta_overlap_is_rejected():
    item = QuoteAuditRequest(answer="Fact.", sources=[{"id": "s", "title": "S", "text": "Fact."}])
    output = {"claims": [{"quote": "Fact.", "relation": "insufficient", "evidence": [], "explanation": "Missing."}],
              "meta_text": [{"quote": "Fact.", "kind": "introduction", "explanation": "Intro."}]}
    assert audit_quotes(item, Fake(output))["meta_text"][0]["status"] == "invalid_reference"
    result = audit_quotes(item, Fake(output), target="Fact.")
    assert result["status"] == "partial_error" and not result["claims"]
