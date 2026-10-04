import json
from types import SimpleNamespace

from medrag.verification.atomic_v2 import audit_atomic_v2
from medrag.verification.answer_audit import AuditRequest as AtomicV2Request


class QueueLLM:
    def __init__(self, *values):
        self.values = iter(values)

    def invoke(self, _):
        return SimpleNamespace(
            content=json.dumps(next(self.values)), usage_metadata=None, response_metadata={}
        )


def case():
    return AtomicV2Request(
        answer="At 2 years. A had 10 events. B had 10 events.",
        sources=[{"id": "s", "title": "Original", "text": "At 2 years, A had 10 events."}],
        strategy="atomic_v2",
    )


def fact():
    return {
        "parent_quote": "A had 10 events.",
        "answer_quotes": ["A", "10 events"],
        "normalized_claim": "At 2 years, A had 10 events.",
        "slots": {},
        "decomposition_status": "atomic",
        "qualifiers": [
            {"kind": "time_denominator", "quote": "2 years", "parent_quote": "At 2 years."}
        ],
    }


def run(facts, judgments=None):
    if judgments is None:
        judgments = [
            {
                "fact_id": f"fact-{i + 1}",
                "relation": "supported",
                "evidence": [{"source_id": "s", "quote": case().sources[0].text}],
                "explanation": "Supplied text.",
            }
            for i in range(len(facts))
        ]
    return audit_atomic_v2(
        case(),
        QueueLLM(
            {"facts": facts, "completeness_note": "B remains unextracted."},
            {"judgments": judgments},
        ),
    )


def test_parent_scoping_and_cross_sentence_qualifier():
    result = run([fact()])
    claim = result["claims"][0]
    assert claim["status"] == "ok"
    assert claim["answer_bindings"][1]["status"] == "unique"
    assert claim["qualifier_anchors"][0]["binding"]["span"]["start"] == 3
    assert result["strategy"] == "atomic_v2"
    assert len(result["calls"]) == 2


def test_omitted_time_number_keeps_model_relation_but_requires_review():
    raw = fact()
    raw["normalized_claim"] = "A had 10 events."
    claim = run([raw])["claims"][0]
    assert claim["relation"] == "supported"
    assert claim["status"] == "needs_review"
    assert claim["fidelity_diagnostic"]["numbers_absent_from_interpretation"] == ["2"]


def test_unresolved_qualifier_is_not_a_completed_check():
    raw = fact()
    raw["qualifiers"][0]["quote"] = "20 years"
    result = run([raw])
    assert result["claims"][0]["status"] == "needs_review"
    assert result["summary"]["supported"] == 0
    assert result["claims"][0]["relation"] == "supported"


def test_duplicate_interpretations_do_not_create_independent_support():
    result = run([fact(), fact()])
    assert result["claims"][1]["duplicate_of"] == "fact-1"
    assert result["claims"][1]["status"] == "needs_review"
    assert result["summary"]["supported"] == 1


def test_missing_parent_cannot_receive_a_judgment():
    raw = fact()
    raw["parent_quote"] = "A had 100 events."
    result = run([raw])
    assert len(result["calls"]) == 1
    assert result["claims"][0]["relation"] is None
    assert result["claims"][0]["status"] == "invalid_reference"


def test_omitted_judgment_remains_unchecked():
    result = run([fact()], judgments=[])
    assert result["claims"][0]["relation"] is None
    assert result["summary"]["failed_or_unchecked"] == 1
