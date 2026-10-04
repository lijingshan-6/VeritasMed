"""The compared answer methods. All use the same Flash model, corpus and retrieval stack.

A0 closed_book   no retrieval
A1 vanilla_rag   hybrid search + rerank, top 5 passages, one cited answer
A2 veritasmed    the full Ask graph (current default)
A4 gold_context  the question's own abstract, one cited answer (upper bound)
judge            maps any answer text to yes / no / maybe, identically for every arm
"""
from __future__ import annotations

import json
import time
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage

ANSWER_RULES = """Answer the biomedical research question in 2-5 plain sentences. State the
finding directly, with the population, comparison and numbers it rests on. Use only the supplied
passages. Put the citation key in square brackets after every sentence that uses a passage, e.g.
[PMID:12345]. Do not cite keys that are not supplied. If the passages do not settle the question,
say what they do and do not show. Return JSON only: {"answer": "..."}"""

CLOSED_BOOK = """Answer the biomedical research question in 2-5 plain sentences from your own
knowledge. State the finding directly. Return JSON only: {"answer": "..."}"""

JUDGE = """You read an answer to a yes/no research question and report what the ANSWER concludes,
not what you believe. yes: the answer concludes the question is affirmed. no: it concludes the
opposite. maybe: the answer says the evidence is mixed, conditional, inconclusive, or that the
question cannot be settled. Return JSON only: {"verdict": "yes" | "no" | "maybe"}"""


def _call(gateway, system: str, payload: dict) -> tuple[dict, dict]:
    response = gateway.invoke([SystemMessage(content=system), HumanMessage(content=json.dumps(payload, ensure_ascii=False))])
    usage = dict(response.usage_metadata or {})
    usage["model"] = response.response_metadata.get("model")
    return json.loads(response.content), usage


def _passages(chunks) -> list[dict]:
    return [{"key": f"PMID:{c['doc_id']}", "section": c.get("section", ""), "text": c["text"]} for c in chunks]


def closed_book(gateway, q: dict) -> dict:
    out, usage = _call(gateway, CLOSED_BOOK, {"question": q["question"]})
    return {"answer": str(out.get("answer", "")), "chunks": [], "usage": [usage]}


def vanilla_rag(gateway, q: dict, retrieve) -> dict:
    chunks = retrieve(q["question"])
    out, usage = _call(gateway, ANSWER_RULES, {"question": q["question"], "passages": _passages(chunks)})
    return {"answer": str(out.get("answer", "")), "chunks": chunks, "usage": [usage]}


def gold_context(gateway, q: dict) -> dict:
    chunks = [{"chunk_id": f"pubmed:{q['pmid']}:{i}", "doc_id": q["pmid"], "section": (q["gold_labels"][i] if i < len(q["gold_labels"]) else "").title(),
               "text": " ".join(t.split())} for i, t in enumerate(q["gold_contexts"])]
    out, usage = _call(gateway, ANSWER_RULES, {"question": q["question"], "passages": _passages(chunks)})
    return {"answer": str(out.get("answer", "")), "chunks": chunks, "usage": [usage]}


def veritasmed(q: dict) -> dict:
    from medrag.agent.graph import app
    from medrag.agent.invocation import build_initial_state
    from medrag.agent.usage import collect_usage

    with collect_usage() as calls:
        try:
            final = app.invoke(build_initial_state(q["question"]), config={"configurable": {"thread_id": str(uuid4())}})
        except Exception as exc:
            exc.usage = calls  # tokens spent before the failure still count against the budget
            raise
    chunks = [{"chunk_id": c.chunk_id, "doc_id": c.payload.get("doc_id"), "section": c.payload.get("section", ""), "text": c.text}
              for c in final.get("retrieved_chunks", [])]
    return {"answer": final.get("answer", ""), "chunks": chunks, "usage": calls,
            "agent": {k: final.get(k) for k in ("evidence_status", "evidence_gap", "faithful", "regen_count", "iterations", "rewritten_queries")},
            "components": final.get("answer_components", [])}


def judge(gateway, q: dict, answer: str) -> tuple[str | None, dict]:
    out, usage = _call(gateway, JUDGE, {"question": q["question"], "answer": answer})
    verdict = str(out.get("verdict", "")).strip().lower()
    return (verdict if verdict in {"yes", "no", "maybe"} else None), usage


def make_retriever():
    """The Agent's own hybrid retriever and reranker, used identically by the RAG baseline."""
    from medrag.agent.nodes.retrieval import _get_reranker, _get_retriever, _passages_of, complete_documents

    def retrieve(question: str, k: int = 5):
        candidates = _get_retriever().retrieve(question, k=12)
        ranked = _get_reranker().rerank(question, candidates, top_k=k)
        if ranked:  # same whole-abstract completion as the Agent's general path
            ranked = complete_documents(ranked, [ranked[0].payload.get("doc_id")], _passages_of)
        return [{"chunk_id": c.chunk_id, "doc_id": c.payload.get("doc_id"), "section": c.payload.get("section", ""), "text": c.text}
                for c in ranked]
    return retrieve


def timed(fn, *args):
    started = time.perf_counter()
    try:
        out = fn(*args)
        out["status"] = "ok"
    except Exception as exc:  # noqa: BLE001 - every failure is kept as a result
        out = {"status": "error", "error_type": type(exc).__name__, "error": str(exc)[:300],
               "usage": list(getattr(exc, "usage", []))}
    out["seconds"] = round(time.perf_counter() - started, 2)
    return out
