import json
from types import SimpleNamespace

from medrag.verification.atomic_audit import audit_atomic
from medrag.verification.atomic_schema import AtomicAuditRequest
from medrag.verification.research_metrics import fixed_metrics
from medrag.verification.numeric_checks import numeric_diagnostic


class QueueLLM:
    def __init__(self, *values):
        self.values = iter(values)

    def invoke(self, _):
        return SimpleNamespace(
            content=json.dumps(next(self.values)), usage_metadata=None, response_metadata={}
        )


def test_discontiguous_fact_is_linked_without_inventing_quote():
    answer = "Group A and group B had 10 and 20 events, respectively."
    item = AtomicAuditRequest(
        answer=answer, sources=[{"id": "s", "title": "Trial", "text": "Group A had 10 events."}]
    )
    extraction = {
        "facts": [
            {
                "parent_quote": answer,
                "answer_quotes": ["Group A", "10"],
                "normalized_claim": "Group A had 10 events.",
                "slots": {"subject": "Group A"},
                "decomposition_status": "atomic",
            }
        ],
        "completeness_note": "Group B remains to check",
    }
    judgment = {
        "judgments": [
            {
                "fact_id": "fact-1",
                "relation": "supported",
                "evidence": [{"source_id": "s", "quote": "Group A had 10 events."}],
                "explanation": "Exact count.",
            }
        ]
    }
    r = audit_atomic(item, QueueLLM(extraction, judgment))
    assert len(r["claims"][0]["answer_spans"]) == 2
    assert r["claims"][0]["status"] == "ok"
    assert (
        r["checked_coverage"]["covered_nonspace_characters"]
        < r["checked_coverage"]["total_nonspace_characters"]
    )


def test_ambiguous_extraction_never_gets_verified():
    item = AtomicAuditRequest(
        answer="A had 10. B had 10.", sources=[{"id": "s", "title": "T", "text": "A had 10."}]
    )
    extraction = {
        "facts": [
            {
                "parent_quote": item.answer,
                "answer_quotes": ["10"],
                "normalized_claim": "A had 10.",
                "slots": {},
                "decomposition_status": "atomic",
            }
        ],
        "completeness_note": "Repeated value",
    }
    r = audit_atomic(item, QueueLLM(extraction))
    assert r["claims"][0]["status"] == "invalid_reference"
    assert len(r["calls"]) == 1


def test_missing_judgment_is_unchecked_not_insufficient():
    item = AtomicAuditRequest(
        answer="A had 10.", sources=[{"id": "s", "title": "T", "text": "A had 10."}]
    )
    extraction = {
        "facts": [
            {
                "parent_quote": item.answer,
                "answer_quotes": [item.answer],
                "normalized_claim": item.answer,
                "slots": {},
                "decomposition_status": "atomic",
            }
        ],
        "completeness_note": "One fact",
    }
    r = audit_atomic(item, QueueLLM(extraction, {"judgments": []}))
    assert r["claims"][0]["relation"] is None
    assert r["summary"]["failed_or_unchecked"] == 1


def test_failure_cannot_improve_balanced_accuracy():
    entries = [
        {"case_id": "a", "group_id": "g", "relation": "contradicted"},
        {"case_id": "b", "group_id": "h", "relation": "supported"},
    ]
    r = fixed_metrics(
        entries, [{"case_id": "a", "status": "execution_error", "binary_prediction": 0}]
    )
    assert r["balanced_accuracy"] == 0
    assert r["completion"] == 0
    assert r["false_acceptance_rate"] == 0  # Must be read alongside completion/accuracy.


def test_numeric_absence_and_multi_arm_remain_unknown():
    assert (
        numeric_diagnostic(
            "A dose was 10 mg",
            [{"text": "A dose was not recorded."}],
            {"subject": "A", "outcome": "dose"},
        )["status"]
        == "unresolved"
    )
    assert (
        numeric_diagnostic(
            "A dose was 10 mg", [{"text": "A dose was 0.01 g"}], {"subject": "A", "outcome": "dose"}
        )["status"]
        == "equivalent"
    )
    assert (
        numeric_diagnostic(
            "A dose was 10 mg",
            [{"text": "A dose was 20 mg and B dose 10 mg"}],
            {"subject": "A", "outcome": "dose"},
        )["status"]
        == "unresolved"
    )
