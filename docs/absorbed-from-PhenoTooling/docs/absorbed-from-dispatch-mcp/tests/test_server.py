"""Tests for dispatch_mcp.server."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from dispatch_mcp.core.types import JobResult


def run_async(result: object) -> object:
    return asyncio.run(result)


class TestDispatchCustom:
    def test_dispatch_custom_success(self) -> None:
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.dispatch_message = AsyncMock(
                return_value=JobResult(ok=True, tier="worker", message="hello")
            )

            from dispatch_mcp.server import dispatch_custom

            result = run_async(dispatch_custom("worker", "hello"))
            mock_router.dispatch_message.assert_awaited_once_with(
                tier="worker", message="hello"
            )
            assert result == {"ok": True, "tier": "worker", "message": "hello"}

    def test_dispatch_custom_propagates_router_error(self) -> None:
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.dispatch_message = AsyncMock(side_effect=RuntimeError("boom"))

            from dispatch_mcp.server import dispatch_custom

            with pytest.raises(RuntimeError, match="boom"):
                run_async(dispatch_custom("main", "test"))

    def test_invalid_tier_raises(self) -> None:
        from dispatch_mcp.server import dispatch_custom

        with pytest.raises(ValueError, match="Invalid tier 'rogue'"):
            run_async(dispatch_custom("rogue", "test"))

    def test_missing_omniroute_url_bubbles_from_router(self) -> None:
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.dispatch_message = AsyncMock(
                side_effect=ValueError("OMNIROUTE_URL missing")
            )

            from dispatch_mcp.server import dispatch_custom

            with pytest.raises(ValueError, match="OMNIROUTE_URL"):
                run_async(dispatch_custom("worker", "test"))


class TestDispatchHealth:
    def test_dispatch_health_success(self) -> None:
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.health = AsyncMock(return_value=JobResult(status="ok", error=None))

            from dispatch_mcp.server import dispatch_health

            result = run_async(dispatch_health())
            mock_router.health.assert_awaited_once_with()
            assert result == {"status": "ok"}


class TestNamedDispatchTools:
    @pytest.mark.parametrize(
        "tool_func,tier",
        [
            ("dispatch_worker", "worker"),
            ("dispatch_main", "main"),
            ("dispatch_codeman", "codeman"),
            ("dispatch_freetier", "freetier"),
            ("dispatch_kimi", "kimi"),
            ("dispatch_kimi_thinking", "kimi_thinking"),
            ("dispatch_minimax", "minimax"),
            ("dispatch_opus", "opus"),
            ("dispatch_haiku", "haiku"),
            ("dispatch_gemini", "gemini"),
        ],
    )
    def test_named_tool_exists_and_callable(self, tool_func: str, tier: str) -> None:
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.worker.return_value = AsyncMock(
                return_value=JobResult(ok=True, tier=tier, message="hello")
            )

            from dispatch_mcp import server

            func = getattr(server, tool_func)
            assert callable(func)
            result = run_async(func("hello"))
            mock_router.worker.assert_called_with(tier)
            assert result == {"ok": True, "tier": tier, "message": "hello"}

    def test_dispatch_worker_rejects_oversized_message(self) -> None:
        with patch("dispatch_mcp.server._router") as mock_router:
            from dispatch_mcp.server import dispatch_worker

            oversized = "x" * (4096 + 1)
            with pytest.raises(ValueError, match="exceeds maximum length"):
                run_async(dispatch_worker(oversized))
            mock_router.worker.assert_not_called()


class TestSanitizeResponse:
    def test_sanitize_response_strips_internal_keys(self) -> None:
        from dispatch_mcp.adapters.omni_http import OmniHttpAdapter

        response = {
            "ok": True,
            "tier": "worker",
            "message": "hello",
            "internal_host": "omniroute-1.internal",
            "stack_trace": "Traceback (most recent call last):\n  ...",
            "db_password": "hunter2",
        }
        # Static method — call on the class directly so we
        # don't need to construct a real adapter.
        result = OmniHttpAdapter._sanitize_response(response)
        assert result == {"ok": True, "tier": "worker", "message": "hello"}

    def test_sanitize_response_handles_non_dict(self) -> None:
        from dispatch_mcp.adapters.omni_http import OmniHttpAdapter

        # All of these must coerce to a safe empty dict so the
        # public surface never raises on unexpected upstream
        # payloads.
        assert OmniHttpAdapter._sanitize_response(None) == {}
        assert OmniHttpAdapter._sanitize_response([]) == {}
        assert OmniHttpAdapter._sanitize_response("oops") == {}
        assert OmniHttpAdapter._sanitize_response(42) == {}


class TestDispatchLiveness:
    def test_dispatch_liveness_returns_status(self) -> None:
        from dispatch_mcp.server import dispatch_liveness

        result = run_async(dispatch_liveness())
        assert result == {"status": "alive", "message": "dispatch-mcp"}


class TestDispatchPing:
    def test_dispatch_ping_uses_router_ping(self) -> None:
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.ping = AsyncMock(
                return_value=JobResult(status="alive", message="pong")
            )

            from dispatch_mcp.server import dispatch_ping

            result = run_async(dispatch_ping())
            mock_router.ping.assert_awaited_once_with()
            # The tool enriches the router result with a protocol
            # version and an explicit upstream reachability flag
            # so clients can render the outcome without having
            # to consult two separate fields.
            assert result["status"] == "alive"
            assert result["message"] == "pong"
            assert result["upstreamReachable"] is True
            assert result["protocolVersion"]  # negotiated version, non-empty


class TestDispatchProtocol:
    def test_dispatch_protocol_uses_router_protocol_info(self) -> None:
        with patch("dispatch_mcp.server._router") as mock_router:
            from dispatch_mcp.core.protocol import (
                ProtocolInfo,
                ServerCapabilities,
                ServerInfo,
            )

            mock_router.protocol_info = lambda: ProtocolInfo(
                serverVersion="0.2.0",
                supportedVersions=["2024-11-05", "2025-03-26"],
                defaultVersion="2025-03-26",
                negotiatedVersion="2025-03-26",
                capabilities=ServerCapabilities(),
                serverInfo=ServerInfo(name="dispatch-mcp", version="0.2.0"),
            )

            from dispatch_mcp.server import dispatch_protocol

            result = run_async(dispatch_protocol())
            # Discoverability surface is stable:
            assert result["server"] == "dispatch-mcp"
            assert "supportedVersions" in result
            assert "defaultVersion" in result
            assert "negotiatedVersion" in result
            assert "capabilities" in result
            assert "serverInfo" in result
            assert "handshake" in result
            # The client_info echo defaults to None/None:
            assert result["clientInfo"] == {"name": None, "version": None}
            assert result["requestedClientVersion"] is None

    def test_dispatch_protocol_negotiates_client_version(self) -> None:
        with patch("dispatch_mcp.server._router") as mock_router:
            from dispatch_mcp.core.protocol import (
                ProtocolInfo,
                ServerCapabilities,
                ServerInfo,
            )

            mock_router.protocol_info = lambda: ProtocolInfo(
                serverVersion="0.2.0",
                supportedVersions=["2024-11-05", "2025-03-26", "2025-06-18"],
                defaultVersion="2025-03-26",
                negotiatedVersion="2025-03-26",
                capabilities=ServerCapabilities(),
                serverInfo=ServerInfo(name="dispatch-mcp", version="0.2.0"),
            )

            from dispatch_mcp.server import dispatch_protocol

            result = run_async(
                dispatch_protocol("2025-06-18", "claude-code", "1.0.0")
            )
            # Mutually supported version is honored:
            assert result["negotiatedVersion"] == "2025-06-18"
            assert result["requestedClientVersion"] == "2025-06-18"
            assert result["clientInfo"] == {"name": "claude-code", "version": "1.0.0"}

    def test_dispatch_protocol_falls_back_to_default_for_unknown_version(self) -> None:
        with patch("dispatch_mcp.server._router") as mock_router:
            from dispatch_mcp.core.protocol import (
                ProtocolInfo,
                ServerCapabilities,
                ServerInfo,
            )

            mock_router.protocol_info = lambda: ProtocolInfo(
                serverVersion="0.2.0",
                supportedVersions=["2025-03-26", "2025-06-18"],
                defaultVersion="2025-03-26",
                negotiatedVersion="2025-03-26",
                capabilities=ServerCapabilities(),
                serverInfo=ServerInfo(name="dispatch-mcp", version="0.2.0"),
            )

            from dispatch_mcp.server import dispatch_protocol

            # An unknown version falls back to the newest supported.
            result = run_async(dispatch_protocol("2099-01-01"))
            assert result["negotiatedVersion"] == "2025-06-18"


class TestBuildHandshake:
    def test_build_handshake_returns_initialize_result(self) -> None:
        from dispatch_mcp.core.protocol import InitializeResult
        from dispatch_mcp.server import build_handshake

        result = build_handshake("2025-06-18")
        assert isinstance(result, InitializeResult)
        assert result.protocolVersion == "2025-06-18"
        assert result.serverInfo.name == "dispatch-mcp"
        assert result.capabilities.tools is True
        # Instructions are surfaced so the client can show them
        # to the user:
        assert "dispatch_protocol" in (result.instructions or "")

    def test_build_handshake_uses_default_for_missing_version(self) -> None:
        from dispatch_mcp.core.protocol import DEFAULT_NEGOTIATED_VERSION
        from dispatch_mcp.server import build_handshake

        result = build_handshake(None)
        assert result.protocolVersion == DEFAULT_NEGOTIATED_VERSION
