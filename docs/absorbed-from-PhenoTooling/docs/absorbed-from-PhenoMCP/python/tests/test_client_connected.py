"""Comprehensive tests for MCP client connected state operations."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pheno_mcp.client import Client, ClientConfig


class TestClientConnectedState:
    """Tests for Client connected state operations."""

    @pytest.fixture
    def configured_client(self) -> Client:
        """Create a client with configuration."""
        config = ClientConfig(
            server_command=["python", "server.py"],
            timeout=60.0,
        )
        return Client(config)

    @pytest.fixture
    async def connected_client(self, configured_client: Client) -> Client:
        """Create and connect a client."""
        await configured_client.connect()
        yield configured_client
        await configured_client.disconnect()

    async def test_connect_sets_connected_state(self, configured_client: Client) -> None:
        """Test connect changes connection state."""
        assert not configured_client.is_connected
        await configured_client.connect()
        assert configured_client.is_connected

    async def test_double_connect_is_idempotent(self, configured_client: Client) -> None:
        """Test connecting twice does not raise."""
        await configured_client.connect()
        await configured_client.connect()  # Should not raise
        assert configured_client.is_connected

    async def test_disconnect_clears_state(self, connected_client: Client) -> None:
        """Test disconnect clears connection."""
        await connected_client.disconnect()
        assert not connected_client.is_connected

    async def test_double_disconnect_is_idempotent(self, connected_client: Client) -> None:
        """Test disconnecting twice does not raise."""
        await connected_client.disconnect()
        await connected_client.disconnect()  # Should not raise
        assert not connected_client.is_connected

    async def test_call_tool_with_unknown_tool_raises(
        self, connected_client: Client
    ) -> None:
        """Test calling unknown tool raises ValueError."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await connected_client.call_tool("nonexistent")

    async def test_call_tool_with_none_arguments(
        self, connected_client: Client
    ) -> None:
        """Test calling tool with None arguments works."""
        connected_client._tools["test_tool"] = AsyncMock(return_value="result")
        result = await connected_client.call_tool("test_tool", None)
        assert result == "result"

    async def test_call_tool_with_empty_arguments(
        self, connected_client: Client
    ) -> None:
        """Test calling tool with empty dict arguments works."""
        connected_client._tools["test_tool"] = AsyncMock(return_value="result")
        result = await connected_client.call_tool("test_tool", {})
        assert result == "result"

    async def test_read_resource_with_unknown_resource_raises(
        self, connected_client: Client
    ) -> None:
        """Test reading unknown resource raises ValueError."""
        with pytest.raises(ValueError, match="Unknown resource"):
            await connected_client.read_resource("file://nonexistent.txt")


class TestClientConfigEdgeCases:
    """Tests for ClientConfig edge cases."""

    def test_config_with_custom_env(self) -> None:
        """Test config with custom environment variables."""
        config = ClientConfig(
            server_command=["python", "server.py"],
            server_env={"MCP_DEBUG": "true", "LOG_LEVEL": "debug"},
        )
        assert config.server_env["MCP_DEBUG"] == "true"
        assert config.server_env["LOG_LEVEL"] == "debug"

    def test_config_with_empty_command(self) -> None:
        """Test config with empty command list."""
        config = ClientConfig(server_command=[])
        assert config.server_command == []

    def test_config_timeout_zero(self) -> None:
        """Test config with zero timeout."""
        config = ClientConfig(timeout=0.0)
        assert config.timeout == 0.0

    def test_config_timeout_negative(self) -> None:
        """Test config with negative timeout is allowed."""
        config = ClientConfig(timeout=-1.0)
        assert config.timeout == -1.0
