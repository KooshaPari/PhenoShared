"""MCP server implementation with tool, resource, and prompt registration."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any


JSONRPC_VERSION = "2.0"
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603


@dataclass
class ServerConfig:
    """Server configuration.

    Attributes:
        name: Server name.
        version: Server version string.
        host: Host address to bind to.
        port: Port number to listen on.
    """

    name: str = "pheno-mcp"
    version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8000


@dataclass
class Tool:
    """An MCP tool registered with a server.

    Attributes:
        name: Unique tool identifier.
        description: Human-readable description.
        input_schema: JSON Schema for tool input.
        handler: Optional async function to call when the tool is invoked.
    """

    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    handler: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the tool to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class Resource:
    """An MCP resource registered with a server.

    Attributes:
        uri: Unique resource identifier.
        name: Human-readable resource name.
        description: Resource description.
        mime_type: MIME type of the resource.
    """

    uri: str
    name: str = ""
    description: str = ""
    mime_type: str = "text/plain"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the resource to a dictionary."""
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass
class Prompt:
    """An MCP prompt registered with a server.

    Attributes:
        name: Unique prompt identifier.
        description: Human-readable prompt description.
        arguments: List of argument definitions.
    """

    name: str
    description: str = ""
    arguments: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the prompt to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "arguments": list(self.arguments),
        }


class Server:
    """MCP server for handling tools, resources, and prompts.

    Attributes:
        name: Server name.
        version: Server version string.
    """

    def __init__(self, config: ServerConfig | None = None) -> None:
        """Initialize the server.

        Args:
            config: Optional server configuration.
        """
        self._config = config or ServerConfig()
        self._tools: dict[str, Tool] = {}
        self._resources: dict[str, Resource] = {}
        self._prompts: dict[str, Prompt] = {}

    @property
    def name(self) -> str:
        """Server name."""
        return self._config.name

    @property
    def version(self) -> str:
        """Server version."""
        return self._config.version

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register_tool(self, tool: Tool) -> None:
        """Register a tool with the server.

        Args:
            tool: The Tool to register. Overwrites existing tool with same name.
        """
        self._tools[tool.name] = tool

    def register_resource(self, resource: Resource) -> None:
        """Register a resource with the server.

        Args:
            resource: The Resource to register. Overwrites existing resource with same URI.
        """
        self._resources[resource.uri] = resource

    def register_prompt(self, prompt: Prompt) -> None:
        """Register a prompt with the server.

        Args:
            prompt: The Prompt to register. Overwrites existing prompt with same name.
        """
        self._prompts[prompt.name] = prompt

    # -------------------------------------------------------------------------
    # Listing
    # -------------------------------------------------------------------------

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools.

        Returns:
            List of tool dictionaries.
        """
        return [tool.to_dict() for tool in self._tools.values()]

    def list_resources(self) -> list[dict[str, Any]]:
        """List all registered resources.

        Returns:
            List of resource dictionaries.
        """
        return [resource.to_dict() for resource in self._resources.values()]

    def list_prompts(self) -> list[dict[str, Any]]:
        """List all registered prompts.

        Returns:
            List of prompt dictionaries.
        """
        return [prompt.to_dict() for prompt in self._prompts.values()]

    # -------------------------------------------------------------------------
    # Request handling
    # -------------------------------------------------------------------------

    async def handle_request(
        self, method: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Handle an MCP request.

        Args:
            method: The MCP method name (e.g., "tools/list").
            params: Optional request parameters.

        Returns:
            Request result.

        Errors are returned as JSON-RPC-style error objects instead of raising.
        """
        if not isinstance(method, str) or not method.strip():
            return self._error_response(
                JSONRPC_INVALID_REQUEST,
                "Invalid request",
                {"reason": "method must be a non-empty string"},
            )

        if params is None:
            params = {}
        elif not isinstance(params, dict):
            return self._error_response(
                JSONRPC_INVALID_REQUEST,
                "Invalid request",
                {"reason": "params must be an object"},
            )

        if method == "tools/list":
            return {"tools": self.list_tools()}

        if method == "resources/list":
            return {"resources": self.list_resources()}

        if method == "prompts/list":
            return {"prompts": self.list_prompts()}

        if method == "tools/call":
            return await self._handle_tools_call(params)

        return self._error_response(
            JSONRPC_METHOD_NOT_FOUND,
            "Method not found",
            {"method": method},
        )

    async def _handle_tools_call(self, params: dict[str, Any]) -> Any:
        """Handle a tools/call request.

        Args:
            params: The request parameters containing 'name' and 'arguments'.

        Returns:
            Tool execution result, or a JSON-RPC-style error object on failure.
        """
        if not isinstance(params, dict):
            return self._error_response(
                JSONRPC_INVALID_REQUEST,
                "Invalid request",
                {"reason": "params must be an object"},
            )

        name = params.get("name")
        if not isinstance(name, str) or not name.strip():
            return self._error_response(
                JSONRPC_INVALID_PARAMS,
                "Invalid params",
                {"reason": "tool name must be a non-empty string"},
            )

        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return self._error_response(
                JSONRPC_INVALID_PARAMS,
                "Invalid params",
                {"reason": "arguments must be an object", "tool": name},
            )

        if name not in self._tools:
            return self._error_response(
                JSONRPC_METHOD_NOT_FOUND,
                "Method not found",
                {"tool": name},
            )

        tool = self._tools[name]

        if tool.handler is None:
            return None

        try:
            if inspect.iscoroutinefunction(tool.handler):
                return await tool.handler(arguments)
            return tool.handler(arguments)
        except Exception as exc:  # pragma: no cover - defensive guard
            return self._error_response(
                JSONRPC_INTERNAL_ERROR,
                "Internal error",
                {"tool": name, "detail": str(exc)},
            )

    @staticmethod
    def _error_response(
        code: int, message: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a JSON-RPC-style error response."""
        error: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {
            "jsonrpc": JSONRPC_VERSION,
            "error": error,
            "id": None,
        }


def create_configured_server(config: ServerConfig | None = None) -> "Server":
    """Create a Server pre-loaded with all pheno_mcp tool bundles.

    Registers governance, agent, knowledge, policy, session, and workflow tools so callers get a
    fully-wired instance without needing to import every register_* helper.

    Args:
        config: Optional server configuration; defaults are used when omitted.

    Returns:
        A Server instance with all tool bundles registered.
    """
    from pheno_mcp.tools.governance_tools import register_governance_tools
    from pheno_mcp.tools.agent_tools import register_agent_tools
    from pheno_mcp.tools.knowledge_tools import register_knowledge_tools
    from pheno_mcp.tools.policy_tools import register_policy_tools
    from pheno_mcp.tools.session_tools import register_session_tools
    from pheno_mcp.tools.workflow_tools import register_workflow_tools

    server = Server(config)
    register_governance_tools(server)
    register_agent_tools(server)
    register_knowledge_tools(server)
    register_policy_tools(server)
    register_session_tools(server)
    register_workflow_tools(server)
    return server
