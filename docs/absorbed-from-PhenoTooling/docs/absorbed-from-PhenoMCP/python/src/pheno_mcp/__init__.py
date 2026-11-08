"""PhenoMCP - Model Context Protocol Python library.

Provides Client, Server, Tool, Resource, and Prompt implementations
for the Model Context Protocol (MCP).
"""

from __future__ import annotations

__version__ = "0.1.0"

from pheno_mcp.client import Client, ClientConfig
from pheno_mcp.models import (
    CallToolResult,
    ListResourcesResult,
    Prompt,
    Resource,
    Tool,
)
from pheno_mcp.server import Prompt as ServerPrompt
from pheno_mcp.server import Resource as ServerResource
from pheno_mcp.server import Server, ServerConfig, Tool as ServerTool
from pheno_mcp.server import create_configured_server
from pheno_mcp.transport import build_fastmcp_bridge, run_stdio, run_stdio_async

__all__ = [
    "__version__",
    "CallToolResult",
    "Client",
    "ClientConfig",
    "ListResourcesResult",
    "Prompt",
    "Resource",
    "Server",
    "ServerConfig",
    "Tool",
    "build_fastmcp_bridge",
    "create_configured_server",
    "run_stdio",
    "run_stdio_async",
]
