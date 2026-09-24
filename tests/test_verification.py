"""Small offline checks for benchmark integrity and exact evidence binding."""
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from medrag.verification.schema import Decision, EvidenceDocument, bind_evidence
from medrag.verification.scifact import adapt_pairs, select_pilot
from medrag.verification.scoring import score
from medrag.verification.verifier import prompt_payload, verify


def corpus():
    return [{"doc_id": i, "title": "Study", "abstract": ["A 😀", "B", "A 😀"]}
            for i in range(1, 8)]


def claim(i, doc, label=None, rationales=None):
    return {"id": i, "claim": "A claim", "cited_doc_ids": [doc],
            "evidence": {} if label is None else {str(doc): [
                {"label": label, "sentences": ids} for ids in (rationales or [[0]])]}}


def test_adapter_uses_cited_and_evidence_docs_without_inventing_negatives():
    row = claim(1, 1, "SUPPORT", [[0], [1, 2]])
    row["evidence"]["2"] = [{"label": "CONTRADICT", "sentences": [1]}]
    cases = adapt_pairs(corpus(), [row, claim(2, 3)], "train")
    assert [c.input.document.document_id for c in cases] == ["1", "2", "3"]
    assert [c.relation for c in cases] == ["supported", "contradicted", "insufficient"]
    assert cases[0].rationale_sets == [[0], [1, 2]]
    payload = json.loads(prompt_payload(cases[0].input))
    assert set(payload) == {"claim", "document_id", "title", "sentences"}
    assert len(payload["sentences"]) == 3  # complete abstract, not gold rationale only


def test_selection_excludes_all_related_dev_documents_and_is_deterministic():
    rows = [claim(1, 1, "SUPPORT"), claim(2, 2, "SUPPORT"),
            claim(3, 3, "CONTRADICT"), claim(4, 4), claim(5, 4)]
    rows[0]["cited_doc_ids"].append(7)
    train = adapt_pairs(corpus(), rows, "train")
    selected, stats = select_pilot(train, [claim(10, 7)], per_label=1)
    assert {c.input.document.document_id for c in selected} == {"2", "3", "4"}
    assert selected == select_pilot(train, [claim(10, 7)], per_label=1)[0]
    assert set(stats["selected_counts"].values()) == {1}


def test_binding_uses_codepoints_and_the_selected_duplicate_position():
    doc = EvidenceDocument(document_id="1", title="Study", sentences=["A 😀", "B", "A 😀"])
    decision = Decision(relation="supported", sentence_ids=[2], explanation="Text supports")
    span = bind_evidence(doc, decision)[0]
    assert span.start == 6 and span.end == 9
    assert doc.canonical_text[span.start:span.end] == span.text == "A 😀"
    assert span.document_sha256 == doc.sha256
    with pytest.raises(ValueError):
        bind_evidence(doc, decision.model_copy(update={"sentence_ids": [3]}))


@pytest.mark.parametrize("ids", [[-1], [True], [0, 0], []])
def test_invalid_evidence_ids_not_silently_fixed(ids):
    with pytest.raises(ValidationError):
        Decision(relation="supported", sentence_ids=ids, explanation="Explanation")


class StubLLM:
    def __init__(self, content):
        self.content = content

    def invoke(self, messages):
        assert "rationale_sets" not in messages[1].content
        return SimpleNamespace(content=self.content, usage_metadata=None, response_metadata={})


def test_errors_not_counted_as_insufficient_and_alternative_rationales_match():
    cases = adapt_pairs(corpus(), [claim(1, 1, "SUPPORT", [[0], [1, 2]]),
                                  claim(2, 2, "CONTRADICT"), claim(3, 3)], "train")
    good = json.dumps({"relation": "supported", "sentence_ids": [1, 2], "explanation": "Support"})
    records = [verify(cases[0].input, StubLLM(good)), verify(cases[1].input, StubLLM("not JSON"))]
    summary = score(cases, records)
    assert summary["correct"] == 1 and summary["total"] == 3
    assert summary["confusion_matrix"]["contradicted"]["error"] == 1
    assert summary["confusion_matrix"]["insufficient"]["not_run"] == 1
    assert summary["label_and_exact_rationale_match"] == {"matched": 1, "eligible": 2}
    assert summary["usage"]["reported_token_totals"] is None
    assert summary["per_class"]["contradicted"]["precision"] is None
    with pytest.raises(ValueError, match="Duplicate"):
        score(cases, records + records)


def test_unknown_source_id_is_an_error_not_an_unbound_quote():
    case = adapt_pairs(corpus(), [claim(1, 1, "SUPPORT")], "train")[0]
    result = verify(case.input, StubLLM(json.dumps({"relation": "supported",
                    "sentence_ids": [100], "explanation": "Support"})))
    assert result["status"] == "invalid_evidence_reference"
    assert result["raw_output"] is not None and result["evidence"] == []


def test_execution_errors_do_not_persist_provider_bodies():
    class FailedLLM:
        def invoke(self, messages):
            raise RuntimeError("a provider body containing a secret")
    case = adapt_pairs(corpus(), [claim(1, 1)], "train")[0]
    result = verify(case.input, FailedLLM())
    assert result["status"] == "execution_error" and result["error_type"] == "RuntimeError"
    assert "secret" not in json.dumps(result)
