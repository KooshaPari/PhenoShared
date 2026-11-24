"""ASGI middleware that propagates `X-Request-Id`.

Reads the header from the incoming scope, falling back to a freshly
generated UUID4. Stores the value in the module-level ContextVar so
downstream code (handlers, loggers, downstream calls) can read it
without explicit threading. Echoes the ID on the response.

Optional import: requires `fastapi`/`starlette`. The module-level
`RequestIdMiddleware` factory performs a lazy import so the rest of
the package remains importable without these deps.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Awaitable, Callable

from phenotype_request_id.context import (
    get_request_id,
    set_request_id,
)

HEADER_NAME = "x-request-id"
RESPONSE_HEADER = "X-Request-Id"

# Standard-library logger used for entry/exit traces. Lazy, so we don't
# pay the cost if the application configures its own logging.
_logger = logging.getLogger("phenotype_request_id")


def _coerce_header(value: Any) -> str | None:
    """Normalize a header value (bytes/str/list) to a stripped str."""
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("latin-1")
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return None
    # Cap at a reasonable length to avoid header-injection abuse.
    return value[:200]


def _extract_inbound(scope: dict[str, Any]) -> str:
    """Pull X-Request-Id from raw ASGI headers, or generate a UUID4."""
    for raw_name, raw_value in scope.get("headers", ()) or ():
        if raw_name.lower() == HEADER_NAME.encode("ascii"):
            coerced = _coerce_header(raw_value)
            if coerced:
                return coerced
    return uuid.uuid4().hex


def _log_event(event: str, rid: str) -> None:
    """Entry/exit log. No-op if structlog isn't installed (we use stdlib)."""
    if _logger.handlers or _logger.parent and _logger.parent.handlers:
        _logger.info("%s request_id=%s", event, rid)


def _build_middleware_class() -> type:
    """Lazy import starlette; only required when the middleware is used."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.types import ASGIApp

    class RequestIdMiddleware(BaseHTTPMiddleware):
        """ASGI middleware that propagates X-Request-Id via ContextVar."""

        def __init__(self, app: ASGIApp, header_name: str = RESPONSE_HEADER) -> None:
            super().__init__(app)
            self._header_name = header_name

        async def dispatch(
            self,
            request: Request,
            call_next: Callable[[Request], Awaitable[Response]],
        ) -> Response:
            inbound = _extract_inbound(request.scope)
            token = set_request_id(inbound)
            _log_event("request.start", inbound)
            try:
                response = await call_next(request)
            finally:
                from phenotype_request_id.context import reset_request_id

                reset_request_id(token)
            _log_event("request.end", inbound)
            response.headers[self._header_name] = get_request_id() or inbound
            return response

    return RequestIdMiddleware


def RequestIdMiddleware(app: Any, header_name: str = RESPONSE_HEADER) -> Any:  # noqa: N802
    """Factory mirroring starlette's `add_middleware(MiddlewareClass)` API.

    Use as: `app.add_middleware(RequestIdMiddleware)`.
    """
    cls = _build_middleware_class()
    return cls(app, header_name=header_name)
