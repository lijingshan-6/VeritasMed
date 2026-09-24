"""Context and routing boundaries; mock outputs do not measure semantic accuracy."""
import json
from types import SimpleNamespace

import pytest

from medrag.verification.context_audit import AuditRequest, audit_context
from medrag.verification.ragtruth import score_answers


class Stub:
    def __init__(self, value):
        self.value = value

    def invoke(self, messages):
        assert "gold_spans" not in messages[1].content
        return SimpleNamespace(content=json.dumps(self.value), usage_metadata=None, response_metadata={})


def test_context_preserves_attribution_but_is_not_evidence():
    item = AuditRequest(answer="😀 Officials alleged that X failed.\nAn investigation is pending.", sources=[
        {"id": "s", "title": "Source", "text": "Officials alleged that X failed."}])
    claim = {"quote": "X failed", "occurrence": 0, "context_id": "context-1", "relation": "supported",
             "evidence": [{"source_id": "s", "quote": "Officials alleged that X failed.", "occurrence": 0}], "explanation": "Allegation only."}
    result = audit_context(item, Stub({"claims": [claim], "meta_text": []}))
    assert result["claims"][0]["context_span"]["text"].startswith("😀 Officials alleged")
    assert result["claims"][0]["answer_span"]["start"] == 25
    claim["context_id"] = "context-2"
    result = audit_context(item, Stub({"claims": [claim], "meta_text": []}))
    assert result["summary"]["supported"] == 0
    assert result["claims"][0]["status"] == "invalid_reference"


def test_meta_is_visible_and_never_exempts_gold_from_recall():
    item = AuditRequest(answer="Summary in 10 words.", sources=[{"id": "s", "title": "Source", "text": "Study fact."}])
    result = audit_context(item, Stub({"claims": [], "meta_text": [{"quote": item.answer, "occurrence": 0,
                           "kind": "word_count", "explanation": "Self-description."}]}))
    assert result["summary"]["supported"] == 0
    assert result["meta_text"][0]["status"] == "not_source_checked"
    assert result["checked_coverage"]["covered_nonspace_characters"] == 0
    case = {"id": "1", "source_id": "s", "input": item, "gold_spans": [{"start": 0, "end": len(item.answer)}]}
    assert score_answers([case], [{"case_id": "1", "audit": result}])["gold_span_recall_any_overlap"] == 0


def test_no_silent_source_truncation_or_blank_inputs():
    sources = [{"id": str(i), "title": "Source", "text": "Text."} for i in range(8)]
    assert len(AuditRequest(answer="An answer", sources=sources).sources) == 8
    with pytest.raises(ValueError):
        AuditRequest(answer="  ", sources=sources)
    with pytest.raises(ValueError):
        AuditRequest(answer="Answer", sources=[dict(s, text="x" * 11000) for s in sources])
