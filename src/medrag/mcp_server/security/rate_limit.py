"""Token-bucket rate limiter for VeritasMed MCP server.

Limits:
  - Global:   30 requests / minute  (all tools combined)
  - Generate: 10 requests / minute  (agent/ask tools only)

Thread-safe; uses threading.Lock for the in-process bucket.
Raises RateLimitError (subclass of ValueError) when the bucket is empty.
"""
from __future__ import annotations

import logging
import threading
import time
from functools import wraps
from typing import Callable

logger = logging.getLogger(__name__)


class RateLimitError(ValueError):
    """Raised when a request exceeds the configured rate limit."""


class TokenBucket:
    """Leaky-bucket rate limiter.

    Args:
        capacity: Maximum tokens in the bucket.
        refill_rate: Tokens added per second (= requests / 60 for per-minute limits).
    """

    def __init__(self, capacity: float, refill_rate: float) -> None:
        self.capacity    = capacity
        self.refill_rate = refill_rate
        self._tokens     = float(capacity)
        self._last_refill = time.monotonic()
        self._lock       = threading.Lock()

    def consume(self, tokens: float = 1.0) -> bool:
        """Attempt to consume `tokens` from the bucket.

        Returns True if successful, False if rate limit exceeded.
        """
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self.capacity,
                self._tokens + elapsed * self.refill_rate,
            )
            self._last_refill = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def refund(self, tokens: float = 1.0) -> None:
        """Return tokens to the bucket (thread-safe).

        Called when a downstream check fails after the global bucket was
        already consumed, so the slot is not wasted.
        """
        with self._lock:
            self._tokens = min(self.capacity, self._tokens + tokens)


# ── Global buckets ─────────────────────────────────────────────────────────────

_GLOBAL_BUCKET   = TokenBucket(capacity=30, refill_rate=30 / 60)   # 30 rpm
_GENERATE_BUCKET = TokenBucket(capacity=10, refill_rate=10 / 60)   # 10 rpm


def check_rate_limit(is_generate: bool = False) -> None:
    """Check and consume from rate limit buckets.

    Args:
        is_generate: True for expensive generate/ask tool calls.

    Raises:
        RateLimitError: if any bucket is exhausted.
    """
    if not _GLOBAL_BUCKET.consume():
        logger.warning("[rate_limit] global bucket exhausted")
        raise RateLimitError(
            "Rate limit exceeded: max 30 requests/minute. Please retry later."
        )
    if is_generate and not _GENERATE_BUCKET.consume():
        _GLOBAL_BUCKET.refund()  # thread-safe: undo the global consume before raising
        logger.warning("[rate_limit] generate bucket exhausted")
        raise RateLimitError(
            "Rate limit exceeded for answer generation: max 10 requests/minute."
        )


def rate_limit(is_generate: bool = False):
    """Decorator that applies rate limiting to a tool function.

    Usage:
        @rate_limit(is_generate=True)
        def ask(query: str, ...) -> ...:
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            check_rate_limit(is_generate=is_generate)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


__all__ = ["RateLimitError", "TokenBucket", "check_rate_limit", "rate_limit"]
