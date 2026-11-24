"""HTTP adapter for OmniRoute.

The :class:`OmniHttpAdapter` is the only network-facing adapter in the
project. It implements the :class:`Router` port
(:mod:`dispatch_mcp.core.port`) against ``httpx.Client``.

The original sync surface (``dispatch(message, tier, payload)``,
``health()``, ``cancel(request_id)``, ``_sanitize_response``) is
preserved for backward compatibility with downstream consumers and the
existing test suite. New MCP-protocol methods — :meth:`worker`,
:meth:`dispatch` (keyword-only, async, returns :class:`JobResult`),
:meth:`ping`, :meth:`protocol_info`, :meth:`close` — are added on
top of the legacy transport so that adapters, tests, and downstream
consumers see no regression.
"""

from __future__ import annotations

from contextlib import suppress
from importlib import metadata as _metadata
from typing import Any

import httpx

from dispatch_mcp.core.protocol import (
    DEFAULT_NEGOTIATED_VERSION,
    PROTOCOL_DISCOVERY_DESCRIPTION,
    SUPPORTED_PROTOCOL_VERSIONS,
    ProtocolInfo,
    ServerCapabilities,
    ServerInfo,
)
from dispatch_mcp.core.types import JobResult


def _resolve_dispatch_mcp_version() -> str:
    """Return the installed dispatch-mcp version, or ``"0.0.0+unknown"``."""
    try:
        return _metadata.version("dispatch-mcp")
    except _metadata.PackageNotFoundError:
        return "0.0.0+unknown"


_DISPATCH_MCP_VERSION: str = _resolve_dispatch_mcp_version()


# Public allowlist of response keys safe to surface to MCP
# callers. Internal fields — hostnames, stack traces, secrets
# leaked by upstream libraries — must be filtered out before the
# response is forwarded. The list mirrors the canonical
# :class:`dispatch_mcp.core.types.JobResult` fields plus the
# cost-tracking additions, so any key the server actually uses
# is preserved and everything else is dropped.
_PUBLIC_RESPONSE_KEYS: frozenset[str] = frozenset(
    {
        "ok",
        "tier",
        "message",
        "status",
        "error",
        "cost_usd",
        "input_tokens",
        "output_tokens",
        "model",
        "request_id",
        "usage",
    }
)


def _coerce_dispatch_response(body: dict[str, Any], *, tier: str) -> JobResult:
    """Translate a sanitized ``/dispatch`` body into a :class:`JobResult`."""
    return JobResult(
        ok=body.get("ok") if isinstance(body.get("ok"), bool) else None,
        tier=str(body.get("tier") or tier),
        message=str(body["message"]) if isinstance(body.get("message"), str) else None,
        status=str(body["status"]) if isinstance(body.get("status"), str) else None,
        error=str(body["error"]) if isinstance(body.get("error"), str) else None,
        cost_usd=body.get("cost_usd")
        if isinstance(body.get("cost_usd"), (int, float))
        else None,
        input_tokens=body.get("input_tokens")
        if isinstance(body.get("input_tokens"), int)
        else None,
        output_tokens=body.get("output_tokens")
        if isinstance(body.get("output_tokens"), int)
        else None,
        model=str(body["model"]) if isinstance(body.get("model"), str) else None,
        request_id=str(body["request_id"])
        if isinstance(body.get("request_id"), str)
        else None,
    )


class _TierWorker:
    """A callable bound to a single tier; created by
    :meth:`OmniHttpAdapter.worker`."""

    __slots__ = ("_adapter", "_tier")

    def __init__(self, adapter: OmniHttpAdapter, tier: str) -> None:
        self._adapter = adapter
        self._tier = tier

    def dispatch(
        self,
        message: str,
        tier: str,  # noqa: ARG002 — positional, see protocol note below
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Legacy positional dispatch — delegates to :meth:`OmniHttpAdapter.dispatch`.

        The :class:`Worker` protocol requires a sync positional
        ``dispatch`` so the per-tier helpers exposed by
        :meth:`OmniHttpAdapter.worker` can be awaited in legacy
        callers. New code should prefer
        :meth:`OmniHttpAdapter.dispatch_message` (the async
        :class:`Router` entrypoint) or :meth:`__call__` for typed
        :class:`JobResult` returns.
        """
        return self._adapter.dispatch(message, self._tier, payload)

    async def __call__(self, message: str) -> JobResult:
        """Typed dispatch — returns a :class:`JobResult`."""
        return await self._adapter.dispatch_message(tier=self._tier, message=message)


class OmniHttpAdapter:
    """HTTP adapter for OmniRoute dispatch endpoints.

    Construction takes the base URL of the OmniRoute backend
    and an optional pre-built :class:`httpx.Client` for tests
    that want to inject a mock transport. The adapter is a
    pure transport — it does no policy enforcement, no logging
    of payload contents, and no caching. The cost-tracking
    middleware wraps a configured adapter to layer in those
    concerns.
    """

    def __init__(
        self,
        base_url: str,
        client: httpx.Client | None = None,
        *,
        server_name: str = "dispatch-mcp",
        server_vendor: str | None = None,
    ) -> None:
        # ``rstrip`` is safe on any string; allow empty base_url
        # at construction time and let downstream callers fail
        # when they actually issue a request.
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=10.0)
        self._server_name = server_name
        self._server_vendor = server_vendor

    # ---------------------------------------------------------- legacy surface

    def dispatch(
        self,
        message: str,
        tier: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Legacy positional dispatch. Returns a sanitized dict.

        Kept for backward compatibility with downstream consumers and
        the :class:`_TierWorker` factory. New code should prefer
        :meth:`dispatch_message`, the async keyword-only
        :class:`Router` protocol entrypoint that returns a typed
        :class:`JobResult`.
        """
        response = self._client.post(
            f"{self.base_url}/dispatch",
            json={"message": message, "tier": tier, "payload": payload or {}},
        )
        response.raise_for_status()
        return self._sanitize_response(response.json())

    def health(self) -> dict[str, Any]:
        response = self._client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return self._sanitize_response(response.json())

    def cancel(self, request_id: str) -> bool:
        response = self._client.post(
            f"{self.base_url}/cancel", json={"request_id": request_id}
        )
        response.raise_for_status()
        body = self._sanitize_response(response.json())
        return bool(body.get("ok", False))

    @staticmethod
    def _sanitize_response(response: Any) -> dict[str, Any]:
        """Return a copy of ``response`` with internal keys removed.

        Defensive: when the upstream returns a non-dict (None,
        a list, a string), we coerce it into a safe empty dict
        so callers downstream can rely on a uniform shape. The
        allowlist is used as a positive filter rather than a
        blacklist so a new internal field added to the
        upstream response cannot accidentally leak.
        """
        if not isinstance(response, dict):
            return {}
        return {
            key: value
            for key, value in response.items()
            if key in _PUBLIC_RESPONSE_KEYS
        }

    # ----------------------------------------------------------- MCP-protocol

    @property
    def client(self) -> httpx.Client:
        """The underlying ``httpx.Client`` (exposed for tests/health)."""
        return self._client

    def worker(self, tier: str) -> _TierWorker:
        """Return a per-tier callable bound to ``tier``.

        The returned object implements the :class:`Worker` protocol: it
        exposes a ``dispatch(message, tier, payload)`` method for
        backward compatibility and a ``__call__(message) -> JobResult``
        shortcut for the typed :func:`dispatch_mcp.server._make_dispatch`
        wrapper.
        """
        return _TierWorker(self, tier)

    async def dispatch_message(
        self,
        *,
        tier: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> JobResult:
        """Async ``Router.dispatch_message`` entrypoint.

        The transport is sync (``httpx.Client``) but the adapter exposes
        a coroutine so the MCP server can ``await`` it uniformly. This
        is the :class:`dispatch_mcp.core.port.Router` protocol's primary
        dispatch method; the legacy positional surface is preserved on
        :meth:`dispatch` for backward compatibility.
        """
        try:
            response = self._client.post(
                f"{self.base_url}/dispatch",
                json={"message": message, "tier": tier, "payload": payload or {}},
            )
            response.raise_for_status()
            body = self._sanitize_response(response.json())
        except (httpx.HTTPError, httpx.RequestError, ValueError):
            return JobResult(ok=False, tier=tier, error="dispatch failed")
        return _coerce_dispatch_response(body, tier=tier)

    async def ping(self) -> JobResult:
        """Cheap ``/ping`` probe. Maps transport errors to ``unreachable``."""
        try:
            response = self._client.get(f"{self.base_url}/ping")
            response.raise_for_status()
        except (httpx.HTTPError, httpx.RequestError, ValueError):
            return JobResult(status="unreachable", error="ping failed")
        return JobResult(status="alive", message="pong")

    def protocol_info(self) -> ProtocolInfo:
        """Return the typed protocol discovery payload. No I/O."""
        return ProtocolInfo(
            serverVersion=_DISPATCH_MCP_VERSION,
            supportedVersions=list(SUPPORTED_PROTOCOL_VERSIONS),
            defaultVersion=DEFAULT_NEGOTIATED_VERSION,
            negotiatedVersion=DEFAULT_NEGOTIATED_VERSION,
            capabilities=ServerCapabilities(),
            serverInfo=ServerInfo(
                name=self._server_name,
                version=_DISPATCH_MCP_VERSION,
                vendor=self._server_vendor,
            ),
            description=PROTOCOL_DISCOVERY_DESCRIPTION,
        )

    def close(self) -> None:
        """Release the underlying ``httpx`` client.

        The original adapter owns its ``httpx.Client``; tests inject a
        pre-built client and skip this path. We always attempt a
        ``close()`` call because ``httpx.Client`` is idempotent and a
        no-op for an already-closed client. Errors are swallowed so
        the MCP server's SIGTERM/SIGINT handlers can never raise.
        """
        with suppress(Exception):
            self._client.close()


__all__ = ["OmniHttpAdapter"]
