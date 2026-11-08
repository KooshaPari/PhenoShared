"""ContextVar-backed request-ID store.

Zero dependencies. Use `with_request_id` to set the value for a scope
(typical: inside a middleware that wraps the downstream call).
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

# Single module-level ContextVar. Using `str | None` keeps the type
# honest without forcing a default at import time.
_request_id_var: ContextVar[str | None] = ContextVar(
    "phenotype_request_id", default=None
)


def get_request_id() -> str | None:
    """Return the current request ID, or None if unset."""
    return _request_id_var.get()


def set_request_id(value: str) -> object:
    """Set the request ID for the current context. Returns the token."""
    if not isinstance(value, str) or not value:
        raise ValueError("request id must be a non-empty string")
    return _request_id_var.set(value)


def reset_request_id(token: object) -> None:
    """Reset the request ID using a token returned by `set_request_id`."""
    _request_id_var.reset(token)  # type: ignore[arg-type]


@contextmanager
def with_request_id(value: str) -> Iterator[str]:
    """Context manager: set the request ID, yield it, reset on exit."""
    if not isinstance(value, str) or not value:
        raise ValueError("request id must be a non-empty string")
    token = _request_id_var.set(value)
    try:
        yield value
    finally:
        _request_id_var.reset(token)
