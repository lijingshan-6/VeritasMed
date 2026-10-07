"""VeritasMed as MCP tools, for Claude Desktop, Claude Code or any MCP client (local, stdio).

    audit_answer       check any answer, from any model, against the source texts you supply
    ask                answer a question from the indexed literature, with each part bound to sentences
    search_literature  return the passages the retriever finds for a query

`ask` returns its sources in the same shape `audit_answer` takes, so a client can ask and then
audit. `audit_answer` needs only the Flash endpoint in .env; `ask` and `search_literature` also need
the local index (python scripts/run_demo.py builds it). Run:

    fastmcp run src/medrag/mcp_server/server.py                       # stdio, for a client config
    fastmcp dev inspector src/medrag/mcp_server/server.py --with-editable .   # interactive inspector
"""
from __future__ import annotations

import asyncio
from threading import BoundedSemaphore
from typing import Annotated
from uuid import uuid4

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field, ValidationError

from medrag.config import load_project_env
from medrag.verification.answer_audit import AuditRequest, audit_answer as run_direct_audit

load_project_env()

mcp = FastMCP(
    "VeritasMed",
    instructions=(
        "VeritasMed checks medical answers against their sources. Use audit_answer to verify any answer "
        "(yours or another model's) against the exact source texts it relies on: every claim comes back "
        "supported, contradicted or insufficient, with the quoted evidence. Use ask for answers grounded "
        "in the indexed literature; its sources can be passed straight to audit_answer. Verdicts are model "
        "judgments about the supplied text, not clinical advice."
    ),
)
_audits = BoundedSemaphore(3)  # each audit is one paid model call; keep a runaway client in check


def _source_audit(item: AuditRequest, result: dict) -> dict:
    """Keep what a client needs to act on; drop raw model output and transport metadata."""
    sources = {s.id: s for s in item.sources}
    claims = []
    for c in result["claims"]:
        claims.append({
            "claim": c.get("quote", ""),
            "verdict": c.get("relation") if c["status"] == "ok" else "unchecked",
            "explanation": c.get("explanation", ""),
            "evidence": [{"source_id": e["source_id"], "title": sources[e["source_id"]].title, "quote": e["text"]}
                         for e in c.get("evidence", [])],
            **({"warning": c["significance_diagnostic"]["note"]} if c.get("significance_diagnostic") else {}),
            **({"problem": c.get("error_type")} if c["status"] != "ok" else {}),
        })
    uncovered = [g["text"] for g in result["checked_coverage"]["uncovered"]]
    usage = [c.get("usage") or {} for c in result["calls"]]
    return {
        "status": result["status"],
        "summary": result["summary"],
        "claims": claims,
        "unchecked_text": uncovered,
        "claims_at_cap": result["claims_at_cap"],
        "tokens": {"input": sum(u.get("input_tokens") or 0 for u in usage),
                   "output": sum(u.get("output_tokens") or 0 for u in usage)},
        "scope": result["scope"],
    }


def _gateway():
    from medrag.verification.gateway import FlashGateway
    try:
        return FlashGateway()
    except Exception as exc:  # missing key or wrong profile: say what to fix, not a stack trace
        raise ToolError("Set LLM_BACKEND=openhub, OPENHUB_API_KEY and the Flash model in .env to run audits.") from exc


def _audit_sync(answer: str, sources: list[dict], gateway=None) -> dict:
    try:
        item = AuditRequest(answer=answer, sources=sources, strategy="direct")
    except ValidationError as exc:
        raise ToolError(f"Invalid input: {exc.errors()[0]['msg']}") from exc
    if not _audits.acquire(blocking=False):
        raise ToolError("Three audits are already running; try again when one finishes.")
    try:
        return _source_audit(item, run_direct_audit(item, gateway or _gateway()))
    finally:
        _audits.release()


@mcp.tool(timeout=300, annotations={"readOnlyHint": True, "openWorldHint": True})
async def audit_answer(
    answer: Annotated[str, Field(description="The answer to check, exactly as written (up to 12,000 characters).")],
    sources: Annotated[list[dict], Field(description=(
        "The texts the answer should rest on: a list of {id, title, text}, at most 40, ids unique. "
        "Put the citation key the answer uses (for example PMID:12345) in the id or title."))],
) -> dict:
    """Check every factual claim in an answer against the supplied source texts.

    Each claim comes back as supported, contradicted or insufficient, with exact quotes from the
    sources; text no judgment covers is listed under unchecked_text. A claim that states "no
    difference" for a non-significant result carries a warning. The answer is never rewritten.
    One Flash model call, usually 20-60 seconds.
    """
    return await asyncio.to_thread(_audit_sync, answer, sources)


def _ask_sync(question: str) -> dict:
    from medrag.agent.graph import app
    from medrag.agent.invocation import build_initial_state

    final = app.invoke(build_initial_state(question), config={"configurable": {"thread_id": str(uuid4())}})
    sources = []
    for i, c in enumerate(final.get("retrieved_chunks", [])):
        payload = c.payload if hasattr(c, "payload") else c
        citation = f"PMID:{payload['pmid']}" if payload.get("pmid") else f"PMC:{payload.get('doc_id', '')}"
        title = f"{citation} · {payload.get('title', '')}"
        sources.append({"id": f"evidence-{i + 1}", "title": title, "text": f"{title}\n\n{payload.get('text', '')}"})
    parts = [{
        "asked": comp.get("requirement", ""),
        "status": comp.get("status", ""),
        "answer": comp.get("answer", ""),
        "evidence": [{"citation": e.get("citation", ""), "sentence": e.get("quote", "")} for e in comp.get("evidence", [])],
        **({"gap": comp["gap"]} if comp.get("gap") else {}),
    } for comp in final.get("answer_components", [])]
    return {
        "answer": final.get("answer", ""),
        "evidence_status": final.get("evidence_status", "insufficient"),
        "parts": parts,
        "sources": sources,
        "next": "Pass answer and sources to audit_answer to check every claim.",
    }


@mcp.tool(timeout=600, annotations={"readOnlyHint": True, "openWorldHint": True})
async def ask(
    question: Annotated[str, Field(description="A question about the indexed medical literature.")],
) -> dict:
    """Answer from the indexed literature, binding each part of the question to source sentences.

    Returns the answer, each part of the question with its status and bound sentences (or a
    reported gap when the sources do not contain it), and the passages used, formatted for
    audit_answer. Several model calls, typically one to two minutes; the first call also loads
    the retrieval models.
    """
    try:
        return await asyncio.to_thread(_ask_sync, question)
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"Ask failed ({type(exc).__name__}). Is the index built and the model endpoint set in .env?") from exc


def _search_sync(query: str, k: int) -> list[dict]:
    from medrag.agent.nodes.retrieval import _get_reranker, _get_retriever

    chunks = _get_reranker().rerank(query, _get_retriever().retrieve(query, k=20), top_k=k)
    return [{"rank": i + 1, "citation": c.citation, "title": c.payload.get("title", ""),
             "section": c.payload.get("section", ""), "text": c.text} for i, c in enumerate(chunks)]


@mcp.tool(timeout=300, annotations={"readOnlyHint": True})
async def search_literature(
    query: Annotated[str, Field(description="Search query.")],
    k: Annotated[int, Field(ge=1, le=10, description="Number of passages, 1-10.")] = 5,
) -> list[dict]:
    """Return the top passages for a query: hybrid dense + sparse retrieval, then reranking.

    No language model is called. The first call loads the retrieval models.
    """
    try:
        return await asyncio.to_thread(_search_sync, query, k)
    except Exception as exc:
        raise ToolError(f"Search failed ({type(exc).__name__}). Build the index first: python scripts/run_demo.py") from exc


def _preload_native_stack() -> None:
    """Load native libraries on the main thread before serving.

    Tools run in worker threads, and on Windows a first native import (numpy, torch) from a worker
    thread of a stdio server can deadlock. The order matters too: pyarrow before torch, and
    sentence_transformers before qdrant_client, or the process can crash. Without the retrieval
    extras installed, audit_answer still works.
    """
    try:
        import pyarrow.dataset  # noqa: F401
        import sentence_transformers  # noqa: F401
        import qdrant_client  # noqa: F401
        from FlagEmbedding.inference.embedder.encoder_only.m3 import M3Embedder  # noqa: F401
    except ImportError:
        pass


if __name__ == "__main__":
    _preload_native_stack()
    mcp.run(show_banner=False)
