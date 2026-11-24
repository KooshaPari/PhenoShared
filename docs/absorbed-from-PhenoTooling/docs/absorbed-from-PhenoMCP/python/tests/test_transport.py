"""Tests for FR-MCP-006 — Transport layer (stdio / HTTP / WS).

Architecture
------------
Unit tests (always run): verify ``build_fastmcp_bridge`` wires tools
correctly by patching FastMCP so the segfault-prone pydantic-core C extension
is never touched.  These run on every Python, including the 3.14 alpha used
by CI where pydantic-core has an ABI mismatch.

Integration tests: guarded by a subprocess probe that checks whether
``mcp`` is actually importable without crashing.  The probe runs once at
collection time.  If mcp is importable the tests run; otherwise they are
skipped (not failed).

Coverage
--------
- ``build_fastmcp_bridge`` wires all 19 configured tools onto FastMCP.
- Tool description and name propagate through the bridge.
- Delegating async handler calls ``server.handle_request`` correctly.
- In-memory MCP client lists tools end-to-end (integration, may skip).
- In-memory MCP client invokes a tool end-to-end (integration, may skip).
- ``run_stdio`` is a synchronous callable; ``run_stdio_async`` is async.
- ``python -m pheno_mcp`` entrypoint imports and exposes ``main()``.
- Transport helpers are re-exported from the top-level package.
"""

from __future__ import annotations

import importlib
import inspect
import subprocess
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

from pheno_mcp.server import Server, ServerConfig, Tool, create_configured_server
from pheno_mcp.transport import build_fastmcp_bridge, run_stdio, run_stdio_async

# ---------------------------------------------------------------------------
# Probe: can mcp actually be imported on this Python build?
# We use a subprocess so a fatal segfault doesn't kill the collection process.
# ---------------------------------------------------------------------------
_MCP_PROBE = subprocess.run(
    [sys.executable, "-c", "from mcp.server.fastmcp import FastMCP; FastMCP('probe')"],
    capture_output=True,
    timeout=15,
)
_MCP_AVAILABLE = _MCP_PROBE.returncode == 0

mcp_integration = pytest.mark.skipif(
    not _MCP_AVAILABLE,
    reason="mcp SDK not importable on this Python build (pydantic-core ABI mismatch with Python 3.14a)",
)

EXPECTED_TOOL_NAMES = {
    "ledger_query",
    "ledger_verify",
    "agent_create",
    "agent_list",
    "agent_get",
    "agent_delete",
    "knowledge_store",
    "knowledge_retrieve",
    "knowledge_search",
    "knowledge_delete",
    "policy_list",
    "policy_get",
    "policy_evaluate",
    "session_suspend",
    "session_resume",
    "workflow_execute",
    "workflow_status",
    "workflow_cancel",
    "workflow_list",
}


def _make_echo_server() -> Server:
    """Return a minimal server with a single synchronous echo tool."""
    srv = Server(ServerConfig(name="echo-test"))
    srv.register_tool(
        Tool(
            name="echo",
            description="Return the input unchanged.",
            input_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            handler=lambda args: {"echoed": args.get("message")},
        )
    )
    return srv


def _make_mock_fastmcp() -> MagicMock:
    """Return a mock that looks enough like FastMCP for bridge unit tests."""
    mock = MagicMock()
    mock._registered: list[dict[str, Any]] = []

    def _add_tool(fn: Any, *, name: str, description: str, **_kw: Any) -> None:
        mock._registered.append({"name": name, "description": description, "fn": fn})

    mock.add_tool.side_effect = _add_tool
    return mock


def _bridge_with_mock(server: Server) -> MagicMock:
    """Run ``build_fastmcp_bridge`` with FastMCP replaced by a mock."""
    fake = _make_mock_fastmcp()
    fake_module = MagicMock()
    fake_module.FastMCP = lambda **kw: fake
    import pheno_mcp.transport as _transport  # noqa: PLC0415

    # Patch the module-globals used by build_fastmcp_bridge's lazy import.
    original = sys.modules.get("mcp.server.fastmcp")
    sys.modules["mcp.server.fastmcp"] = fake_module  # type: ignore[assignment]
    try:
        build_fastmcp_bridge(server)
    finally:
        if original is None:
            sys.modules.pop("mcp.server.fastmcp", None)
        else:
            sys.modules["mcp.server.fastmcp"] = original
    return fake


# ---------------------------------------------------------------------------
# Unit tests — bridge construction (no mcp runtime)
# ---------------------------------------------------------------------------


class TestBuildFastmcpBridgeUnit:
    def test_registers_all_configured_tools(self) -> None:
        """All 19 pheno_mcp tools are registered on the mock FastMCP."""
        fake = _bridge_with_mock(create_configured_server())
        assert {r["name"] for r in fake._registered} == EXPECTED_TOOL_NAMES

    def test_echo_server_one_tool(self) -> None:
        """Echo server produces exactly one registered tool on the bridge."""
        fake = _bridge_with_mock(_make_echo_server())
        assert {r["name"] for r in fake._registered} == {"echo"}

    def test_propagates_description(self) -> None:
        """Tool description is forwarded to add_tool."""
        server = Server(ServerConfig(name="x"))
        server.register_tool(Tool(name="my_tool", description="A handy tool", handler=lambda a: {}))
        fake = _bridge_with_mock(server)
        assert fake._registered[0]["description"] == "A handy tool"

    @pytest.mark.asyncio
    async def test_handler_delegates_to_server(self) -> None:
        """The handler lambda registered on FastMCP calls server.handle_request."""
        fake = _bridge_with_mock(_make_echo_server())
        handler = fake._registered[0]["fn"]
        result = await handler(message="hi")
        assert result == {"echoed": "hi"}


# ---------------------------------------------------------------------------
# Entrypoint smoke tests (no mcp runtime needed)
# ---------------------------------------------------------------------------


def test_main_module_importable() -> None:
    """``python -m pheno_mcp`` entrypoint module imports without error."""
    mod = importlib.import_module("pheno_mcp.__main__")
    assert callable(getattr(mod, "main", None))


def test_run_stdio_is_synchronous_callable() -> None:
    """``run_stdio`` is a regular (non-async) callable."""
    assert callable(run_stdio)
    assert not inspect.iscoroutinefunction(run_stdio)


def test_run_stdio_async_is_coroutine() -> None:
    """``run_stdio_async`` is an async callable."""
    assert inspect.iscoroutinefunction(run_stdio_async)


def test_transport_symbols_in_package_init() -> None:
    """Transport helpers are re-exported from the top-level ``pheno_mcp``."""
    import pheno_mcp  # noqa: PLC0415

    assert hasattr(pheno_mcp, "build_fastmcp_bridge")
    assert hasattr(pheno_mcp, "run_stdio")
    assert hasattr(pheno_mcp, "run_stdio_async")


# ---------------------------------------------------------------------------
# Integration tests — real in-memory MCP transport
# (skipped when mcp not importable on this Python build)
# ---------------------------------------------------------------------------


@mcp_integration
@pytest.mark.asyncio
async def test_in_memory_transport_lists_all_tools() -> None:
    """MCP in-memory client connects and lists all 19 tools via bridge."""
    from mcp.shared.memory import (  # type: ignore[import]  # noqa: PLC0415
        create_connected_server_and_client_session,
    )
    from mcp.server.fastmcp import FastMCP as _RealFastMCP  # type: ignore[import]  # noqa: PLC0415

    server = create_configured_server()
    # Use the real FastMCP for integration path
    fmcp = build_fastmcp_bridge(server)

    async with create_connected_server_and_client_session(fmcp) as client_session:
        result = await client_session.list_tools()
        names = {t.name for t in result.tools}
    assert names == EXPECTED_TOOL_NAMES


@mcp_integration
@pytest.mark.asyncio
async def test_in_memory_transport_tool_call_end_to_end() -> None:
    """Echo tool call travels ClientSession → in-memory streams → bridge → handler."""
    from mcp.shared.memory import (  # type: ignore[import]  # noqa: PLC0415
        create_connected_server_and_client_session,
    )

    fmcp = build_fastmcp_bridge(_make_echo_server())

    async with create_connected_server_and_client_session(fmcp) as client_session:
        result = await client_session.call_tool("echo", {"message": "hello-transport"})

    assert result.content, "Expected non-empty tool result"
    content_text = " ".join(getattr(c, "text", "") for c in result.content)
    assert "hello-transport" in content_text
