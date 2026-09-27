"""MCP must not inherit answers or additive state from another public call."""
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from medrag.agent.state import AgentState


def test_mcp_repeated_label_starts_with_fresh_graph_state(monkeypatch):
    from medrag.agent import graph
    from medrag.mcp_server.server import _ask_agent_sync, _UsageAccumulator

    received = []

    def answer(state):
        received.append(state)
        return {"answer": state["query"], "history": [{"query": state["query"]}],
                "rewritten_queries": ["old rewrite"], "repair_history": [{"old": True}]}

    builder = StateGraph(AgentState)
    builder.add_node("answer", answer)
    builder.add_edge(START, "answer")
    builder.add_edge("answer", END)
    monkeypatch.setattr(graph, "app", builder.compile(checkpointer=InMemorySaver()))
    first = _ask_agent_sync("first", "default", _UsageAccumulator())
    second = _ask_agent_sync("second", "default", _UsageAccumulator())
    assert (first["answer"], second["answer"]) == ("first", "second")
    assert received[1]["history"] == []
    assert received[1]["rewritten_queries"] == []
    assert received[1]["repair_history"] == []


def test_visual_stub_logs_rejected_authentication(monkeypatch):
    import pytest
    from medrag.mcp_server import server

    records = []
    monkeypatch.setenv("MEDRAG_LOCAL_TOKEN", "test-only-token")
    monkeypatch.setattr(server, "log_tool_call", lambda *args, **kwargs: records.append(args))
    with pytest.raises(server.AuthError):
        server.search_visual("sample", token="wrong")
    assert len(records) == 1
    assert records[0][0:3] == ("search_visual", "sample", "rejected:AuthError")
