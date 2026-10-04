"""Live audit API: Direct is the default, Atomic v2 is opt-in; no model in tests."""
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from medrag.api.routes import audit


def _client():
    app = FastAPI()
    app.include_router(audit.router)
    return TestClient(app)


def test_live_service_and_validation(monkeypatch):
    class FakeGateway:
        def invoke(self, _):
            return SimpleNamespace(content='{"claims": []}', usage_metadata=None, response_metadata={})
    monkeypatch.setattr(audit, "FlashGateway", FakeGateway)
    client = _client()
    response = client.post("/api/audit", json={"answer": "An answer.", "sources": [
        {"id": "s", "title": "Source", "text": "A source."}]})
    assert response.status_code == 200
    assert response.json()["mode"] == "live"
    assert response.json()["audit"]["status"] == "no_claims"
    assert client.post("/api/audit", json={"answer": "", "sources": []}).status_code == 422


def test_retired_strategies_are_rejected(monkeypatch):
    monkeypatch.setattr(audit, "FlashGateway", lambda: object())
    body = {"answer": "An answer.", "sources": [{"id": "s", "title": "Source", "text": "A source."}]}
    for strategy in ("split", "context", "quote_v2", "atomic_v1"):
        assert _client().post("/api/audit", json={**body, "strategy": strategy}).status_code == 422


def test_missing_gateway_configuration_is_explicit(monkeypatch):
    def unconfigured():
        raise KeyError("OPENHUB_MODEL")
    monkeypatch.setattr(audit, "FlashGateway", unconfigured)
    response = _client().post("/api/audit", json={"answer": "An answer.", "sources": [
        {"id": "s", "title": "Source", "text": "A source."}]})
    assert response.status_code == 503
