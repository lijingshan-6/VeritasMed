"""
Legacy raw checkpoint lookup. Browser conversations live in IndexedDB and
cannot be recovered by passing their public ID to this endpoint.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from medrag.agent.graph import app as langgraph_app
from medrag.api.models import HistoryResponse, HistoryTurn

router = APIRouter()


@router.get("/api/history/{thread_id}", response_model=HistoryResponse, deprecated=True,
            description="Legacy raw checkpoint lookup, not browser conversation history. Public Ask IDs are not checkpoint IDs; use conversation export/import in the browser.")
async def get_history(thread_id: str) -> HistoryResponse:
    config = {"configurable": {"thread_id": thread_id}}

    try:
        state_snapshot = langgraph_app.get_state(config)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if state_snapshot is None or not state_snapshot.values:
        return HistoryResponse(thread_id=thread_id, turns=[], summary="")

    values = state_snapshot.values
    history: list[dict] = values.get("history", [])
    summary: str = values.get("summary", "")

    turns: list[HistoryTurn] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        turns.append(
            HistoryTurn(
                query=entry.get("query", ""),
                answer=entry.get("answer", ""),
                citations=entry.get("citations", []),
                timestamp=entry.get(
                    "timestamp",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        )

    return HistoryResponse(thread_id=thread_id, turns=turns, summary=summary)
