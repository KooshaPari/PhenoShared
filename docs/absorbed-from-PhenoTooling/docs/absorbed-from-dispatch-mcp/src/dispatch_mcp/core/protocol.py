"""MCP protocol schemas, version constants, and capability models for dispatch-mcp.

This module is the canonical source of truth for the protocol surface that
``dispatch-mcp`` advertises and consumes. It is intentionally framework-free
(no FastMCP imports) so that core domain code and adapters can validate
handshake messages without dragging in the MCP server runtime.

The model here mirrors the upstream Model Context Protocol ``initialize``
handshake shape (a subset sufficient for ``dispatch-mcp``) plus the
dispatch-mcp-specific request/response envelopes. Keeping these as
Pydantic v2 ``BaseModel`` subclasses gives us free JSON schema generation,
strict validation, and type-checkable field access.

Hierarchy
---------
- :class:`ProtocolVersion` — a newtype-validated YYYY-MM-DD MCP version
  string.
- :data:`SUPPORTED_PROTOCOL_VERSIONS` — ordered list, newest-last, of
  protocol revisions this server can speak.
- :data:`DEFAULT_NEGOTIATED_VERSION` — assumed client version if the
  client omits one.
- :class:`ServerCapabilities` — what the server can do.
- :class:`ServerInfo` — identity advertised during handshake.
- :class:`InitializeRequest` / :class:`InitializeResult` — the
  ``initialize`` request/response pair.
- :class:`PingRequest` / :class:`PingResult` — liveness probe envelope.
- :class:`DispatchRequest` / :class:`DispatchResponse` — the
  dispatch-mcp-specific message envelope.
- :class:`ProtocolInfo` — the discovery payload returned by the
  ``dispatch_protocol`` MCP tool.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# ---------------------------------------------------------------------------
# Version constants
# ---------------------------------------------------------------------------

#: A protocol version string is a calendar date (ISO 8601) per the MCP spec.
ProtocolVersion = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$", min_length=10, max_length=10),
]

#: Ordered, oldest → newest, list of protocol revisions this server can speak.
#: The order matters: :func:`negotiate_version` returns the latest entry the
#: client also claims to support, falling back to the most recent mutually
#: supported version.
SUPPORTED_PROTOCOL_VERSIONS: tuple[ProtocolVersion, ...] = (
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
)

#: Version assumed when the client does not send a ``protocolVersion`` field
#: (MCP spec calls this "default negotiated version"). 2025-03-26 is the
#: value the upstream ``mcp`` Python SDK uses.
DEFAULT_NEGOTIATED_VERSION: ProtocolVersion = "2025-03-26"

#: Human-readable description attached to the :class:`ProtocolInfo` payload.
PROTOCOL_DISCOVERY_DESCRIPTION: str = (
    "dispatch-mcp advertises the supported MCP protocol versions, server "
    "identity, and capabilities, plus the JSON-RPC method names that "
    "clients use during the initialize/ping/initialized handshake."
)


def negotiate_version(
    client_version: ProtocolVersion | None,
    *,
    supported: tuple[ProtocolVersion, ...] = SUPPORTED_PROTOCOL_VERSIONS,
    default: ProtocolVersion = DEFAULT_NEGOTIATED_VERSION,
) -> ProtocolVersion:
    """Return the protocol version to use, or raise :class:`ProtocolError`.

    Selection rules, in order:

    1. If the client did not send a version (``None``), use ``default``.
    2. If the client's version is in ``supported``, use it.
    3. Otherwise, pick the most recent entry in ``supported`` (mirroring the
       upstream SDK's behavior of speaking the freshest mutually-supported
       revision). Raise :class:`ProtocolError` if the lists are empty.
    """
    if not supported:
        raise ProtocolError("server has no supported protocol versions configured")
    if client_version is None:
        return default
    if client_version in supported:
        return client_version
    # Client is on a version we know about (or claims to be). Pick the newest
    # version we still support, which is the last entry in the tuple.
    return supported[-1]


# ---------------------------------------------------------------------------
# Server identity + capabilities
# ---------------------------------------------------------------------------


class ServerInfo(BaseModel):
    """Server identity advertised during the ``initialize`` handshake."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=128)
    version: str = Field(..., min_length=1, max_length=64)
    vendor: str | None = Field(default=None, max_length=128)


class ServerCapabilities(BaseModel):
    """Capabilities advertised by the server.

    The MCP spec allows arbitrary extra keys for experimental features; we
    keep ``extra="allow"`` so an upstream SDK can extend the object without
    forcing us to release.
    """

    model_config = ConfigDict(extra="allow")

    tools: bool = True
    resources: bool = False
    prompts: bool = False
    logging: bool = False
    # dispatch-mcp-specific capability flag: server can perform the
    # version-discovery handshake.
    protocol_discovery: bool = True


# ---------------------------------------------------------------------------
# initialize handshake
# ---------------------------------------------------------------------------


class ClientInfo(BaseModel):
    """Information about the connecting client, as sent in ``initialize``."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)


class InitializeRequestParams(BaseModel):
    """Parameters of an ``initialize`` request."""

    model_config = ConfigDict(extra="allow")

    # The Pydantic field names mirror the MCP spec's camelCase
    # wire format verbatim (protocolVersion, clientInfo). N815
    # is suppressed for the class as a whole so individual
    # declarations stay clean.
    protocolVersion: ProtocolVersion  # noqa: N815
    capabilities: dict[str, object] = Field(default_factory=dict)
    clientInfo: ClientInfo  # noqa: N815


class InitializeRequest(BaseModel):
    """The ``initialize`` request body (the ``params`` field, not the envelope)."""

    model_config = ConfigDict(extra="forbid")

    protocolVersion: ProtocolVersion  # noqa: N815
    capabilities: dict[str, object] = Field(default_factory=dict)
    clientInfo: ClientInfo  # noqa: N815


class InitializeResult(BaseModel):
    """The server's response to ``initialize``."""

    model_config = ConfigDict(extra="forbid")

    protocolVersion: ProtocolVersion  # noqa: N815
    capabilities: ServerCapabilities
    serverInfo: ServerInfo  # noqa: N815
    # Optional human-readable instructions for the client to surface to the
    # user. dispatch-mcp currently has none.
    instructions: str | None = None


# ---------------------------------------------------------------------------
# ping
# ---------------------------------------------------------------------------


class PingRequest(BaseModel):
    """A ``ping`` request. Empty by spec — the body is the envelope."""

    model_config = ConfigDict(extra="forbid")


class PingResult(BaseModel):
    """A ``ping`` response. Empty by spec."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Dispatch envelope (dispatch-mcp-specific)
# ---------------------------------------------------------------------------


class DispatchRequest(BaseModel):
    """Typed envelope for a dispatch call.

    Mirrors the wire format that ``OmniHttpAdapter`` posts to OmniRoute's
    ``/dispatch`` endpoint. The ``tier`` allow-list is enforced at the
    server layer; this model only validates shape.
    """

    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=4096)
    tier: str = Field(..., min_length=1, max_length=64)
    payload: dict[str, object] | None = None


class DispatchResponse(BaseModel):
    """Typed envelope for a dispatch response.

    Matches the public :class:`dispatch_mcp.core.types.JobResult` schema.
    """

    model_config = ConfigDict(extra="forbid")

    ok: bool | None = None
    tier: str | None = None
    message: str | None = None
    status: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Protocol discovery payload
# ---------------------------------------------------------------------------


class ProtocolInfo(BaseModel):
    """Payload returned by the ``dispatch_protocol`` MCP tool.

    This is the version-discovery endpoint: clients call it to learn which
    MCP protocol versions this server supports, what its capabilities are,
    and how to perform the ``initialize`` handshake.
    """

    model_config = ConfigDict(extra="forbid")

    server: Literal["dispatch-mcp"] = "dispatch-mcp"
    serverVersion: str  # noqa: N815
    supportedVersions: list[ProtocolVersion]  # noqa: N815
    defaultVersion: ProtocolVersion  # noqa: N815
    negotiatedVersion: ProtocolVersion  # noqa: N815
    capabilities: ServerCapabilities
    serverInfo: ServerInfo | None = None  # noqa: N815
    description: str = PROTOCOL_DISCOVERY_DESCRIPTION
    handshake: dict[str, str] = Field(
        default_factory=lambda: {
            "initialize": "POST /v1/mcp  (method=initialize)",
            "initialized": "POST /v1/mcp  (notification=notifications/initialized)",
            "ping": "POST /v1/mcp  (method=ping)",
            "tools/list": "POST /v1/mcp  (method=tools/list)",
            "tools/call": "POST /v1/mcp  (method=tools/call)",
        }
    )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ProtocolError(ValueError):
    """Raised when a client requests a protocol version the server cannot honor.

    A 1:1 subclass of :class:`ValueError` so that FastMCP surfaces it as a
    JSON-RPC ``-32602`` (Invalid params) by default.
    """


__all__ = [
    "DEFAULT_NEGOTIATED_VERSION",
    "PROTOCOL_DISCOVERY_DESCRIPTION",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "ClientInfo",
    "DispatchRequest",
    "DispatchResponse",
    "InitializeRequest",
    "InitializeRequestParams",
    "InitializeResult",
    "PingRequest",
    "PingResult",
    "ProtocolError",
    "ProtocolInfo",
    "ProtocolVersion",
    "ServerCapabilities",
    "ServerInfo",
    "negotiate_version",
]
