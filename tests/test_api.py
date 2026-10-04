"""API behavior with local graphs and controlled dependency responses."""

import asyncio
import threading
import time

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from starlette.websockets import WebSocketDisconnect
from typing_extensions import TypedDict

from medrag.agent.state import AgentState
from medrag.api.models import AskRequest
from medrag.api.routes import ask, corpus


class State(TypedDict, total=False):
    query: str
    answer: str
    citations: list[str]


def _graph(node):
    graph = StateGraph(State)
    graph.add_node("generate", node)
    graph.add_edge(START, "generate")
    graph.add_edge("generate", END)
    return graph.compile(checkpointer=InMemorySaver())


def _client(router):
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _events(ws):
    events = []
    try:
        while True:
            events.append(ws.receive_json())
    except WebSocketDisconnect:
        return events


def test_worker_exception_sends_error_without_done(monkeypatch):
    def fail(_state):
        raise RuntimeError("private upstream token")

    monkeypatch.setattr(ask, "langgraph_app", _graph(fail))
    with _client(ask.router).websocket_connect("/api/ask") as ws:
        ws.send_json({"query": "question", "thread_id": "failure"})
        events = _events(ws)

    assert [e["event"] for e in events if e["event"] in ("error", "done")] == ["error"]
    assert "private upstream token" not in str(events)


def test_context_resolution_runs_before_fresh_graph_and_is_returned(monkeypatch):
    from medrag.agent.conversation import ContextResolution

    received = []
    def resolve(query, context, omitted):
        assert context[0].turn_id == "t1"
        return ContextResolution(original_query=query, resolved_query=query + " Study A",
            supplied_turn_ids=["t1"], context_turn_ids=["t1"], status="follow_up")

    def generate(state):
        received.append(state["query"])
        return {"answer": "New answer from fresh retrieval", "citations": []}

    monkeypatch.setattr(ask, "resolve_context", resolve)
    monkeypatch.setattr(ask, "langgraph_app", _graph(generate))
    with _client(ask.router).websocket_connect("/api/ask") as ws:
        ws.send_json({"query": "Its sample?", "context": [{"turn_id": "t1", "revision_id": "r1", "question": "Study A?", "answer": "OLD ANSWER IS NOT EVIDENCE"}]})
        events = _events(ws)
    assert received == ["Its sample? Study A"]
    assert events[0] == {"event": "node_start", "node": "resolve_context"}
    assert events[-1]["data"]["conversation_context"]["context_turn_ids"] == ["t1"]
    assert events[-1]["data"]["chunks"] == []


def test_clarification_does_not_run_retrieval_or_claim_faithfulness(monkeypatch):
    from medrag.agent.conversation import ContextResolution

    monkeypatch.setattr(ask, "resolve_context", lambda *args: ContextResolution(
        original_query="Its sample?", resolved_query="", needs_clarification=True,
        clarification="Which study?", status="clarify"))
    def forbidden(_state):
        raise AssertionError("Must not generate before intent is clear")
    monkeypatch.setattr(ask, "langgraph_app", _graph(forbidden))
    with _client(ask.router).websocket_connect("/api/ask") as ws:
        ws.send_json({"query": "Its sample?"})
        events = _events(ws)
    assert [e["event"] for e in events] == ["done"]
    result = events[0]["data"]
    assert result["answer"] == "Which study?"
    assert result["faithful"] is False and result["chunks"] == []


def test_timeout_sends_error_without_done(monkeypatch):
    def slow(_state):
        time.sleep(0.2)
        return {"answer": "late"}

    monkeypatch.setattr(ask, "langgraph_app", _graph(slow))
    monkeypatch.setattr(ask, "_STREAM_TIMEOUT_S", 0.05, raising=False)
    with _client(ask.router).websocket_connect("/api/ask") as ws:
        ws.send_json({"query": "question", "thread_id": "timeout"})
        events = _events(ws)

    assert [e["event"] for e in events if e["event"] in ("error", "done")] == ["error"]


def test_real_node_start_arrives_before_node_completes(monkeypatch):
    release = threading.Event()

    def waiting(_state):
        release.wait(timeout=2)
        return {"answer": "answer", "citations": []}

    monkeypatch.setattr(ask, "langgraph_app", _graph(waiting))
    with _client(ask.router).websocket_connect("/api/ask") as ws:
        ws.send_json({"query": "question", "thread_id": "starts"})
        first = ws.receive_json()
        assert first == {"event": "node_start", "node": "generate"}
        assert not release.is_set()
        release.set()
        events = _events(ws)

    assert [e["event"] for e in events] == ["node_end", "done"]


def test_disconnect_stops_before_next_node(monkeypatch):
    release = threading.Event()
    first_finished = threading.Event()
    next_started = threading.Event()

    def first(_state):
        release.wait(timeout=2)
        first_finished.set()
        return {"answer": "partial"}

    def second(_state):
        next_started.set()
        return {"answer": "should not run"}

    graph = StateGraph(State)
    graph.add_node("generate", first)
    graph.add_node("check", second)
    graph.add_edge(START, "generate")
    graph.add_edge("generate", "check")
    graph.add_edge("check", END)
    monkeypatch.setattr(ask, "langgraph_app", graph.compile(checkpointer=InMemorySaver()))
    with _client(ask.router).websocket_connect("/api/ask") as ws:
        ws.send_json({"query": "question", "thread_id": "disconnect"})
        assert ws.receive_json()["event"] == "node_start"
        ws.close()
        time.sleep(0.05)
        release.set()

    assert first_finished.wait(timeout=2)
    assert not next_started.wait(timeout=0.1)


def test_repeated_public_thread_starts_without_prior_rewrites(monkeypatch):
    def answer(state):
        rewrites = ["old query rewrite"] if state["query"] == "first" else []
        return {"answer": state["query"], "rewritten_queries": rewrites}

    graph = StateGraph(AgentState)
    graph.add_node("generate", answer)
    graph.add_edge(START, "generate")
    graph.add_edge("generate", END)
    monkeypatch.setattr(ask, "langgraph_app", graph.compile(checkpointer=InMemorySaver()))

    with _client(ask.router).websocket_connect("/api/ask") as ws:
        ws.send_json({"query": "first", "thread_id": "shared-ui-thread"})
        first = _events(ws)[-1]["data"]
    with _client(ask.router).websocket_connect("/api/ask") as ws:
        ws.send_json({"query": "second", "thread_id": "shared-ui-thread"})
        second = _events(ws)[-1]["data"]

    assert first["rewritten_queries"] == ["old query rewrite"]
    assert second["answer"] == "second"
    assert second["rewritten_queries"] == []
    assert second["thread_id"] == "shared-ui-thread"


def test_concurrent_public_thread_requests_keep_their_own_answers(monkeypatch):
    graph = _graph(lambda state: {"answer": state["query"]})
    real_get_state = graph.get_state
    first_read_waiting = threading.Event()
    release_first_read = threading.Event()
    read_lock = threading.Lock()
    reads = 0

    def gated_get_state(config):
        nonlocal reads
        with read_lock:
            reads += 1
            first_read = reads == 1
        if first_read:
            first_read_waiting.set()
            release_first_read.wait(timeout=3)
        return real_get_state(config)

    monkeypatch.setattr(graph, "get_state", gated_get_state)
    monkeypatch.setattr(ask, "langgraph_app", graph)

    with _client(ask.router).websocket_connect("/api/ask") as first_ws:
        first_ws.send_json({"query": "request A", "thread_id": "shared"})
        assert first_ws.receive_json()["event"] == "node_start"
        assert first_ws.receive_json()["event"] == "node_end"
        assert first_read_waiting.wait(timeout=3)
        try:
            with _client(ask.router).websocket_connect("/api/ask") as second_ws:
                second_ws.send_json({"query": "request B", "thread_id": "shared"})
                second_events = _events(second_ws)
        finally:
            release_first_read.set()
        first_events = _events(first_ws)

    assert second_events[-1]["data"]["answer"] == "request B"
    assert first_events[-1]["data"]["answer"] == "request A"
    assert first_events[-1]["data"]["thread_id"] == "shared"


def test_health_401_is_degraded(monkeypatch):
    class Qdrant:
        def get_collection(self, _name):
            return object()

    async def responder(_request):
        return httpx.Response(401)

    monkeypatch.setattr(corpus, "get_qdrant", lambda: Qdrant())
    monkeypatch.setenv("LLM_BACKEND", "openhub")
    monkeypatch.setenv("OPENHUB_BASE_URL", "https://example.invalid/v1")
    client_class = httpx.AsyncClient
    monkeypatch.setattr(corpus.httpx, "AsyncClient", lambda **kwargs: client_class(transport=httpx.MockTransport(responder)))

    result = asyncio.run(corpus.health())
    assert result.llm == "disconnected"
    assert result.status == "degraded"


def test_health_uses_selected_ollama_host(monkeypatch):
    seen = []

    class Qdrant:
        def get_collection(self, _name):
            return object()

    async def responder(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"models": []})

    monkeypatch.setattr(corpus, "get_qdrant", lambda: Qdrant())
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:12345")
    client_class = httpx.AsyncClient
    monkeypatch.setattr(corpus.httpx, "AsyncClient", lambda **kwargs: client_class(transport=httpx.MockTransport(responder)))

    result = asyncio.run(corpus.health())
    assert result.llm == "connected"
    assert result.status == "ok"
    assert seen == ["http://127.0.0.1:12345/api/tags"]


def test_liveness_does_not_depend_on_external_services(monkeypatch):
    monkeypatch.setattr(corpus, "get_qdrant", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    response = _client(corpus.router).get("/api/live")
    assert response.status_code == 200


def test_full_app_exposes_only_current_routes():
    from medrag.api.app import app

    paths = set(app.openapi()["paths"])
    assert {"/api/audit", "/api/chunk/{chunk_id}", "/api/document/{citation}",
            "/api/conversations/examples", "/api/health"} <= paths
    assert not any(p.startswith(("/api/search", "/api/history", "/api/research", "/api/audit/examples")) for p in paths)
