"""Per-request token accounting for every model call made inside the Ask graph.

    with collect_usage() as calls:
        app.invoke(...)
    # calls: one dict per model call (input/output tokens, model)

Outside a `collect_usage` block nothing is recorded.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

_sink: ContextVar[list[dict] | None] = ContextVar("medrag_usage", default=None)


def record(response) -> None:
    sink = _sink.get()
    if sink is None:
        return
    usage = getattr(response, "usage_metadata", None) or {}
    metadata = getattr(response, "response_metadata", None) or {}
    raw = metadata.get("token_usage") or {}  # OpenAI-format usage some gateways return instead
    sink.append({"input_tokens": usage.get("input_tokens", raw.get("prompt_tokens")),
                 "output_tokens": usage.get("output_tokens", raw.get("completion_tokens")),
                 "total_tokens": usage.get("total_tokens", raw.get("total_tokens")),
                 "cache_read_tokens": (usage.get("input_token_details") or {}).get("cache_read", raw.get("prompt_cache_hit_tokens")),
                 "model": metadata.get("model_name") or metadata.get("model")})


@contextmanager
def collect_usage():
    calls: list[dict] = []
    token = _sink.set(calls)
    try:
        yield calls
    finally:
        _sink.reset(token)
