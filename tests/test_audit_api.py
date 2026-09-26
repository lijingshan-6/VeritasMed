"""The small audit service works without loading the retrieval stack."""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from medrag.api.audit_app import app
from medrag.api.routes import audit
from medrag.verification.answer_audit import AuditInput, audit_answer


def test_live_service_and_validation(monkeypatch):
    class FakeGateway:
        def invoke(self, _):
            return SimpleNamespace(content='{"claims": []}', usage_metadata=None, response_metadata={})
    monkeypatch.setattr(audit, "FlashGateway", FakeGateway)
    client = TestClient(app)
    response = client.post("/api/audit", json={"answer": "An answer.", "sources": [
        {"id": "s", "title": "Source", "text": "A source."}]})
    assert response.status_code == 200
    assert response.json()["mode"] == "live"
    assert response.json()["audit"]["status"] == "no_claims"
    assert client.post("/api/audit", json={"answer": "", "sources": []}).status_code == 422


def test_replay_checks_inputs_and_never_calls_model(monkeypatch):
    item = AuditInput(answer="An answer.", sources=[{"id": "s", "title": "Source", "text": "A source."}])
    class Empty:
        def invoke(self, _):
            return SimpleNamespace(content='{"claims": []}', usage_metadata=None, response_metadata={})
    result = audit_answer(item, Empty())
    monkeypatch.setattr(audit, "saved_rows", lambda: [{"case_id": "1", "strategy": "direct", "audit": result}])
    monkeypatch.setattr(audit, "saved_cases", lambda: {"1": {"input": item}})
    def forbidden():
        raise AssertionError("Replay must not call a model")
    monkeypatch.setattr(audit, "FlashGateway", forbidden)
    client = TestClient(app)
    response = client.get("/api/audit/examples/1")
    assert response.status_code == 200 and response.json()["mode"] == "saved"
    assert client.get("/api/audit/examples/1?strategy=split").status_code == 404
    result["answer_sha256"] = "modified"
    assert client.get("/api/audit/examples/1").status_code == 409


def test_context_api_keeps_all_ask_passages_and_separates_meta(monkeypatch):
    import json

    class FakeGateway:
        def invoke(self, messages):
            payload = json.loads(messages[1].content)
            assert len(payload["sources"]) == 8
            assert payload["answer_contexts"][0]["text"] == "Here is a summary."
            return SimpleNamespace(content=json.dumps({"claims": [], "meta_text": [{
                "quote": "Here is a summary.", "occurrence": 0, "kind": "introduction", "explanation": "Introduction."}]}),
                usage_metadata=None, response_metadata={})
    monkeypatch.setattr(audit, "FlashGateway", FakeGateway)
    payload = {"answer": "Here is a summary.", "strategy": "context", "sources": [
        {"id": str(i), "title": "Source", "text": f"Passage {i}."} for i in range(8)]}
    response = TestClient(app).post("/api/audit", json=payload)
    assert response.status_code == 200
    assert response.json()["input"] == payload
    assert response.json()["audit"]["summary"]["supported"] == 0
    assert response.json()["audit"]["meta_text"][0]["status"] == "not_source_checked"


def test_quote_api_returns_ambiguity_without_accepting_supported_claim(monkeypatch):
    import json

    class FakeGateway:
        def invoke(self, _):
            return SimpleNamespace(content=json.dumps({"claims": [{"quote": "A.", "relation": "supported",
                "evidence": [{"source_id": "s", "quote": "A."}], "explanation": "Same text."}], "meta_text": []}),
                usage_metadata=None, response_metadata={})
    monkeypatch.setattr(audit, "FlashGateway", FakeGateway)
    response = TestClient(app).post("/api/audit", json={"answer": "A. A.", "strategy": "quote_v2",
        "sources": [{"id": "s", "title": "Source", "text": "A."}]})
    assert response.status_code == 200
    result = response.json()["audit"]
    assert result["status"] == "partial_error" and result["summary"]["supported"] == 0
    assert result["claims"][0]["bindings"]["answer"]["match_count"] == 2


def test_bundled_medical_replay_without_cache_or_model(monkeypatch, tmp_path):
    import json

    def forbidden(*args, **kwargs):
        raise AssertionError("Medical replay must not download research data or invoke a model")
    monkeypatch.setattr(audit, "CACHE", tmp_path)
    monkeypatch.setattr(audit, "prepare", forbidden)
    monkeypatch.setattr(audit, "FlashGateway", forbidden)
    client = TestClient(app)
    catalogue = client.get("/api/audit/examples").json()
    assert catalogue["sources_downloaded"] is False
    assert catalogue["examples"][0]["id"] == "medical-grade"
    response = client.get("/api/audit/examples/medical-grade")
    assert response.status_code == 200
    record = response.json()
    assert record["mode"] == "saved"
    assert "Single-paper" in record["provenance"]["note"]
    events = json.loads((audit.MEDICAL.parent / "ask-events.json").read_text(encoding="utf8"))
    original = next(e["data"] for e in events if e["event"] == "done")
    assert record["input"]["answer"] == original["answer"]
    assert [s["text"] for s in record["input"]["sources"]] == [c["text"] for c in original["chunks"]]
    corpus = {r["chunk_id"]: r for r in audit.read_jsonl(audit.MEDICAL.parent / "corpus.jsonl")}
    for chunk in original["chunks"]:
        assert chunk["text"] == corpus[chunk["chunk_id"]]["text"]
    for claim in record["audit"]["claims"]:
        if claim["answer_span"]:
            span = claim["answer_span"]
            assert record["input"]["answer"][span["start"]:span["end"]] == span["text"]
        for span in claim["evidence"]:
            source = next(s for s in record["input"]["sources"] if s["id"] == span["source_id"])
            assert source["text"][span["start"]:span["end"]] == span["text"]
    assert client.get("/api/audit/examples/medical-grade?strategy=split").status_code == 404
