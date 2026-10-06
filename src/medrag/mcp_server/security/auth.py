"""Local token authentication for VeritasMed MCP server.

The default MCP transport is local stdio. MEDRAG_LOCAL_TOKEN is an optional
pre-shared tool argument, not a public deployment authentication system.

Token is compared in constant time to prevent timing attacks.
If MEDRAG_LOCAL_TOKEN is not set, authentication is DISABLED
(dev / local-only mode — logs a warning).
"""
from __future__ import annotations

import hmac
import logging
import os
from functools import wraps
from typing import Callable

logger = logging.getLogger(__name__)

_TOKEN_ENV_VAR = "MEDRAG_LOCAL_TOKEN"


class AuthError(PermissionError):
    """Raised when authentication fails."""


def _get_expected_token() -> str | None:
    return os.environ.get(_TOKEN_ENV_VAR)


def verify_token(provided: str) -> None:
    """Verify a provided token against MEDRAG_LOCAL_TOKEN.

    Args:
        provided: Token string from the request.

    Raises:
        AuthError: if token is wrong or missing.
    """
    expected = _get_expected_token()
    if expected is None:
        logger.warning(
            "[auth] %s not set — authentication disabled (local dev mode)", _TOKEN_ENV_VAR
        )
        return

    if not provided:
        raise AuthError("Authentication required: provide MEDRAG_LOCAL_TOKEN.")

    # Constant-time comparison prevents timing-oracle attacks
    if not hmac.compare_digest(
        provided.encode("utf-8"),
        expected.encode("utf-8"),
    ):
        logger.warning("[auth] invalid token attempt")
        raise AuthError("Authentication failed: invalid token.")


def require_auth(fn: Callable) -> Callable:
    """Decorator: extract token from keyword arg 'token' and verify.

    Usage:
        @require_auth
        def search_literature(query: str, token: str = "", ...) -> ...:
            ...
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = kwargs.pop("token", "")
        verify_token(token)
        return fn(*args, **kwargs)
    return wrapper


__all__ = ["AuthError", "verify_token", "require_auth"]
