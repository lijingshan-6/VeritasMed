"""MCP tools through an in-process client, with stubbed models (no network, no index)."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from medrag.mcp_server import server
from medrag.verification.answer_audit import AuditRequest

SOURCE = {"id": "s1", "title": "PMID:24625433 · Noise trial",
          "text": "There was no evidence of a difference in average noise levels (95% CI -4.0 to 0.9 dBA)."}


class Stub:
    def __init__(self, output):
        self.output = output

    def invoke(self, messages):
        return SimpleNamespace(content=json.dumps(self.output), usage_metadata={"input_tokens": 10, "output_tokens": 5},
                               response_metadata={})


def call(name, arguments):
    async def run():
        async with Client(server.mcp) as client:
            return await client.call_tool(name, arguments)
    return asyncio.run(run())


def test_exposes_three_tools():
    async def names():
        async with Client(server.mcp) as client:
            return sorted(t.name for t in await client.list_tools())
    assert asyncio.run(names()) == ["ask", "audit_answer", "search_literature"]


def test_audit_returns_verdicts_quotes_and_the_significance_warning(monkeypatch):
    answer = "HFNC were not noisier than CPAP."
    monkeypatch.setattr(server, "_gateway", lambda: Stub({"claims": [{
        "quote": answer, "occurrence": 0, "relation": "supported", "explanation": "Same finding.",
        "evidence": [{"source_id": "s1", "quote": "There was no evidence of a difference in average noise levels",
                      "occurrence": 0}]}]}))
    out = call("audit_answer", {"answer": answer, "sources": [SOURCE]}).structured_content
    claim = out["claims"][0]
    assert claim["verdict"] == "supported" and claim["evidence"][0]["title"] == SOURCE["title"]
    assert "non-significant" in claim["warning"]
    assert out["summary"]["nonsignificance_flags"] == 1 and out["tokens"] == {"input": 10, "output": 5}
    assert "raw_output" not in json.dumps(out)


def test_audit_rejects_bad_input_with_a_readable_error():
    with pytest.raises(ToolError, match="Invalid input"):
        call("audit_answer", {"answer": "A.", "sources": [SOURCE, SOURCE]})


def test_ask_sources_can_be_passed_straight_to_audit(monkeypatch):
    from medrag.agent import graph

    chunk = SimpleNamespace(payload={"pmid": "24625433", "title": "Noise trial", "text": SOURCE["text"]})
    final = {"answer": "No difference was shown [PMID:24625433].", "evidence_status": "complete",
             "retrieved_chunks": [chunk],
             "answer_components": [{"requirement": "noise", "status": "supported", "answer": "No difference was shown.",
                                    "evidence": [{"citation": "PMID:24625433", "quote": SOURCE["text"]}], "gap": ""}]}
    monkeypatch.setattr(graph, "app", SimpleNamespace(invoke=lambda state, config: final))
    out = call("ask", {"question": "Is HFNC noisier than CPAP?"}).structured_content
    assert out["parts"][0]["evidence"][0]["citation"] == "PMID:24625433" and "gap" not in out["parts"][0]
    AuditRequest(answer=out["answer"], sources=out["sources"])  # the audit accepts them unchanged
    assert out["sources"][0]["text"].startswith("PMID:24625433 · Noise trial")
