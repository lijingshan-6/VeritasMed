"""PII redaction middleware for MedRAG-Agent MCP server.

Redacts common personally identifiable information patterns from
user queries before they are logged or stored.

Redacted patterns
─────────────────
  - Email addresses
  - Phone numbers (US and international)
  - Social Security Numbers (SSN)
  - Credit card numbers (16-digit groups)
  - IP addresses (v4)
  - Names following "patient:" / "subject:" / "my name is" patterns

The MCP entry point redacts the query before retrieval/generation. The audit
logger stores only a hash of the original query. These regexes are heuristic;
they neither remove all identifiers nor protect the separate web API.
"""
from __future__ import annotations

import re
from typing import NamedTuple

# ── Patterns ──────────────────────────────────────────────────────────────────

class _Rule(NamedTuple):
    name: str
    pattern: re.Pattern
    replacement: str


_RULES: list[_Rule] = [
    _Rule(
        "email",
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE),
        "[EMAIL]",
    ),
    _Rule(
        "phone_us",
        re.compile(r"\b(?:\+1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b"),
        "[PHONE]",
    ),
    _Rule(
        "phone_intl",
        re.compile(r"\+\d{1,3}[\s\-.]?\d{2,4}[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}\b"),
        "[PHONE]",
    ),
    _Rule(
        "ssn",
        re.compile(r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b"),
        "[SSN]",
    ),
    _Rule(
        "credit_card",
        re.compile(r"\b(?:\d{4}[\s\-]){3}\d{4}\b"),
        "[CC]",
    ),
    _Rule(
        "ipv4",
        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "[IP]",
    ),
    _Rule(
        "patient_name",
        re.compile(
            r"(?:patient[:\s]+|subject[:\s]+|my\s+name\s+is\s+)"
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            re.IGNORECASE,
        ),
        r"[NAME]",
    ),
]


def redact(text: str) -> str:
    """Apply all PII redaction rules to text.

    Args:
        text: Raw text that may contain PII.

    Returns:
        Text with PII replaced by placeholder tags.
    """
    for rule in _RULES:
        text = rule.pattern.sub(rule.replacement, text)
    return text


def redact_for_log(query: str) -> str:
    """Redact a query string for safe inclusion in audit logs.

    This is called on the query_hash path — the actual query is
    never stored, but if it were, this function would sanitise it.
    """
    return redact(query)


__all__ = ["redact", "redact_for_log"]
