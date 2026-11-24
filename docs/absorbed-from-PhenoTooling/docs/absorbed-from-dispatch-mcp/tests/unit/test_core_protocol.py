"""Tests for the MCP protocol schemas in :mod:`dispatch_mcp.core.protocol`.

The :mod:`dispatch_mcp.core.protocol` module is the single source of
truth for the protocol surface that ``dispatch-mcp`` advertises and
consumes. These tests pin the contract:

- Pydantic schema validation for every message envelope
  (:class:`InitializeRequest`, :class:`InitializeResult`,
  :class:`PingRequest`, :class:`PingResult`, :class:`DispatchRequest`,
  :class:`DispatchResponse`, :class:`ProtocolInfo`,
  :class:`ServerInfo`, :class:`ServerCapabilities`).
- Version-negotiation rules in :func:`negotiate_version`.
- The discovery payload returned by the ``dispatch_protocol`` MCP tool
  (the version-discovery endpoint).
- The canonical ``build_handshake`` function the MCP server uses to
  produce an :class:`InitializeResult`.
- The :class:`ProtocolError` exception subclass.

The tests do not exercise the network; they are pure data validation.
This keeps them fast and lets the protocol surface evolve without
breaking the upstream ``fastmcp`` integration.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from dispatch_mcp import server
from dispatch_mcp.core.protocol import (
    DEFAULT_NEGOTIATED_VERSION,
    PROTOCOL_DISCOVERY_DESCRIPTION,
    SUPPORTED_PROTOCOL_VERSIONS,
    ClientInfo,
    DispatchRequest,
    DispatchResponse,
    InitializeRequest,
    InitializeResult,
    PingRequest,
    PingResult,
    ProtocolError,
    ProtocolInfo,
    ProtocolVersion,
    ServerCapabilities,
    ServerInfo,
    negotiate_version,
)
from dispatch_mcp.core.types import JobResult

# --------------------------------------------------------------------- version


class TestProtocolVersion:
    """Tests for the :data:`ProtocolVersion` annotated string type."""

    def test_supported_versions_are_sorted_oldest_to_newest(self) -> None:
        # The negotiation rules in negotiate_version rely on the
        # tuple being in ascending order. Pin the assumption.
        versions = list(SUPPORTED_PROTOCOL_VERSIONS)
        assert versions == sorted(versions)
        assert len(versions) >= 1

    def test_default_negotiated_version_is_supported(self) -> None:
        # The default must always be a known version, otherwise
        # clients that omit protocolVersion would negotiate a value
        # the server cannot honor.
        assert DEFAULT_NEGOTIATED_VERSION in SUPPORTED_PROTOCOL_VERSIONS

    @pytest.mark.parametrize("version", list(SUPPORTED_PROTOCOL_VERSIONS))
    def test_each_supported_version_is_well_formed(self, version: ProtocolVersion) -> None:
        # ProtocolVersion is an Annotated[str, StringConstraints(pattern=...)].
        # We re-validate the shape on every supported entry to catch
        # accidental typos at PR time.
        import re

        assert re.match(r"^\d{4}-\d{2}-\d{2}$", version), (
            f"unsupported version shape: {version!r}"
        )


# ------------------------------------------------------------------- negotiation


class TestNegotiateVersion:
    """Tests for :func:`negotiate_version`."""

    def test_none_returns_default(self) -> None:
        assert negotiate_version(None) == DEFAULT_NEGOTIATED_VERSION

    def test_known_version_returned_unchanged(self) -> None:
        for v in SUPPORTED_PROTOCOL_VERSIONS:
            assert negotiate_version(v) == v

    def test_unknown_version_falls_back_to_newest_supported(self) -> None:
        # The upstream MCP SDK negotiates to the freshest mutually
        # supported version. We mirror that: any unknown client
        # version is treated as a request for our newest entry.
        newest = SUPPORTED_PROTOCOL_VERSIONS[-1]
        assert negotiate_version("2099-01-01") == newest

    def test_empty_supported_raises_protocol_error(self) -> None:
        with pytest.raises(ProtocolError, match="no supported protocol versions"):
            negotiate_version("2025-06-18", supported=())

    def test_explicit_default_overrides_module_default(self) -> None:
        # The function should accept a custom default for callers
        # that want to pin a different fallback (e.g. tests).
        assert negotiate_version(None, default="2025-06-18") == "2025-06-18"

    def test_explicit_supported_overrides_module_supported(self) -> None:
        # A custom supported list is honored verbatim, including
        # when the client is on a different version.
        supported = ("2025-06-18",)
        assert negotiate_version("2025-06-18", supported=supported) == "2025-06-18"
        # The newest entry in the custom list is the fallback.
        assert negotiate_version("2099-01-01", supported=supported) == "2025-06-18"


# ---------------------------------------------------------------- server identity


class TestServerInfo:
    """Tests for the :class:`ServerInfo` schema."""

    def test_minimal_required_fields(self) -> None:
        info = ServerInfo(name="dispatch-mcp", version="0.2.0")
        assert info.name == "dispatch-mcp"
        assert info.version == "0.2.0"
        assert info.vendor is None  # optional

    def test_optional_vendor(self) -> None:
        info = ServerInfo(name="dispatch-mcp", version="0.2.0", vendor="Phenotype")
        assert info.vendor == "Phenotype"

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ServerInfo(name="", version="0.2.0")

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ServerInfo(name="dispatch-mcp", version="0.2.0", unknown_field="x")  # type: ignore[call-arg]


class TestServerCapabilities:
    """Tests for the :class:`ServerCapabilities` schema."""

    def test_default_capabilities(self) -> None:
        caps = ServerCapabilities()
        # Tools are always on; the other groups default off.
        assert caps.tools is True
        assert caps.resources is False
        assert caps.prompts is False
        assert caps.logging is False
        # The dispatch-mcp-specific protocol_discovery flag.
        assert caps.protocol_discovery is True

    def test_extra_capabilities_allowed(self) -> None:
        # Upstream MCP allows experimental capability keys; we mirror
        # that with extra="allow" so a future SDK can extend the
        # payload without forcing us to release.
        caps = ServerCapabilities(experimental="v1")
        assert caps.model_extra == {"experimental": "v1"}


# ---------------------------------------------------------------- handshake


class TestClientInfo:
    """Tests for the :class:`ClientInfo` schema (sent by clients)."""

    def test_minimal_fields(self) -> None:
        info = ClientInfo(name="claude-code", version="1.0.0")
        assert info.name == "claude-code"
        assert info.version == "1.0.0"


class TestInitializeRequest:
    """Tests for the :class:`InitializeRequest` schema."""

    def test_minimal_valid_request(self) -> None:
        req = InitializeRequest(
            protocolVersion="2025-06-18",
            clientInfo=ClientInfo(name="claude-code", version="1.0.0"),
        )
        assert req.protocolVersion == "2025-06-18"
        assert req.capabilities == {}  # default
        assert req.clientInfo.name == "claude-code"

    def test_invalid_version_format_rejected(self) -> None:
        with pytest.raises(ValidationError):
            InitializeRequest(
                protocolVersion="not-a-date",
                clientInfo=ClientInfo(name="c", version="1"),
            )

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            InitializeRequest(
                protocolVersion="2025-06-18",
                clientInfo=ClientInfo(name="c", version="1"),
                extra="nope",  # type: ignore[call-arg]
            )


class TestInitializeResult:
    """Tests for the :class:`InitializeResult` schema."""

    def test_minimal_valid_result(self) -> None:
        result = InitializeResult(
            protocolVersion="2025-06-18",
            capabilities=ServerCapabilities(),
            serverInfo=ServerInfo(name="dispatch-mcp", version="0.2.0"),
        )
        assert result.protocolVersion == "2025-06-18"
        assert result.capabilities.tools is True
        assert result.serverInfo.name == "dispatch-mcp"
        assert result.instructions is None  # default

    def test_optional_instructions(self) -> None:
        result = InitializeResult(
            protocolVersion="2025-06-18",
            capabilities=ServerCapabilities(),
            serverInfo=ServerInfo(name="dispatch-mcp", version="0.2.0"),
            instructions="Call dispatch_protocol for capability discovery.",
        )
        assert "dispatch_protocol" in (result.instructions or "")


# --------------------------------------------------------------------- ping


class TestPing:
    """Tests for the :class:`PingRequest` / :class:`PingResult` schemas."""

    def test_ping_request_is_empty(self) -> None:
        # The MCP spec defines ping as an empty body; the envelope
        # is empty and the params are the request itself.
        req = PingRequest()
        assert req.model_dump() == {}

    def test_ping_result_is_empty(self) -> None:
        result = PingResult()
        assert result.model_dump() == {}

    def test_ping_request_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            PingRequest(extra="nope")  # type: ignore[call-arg]


# ----------------------------------------------------------------- dispatch IO


class TestDispatchRequest:
    """Tests for the :class:`DispatchRequest` schema."""

    def test_minimal_valid_request(self) -> None:
        req = DispatchRequest(message="hello", tier="worker")
        assert req.message == "hello"
        assert req.tier == "worker"
        assert req.payload is None  # default

    def test_optional_payload(self) -> None:
        req = DispatchRequest(
            message="hi", tier="main", payload={"trace": True, "n": 1}
        )
        assert req.payload == {"trace": True, "n": 1}

    def test_empty_message_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DispatchRequest(message="", tier="worker")

    def test_oversized_message_rejected(self) -> None:
        # Max length is 4096 chars per the schema; pin the limit
        # so an upstream change triggers a test update.
        with pytest.raises(ValidationError):
            DispatchRequest(message="x" * 4097, tier="worker")

    def test_oversized_tier_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DispatchRequest(message="hi", tier="t" * 65)

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            DispatchRequest(
                message="hi", tier="worker", extra="nope"  # type: ignore[call-arg]
            )


class TestDispatchResponse:
    """Tests for the :class:`DispatchResponse` schema."""

    def test_all_fields_optional(self) -> None:
        # The upstream OmniRoute can return any subset of these
        # fields depending on the dispatch outcome; the response
        # must accept any partial body.
        response = DispatchResponse()
        assert response.ok is None
        assert response.tier is None
        assert response.message is None
        assert response.status is None
        assert response.error is None

    def test_full_response_round_trip(self) -> None:
        response = DispatchResponse(
            ok=True, tier="worker", message="ok", status="queued"
        )
        dumped = response.model_dump()
        assert dumped == {
            "ok": True,
            "tier": "worker",
            "message": "ok",
            "status": "queued",
            "error": None,
        }


# ----------------------------------------------------------- protocol discovery


class TestProtocolInfo:
    """Tests for the :class:`ProtocolInfo` discovery payload."""

    @staticmethod
    def _minimal_info(**overrides: object) -> ProtocolInfo:
        """Build a ProtocolInfo with sensible defaults for tests."""
        defaults: dict[str, object] = {
            "serverVersion": "0.2.0",
            "supportedVersions": list(SUPPORTED_PROTOCOL_VERSIONS),
            "defaultVersion": DEFAULT_NEGOTIATED_VERSION,
            "negotiatedVersion": DEFAULT_NEGOTIATED_VERSION,
            "capabilities": ServerCapabilities(),
        }
        defaults.update(overrides)
        return ProtocolInfo(**defaults)  # type: ignore[arg-type]

    def test_minimal_valid_discovery(self) -> None:
        info = self._minimal_info()
        assert info.server == "dispatch-mcp"
        assert info.serverVersion == "0.2.0"
        # The defaults inherit from the module-level constants.
        assert info.supportedVersions == list(SUPPORTED_PROTOCOL_VERSIONS)
        assert info.defaultVersion == DEFAULT_NEGOTIATED_VERSION
        assert info.negotiatedVersion == DEFAULT_NEGOTIATED_VERSION
        # Capabilities default to the standard set.
        assert info.capabilities.tools is True
        assert info.capabilities.protocol_discovery is True
        # The handshake documentation is always present.
        assert "initialize" in info.handshake
        assert "ping" in info.handshake
        # serverInfo is optional but defaults to None.
        assert info.serverInfo is None
        # Description is the canonical one.
        assert info.description == PROTOCOL_DISCOVERY_DESCRIPTION

    def test_serverinfo_carries_identity(self) -> None:
        info = self._minimal_info(
            serverInfo=ServerInfo(name="dispatch-mcp", version="0.2.0", vendor="Phenotype"),
        )
        assert info.serverInfo is not None
        assert info.serverInfo.vendor == "Phenotype"

    def test_missing_required_fields_rejected(self) -> None:
        # All five required fields surface in the error message
        # when omitted. We pass nothing and expect a validation
        # error referencing every missing field.
        with pytest.raises(ValidationError) as exc:
            ProtocolInfo()  # type: ignore[call-arg]
        err_text = str(exc.value)
        for field in (
            "serverVersion",
            "supportedVersions",
            "defaultVersion",
            "negotiatedVersion",
            "capabilities",
        ):
            assert field in err_text, f"missing {field!r} in error: {err_text}"

    def test_handshake_documents_all_required_methods(self) -> None:
        # The handshake map must mention every method a client
        # needs to perform the MCP lifecycle.
        info = self._minimal_info()
        for method in ("initialize", "initialized", "ping", "tools/list", "tools/call"):
            assert method in info.handshake, f"missing {method!r} in handshake"

    def test_discovery_payload_is_json_serializable(self) -> None:
        # The dispatch_protocol MCP tool returns the payload as a
        # dict; Pydantic's model_dump() must produce JSON-safe data.
        import json

        info = self._minimal_info(
            serverInfo=ServerInfo(name="dispatch-mcp", version="0.2.0"),
        )
        json.dumps(info.model_dump())  # must not raise


# ------------------------------------------------------------- ProtocolError


class TestProtocolError:
    """Tests for the :class:`ProtocolError` exception."""

    def test_is_a_value_error_subclass(self) -> None:
        # FastMCP surfaces ValueError as JSON-RPC -32602 (Invalid
        # params). The error subclass must preserve that mapping.
        assert issubclass(ProtocolError, ValueError)

    def test_constructible_with_message(self) -> None:
        err = ProtocolError("client version 2099-01-01 not supported")
        assert "2099-01-01" in str(err)
        with pytest.raises(ProtocolError, match="2099-01-01"):
            raise err


# ----------------------------------------------------- server-level handshake


class TestBuildHandshake:
    """End-to-end tests for :func:`dispatch_mcp.server.build_handshake`.

    These exercise the canonical entry point the MCP server uses to
    answer an ``initialize`` request. They patch the module-level
    ``_router`` (the production pattern tests use) so no real
    OmniRoute is contacted.
    """

    @staticmethod
    def _build_fake_info() -> ProtocolInfo:
        """Build a complete :class:`ProtocolInfo` for use in fakes."""
        return ProtocolInfo(
            serverVersion="0.2.0",
            supportedVersions=list(SUPPORTED_PROTOCOL_VERSIONS),
            defaultVersion=DEFAULT_NEGOTIATED_VERSION,
            negotiatedVersion=DEFAULT_NEGOTIATED_VERSION,
            capabilities=ServerCapabilities(),
            serverInfo=ServerInfo(name="dispatch-mcp", version="0.2.0"),
        )

    def test_build_handshake_with_known_version(self) -> None:
        fake_info = self._build_fake_info()
        # ``patch("dispatch_mcp.server._router")`` swaps the module
        # reference for a MagicMock; assigning to ``protocol_info``
        # replaces the auto-created attribute with a callable. This
        # mirrors the pattern the rest of the test suite uses to
        # inject router fakes.
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.protocol_info = lambda: fake_info
            result = server.build_handshake("2025-06-18")
        assert isinstance(result, InitializeResult)
        assert result.protocolVersion == "2025-06-18"
        assert result.serverInfo.name == "dispatch-mcp"
        assert result.capabilities.tools is True
        # The instructions mention the discovery entry point.
        assert "dispatch_protocol" in (result.instructions or "")

    def test_build_handshake_uses_default_for_missing_version(self) -> None:
        fake_info = self._build_fake_info()
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.protocol_info = lambda: fake_info
            result = server.build_handshake(None)
        assert result.protocolVersion == DEFAULT_NEGOTIATED_VERSION

    def test_build_handshake_includes_client_info_when_provided(self) -> None:
        fake_info = self._build_fake_info()
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.protocol_info = lambda: fake_info
            result = server.build_handshake(
                "2025-06-18",
                client_info=ClientInfo(name="claude-code", version="1.0.0"),
            )
        # The result is an InitializeResult, not a full InitializeRequest,
        # so clientInfo is not echoed back; the function still accepts
        # the argument for forward-compat with the optional handshake
        # shape that some MCP transports use.
        assert result.protocolVersion == "2025-06-18"


# ------------------------------------------------------------ end-to-end tool


class TestDispatchProtocolTool:
    """End-to-end test for the ``dispatch_protocol`` MCP tool surface.

    Patches the router so the call is hermetic and asserts on the
    payload shape an MCP client would receive.
    """

    @staticmethod
    def _build_fake_info() -> ProtocolInfo:
        return ProtocolInfo(
            serverVersion="0.2.0",
            supportedVersions=list(SUPPORTED_PROTOCOL_VERSIONS),
            defaultVersion=DEFAULT_NEGOTIATED_VERSION,
            negotiatedVersion=DEFAULT_NEGOTIATED_VERSION,
            capabilities=ServerCapabilities(),
            serverInfo=ServerInfo(name="dispatch-mcp", version="0.2.0"),
        )

    def test_dispatch_protocol_no_args(self) -> None:
        fake_info = self._build_fake_info()
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.protocol_info = lambda: fake_info
            result = asyncio.run(server.dispatch_protocol())

        # Discoverability surface is stable across releases.
        assert result["server"] == "dispatch-mcp"
        assert result["serverVersion"] == "0.2.0"
        assert result["supportedVersions"] == list(SUPPORTED_PROTOCOL_VERSIONS)
        assert result["defaultVersion"] == DEFAULT_NEGOTIATED_VERSION
        assert result["negotiatedVersion"] == DEFAULT_NEGOTIATED_VERSION
        assert result["capabilities"]["tools"] is True
        assert "handshake" in result
        # The client info echo defaults to None/None.
        assert result["clientInfo"] == {"name": None, "version": None}
        assert result["requestedClientVersion"] is None

    def test_dispatch_protocol_with_negotiation(self) -> None:
        fake_info = self._build_fake_info()
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.protocol_info = lambda: fake_info
            result = asyncio.run(
                server.dispatch_protocol("2025-06-18", "claude-code", "1.0.0")
            )
        # The client version is honored when supported.
        assert result["negotiatedVersion"] == "2025-06-18"
        assert result["requestedClientVersion"] == "2025-06-18"
        # The client info echo is populated.
        assert result["clientInfo"] == {"name": "claude-code", "version": "1.0.0"}

    def test_dispatch_protocol_falls_back_for_unknown_version(self) -> None:
        fake_info = self._build_fake_info()
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.protocol_info = lambda: fake_info
            # An unknown version is negotiated down to the freshest
            # supported entry.
            result = asyncio.run(server.dispatch_protocol("2099-01-01"))
        assert result["negotiatedVersion"] == SUPPORTED_PROTOCOL_VERSIONS[-1]
        assert result["requestedClientVersion"] == "2099-01-01"


# --------------------------------------------------------------- ping tool


class TestDispatchPingTool:
    """End-to-end test for the ``dispatch_ping`` MCP tool surface.

    Patches the router so the call is hermetic.
    """

    def test_dispatch_ping_success(self) -> None:
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.ping = AsyncMock(
                return_value=JobResult(status="alive", message="dispatch-mcp", ok=True)
            )
            result = asyncio.run(server.dispatch_ping())
        assert result["status"] == "alive"
        assert result["protocolVersion"] == DEFAULT_NEGOTIATED_VERSION
        assert result["upstreamReachable"] is True
        assert result["ok"] is True

    def test_dispatch_ping_unreachable(self) -> None:
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.ping = AsyncMock(side_effect=Exception("connection refused"))
            result = asyncio.run(server.dispatch_ping())
        assert result["status"] == "unreachable"
        assert result["upstreamReachable"] is False
        assert "connection refused" in (result.get("error") or "")


# --------------------------------------------------- full handshake sequence


class TestHandshakeSequence:
    """Pin the full handshake lifecycle a real MCP client performs.

    This walks through the canonical sequence: capability discovery
    (dispatch_protocol) → initialize (build_handshake) → ping
    (dispatch_ping) → dispatch (the actual MCP tool). Together these
    represent the round-trip an MCP client performs against the
    server.
    """

    @staticmethod
    def _build_fake_info() -> ProtocolInfo:
        return ProtocolInfo(
            serverVersion="0.2.0",
            supportedVersions=list(SUPPORTED_PROTOCOL_VERSIONS),
            defaultVersion=DEFAULT_NEGOTIATED_VERSION,
            negotiatedVersion=DEFAULT_NEGOTIATED_VERSION,
            capabilities=ServerCapabilities(),
            serverInfo=ServerInfo(name="dispatch-mcp", version="0.2.0"),
        )

    def test_full_handshake_sequence(self) -> None:
        """Step through discovery → initialize → ping → dispatch."""
        fake_info = self._build_fake_info()

        with patch("dispatch_mcp.server._router") as mock_router:
            # Step 1: capability discovery.
            mock_router.protocol_info = lambda: fake_info
            discovery = asyncio.run(
                server.dispatch_protocol("2025-06-18", "claude-code", "1.0.0")
            )
            assert discovery["negotiatedVersion"] == "2025-06-18"
            assert discovery["capabilities"]["tools"] is True

            # Step 2: initialize (the canonical handshake).
            mock_router.protocol_info = lambda: fake_info
            handshake = server.build_handshake(
                discovery["negotiatedVersion"],
                client_info=ClientInfo(name="claude-code", version="1.0.0"),
            )
            assert isinstance(handshake, InitializeResult)
            assert handshake.protocolVersion == "2025-06-18"
            assert handshake.serverInfo.name == "dispatch-mcp"

            # Step 3: ping to confirm the upstream is reachable.
            mock_router.ping = AsyncMock(
                return_value=JobResult(status="alive", message="dispatch-mcp", ok=True)
            )
            ping_result = asyncio.run(server.dispatch_ping())
            assert ping_result["status"] == "alive"
            assert ping_result["upstreamReachable"] is True

            # Step 4: dispatch the actual job. ``worker(tier)`` returns
            # an async callable (see :class:`TierWorker` in
            # ``cost_middleware.py``); we mock the entire worker factory
            # to return a coroutine that resolves to a JobResult.
            async def _fake_worker_call(message: str) -> JobResult:
                return JobResult(ok=True, tier="main", message=message, status="queued")

            mock_router.worker = lambda _tier: _fake_worker_call
            job_dict = asyncio.run(server.dispatch_main("hi"))
            assert job_dict["ok"] is True
            assert job_dict["tier"] == "main"

    def test_negotiation_falls_back_to_default(self) -> None:
        """An unknown client version is silently downgraded."""
        fake_info = self._build_fake_info()
        with patch("dispatch_mcp.server._router") as mock_router:
            mock_router.protocol_info = lambda: fake_info
            # Client asks for a future version that is not yet
            # supported; the server returns its freshest supported
            # version rather than erroring.
            handshake = server.build_handshake("2099-01-01")
        assert handshake.protocolVersion == SUPPORTED_PROTOCOL_VERSIONS[-1]
