# MCP: implemented controls and their limits

**English** | [简体中文](../mcp_security.md)

Describes the post-v0.8 source. **Authentication, rate limiting and audit logging are implemented
in the repository for MCP tools; they do not automatically protect the FastAPI web service.**
This is a local research tool, not a public multi-user service. This replaces earlier five-layer
security/compliance claims; old testing reports are historical records.

## Request processing

`src/medrag/mcp_server/server.py` records results and elapsed time around tool execution.
Before a tool runs:

1. `verify_token` reads `MEDRAG_LOCAL_TOKEN` and compares the argument with `hmac.compare_digest`.
   An unset variable warns and disables authentication; an empty configured string rejects calls.
2. `check_rate_limit` uses process-local token buckets: capacity/refill 30 per minute for all tools
   and another 10 per minute for `ask_agent`. Initial bursts are allowed; these are not sliding-window guarantees.
3. `redact` applies common PII regex substitutions to the query before retrieval/generation.
4. `sanitise_query` rejects known injection patterns, handles special tokens and wraps data boundaries.

Code: [auth](../../src/medrag/mcp_server/security/auth.py),
[rate limits](../../src/medrag/mcp_server/security/rate_limit.py),
[PII](../../src/medrag/mcp_server/security/pii.py),
[injection guard](../../src/medrag/mcp_server/security/injection_guard.py).
Regex rules have misses/false alarms and do not guarantee complete PII removal, arbitrary injection
resistance or compliance. Query cleaning does not make retrieved text, `context_chunks` or output trustworthy.

## Tools and conversations

| Tool | Behavior |
|---|---|
| `search_literature` | Dense/sparse search, optional reranking; at most ten abstract passages |
| `ask_agent` | Full answer graph; fresh checkpoint each call; `thread_id` is only a caller label |
| `evaluate_query` | Scores up to ten supplied chunks; uncalibrated model judgments |
| `search_visual` | Explicit `not_implemented`, not an implemented image search |

MCP does not use the browser's bounded history resolver. Repeated `thread_id` is not conversation
memory. Maintenance fixed additive-state inheritance from reused default checkpoints; web history
uses browser snapshots. Module imports no longer start background BGE loading; calls load lazily,
while direct server-script execution can still warm up.

## Audit logging

[audit.py](../../src/medrag/mcp_server/security/audit.py) writes
`$MEDRAG_DATA_DIR/logs/audit.jsonl` (default `data/logs/audit.jsonl`): time, tool, first 16 hexadecimal
characters of the original-query SHA-256, duration and result. Ask logs callback usage when available,
not provider billing. Authentication/rate/query rejections are logged; successful visual stubs are `stub`.

Raw query strings and tokens are not stored. Hashes still correlate repeated queries and do not
guarantee anonymization. Logs are mutable JSONL without signing, tamper protection, shared
cross-process quotas, rotation or centralized audit. Write failures log an error without blocking
execution. This is not nonrepudiation or an Agent-wide privacy guarantee.

## Usage and reproducible checks

Default transport is local stdio. Install full dependencies and use `start_mcp.ps1`, or:

```sh
fastmcp dev inspector src/medrag/mcp_server/server.py --with-editable .
```

Configure `MEDRAG_LOCAL_TOKEN` in the server environment and pass `token` on each tool call.
Do not commit keys. Network identity/permission isolation is not delivered public-deployment capability.

```sh
python -m pytest -q tests/test_mcp_security.py tests/test_mcp_invocation.py
```

These offline tests cover rules/isolated invocation, not all attacks, live model quality or external
MCP-client end-to-end behavior. The web API has no MCP token/limits/logs. Its three audit slots
bound process concurrency, not access control.
