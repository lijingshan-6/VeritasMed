"""
WebSocket /api/ask — streams the full agentic reasoning loop as events.

Uses asyncio.to_thread + Queue to safely bridge LangGraph's synchronous
app.stream() into the async WebSocket handler.
"""
from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import TimeoutError as FutureTimeoutError
from threading import Event
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from medrag.agent.graph import app as langgraph_app
from medrag.agent.conversation import resolve_context
from medrag.agent.invocation import build_initial_state as _build_initial_state
from medrag.api._helpers import payload_to_chunk
from medrag.api.models import (
    AnswerOut,
    AskRequest,
    ChunkOut,
    ChunkRetrievedData,
    ChunkRetrievedEvent,
    DoneEvent,
    ErrorData,
    ErrorEvent,
    NodeEndData,
    NodeEndEvent,
    NodeStartEvent,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_SENTINEL = object()
_STREAM_TIMEOUT_S = 300.0
_QUEUE_CAPACITY = 32
_PUBLIC_ERROR = "The answer could not be completed. Please try again."


async def _send_safe(ws: WebSocket, payload: dict) -> bool:
    try:
        await ws.send_json(payload)
        return True
    except Exception:  # noqa: BLE001 - send failures are transport-specific
        return False


def _chunks_from_state(state: dict) -> list[ChunkOut]:
    chunks_out: list[ChunkOut] = []
    for c in state.get("retrieved_chunks", []):
        if hasattr(c, "payload"):
            chunks_out.append(payload_to_chunk(c.payload, score=getattr(c, "score", None)))
        elif isinstance(c, dict):
            chunks_out.append(payload_to_chunk(c, score=c.get("score")))
    return chunks_out


def _node_event(
    node_name: str, output: dict
) -> tuple[NodeEndEvent | None, list[ChunkRetrievedEvent]]:
    extras: list[ChunkRetrievedEvent] = []

    if node_name in ("__start__", "__end__", "summarize_gate"):
        return None, extras

    if node_name in ("retrieve", "rerank"):
        chunks = output.get("retrieved_chunks", [])
        for c in chunks:
            if hasattr(c, "payload"):
                co = payload_to_chunk(c.payload, score=getattr(c, "score", None))
            elif isinstance(c, dict):
                co = payload_to_chunk(c, score=c.get("score"))
            else:
                continue
            extras.append(ChunkRetrievedEvent(
                node=node_name,
                data=ChunkRetrievedData(
                    chunk_id=co.chunk_id,
                    citation=co.citation,
                    title=co.title,
                    score=co.score,
                    text_snippet=co.text[:200],
                    source=co.source,
                    external_url=co.external_url,
                ),
            ))
        data = NodeEndData(count=len(chunks))

    elif node_name == "grade":
        data = NodeEndData(
            relevance_score=output.get("relevance_score", 0.0),
            relevant=output.get("relevant", False),
            reason=output.get("grade_reason", ""),
            rewrite_hint=output.get("rewrite_hint", ""),
        )

    elif node_name == "rewrite":
        rqs = output.get("rewritten_queries", [])
        data = NodeEndData(
            new_query=rqs[-1] if rqs else "",
            rewritten_queries=rqs,
        )

    elif node_name == "generate":
        data = NodeEndData(answer_preview=output.get("answer", "")[:120])

    elif node_name == "check":
        data = NodeEndData(
            faithful=output.get("faithful", False),
            issues=output.get("faithfulness_issues", ""),
            confidence=output.get("confidence", 0.0),
        )

    elif node_name == "resolve_context":
        data = NodeEndData(new_query=output.get("new_query"), reason=output.get("reason"))

    elif node_name == "route":
        data = NodeEndData(route=output.get("route", ""))

    else:
        data = NodeEndData()

    return NodeEndEvent(node=node_name, data=data), extras


@router.websocket("/api/ask")
async def ask_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    t_start = time.perf_counter()
    try:
        raw = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
        req = AskRequest(**raw)
    except Exception:  # noqa: BLE001 - do not expose request parser details
        await _send_safe(websocket, ErrorEvent(data=ErrorData(message="Invalid ask request.")).model_dump())
        await websocket.close()
        return

    # Intent uses explicit bounded snapshots; evidence/history reducers always
    # start fresh. A public conversation ID is never a shared graph checkpoint.
    config: dict = {"configurable": {"thread_id": str(uuid4())}}
    resolution = None
    queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_CAPACITY)
    loop = asyncio.get_running_loop()
    stop = Event()
    hidden_nodes = {"__start__", "__end__", "summarize_gate", "inc_regen"}

    def _enqueue(item: tuple) -> bool:
        """Bound thread-to-event-loop buffering; stop after disconnect/timeout."""
        if stop.is_set():
            return False
        try:
            future = asyncio.run_coroutine_threadsafe(queue.put(item), loop)
        except RuntimeError:
            return False
        while not stop.is_set():
            try:
                future.result(timeout=0.25)
                return True
            except FutureTimeoutError:
                continue
            except RuntimeError:
                return False
        future.cancel()
        return False

    def _stream_worker() -> None:
        nonlocal resolution
        try:
            if req.context and not _enqueue(("node_start", "resolve_context", {})):
                return
            resolution = resolve_context(req.query, req.context, req.omitted_context)
            if stop.is_set():
                return
            if req.context:
                _enqueue(("node_output", "resolve_context", {"new_query": resolution.resolved_query, "reason": resolution.status}))
            if resolution.needs_clarification:
                _enqueue(("clarification", None, None))
                return
            initial_state = _build_initial_state(resolution.resolved_query)
            for mode, chunk in langgraph_app.stream(
                initial_state, config=config, stream_mode=["tasks", "updates"]
            ):
                if stop.is_set():
                    break
                if mode == "tasks":
                    if "result" not in chunk and "error" not in chunk:
                        if not _enqueue(("node_start", chunk.get("name"), {})):
                            break
                    elif chunk.get("error") is not None:
                        _enqueue(("error", None, {}))
                        break
                elif mode == "updates":
                    for node_name, output in chunk.items():
                        if not _enqueue(("node_output", node_name, output if isinstance(output, dict) else {})):
                            break
        except Exception:
            logger.exception("LangGraph stream error")
            _enqueue(("error", None, {}))
        finally:
            _enqueue((_SENTINEL, None, None))

    async def _watch_disconnect() -> None:
        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    break
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            stop.set()

    stream_task = asyncio.create_task(asyncio.to_thread(_stream_worker))
    disconnect_task = asyncio.create_task(_watch_disconnect())
    deadline = loop.time() + _STREAM_TIMEOUT_S

    try:
        while True:
            queue_task = asyncio.create_task(queue.get())
            ready, _ = await asyncio.wait(
                {queue_task, disconnect_task},
                timeout=max(0.0, deadline - loop.time()),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if disconnect_task in ready:
                queue_task.cancel()
                await asyncio.gather(queue_task, return_exceptions=True)
                return
            if queue_task not in ready:
                queue_task.cancel()
                await asyncio.gather(queue_task, return_exceptions=True)
                logger.warning("WS response deadline reached")
                stop.set()
                await _send_safe(websocket, ErrorEvent(data=ErrorData(message="The answer timed out. Please try again.")).model_dump())
                return

            kind, name, data = queue_task.result()
            if kind is _SENTINEL:
                break

            if kind == "error":
                stop.set()
                await _send_safe(websocket, ErrorEvent(data=ErrorData(message=_PUBLIC_ERROR)).model_dump())
                return

            if kind == "clarification":
                answer_out = AnswerOut(answer=resolution.clarification, citations=[], confidence=0,
                    faithful=False, faithfulness_issues="Clarification only; no evidence judgment made.",
                    iterations=0, regen_count=0, rewritten_queries=[], chunks=[], thread_id=req.thread_id,
                    latency_ms=round((time.perf_counter() - t_start) * 1000, 1), conversation_context=resolution)
                await _send_safe(websocket, DoneEvent(data=answer_out).model_dump())
                return

            if kind == "node_start":
                if name in hidden_nodes:
                    continue
                if not await _send_safe(websocket, NodeStartEvent(node=name).model_dump()):
                    return

            elif kind == "node_output":
                if name in hidden_nodes:
                    continue
                node_end_ev, extras = _node_event(name, data)
                for ev in extras:
                    if not await _send_safe(websocket, ev.model_dump()):
                        return
                if node_end_ev is not None and not await _send_safe(websocket, node_end_ev.model_dump()):
                    return

        remaining = deadline - loop.time()
        if remaining <= 0:
            raise TimeoutError
        snapshot = await asyncio.wait_for(
            asyncio.to_thread(langgraph_app.get_state, config), timeout=remaining
        )
        final = snapshot.values if snapshot else {}
        latency = round((time.perf_counter() - t_start) * 1000, 1)
        answer_out = AnswerOut(
            conversation_context=resolution,
            evidence_status=final.get("evidence_status"),
            evidence_gap=final.get("evidence_gap", ""),
            answer_components=final.get("answer_components", []),
            answer=final.get("answer", ""),
            citations=final.get("citations", []),
            confidence=final.get("confidence", 0.0),
            faithful=final.get("faithful", False),
            faithfulness_issues=final.get("faithfulness_issues", ""),
            iterations=final.get("iterations", 0),
            regen_count=final.get("regen_count", 0),
            rewritten_queries=final.get("rewritten_queries", []),
            chunks=_chunks_from_state(final),
            thread_id=req.thread_id,
            latency_ms=latency,
        )
        await _send_safe(websocket, DoneEvent(data=answer_out).model_dump())
    except TimeoutError:
        logger.warning("WS final state deadline reached")
        await _send_safe(websocket, ErrorEvent(data=ErrorData(message="The answer timed out. Please try again.")).model_dump())
    except Exception:
        logger.exception("WS consumer error")
        await _send_safe(websocket, ErrorEvent(data=ErrorData(message=_PUBLIC_ERROR)).model_dump())
    finally:
        stop.set()
        disconnect_task.cancel()
        await asyncio.gather(disconnect_task, return_exceptions=True)
        # A synchronous node already in progress cannot be interrupted here.
        # The stop flag prevents scheduling additional nodes/events afterwards.
        if stream_task.done():
            await asyncio.gather(stream_task, return_exceptions=True)
        try:
            await websocket.close()
        except Exception:
            logger.debug("WS close failed after request end", exc_info=True)
