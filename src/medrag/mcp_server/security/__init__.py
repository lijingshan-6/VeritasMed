"""Security middleware for VeritasMed MCP server.

Five-layer defense:
  1. auth            — MEDRAG_LOCAL_TOKEN verification
  2. rate_limit      — token-bucket (30 rpm global, 10 rpm generate)
  3. audit           — structured JSON-Lines audit log
  4. pii             — email / phone / SSN redaction for logs
  5. injection_guard — prompt injection detection + XML boundary tags
"""
from medrag.mcp_server.security.audit import audit, log_tool_call
from medrag.mcp_server.security.auth import AuthError, require_auth, verify_token
from medrag.mcp_server.security.injection_guard import (
    InjectionGuardError,
    check_injection,
    escape_special_tokens,
    sanitise_query,
    wrap_document,
)
from medrag.mcp_server.security.pii import redact, redact_for_log
from medrag.mcp_server.security.rate_limit import (
    RateLimitError,
    TokenBucket,
    check_rate_limit,
    rate_limit,
)

__all__ = [
    # audit
    "audit",
    "log_tool_call",
    # auth
    "AuthError",
    "require_auth",
    "verify_token",
    # injection_guard
    "InjectionGuardError",
    "check_injection",
    "escape_special_tokens",
    "sanitise_query",
    "wrap_document",
    # pii
    "redact",
    "redact_for_log",
    # rate_limit
    "RateLimitError",
    "TokenBucket",
    "check_rate_limit",
    "rate_limit",
]
