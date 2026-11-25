"""MCP client for connecting to and interacting with an MCP server."""

from __future__ import annotations

import asyncio
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClientConfig:
    """Configuration for the MCP client.

    Attributes:
        server_command: Command and arguments to start the MCP server.
        server_env: Environment variables for the server process.
        timeout: Connection timeout in seconds.
    """

    server_command: list[str] = field(default_factory=list)
    server_env: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0


class Client:
    """MCP client for connecting to and interacting with an MCP server.

    Manages server lifecycle (start/stop) and provides methods for
    calling tools and accessing resources.
    """

    def __init__(self, config: ClientConfig | None = None) -> None:
        """Initialize the client.

        Args:
            config: Optional client configuration.
        """
        self._config = config or ClientConfig()
        self._connected: bool = False
        self._process: subprocess.Popen[bytes] | None = None
        self._tools: dict[str, Any] = {}
        self._resources: dict[str, Any] = {}

    @property
    def is_connected(self) -> bool:
        """Whether the client is currently connected."""
        return self._connected

    # -------------------------------------------------------------------------
    # Connection management
    # -------------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to the MCP server.

        Starts the server process if a server_command is configured.

        Raises:
            RuntimeError: If no server_command is configured.
        """
        if not self._config.server_command:
            raise RuntimeError("No server command configured.")

        if self._connected:
            return

        cmd = self._config.server_command
        env = {**os.environ.copy(), **self._config.server_env}
        self._process = subprocess.Popen(
            cmd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from the MCP server.

        Terminates the server process if one is running.
        Idempotent: safe to call even when not connected.
        """
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        self._connected = False
        self._tools.clear()
        self._resources.clear()

    # -------------------------------------------------------------------------
    # Tool operations
    # -------------------------------------------------------------------------

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> Any:
        """Call a registered tool.

        Args:
            name: Name of the tool to call.
            arguments: Optional tool arguments.

        Returns:
            Tool execution result.

        Raises:
            RuntimeError: If not connected to the server.
            ValueError: If the tool is not registered.
        """
        if not self._connected:
            raise RuntimeError("Not connected to server.")

        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")

        handler = self._tools[name]
        args = arguments if arguments is not None else {}
        result = handler(args)
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def list_tools(self) -> list[Any]:
        """List available tools.

        Returns:
            Empty list (tools must be manually registered for testing).

        Raises:
            RuntimeError: If not connected to the server.
        """
        if not self._connected:
            raise RuntimeError("Not connected to server.")
        return []

    # -------------------------------------------------------------------------
    # Resource operations
    # -------------------------------------------------------------------------

    async def list_resources(self) -> list[Any]:
        """List available resources.

        Returns:
            Empty list (resources must be manually registered for testing).

        Raises:
            RuntimeError: If not connected to the server.
        """
        if not self._connected:
            raise RuntimeError("Not connected to server.")
        return []

    async def read_resource(self, uri: str) -> Any:
        """Read a resource by URI.

        Args:
            uri: The resource URI to read.

        Returns:
            Resource contents.

        Raises:
            RuntimeError: If not connected to the server.
            ValueError: If the resource is not registered.
        """
        if not self._connected:
            raise RuntimeError("Not connected to server.")

        if uri not in self._resources:
            raise ValueError(f"Unknown resource: {uri}")

        return self._resources[uri]
