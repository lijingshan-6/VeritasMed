"""The downloadable showcase must work without keys or retrieval services."""
import json

from fastapi.testclient import TestClient

from medrag.api.replay_app import app
from medrag.api.routes.conversations import ROOT


def test_replay_disallows_new_inference(monkeypatch):
    from medrag.api.routes import audit

    def forbidden():
        raise AssertionError("The replay must never construct a model gateway")

    monkeypatch.setattr(audit, "FlashGateway", forbidden)
    client = TestClient(app)
    response = client.post("/api/audit", json={"answer": "text", "sources": []})
    assert response.status_code == 409
    assert client.get("/api/conversations/examples/missing").status_code == 404


def test_replay_original_passage_and_adjacent_context():
    rows = [json.loads(line) for line in (ROOT / "corpus.jsonl").read_text(encoding="utf8").splitlines()]
    main = next(row for row in rows if row["chunk_idx"] == 1)
    by_id = {r["chunk_id"]: r for r in rows}
    response = TestClient(app).get("/api/chunk/" + main["chunk_id"])
    assert response.status_code == 200
    context = response.json()
    assert context["chunk"]["text"] == main["text"]
    assert context["prev_chunk"]["text"] == by_id[main["chunk_id"].rsplit(":", 1)[0] + ":0"]["text"]
    without = TestClient(app).get("/api/chunk/" + main["chunk_id"] + "?context_window=0").json()
    assert without["prev_chunk"] is None and without["next_chunk"] is None


def test_atomic_v2_api_is_distinct_and_direct_remains_default(monkeypatch):
    from fastapi import FastAPI
    from medrag.api.routes import audit

    calls = []
    monkeypatch.setattr(audit, "FlashGateway", lambda: object())
    monkeypatch.setattr(audit, "audit_atomic_v2", lambda item, gateway: calls.append("atomic_v2") or {"status": "ok"})
    monkeypatch.setattr(audit, "audit_answer", lambda item, gateway: calls.append("direct") or {"status": "ok"})
    full = FastAPI()
    full.include_router(audit.router)
    client = TestClient(full)
    body = {"answer": "An answer.", "sources": [{"id": "s", "title": "Source", "text": "Original."}]}
    assert client.post("/api/audit", json=body).status_code == 200
    assert client.post("/api/audit", json={**body, "strategy": "atomic_v2"}).status_code == 200
    assert calls == ["direct", "atomic_v2"]
