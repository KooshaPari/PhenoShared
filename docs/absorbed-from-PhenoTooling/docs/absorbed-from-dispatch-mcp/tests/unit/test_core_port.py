"""Structural tests for the :mod:`dispatch_mcp.core.port` Protocols.

The :class:`Worker` and :class:`Router` protocols are
``@runtime_checkable`` so the MCP server can verify structural
conformance at startup. These tests pin the contract — any
adapter or fake that the rest of the suite relies on must
satisfy the full method set or it cannot be substituted in.
"""

from __future__ import annotations

from typing import Any

from dispatch_mcp.core.port import Router, Worker
from dispatch_mcp.core.protocol import ProtocolInfo
from dispatch_mcp.core.types import JobResult


class FakeWorker:
    """A minimal but complete :class:`Worker` implementation.

    Implements both the legacy positional ``dispatch`` and the
    new keyword-only ``__call__`` shapes that the cost-aware
    middleware uses to dispatch a typed :class:`JobResult`.
    """

    def dispatch(
        self,
        message: str,
        tier: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {"message": message, "tier": tier, "payload": payload or {}}

    def __call__(self, message: str) -> JobResult:
        return JobResult(ok=True, message=message, status="ok")


class FakeRouter:
    """A minimal but complete :class:`Router` implementation.

    The protocol gained many members when cost tracking and
    protocol discovery landed (``client`` attribute,
    ``worker()``, async ``dispatch_message``/``ping``,
    and ``protocol_info()``/``close()``). The fake implements
    every one with a no-op or trivial stub so the structural
    check is purely about shape, not behavior.
    """

    client: Any = None

    def __init__(self) -> None:
        self._worker = FakeWorker()

    def health(self) -> dict[str, Any]:
        return {"status": "ok"}

    def cancel(self, request_id: str) -> bool:
        return request_id == "req-123"

    def worker(self, tier: str) -> Worker:
        return self._worker

    async def dispatch_message(
        self,
        *,
        tier: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> JobResult:
        return JobResult(ok=True, tier=tier, message=message)

    async def ping(self) -> JobResult:
        return JobResult(status="alive", message="pong")

    def protocol_info(self) -> ProtocolInfo:
        from dispatch_mcp.core.protocol import (
            DEFAULT_NEGOTIATED_VERSION,
            ServerCapabilities,
            ServerInfo,
        )
        return ProtocolInfo(
            serverVersion="0.0.0+test",
            supportedVersions=[DEFAULT_NEGOTIATED_VERSION],
            defaultVersion=DEFAULT_NEGOTIATED_VERSION,
            negotiatedVersion=DEFAULT_NEGOTIATED_VERSION,
            capabilities=ServerCapabilities(),
            serverInfo=ServerInfo(name="test", version="0.0.0+test"),
        )

    async def close(self) -> None:
        return None


class NotARouter:
    """A type that should not satisfy :class:`Router`.

    Missing the ``client`` attribute and most of the methods;
    only the legacy ``health`` is present, which is not enough
    to make ``isinstance(router, Router)`` succeed.
    """

    def health(self) -> dict[str, Any]:
        return {"status": "partial"}


def test_worker_protocol_accepts_structural_implementation() -> None:
    worker = FakeWorker()

    assert isinstance(worker, Worker)
    assert worker.dispatch("hello", "worker", {"trace": True})["tier"] == "worker"
    # The new ``__call__`` shape is what the cost middleware uses.
    result = worker("hello")
    assert result.ok is True
    assert result.message == "hello"


def test_router_protocol_accepts_structural_implementation() -> None:
    router = FakeRouter()

    assert isinstance(router, Router)
    assert router.health() == {"status": "ok"}
    assert router.cancel("req-123") is True
    # The async MCP-protocol surface is also covered.
    assert router.client is None
    info = router.protocol_info()
    assert info.serverVersion == "0.0.0+test"


def test_non_conforming_type_is_rejected_by_protocol_checks() -> None:
    candidate = NotARouter()

    assert not isinstance(candidate, Router)
    assert not isinstance(candidate, Worker)
