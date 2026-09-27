"""MedRAG-Agent MCP Server (Week 5 — LangGraph + Security).

Tools exposed to Claude Desktop / Claude Code:
  1. search_literature   — hybrid retrieval (P2/P3), returns document snippets
  2. ask_agent           — full LangGraph agentic loop with rewrite + faithfulness check
  3. evaluate_query      — grade how well a set of chunks answers a query (no generation)
  4. search_visual       — stub for future visual / image search capability

Request controls (MCP only, not the web API):
  1. auth            — MEDRAG_LOCAL_TOKEN env var (disabled if not set → dev mode)
  2. rate_limit      — 30 rpm global, 10 rpm for ask_agent
  3. pii             — pattern-based query redaction before retrieval
  4. injection_guard — pattern detection / query wrapping, not complete protection
  Audit logging wraps execution: query hash, outcome and timing; not raw query text.

Run for local development (FastMCP 3.x — use fastmcp CLI, not mcp CLI):
    fastmcp dev inspector src/medrag/mcp_server/server.py --with-editable .

Install into Claude Desktop (run once):
    fastmcp install claude-desktop src/medrag/mcp_server/server.py --name MedRAG-Agent --with-editable .
"""
from __future__ import annotations

# Windows + CUDA: preload pyarrow before torch to avoid access violation (0xC0000005)
import pyarrow.dataset  # noqa: F401

import asyncio
import contextlib
import io
import logging
import sys
import threading
import time
from typing import Any
from uuid import uuid4

# Force UTF-8 for Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from fastmcp import Context, FastMCP
from langchain_core.callbacks import BaseCallbackHandler

from medrag.config import load_project_env

load_project_env()

from medrag.agent.nodes.retrieval import _get_retriever, _get_reranker
from medrag.agent.invocation import build_initial_state
from medrag.mcp_server.security import (
    AuthError,
    InjectionGuardError,
    RateLimitError,
    check_rate_limit,
    log_tool_call,
    sanitise_query,
    verify_token,
)

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ── Token usage accumulator (LangChain callback) ───────────────────────────────

class _UsageAccumulator(BaseCallbackHandler):
    """Lightweight LangChain callback that sums prompt/completion tokens.

    Works with both ChatOpenAI (OpenAI-compatible) and ChatOllama responses.
    Pass an instance via config["callbacks"] when calling app.invoke().
    """

    raise_error: bool = False

    def __init__(self) -> None:
        super().__init__()
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0

    # LangChain v0.1+ interface
    def on_llm_end(self, response, **kwargs) -> None:  # type: ignore[override]
        try:
            for gen_list in response.generations:
                for gen in gen_list:
                    # ChatOpenAI stores usage in generation_info
                    info = getattr(gen, "generation_info", {}) or {}
                    usage = info.get("usage", {}) or {}
                    self.prompt_tokens     += usage.get("prompt_tokens", 0)
                    self.completion_tokens += usage.get("completion_tokens", 0)
            # Also try llm_output (older format)
            llm_out = getattr(response, "llm_output", {}) or {}
            token_usage = llm_out.get("token_usage", {}) or {}
            if token_usage:
                self.prompt_tokens     += token_usage.get("prompt_tokens", 0)
                self.completion_tokens += token_usage.get("completion_tokens", 0)
        except Exception:
            pass  # never let logging break the pipeline

    # Required stub so LangChain doesn't complain
    def on_llm_start(self, *args, **kwargs) -> None:  # noqa: D401
        pass

    def on_llm_error(self, *args, **kwargs) -> None:
        pass


# ── Security helpers ───────────────────────────────────────────────────────────

def _security_check(query: str, token: str, is_generate: bool = False) -> str:
    """Run auth → rate_limit → pii_redact → injection_guard; return sanitised query.

    Pattern-based redaction happens before retrieval or generation. It can miss
    identifying text and is not a privacy/compliance guarantee. The audit log
    hashes the original query (caller's responsibility) for correlation.

    Raises AuthError, RateLimitError, or InjectionGuardError on violation.
    """
    from medrag.mcp_server.security.pii import redact
    verify_token(token)
    check_rate_limit(is_generate=is_generate)
    return sanitise_query(redact(query))


@contextlib.contextmanager
def _audit_tool(name: str, query: str, success_status: str = "ok"):
    """Context manager: measures latency and calls log_tool_call on exit."""
    t0 = time.perf_counter()
    status = success_status
    try:
        yield
    except (AuthError, RateLimitError, InjectionGuardError) as exc:
        status = f"rejected:{type(exc).__name__}"
        raise
    except Exception as exc:
        status = f"error:{type(exc).__name__}"
        raise
    finally:
        log_tool_call(name, query, status, (time.perf_counter() - t0) * 1000)


# ── MCP server ─────────────────────────────────────────────────────────────────

mcp = FastMCP(
    "MedRAG-Agent",
    instructions=(
        "MedRAG-Agent provides retrieval-augmented QA over a PubMed/PMC medical corpus. "
        "Tools: "
        "'search_literature' — retrieve relevant document snippets (fast, P2/P3); "
        "'ask_agent' — full agentic loop: retrieves, grades, rewrites if needed, "
        "generates a grounded answer with inline citations and faithfulness check; "
        "'evaluate_query' — grade how well given context answers a query; "
        "'search_visual' — stub for image/figure search (not yet implemented). "
        "All tools require MEDRAG_LOCAL_TOKEN if set in server environment."
    ),
)


async def _report_progress(
    ctx: Context | None,
    progress: float,
    total: float,
    message: str,
) -> None:
    if ctx is not None:
        await ctx.report_progress(progress, total, message)


def _search_literature_sync(
    sanitised: str,
    k: int,
    rerank: bool,
) -> list[dict]:
    retriever = _get_retriever()
    chunks = retriever.retrieve(sanitised, k=20 if rerank else k)
    if rerank and chunks:
        chunks = _get_reranker().rerank(sanitised, chunks, top_k=k)
    else:
        chunks = chunks[:k]
    return [
        {
            "rank": i + 1,
            "citation": c.citation,
            "score": round(float(c.score), 4),
            "snippet": c.text[:500],
            "source": c.payload.get("source", ""),
            "doc_id": c.payload.get("doc_id", ""),
        }
        for i, c in enumerate(chunks)
    ]


@mcp.tool(timeout=600)
async def search_literature(
    query: str,
    k: int = 5,
    rerank: bool = True,
    token: str = "",
    ctx: Context | None = None,
) -> list[dict]:
    """Retrieve top-k relevant medical document chunks from PubMed/PMC.

    Performs hybrid dense+sparse RRF retrieval (P2), optionally followed
    by BGE cross-encoder reranking (P3 quality).

    First call loads BGE models (GPU ~30–90s, CPU much longer). Inspector users:
    set Configuration → Maximum Total Timeout to 300000 (5 min), or uncheck
    rerank for a faster smoke test.

    Args:
        query: Medical question or search query.
        k: Number of documents to return (1–10, default 5).
        rerank: If True (default), apply cross-encoder reranking for highest precision.
        token: Optional auth token (MEDRAG_LOCAL_TOKEN).

    Returns:
        List of dicts: rank, citation, score, snippet (500 chars), source, doc_id.
    """
    with _audit_tool("search_literature", query):
        await _report_progress(ctx, 5, 100, "Validating request…")
        sanitised = _security_check(query, token, is_generate=False)
        k = max(1, min(k, 10))

        await _report_progress(
            ctx, 15, 100,
            "Loading BGE embedder (first run can take 1–2 min; see terminal logs)…",
        )
        await _report_progress(ctx, 45, 100, "Searching Qdrant…")
        if rerank:
            await _report_progress(ctx, 70, 100, "Reranking with cross-encoder…")

        result = await asyncio.to_thread(_search_literature_sync, sanitised, k, rerank)
        await _report_progress(ctx, 100, 100, "Done")
        return result


def _ask_agent_sync(
    sanitised: str,
    thread_id: str,
    usage: _UsageAccumulator,
) -> dict:
    from medrag.agent.graph import app

    config = {
        "configurable": {"thread_id": str(uuid4())},
        "metadata": {"public_thread_id": thread_id},
        "callbacks": [usage],
    }
    result = app.invoke(build_initial_state(sanitised), config=config)
    return {
        "answer": result.get("answer", ""),
        "evidence_status": result.get("evidence_status", "insufficient"),
        "evidence_gap": result.get("evidence_gap", ""),
        "answer_components": result.get("answer_components", []),
        "citations": result.get("citations", []),
        "confidence": result.get("confidence", 0.0),
        "faithful": result.get("faithful", False),
        "faithfulness_issues": result.get("faithfulness_issues", ""),
        "iterations": result.get("iterations", 0),
        "regen_count": result.get("regen_count", 0),
    }


async def _run_with_progress_heartbeat(
    ctx: Context | None,
    fn,
    *args,
    message: str = "Agent running (retrieve → grade → generate)…",
):
    """Run blocking agent work in a thread; pulse progress so Inspector resets timeouts."""

    if ctx is None:
        return await asyncio.to_thread(fn, *args)

    done = asyncio.Event()
    result: list[Any] = []
    error: list[BaseException] = []

    async def heartbeat() -> None:
        progress = 10.0
        while not done.is_set():
            await ctx.report_progress(progress, 100, message)
            progress = min(progress + 8.0, 92.0)
            try:
                await asyncio.wait_for(done.wait(), timeout=12.0)
            except asyncio.TimeoutError:
                continue

    async def worker() -> None:
        try:
            result.append(await asyncio.to_thread(fn, *args))
        except BaseException as exc:
            error.append(exc)
        finally:
            done.set()

    await asyncio.gather(heartbeat(), worker())
    if error:
        raise error[0]
    return result[0]


@mcp.tool(timeout=600)
async def ask_agent(
    query: str,
    thread_id: str = "default",
    token: str = "",
    ctx: Context | None = None,
) -> dict:
    """Answer a medical question using the full LangGraph agentic loop.

    Typical runtime: 1–3 min (several LLM + reranker calls). MCP Inspector: set
    Configuration → Maximum Total Timeout to 300000+ and keep
    Reset Timeout on Progress enabled.

    Args:
        query: Medical question to answer.
        thread_id: Caller label for tracing (default: "default"). Each call is
            isolated; this does not supply conversation history. Use web Ask
            for bounded contextual follow-ups.
        token: Optional auth token (MEDRAG_LOCAL_TOKEN).

    Returns:
        Dict with keys: answer, citations, confidence, faithful, faithfulness_issues,
        iterations (rewrites performed), regen_count.
    """
    t0 = time.perf_counter()
    status = "ok"
    usage: _UsageAccumulator | None = None
    try:
        await _report_progress(ctx, 5, 100, "Validating request…")
        sanitised = _security_check(query, token, is_generate=True)
        usage = _UsageAccumulator()
        await _report_progress(
            ctx, 10, 100,
            "Starting agent (route → retrieve → rerank → grade → generate)…",
        )
        out = await _run_with_progress_heartbeat(
            ctx,
            _ask_agent_sync,
            sanitised,
            thread_id,
            usage,
        )
        await _report_progress(ctx, 100, 100, "Done")
        return out
    except (AuthError, RateLimitError, InjectionGuardError) as exc:
        status = f"rejected:{type(exc).__name__}"
        raise
    except Exception as exc:
        status = f"error:{type(exc).__name__}"
        raise
    finally:
        pt = usage.prompt_tokens if usage else None
        ct = usage.completion_tokens if usage else None
        log_tool_call(
            "ask_agent", query, status,
            (time.perf_counter() - t0) * 1000,
            prompt_tokens=pt or None,
            completion_tokens=ct or None,
        )


@mcp.tool()
def evaluate_query(
    query: str,
    context_chunks: list[str],
    token: str = "",
) -> dict:
    """Grade whether provided context chunks can fully answer a query.

    Useful for debugging retrieval quality or testing custom contexts.
    Uses the same LLM grader as the agentic loop (thinking mode ON).

    Args:
        query: The medical question to evaluate against.
        context_chunks: List of document text strings to evaluate.
        token: Optional auth token (MEDRAG_LOCAL_TOKEN).

    Returns:
        Dict: relevant (bool), score (0–1), reason (str), rewrite_hint (str).
    """
    with _audit_tool("evaluate_query", query):
        sanitised = _security_check(query, token, is_generate=False)

        from medrag.agent.nodes import grade_relevance
        from medrag.retrieval.retriever import RetrievedChunk

        # Wrap plain strings as minimal RetrievedChunk objects
        chunks = [
            RetrievedChunk(
                chunk_id=f"user-{i}",
                text=c,
                score=1.0,
                payload={"source": "user", "doc_id": f"user-{i}"},
            )
            for i, c in enumerate(context_chunks[:10])  # cap at 10
        ]

        # Build minimal state for the grade node
        state = {
            "query": sanitised,
            "original_query": sanitised,
            "retrieved_chunks": chunks,
            "relevance_score": 0.0,
            "relevant": False,
            "grade_reason": "",
            "rewrite_hint": "",
            "query_type": "",       # defaults to "synthesis" inside grade_relevance
            "iterations": 0,
            "rewritten_queries": [],
            "answer": "",
            "citations": [],
            "confidence": 0.0,
            "faithful": False,
            "faithfulness_issues": "",
            "regen_count": 0,
            "history": [],
            "summary": "",
        }

        result = grade_relevance(state)
        return {
            "relevant": result["relevant"],   # LLM boolean judgment, threshold-aware
            "score": result["relevance_score"],
            "reason": result["grade_reason"],
            "rewrite_hint": result["rewrite_hint"],
        }


@mcp.tool()
def search_visual(
    query: str,
    modality: str = "figure",
    k: int = 5,
    token: str = "",
) -> dict:
    """[STUB] Search for medical images, figures, or tables.

    This tool is not yet implemented. It will support searching PMC
    Open Access figures, radiology images, and anatomical diagrams
    when the visual index is built in a future release.

    Args:
        query: Description of the image or figure to search for.
        modality: Type of visual content: "figure", "table", "radiology".
        k: Number of results to return (1–10).
        token: Optional auth token (MEDRAG_LOCAL_TOKEN).

    Returns:
        Dict with status="not_implemented" and a message.
    """
    with _audit_tool("search_visual", query, success_status="stub"):
        _security_check(query, token, is_generate=False)
    return {
        "status": "not_implemented",
        "message": (
            "Visual search is not yet available. "
            "The PMC figure index is planned for a future release. "
            "Use search_literature for text-based retrieval."
        ),
        "modality": modality,
        "k": k,
    }


def _start_mcp_warmup() -> None:
    """Load embedder + reranker in background so the first tool call is faster."""

    def _run() -> None:
        try:
            logger.info("[mcp] background warmup: loading retriever + reranker …")
            _get_retriever()
            _get_reranker()
            logger.info("[mcp] background warmup: ready")
        except Exception as exc:
            logger.warning("[mcp] background warmup failed (first tool call will retry): %s", exc)

    threading.Thread(target=_run, daemon=True, name="medrag-mcp-warmup").start()


if __name__ == "__main__":
    _start_mcp_warmup()
    mcp.run()
