"""MCP transport binding for pheno_mcp.

Bridges pheno_mcp's ``Server`` / ``create_configured_server`` to the
FastMCP / MCP-SDK transport layer so a real MCP client can connect
over stdio (or streamable-HTTP).

Design
------
We wrap the pheno_mcp ``Server`` by:

1. Creating a ``FastMCP`` instance with the same name.
2. Iterating every registered ``Tool`` and calling ``FastMCP.add_tool``
   with a thin async lambda that delegates to ``Server.handle_request``.
3. Exposing ``run_stdio`` (sync) and ``run_stdio_async`` (async) helpers
   that drive FastMCP's built-in stdio runner — no hand-rolled protocol.

Only the tools present at *bridge time* are registered (the server is
fully configured before calling ``build_fastmcp_bridge``).  Call the
factory again if the underlying server changes.

Usage::

    from pheno_mcp.transport import build_fastmcp_bridge, run_stdio

    # simplest — uses create_configured_server() internally
    run_stdio()

    # or bring your own server:
    from pheno_mcp import create_configured_server, ServerConfig
    server = create_configured_server(ServerConfig(name="my-server"))
    fmcp = build_fastmcp_bridge(server)
    fmcp.run(transport="stdio")
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP as _FastMCP

from pheno_mcp.server import Server, ServerConfig, create_configured_server


def build_fastmcp_bridge(server: Server) -> "_FastMCP":
    """Wrap a pheno_mcp ``Server`` in a FastMCP instance.

    Each registered tool is re-exposed on the FastMCP server as an async
    function that delegates to ``server.handle_request("tools/call", ...)``.
    FastMCP handles all transport-level framing (JSON-RPC init, tool/list
    advertising, etc.).

    Args:
        server: A fully-configured :class:`~pheno_mcp.server.Server`.

    Returns:
        A :class:`mcp.server.fastmcp.FastMCP` instance ready to ``run()``.
    """
    from mcp.server.fastmcp import FastMCP  # deferred — optional dep at import time

    fmcp = FastMCP(
        name=server.name,
        host=server._config.host,
        port=server._config.port,
    )

    for tool_dict in server.list_tools():
        _register_tool_on_fastmcp(fmcp, server, tool_dict)

    return fmcp


def _register_tool_on_fastmcp(
    fmcp: "_FastMCP",
    server: Server,
    tool_dict: dict[str, Any],
) -> None:
    """Register one pheno_mcp tool on a FastMCP instance."""
    tool_name: str = tool_dict["name"]
    tool_description: str = tool_dict.get("description", "")

    async def _handler(**kwargs: Any) -> Any:
        return await server.handle_request(
            "tools/call",
            {"name": tool_name, "arguments": kwargs},
        )

    # Rename the function so FastMCP picks up the right tool name.
    _handler.__name__ = tool_name
    _handler.__doc__ = tool_description

    fmcp.add_tool(
        _handler,
        name=tool_name,
        description=tool_description,
    )


# ---------------------------------------------------------------------------
# Convenience runners
# ---------------------------------------------------------------------------

def run_stdio(config: ServerConfig | None = None) -> None:
    """Build a configured server and run it over MCP stdio transport.

    Blocks until the stdio stream is closed (i.e. the MCP client disconnects).
    This is the function called by ``python -m pheno_mcp``.

    Args:
        config: Optional :class:`~pheno_mcp.server.ServerConfig`; defaults
                are used when omitted.
    """
    server = create_configured_server(config)
    fmcp = build_fastmcp_bridge(server)
    fmcp.run(transport="stdio")


async def run_stdio_async(config: ServerConfig | None = None) -> None:
    """Async variant of :func:`run_stdio`; useful in test harnesses.

    Args:
        config: Optional :class:`~pheno_mcp.server.ServerConfig`; defaults
                are used when omitted.
    """
    server = create_configured_server(config)
    fmcp = build_fastmcp_bridge(server)
    await fmcp.run_stdio_async()
