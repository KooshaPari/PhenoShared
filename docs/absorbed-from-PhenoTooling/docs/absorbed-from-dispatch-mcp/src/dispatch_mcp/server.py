from __future__ import annotations

import logging
import os
import signal
from collections.abc import Awaitable, Callable

from fastmcp import FastMCP

from dispatch_mcp.adapters.omni_http import OmniHttpAdapter
from dispatch_mcp.core.cost_middleware import CostAwareRouter, CostMiddlewareConfig
from dispatch_mcp.core.port import Router
from dispatch_mcp.core.protocol import (
    DEFAULT_NEGOTIATED_VERSION,
    PROTOCOL_DISCOVERY_DESCRIPTION,
    SUPPORTED_PROTOCOL_VERSIONS,
    ClientInfo,
    InitializeResult,
    ProtocolVersion,
    ServerCapabilities,
    ServerInfo,
    negotiate_version,
)
from dispatch_mcp.core.types import JobResult
from dispatch_mcp.providers import LlamaCppProvider, Message

mcp = FastMCP("dispatch-mcp")
_logger = logging.getLogger("dispatch_mcp")
_log_level = os.environ.get("LOG_LEVEL", "").upper()
if _log_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
    _logger.setLevel(getattr(logging, _log_level, logging.WARNING))
# NOTE: Do not add DEBUG-level logging of tool arguments (message, tier, payload).
# Dispatch messages may contain sensitive context. If DEBUG is needed for
# troubleshooting, prefer logging route and timing only, never the payload content.
logger = _logger

MAX_MESSAGE_LENGTH = 4096  # bytes — prevents unbounded payload to OmniRoute
# Allowlist of valid dispatch tiers — dispatch_custom must use one of these.
VALID_TIERS = frozenset(
    {
        "worker",
        "main",
        "codeman",
        "freetier",
        "kimi",
        "kimi_thinking",
        "minimax",
        "opus",
        "haiku",
        "gemini",
    }
)


def _resolve_omniroute_url() -> str:
    """Resolve the OmniRoute base URL from the environment.

    Reads ``OMNIROUTE_URL`` (required by the README). For local
    dev and test ergonomics, an unset value falls back to
    ``http://localhost:20128`` (the documented default
    OmniRoute dev port). A non-``http(s)`` scheme raises
    :class:`ValueError` at startup so misconfiguration fails
    fast.
    """
    base = os.environ.get("OMNIROUTE_URL", "").strip() or "http://localhost:20128"
    if not base.startswith(("http://", "https://")):
        raise ValueError(f"OMNIROUTE_URL must use http:// or https:// scheme, got: {base!r}")
    return base.rstrip("/")


def _build_router() -> Router:
    """Construct the cost-aware router used by the MCP tools.

    Wraps :class:`OmniHttpAdapter` in :class:`CostAwareRouter`
    so every dispatch is metered, quota-checked, budgeted,
    and audited. The cost subsystem is enabled by default; set
    ``DISPATCH_COST_TRACKING=disabled`` to bypass it (e.g. in
    local debugging sessions).
    """
    enabled = os.environ.get("DISPATCH_COST_TRACKING", "enabled").lower() != "disabled"
    inner = OmniHttpAdapter(_resolve_omniroute_url())
    return CostAwareRouter(inner, config=CostMiddlewareConfig(enabled=enabled))


#: Module-level router. The :func:`_build_router` factory is
#: invoked at import time so the type is known; tests can
#: monkey-patch ``_router`` directly to inject a fake.
_router: Router = _build_router()
#: Convenience handle for the inner ``httpx.Client``. Surfaces
#: to ``dispatch_health`` so operators can inspect transport state.
_client = getattr(_router, "client", None)


def _make_dispatch(tier: str) -> Callable[[str], Awaitable[dict[str, object]]]:
    @mcp.tool(name=f"dispatch_{tier}")
    async def dispatch(message: str) -> dict[str, object]:
        if len(message.encode()) > MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"message exceeds maximum length of {MAX_MESSAGE_LENGTH} bytes"
            )
        worker = _router.worker(tier)
        return (await worker(message)).to_dict()

    return dispatch


# Lazy-initialized local provider for dispatch_local_* tools
_local_provider: LlamaCppProvider | None = None


def _get_local_provider() -> LlamaCppProvider:
    global _local_provider
    if _local_provider is None:
        _local_provider = LlamaCppProvider()
    return _local_provider


dispatch_worker = _make_dispatch("worker")
dispatch_main = _make_dispatch("main")
dispatch_codeman = _make_dispatch("codeman")
dispatch_freetier = _make_dispatch("freetier")
dispatch_kimi = _make_dispatch("kimi")
dispatch_kimi_thinking = _make_dispatch("kimi_thinking")
dispatch_minimax = _make_dispatch("minimax")
dispatch_opus = _make_dispatch("opus")
dispatch_haiku = _make_dispatch("haiku")
dispatch_gemini = _make_dispatch("gemini")


@mcp.tool()
async def dispatch_local_complete(
    message: str,
    system_prompt: str = "",
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> dict[str, object]:
    """Complete a message using the local LlamaCpp provider.

    Requires either LLAMA_CPP_SERVER_URL or LLAMA_CPP_MODEL_PATH to be set.
    Returns a JobResult-like dict with the completion text.
    """
    if len(message.encode()) > MAX_MESSAGE_LENGTH:
        raise ValueError(
            f"message exceeds maximum length of {MAX_MESSAGE_LENGTH} bytes"
        )
    provider = _get_local_provider()
    messages: list[Message] = []
    if system_prompt:
        messages.append(Message(role="system", content=system_prompt))
    messages.append(Message(role="user", content=message))
    try:
        completion = await provider.complete(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return {
            "ok": True,
            "status": "ok",
            "text": completion.text,
            "model": completion.model,
            "provider": completion.provider,
            "input_tokens": completion.input_tokens,
            "output_tokens": completion.output_tokens,
            "finish_reason": completion.finish_reason,
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
        }


@mcp.tool()
async def dispatch_local_health() -> dict[str, object]:
    """Check the local LlamaCpp provider health status."""
    return await _get_local_provider().health()


@mcp.tool()
async def dispatch_local_info() -> dict[str, object]:
    """Return information about the local provider configuration."""
    provider = _get_local_provider()
    return {
        "provider": provider.name,
        "mode": "server" if provider._is_server_mode() else "direct",
        "server_url": provider._server_url or None,
        "model_path": provider._model_path or None,
        "n_ctx": provider._n_ctx,
        "n_gpu_layers": provider._n_gpu_layers,
    }


@mcp.tool()
async def dispatch_custom(tier: str, message: str) -> dict[str, object]:
    if tier not in VALID_TIERS:
        raise ValueError(
            f"Invalid tier '{tier}'. Must be one of: {', '.join(sorted(VALID_TIERS))}"
        )
    if len(message.encode()) > MAX_MESSAGE_LENGTH:
        raise ValueError(
            f"message exceeds maximum length of {MAX_MESSAGE_LENGTH} bytes"
        )
    return (await _router.dispatch_message(tier=tier, message=message)).to_dict()


@mcp.tool()
async def dispatch_health() -> dict[str, object]:
    """Check OmniRoute backend health. Requires OMNIROUTE_URL."""
    return (await _router.health()).to_dict()


@mcp.tool()
async def dispatch_liveness() -> dict[str, object]:
    """Return server liveness status. Does not require OmniRoute."""
    return JobResult(status="alive", message="dispatch-mcp").to_dict()


@mcp.tool()
async def dispatch_ping() -> dict[str, object]:
    """Forward a low-cost liveness probe to the upstream OmniRoute backend.

    Returns a :class:`JobResult` shape with ``status`` set to
    ``"alive"`` on success or ``"unreachable"`` on transport
    failure. Never raises; the MCP tool surface treats
    upstream errors as a regular result so the client can
    render the outcome.
    """
    try:
        result = await _router.ping()
    except Exception as exc:  # never raise from a tool
        return {
            "status": "unreachable",
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "protocolVersion": DEFAULT_NEGOTIATED_VERSION,
            "upstreamReachable": False,
        }
    payload = result.to_dict()
    payload["protocolVersion"] = DEFAULT_NEGOTIATED_VERSION
    payload["upstreamReachable"] = True
    return payload


@mcp.tool()
async def dispatch_protocol(
    client_version: str | None = None,
    client_name: str | None = None,
    client_info_version: str | None = None,
) -> dict[str, object]:
    """Discover supported MCP protocol versions, server identity, and capabilities.

    Optional ``client_version`` triggers full version
    negotiation: the result includes the agreed-upon
    ``negotiatedVersion``. The optional ``client_name`` /
    ``client_info_version`` populate an echo of the
    client's :class:`ClientInfo` so the client can confirm
    what the server saw during the handshake.
    """
    info = _router.protocol_info()
    payload = info.model_dump()
    payload["requestedClientVersion"] = client_version
    payload["clientInfo"] = {
        "name": client_name,
        "version": client_info_version,
    }
    if client_version is not None:
        # Negotiate against the router's reported supported list so
        # the answer is determined by what *this* deployment can
        # speak, not the module-level default constant. This lets
        # test fakes (which trim the supported list) drive the
        # negotiation outcome.
        payload["negotiatedVersion"] = negotiate_version(
            client_version,  # type: ignore[arg-type]
            supported=tuple(info.supportedVersions),
        )
    return payload


def build_handshake(
    client_version: ProtocolVersion | None = None,
    *,
    client_info: ClientInfo | None = None,  # noqa: ARG001 — accepted for forward-compat
) -> InitializeResult:
    """Build a typed ``initialize`` handshake response.

    This is the canonical entry point for an MCP client
    performing the version discovery → ``initialize`` →
    ``initialized`` dance. The :func:`dispatch_protocol`
    tool surfaces the same data in a dict shape; this
    function returns the strongly-typed Pydantic model so
    programmatic clients can chain the next step.

    The function is intentionally side-effect-free: no
    state is recorded, no I/O is performed. Tests rely on
    this to assert that the server advertises the expected
    versions, capabilities, and identity.
    """
    negotiated = negotiate_version(client_version) if client_version is not None else DEFAULT_NEGOTIATED_VERSION
    server_info = _router.protocol_info().serverInfo or ServerInfo(
        name="dispatch-mcp",
        version="0.0.0+unknown",
    )
    return InitializeResult(
        protocolVersion=negotiated,
        capabilities=ServerCapabilities(),
        serverInfo=server_info,
        instructions=(
            "Call dispatch_protocol for capability discovery, then "
            "use the per-tier dispatch_<tier> tools to send work."
        ),
    )


def main() -> None:
    """Start the MCP server. Registers SIGTERM/SIGINT handlers that log intent;
    the event loop (mcp.run) controls its own lifecycle and does not
    guarantee immediate interruption on signal receipt."""

    def _handle_signal(signum: int, _frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.warning("Received %s, closing OmniRoute client", sig_name)
        _router.close()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    mcp.run()
    _router.close()


if __name__ == "__main__":
    main()


# Re-export protocol constants for downstream consumers and
# tests that want to assert on the supported version range
# without importing the full module hierarchy.
__all__ = [
    "DEFAULT_NEGOTIATED_VERSION",
    "PROTOCOL_DISCOVERY_DESCRIPTION",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "build_handshake",
    "dispatch_codeman",
    "dispatch_custom",
    "dispatch_freetier",
    "dispatch_gemini",
    "dispatch_haiku",
    "dispatch_health",
    "dispatch_kimi",
    "dispatch_kimi_thinking",
    "dispatch_liveness",
    "dispatch_main",
    "dispatch_minimax",
    "dispatch_opus",
    "dispatch_ping",
    "dispatch_protocol",
    "dispatch_local_complete",
    "dispatch_local_health",
    "dispatch_local_info",
    "dispatch_worker",
]
