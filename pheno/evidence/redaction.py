"""Secret redaction for persisted research metadata.

Request headers are never part of the registry contract.  These helpers are a
second line of defence for API payloads, URLs, and imported local metadata.
"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "<redacted>"

_SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "client_secret",
    "cookie",
    "hf_token",
    "password",
    "proxy_authorization",
    "refresh_token",
    "secret",
    "set_cookie",
    "token",
    "x_api_key",
}

_TOKEN_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)

_QUERY_SECRET = re.compile(
    r"(?i)([?&](?:access_token|api_key|apikey|client_secret|refresh_token|token)=)[^&#\s]+"
)


def _normalized_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def redact_text(value: str) -> str:
    """Remove common bearer/token forms without changing ordinary identifiers."""

    redacted = _QUERY_SECRET.sub(lambda match: match.group(1) + REDACTED, value)
    for pattern in _TOKEN_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    return redacted


def redact_object(value: Any) -> Any:
    """Return a recursively redacted JSON-compatible value."""

    if isinstance(value, dict):
        result: dict[Any, Any] = {}
        for key, item in value.items():
            if _normalized_key(key) in _SENSITIVE_KEYS:
                result[key] = REDACTED
            else:
                result[key] = redact_object(item)
        return result
    if isinstance(value, list):
        return [redact_object(item) for item in value]
    if isinstance(value, tuple):
        return [redact_object(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def contains_secret(value: Any) -> bool:
    """Return ``True`` when the redactor would alter ``value``."""

    return bool(redact_object(value) != value)


__all__ = ["REDACTED", "contains_secret", "redact_object", "redact_text"]
