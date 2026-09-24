"""Offline guards on constructed-source views and the ablatable reducer."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from medrag.verification.diagnostics import load_diagnostics
from medrag.verification.schema import EvidenceDocument, VerificationInput
from medrag.verification.structured import ComponentCheck, reduce_checks, verify_structured
from medrag.verification.verifier import prompt_payload


def check(relation, ids):
    return ComponentCheck(component="count", relation=relation, sentence_ids=ids, explanation="Test")


def test_reducer_never_marks_missing_or_conflicting_components_supported():
    assert reduce_checks([check("supported", [0]), check("insufficient", [])]).relation == "insufficient"
    decision = reduce_checks([check("supported", [0]), check("contradicted", [1])])
    assert decision.relation == "contradicted" and decision.sentence_ids == [1]
    assert reduce_checks([check("supported", [0]), check("supported", [2])]).sentence_ids == [0, 2]


def test_structured_preserves_model_decision_for_same_output_ablation():
    class Stub:
        def invoke(self, messages):
            return SimpleNamespace(content=json.dumps({"relation": "supported", "sentence_ids": [0],
                "explanation": "Model final", "checks": [check("insufficient", []).model_dump()]}),
                usage_metadata=None, response_metadata={"model": "stub"})
    item = VerificationInput(case_id="a", claim="Count is 12", document=EvidenceDocument(
        document_id="d", title="Study", sentences=["Some participants."]))
    result = verify_structured(item, Stub(), "structured")
    assert result["status"] == "ok"
    assert result["decision"]["relation"] == "insufficient"
    assert result["model_decision"]["relation"] == "supported"
    assert result["evidence"] == [] and len(result["model_evidence"]) == 1


def test_diagnostic_view_ids_are_mapped_without_label_leakage(tmp_path, monkeypatch):
    import medrag.verification.diagnostics as module
    corpus = [{"doc_id": 1, "title": "Study", "abstract": ["12 people enrolled.", "Background.", "Another fact."]}]
    train = [{"cited_doc_ids": [1], "evidence": {}}]
    monkeypatch.setattr(module, "read_jsonl", lambda p: corpus if p.name == "corpus.jsonl" else train if p.name == "claims_train.jsonl" else [])
    monkeypatch.setattr(module, "prepare_pilot", lambda p: ([], {}))
    specification = {"label_provenance": "constructed", "families": [{
        "family_id": "f", "document_id": "1", "category": "count", "anchor_sentence_ids": [0],
        "withheld_sentence_ids": [0], "control_removed_sentence_ids": [1],
        "claims": {"supported": "12 enrolled", "equivalent": "Twelve enrolled", "contradicted": "13 enrolled"}}]}
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(specification))
    cases, manifest = load_diagnostics(Path("unused"), path)
    assert len(cases) == 4
    assert [c.relation for c in cases] == ["supported", "supported", "contradicted", "insufficient"]
    assert cases[-1].input.claim == cases[0].input.claim
    assert len({len(c.input.document.sentences) for c in cases}) == 1
    assert manifest["cases"][-1]["original_sentence_ids"] == [1, 2]
    for c in cases:
        assert "label_provenance" not in prompt_payload(c.input)
        assert "rationale_sets" not in prompt_payload(c.input)
        assert "case_id" not in prompt_payload(c.input)
    specification["families"][0]["control_removed_sentence_ids"] = [0]
    path.write_text(json.dumps(specification))
    with pytest.raises(ValueError, match="Anchor"):
        load_diagnostics(Path("unused"), path)


def test_raw_gateway_preserves_mixed_models_and_terminal_usage():
    from medrag.verification.gateway import FlashGateway
    from langchain_core.messages import HumanMessage

    chunks = [SimpleNamespace(model="flash-a", usage=None, choices=[SimpleNamespace(
        delta=SimpleNamespace(content="{}", reasoning_content=None), finish_reason=None)]),
        SimpleNamespace(model="flash-b", usage=SimpleNamespace(prompt_tokens=12, completion_tokens=4, total_tokens=16),
                        choices=[SimpleNamespace(delta=None, finish_reason="stop")])]

    class Stream:
        def __enter__(self):
            return iter(chunks)

        def __exit__(self, *args):
            pass

    gateway = FlashGateway.__new__(FlashGateway)
    gateway.model = "flash"
    gateway.settings = {"reasoning_effort": "high", "max_tokens": 100}
    gateway.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: Stream())))
    response = gateway.invoke([HumanMessage(content="Test")])
    assert response.response_metadata["model_identifiers"] == ["flash-a", "flash-b"]
    assert response.response_metadata["model"] is None
    assert response.usage_metadata["total_tokens"] == 16
    chunks[:] = chunks[:1]
    assert gateway.invoke([HumanMessage(content="Test")]).usage_metadata is None
