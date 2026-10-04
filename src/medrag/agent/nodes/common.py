"""Structured model calls and prompt formatting shared by graph nodes."""
from __future__ import annotations

import logging
import json
import re
from typing import Any
from langchain_core.messages import HumanMessage
from medrag.agent.utils import strip_thinking
from medrag.retrieval.retriever import RetrievedChunk

logger = logging.getLogger("medrag.agent.nodes")


def _transient(exc: Exception) -> bool:
    """A dropped stream, connection error or timeout; never auth, billing or rate limits."""
    status = getattr(exc, "status_code", None)
    if status is not None:
        return status >= 500
    return type(exc).__name__ in {"APIError", "APIConnectionError", "APITimeoutError"}


def _invoke_once(llm, messages):
    """One model call, repeated once after a transient transport failure."""
    import time
    try:
        return llm.invoke(messages)
    except Exception as exc:  # noqa: BLE001 - classified below; anything else propagates
        if not _transient(exc):
            raise
        logger.warning("[llm] transient transport failure (%s) — retrying once", type(exc).__name__)
        time.sleep(2)
        return llm.invoke(messages)


def _invoke_with_retry(llm, messages, retries: int = 1) -> str:
    """Invoke LLM and retry once if response is empty (transient API issue)."""
    import time
    for attempt in range(1 + retries):
        resp = _invoke_once(llm, messages)
        content = resp.content or ""
        raw = strip_thinking(content)
        if raw and raw.strip():
            return raw
        # If strip_thinking removed everything but original had content, use original
        if content and content.strip():
            logger.warning("[llm] strip_thinking returned empty but raw has %d chars — using raw", len(content))
            return content.strip()
        if attempt < retries:
            logger.warning("[llm] empty response — retrying (attempt %d/%d)", attempt + 1, retries)
            time.sleep(2)
    return raw  # return empty on final attempt


def _parse_json(text: str) -> dict[str, Any]:
    """Strip markdown fences and parse JSON; return {} on failure."""
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group())
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                pass
    logger.warning("Failed to parse LLM JSON output: %s", text[:200])
    return {}


def _invoke_json_with_retry(
    llm: Any,
    messages: list[Any],
    *,
    required_keys: tuple[str, ...],
) -> tuple[str, dict[str, Any]]:
    """Retry one malformed structured response before changing graph state."""

    raw = ""
    for attempt in range(2):
        attempt_messages = messages
        if attempt:
            attempt_messages = [
                *messages,
                HumanMessage(
                    content=(
                        "Your previous response was invalid or incomplete JSON. Return only "
                        "one valid JSON object with every required key; retain all evidence and details."
                    )
                ),
            ]
        raw = _invoke_with_retry(llm, attempt_messages, retries=0)
        parsed = _parse_json(raw)
        if parsed and all(key in parsed for key in required_keys):
            return raw, parsed
        if attempt == 0:
            logger.warning("[llm] invalid structured output — retrying once in place")
    return raw, {}


def _format_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks for the generate prompt.

    Each chunk is prefixed with its citation key in square brackets so the
    model can reference it exactly in the 'cite' field of each claim.
    """
    parts = [
        f"[{c.citation}] chunk_id={c.chunk_id} (score={c.score:.3f}):\n{c.text}"
        for c in chunks
    ]
    return "\n\n".join(parts)


def _format_outline(components: list[dict], *, include_quotes: bool, all_spans: dict | None = None) -> str:
    """Avoid copying the same source paragraph into every prompt component."""
    evidence = []
    compact = []
    for component in components:
        item = {k: v for k, v in component.items() if k not in {"evidence", "answer"}}
        references = []
        for span in component["evidence"]:
            if span not in evidence:
                evidence.append(span)
            references.append(next((k for k, v in (all_spans or {}).items() if v == span),
                                   f"B{evidence.index(span) + 1}"))
        item["evidence_ids"] = references
        compact.append(item)
    spans = {next((k for k, v in (all_spans or {}).items() if v == span), f"B{i + 1}"):
             (span if include_quotes else {k: v for k, v in span.items() if k != "quote"})
             for i, span in enumerate(evidence)}
    return json.dumps({"components": compact, "source_passages": spans}, ensure_ascii=False)


def _unique_texts(values: Any, *, limit: int) -> list[str]:
    """Return bounded, non-empty, case-insensitively unique strings."""

    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        normalized = " ".join(value.split()).strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        result.append(normalized)
        seen.add(key)
        if len(result) >= limit:
            break
    return result


def _format_requirements(requirements: Any, fallback: str) -> str:
    items = _unique_texts(requirements, limit=8) or [fallback]
    return "\n".join(f"- {item}" for item in items)


def _boundary_sentence(value: str, fallback: str) -> str:
    text = " ".join(value.split()).strip() or fallback
    return text if text.endswith((".", "!", "?")) else f"{text}."
