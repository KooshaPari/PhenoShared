"""Tests for the OmniHttpAdapter transport."""

from __future__ import annotations

import httpx
import respx

from dispatch_mcp.adapters.omni_http import OmniHttpAdapter
from dispatch_mcp.core.port import Router, Worker
from dispatch_mcp.core.protocol import ProtocolInfo


@respx.mock
def test_dispatch_returns_dict() -> None:
    route = respx.post("https://omni.example/dispatch").mock(
        return_value=httpx.Response(200, json={"ok": True, "status": "queued"})
    )
    adapter = OmniHttpAdapter("https://omni.example")

    result = adapter.dispatch("hello", "worker", {"priority": "high"})

    assert route.called
    assert isinstance(result, dict)
    assert result == {"ok": True, "status": "queued"}


@respx.mock
def test_dispatch_sanitizes_internal_fields() -> None:
    # The adapter must strip internal-only fields the upstream
    # backend leaks (hostnames, stack traces) before forwarding
    # to the MCP tool layer.
    respx.post("https://omni.example/dispatch").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "message": "queued",
                "internal_host": "omni-1.local",
                "stack_trace": "Traceback (most recent call last):\n  ...",
            },
        )
    )
    adapter = OmniHttpAdapter("https://omni.example")

    result = adapter.dispatch("hello", "worker")

    assert result == {"ok": True, "message": "queued"}


@respx.mock
def test_health_handles_200() -> None:
    route = respx.get("https://omni.example/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    adapter = OmniHttpAdapter("https://omni.example")

    result = adapter.health()

    assert route.called
    assert result["status"] == "ok"


@respx.mock
def test_cancel_returns_bool() -> None:
    route = respx.post("https://omni.example/cancel").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    adapter = OmniHttpAdapter("https://omni.example")

    result = adapter.cancel("req-123")

    assert route.called
    assert isinstance(result, bool)
    assert result is True


# ----------------------------------------------------------- protocol surface


def test_adapter_satisfies_router_protocol() -> None:
    """Structural check: the adapter must implement the full Router port."""
    adapter = OmniHttpAdapter("https://omni.example")
    assert isinstance(adapter, Router)


def test_adapter_protocol_info_is_typed() -> None:
    adapter = OmniHttpAdapter("https://omni.example", server_vendor="Phenotype")
    info = adapter.protocol_info()

    assert isinstance(info, ProtocolInfo)
    assert info.server == "dispatch-mcp"
    assert info.serverInfo is not None
    assert info.serverInfo.name == "dispatch-mcp"
    assert info.serverInfo.vendor == "Phenotype"
    # The version list is sorted oldest → newest and non-empty:
    assert len(info.supportedVersions) >= 1
    assert info.defaultVersion in info.supportedVersions
    assert info.negotiatedVersion in info.supportedVersions
    # Capability flags default to tools=True and resources=False:
    assert info.capabilities.tools is True
    assert info.capabilities.resources is False
    # Handshake documentation is present so clients can self-describe:
    assert "initialize" in info.handshake
    assert "ping" in info.handshake


@respx.mock
def test_adapter_worker_satisfies_worker_protocol() -> None:
    """The factory must return a typed Worker bound to a tier."""
    respx.post("https://omni.example/dispatch").mock(
        return_value=httpx.Response(200, json={"ok": True, "message": "queued"})
    )
    adapter = OmniHttpAdapter("https://omni.example")
    worker = adapter.worker("worker")

    assert isinstance(worker, Worker)
    # Legacy positional dispatch still works:
    assert worker.dispatch("hello", "worker") == {
        "ok": True,
        "message": "queued",
    }


@respx.mock
def test_adapter_dispatch_message_returns_typed_result() -> None:
    """``dispatch_message`` (the new keyword-only API) returns a JobResult."""
    respx.post("https://omni.example/dispatch").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "tier": "main", "message": "ok", "status": "ok"},
        )
    )
    adapter = OmniHttpAdapter("https://omni.example")

    import asyncio

    result = asyncio.run(adapter.dispatch_message(tier="main", message="hi"))
    assert result.ok is True
    assert result.tier == "main"
    assert result.message == "ok"


@respx.mock
def test_adapter_dispatch_message_handles_upstream_error() -> None:
    """A transport error must coerce into a typed failure, not raise."""
    respx.post("https://omni.example/dispatch").mock(
        return_value=httpx.Response(500, text="boom")
    )
    adapter = OmniHttpAdapter("https://omni.example")

    import asyncio

    result = asyncio.run(adapter.dispatch_message(tier="main", message="hi"))
    assert result.ok is False
    assert result.tier == "main"
    assert result.error is not None


@respx.mock
def test_adapter_ping_returns_alive_on_2xx() -> None:
    route = respx.get("https://omni.example/ping").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    adapter = OmniHttpAdapter("https://omni.example")

    import asyncio

    result = asyncio.run(adapter.ping())
    assert route.called
    assert result.status == "alive"


@respx.mock
def test_adapter_ping_returns_unreachable_on_5xx() -> None:
    respx.get("https://omni.example/ping").mock(
        return_value=httpx.Response(503, text="nope")
    )
    adapter = OmniHttpAdapter("https://omni.example")

    import asyncio

    result = asyncio.run(adapter.ping())
    assert result.status == "unreachable"


def test_adapter_close_swallows_errors() -> None:
    """``close()`` must never raise — it's called from signal handlers."""
    adapter = OmniHttpAdapter("https://omni.example")
    # Even if the inner client is already closed, close() should not raise.
    adapter._client.close()
    adapter.close()  # idempotent


def test_adapter_client_property() -> None:
    adapter = OmniHttpAdapter("https://omni.example")
    # The ``client`` property is exposed so the cost middleware
    # and health probes can share the transport handle.
    assert isinstance(adapter.client, httpx.Client)
