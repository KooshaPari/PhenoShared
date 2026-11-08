"""Typed ports for the dispatch-mcp hexagonal core.

The :mod:`dispatch_mcp.core` layer defines the contracts that the
``server`` (composition) layer can rely on, without depending on any
transport. ``adapters`` provides the concrete HTTP/OmniRoute
implementations of these ports.

Two port kinds live here, both ``@runtime_checkable`` so that the
MCP server can perform structural-typing checks at startup:

- :class:`Worker` — a per-tier callable used by ``dispatch_<tier>``
  tools. Exposes the legacy positional ``dispatch`` and a typed
  ``__call__`` shortcut that returns :class:`JobResult`.
- :class:`Router` — the broader surface used by ``dispatch_custom``,
  ``dispatch_health``, ``dispatch_ping``, and ``dispatch_protocol``.
  Combines a per-tier worker factory with health, liveness, and
  protocol-discovery concerns.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dispatch_mcp.core.protocol import ProtocolInfo
from dispatch_mcp.core.types import JobResult


@runtime_checkable
class Worker(Protocol):
    """Port for dispatching work through an adapter.

    The original positional ``dispatch`` API is preserved for backward
    compatibility. New code should prefer the ``__call__`` shortcut,
    which is the public shape the
    :func:`dispatch_mcp.server._make_dispatch` wrapper relies on.
    """

    def dispatch(
        self, message: str, tier: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Dispatch a message and return the backend response."""

    async def __call__(self, message: str) -> JobResult:
        """Dispatch ``message`` and return a typed :class:`JobResult`."""


@runtime_checkable
class Router(Protocol):
    """Top-level port combining dispatch, health, and discovery concerns.

    The original ``health``/``cancel`` surface is preserved. New methods
    (``worker``, ``dispatch`` (keyword-only, returns
    :class:`JobResult`), ``ping``, ``protocol_info``, ``close``) layer
    in MCP protocol support without breaking the existing
    ``health``/``cancel`` contract.

    ``close`` is intentionally synchronous so the existing
    ``CostAwareRouter`` (which flushes the audit log synchronously) and
    the ``httpx``-backed ``OmniHttpAdapter`` can both satisfy the
    protocol without an extra coroutine wrapper. The MCP composition
    layer invokes it directly in its SIGTERM/SIGINT handler.
    """

    client: Any

    # ----- core dispatch surface (existing + new) ------------------------

    async def health(self) -> dict[str, Any]:
        """Return backend health information as a raw dict (legacy)."""

    def cancel(self, request_id: str) -> bool:
        """Cancel a previously created request."""

    def worker(self, tier: str) -> Any:
        """Return a per-tier async callable bound to ``tier``.

        The return type is intentionally broad (``Any``) so that
        different router implementations (the ``TierWorker``
        in :mod:`dispatch_mcp.core.cost_middleware`, the
        ``_TierWorker`` in :mod:`dispatch_mcp.adapters.omni_http`,
        and any test fakes) can satisfy the port without
        inheriting from a common base class. The contract
        is: ``await worker(message)`` resolves to a
        :class:`JobResult`.
        """

    async def dispatch_message(
        self,
        *,
        tier: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> JobResult:
        """Dispatch ``message`` to ``tier`` and return a typed :class:`JobResult`."""

    # ----- MCP protocol extensions ---------------------------------------

    async def ping(self) -> JobResult:
        """Issue a low-cost liveness probe; never raises."""

    def protocol_info(self) -> ProtocolInfo:
        """Return the protocol discovery payload (synchronous, no I/O)."""

    def close(self) -> None:
        """Release adapter-held resources (HTTP clients, file handles, ...).

        Synchronous so the SIGTERM/SIGINT handler in
        :mod:`dispatch_mcp.server` can invoke it directly
        without an event loop. The :class:`AuditLog` flush it
        triggers is also synchronous.
        """


__all__ = ["Router", "Worker"]
