"""Audit logging middleware for VeritasMed MCP server.

Writes structured JSON-Lines to data/logs/audit.jsonl.
Each entry records: timestamp, tool, query_hash, latency_ms, status,
and (when available) prompt_tokens / completion_tokens for cost tracking.

PII-safe: the query itself is NOT logged; only a SHA-256 prefix is stored.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

_LOG_DIR  = Path(os.environ.get("MEDRAG_DATA_DIR", "data")) / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_AUDIT_FILE = _LOG_DIR / "audit.jsonl"


def _query_hash(query: str) -> str:
    """Return first 16 hex chars of SHA-256 of the query string."""
    return hashlib.sha256(query.encode()).hexdigest()[:16]


def _write_entry(entry: dict) -> None:
    try:
        with _AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.error("[audit] failed to write: %s", exc)


def log_tool_call(
    tool_name: str,
    query: str,
    status: str,
    latency_ms: float,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    extra: dict | None = None,
) -> None:
    """Write a single audit record synchronously.

    Args:
        tool_name:         MCP tool that was called.
        query:             Raw query (hashed before logging).
        status:            "ok" or "error:<ExcType>" or "rejected:<ExcType>".
        latency_ms:        Wall-clock time for the tool call.
        prompt_tokens:     Total prompt tokens consumed (all LLM calls combined).
        completion_tokens: Total completion tokens generated.
        extra:             Any additional key/value pairs to merge into the record.
    """
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "query_hash": _query_hash(query),
        "status": status,
        "latency_ms": round(latency_ms, 1),
    }
    if prompt_tokens is not None:
        entry["prompt_tokens"] = prompt_tokens
    if completion_tokens is not None:
        entry["completion_tokens"] = completion_tokens
    if extra:
        entry.update(extra)
    _write_entry(entry)


def audit(tool_name: str):
    """Decorator that wraps a tool function with audit logging.

    Usage:
        @audit("search_literature")
        def search_literature(query: str, ...) -> ...:
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            query = kwargs.get("query", args[0] if args else "")
            t0 = time.perf_counter()
            status = "ok"
            try:
                result = fn(*args, **kwargs)
                return result
            except Exception as exc:
                status = f"error:{type(exc).__name__}"
                raise
            finally:
                latency_ms = (time.perf_counter() - t0) * 1000
                log_tool_call(tool_name, str(query), status, latency_ms)
        return wrapper
    return decorator


__all__ = ["audit", "log_tool_call"]
