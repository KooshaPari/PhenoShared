"""Tests for MCP client implementation."""

from __future__ import annotations

import pytest
from pheno_mcp.client import Client, ClientConfig


class TestClient:
    """Tests for Client class."""

    def test_client_initialization(self) -> None:
        """Test client initializes with defaults."""
        client = Client()
        assert not client.is_connected

    def test_client_initialization_with_config(self) -> None:
        """Test client initializes with custom config."""
        config = ClientConfig(
            server_command=["python", "server.py"],
            timeout=60.0,
        )
        client = Client(config)
        assert not client.is_connected
        assert client._config.timeout == 60.0

    def test_client_disconnect_when_not_connected(self) -> None:
        """Test disconnecting when not connected is a no-op."""
        client = Client()
        # Should not raise
        import asyncio
        asyncio.run(client.disconnect())
        assert not client.is_connected

    async def test_client_connect_without_command(self) -> None:
        """Test connecting without server command raises error."""
        client = Client()
        with pytest.raises(RuntimeError, match="No server command"):
            await client.connect()

    async def test_call_tool_when_not_connected(self) -> None:
        """Test calling tool when not connected raises error."""
        client = Client()
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.call_tool("test_tool")

    async def test_list_tools_when_not_connected(self) -> None:
        """Test listing tools when not connected raises error."""
        client = Client()
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.list_tools()

    async def test_list_resources_when_not_connected(self) -> None:
        """Test listing resources when not connected raises error."""
        client = Client()
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.list_resources()

    async def test_read_resource_when_not_connected(self) -> None:
        """Test reading resource when not connected raises error."""
        client = Client()
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.read_resource("file://test.txt")


class TestClientConfig:
    """Tests for ClientConfig class."""

    def test_config_defaults(self) -> None:
        """Test config has correct defaults."""
        config = ClientConfig()
        assert config.server_command == []
        assert config.server_env == {}
        assert config.timeout == 30.0

    def test_config_custom_values(self) -> None:
        """Test config with custom values."""
        config = ClientConfig(
            server_command=["python", "-m", "server"],
            server_env={"DEBUG": "1"},
            timeout=120.0,
        )
        assert config.server_command == ["python", "-m", "server"]
        assert config.server_env == {"DEBUG": "1"}
        assert config.timeout == 120.0

    def test_config_mutable_default_issue(self) -> None:
        """Test that default mutable values don't share state."""
        config1 = ClientConfig()
        config2 = ClientConfig()
        # Modify one config's mutable fields
        config1.server_env["KEY"] = "value"
        # Other config should not be affected (using field(default_factory=))
        assert "KEY" not in config2.server_env


class TestClientAsyncEdgeCases:
    """Tests for client async edge cases."""

    async def test_client_double_connect(self) -> None:
        """Test connecting twice is idempotent."""
        config = ClientConfig(server_command=["echo", "test"])
        client = Client(config)
        await client.connect()
        assert client.is_connected
        # Connect again - should be no-op
        await client.connect()
        assert client.is_connected
        await client.disconnect()

    async def test_client_double_disconnect(self) -> None:
        """Test disconnecting twice is idempotent."""
        client = Client()
        # Disconnect when not connected
        await client.disconnect()
        assert not client.is_connected
        # Disconnect again
        await client.disconnect()
        assert not client.is_connected

    async def test_call_tool_unknown_tool(self) -> None:
        """Test calling unknown tool raises error."""
        config = ClientConfig(server_command=["echo", "test"])
        client = Client(config)
        await client.connect()
        with pytest.raises(ValueError, match="Unknown tool"):
            await client.call_tool("nonexistent_tool")
        await client.disconnect()

    async def test_call_tool_with_empty_arguments(self) -> None:
        """Test calling tool with no arguments works."""
        async def mock_handler(args):
            return {"result": "ok"}

        config = ClientConfig(server_command=["echo", "test"])
        client = Client(config)
        await client.connect()
        # Manually register a tool for testing
        client._tools["test_tool"] = mock_handler
        result = await client.call_tool("test_tool")
        assert result == {"result": "ok"}
        await client.disconnect()

    async def test_call_tool_with_arguments(self) -> None:
        """Test calling tool with arguments."""
        async def mock_handler(args):
            return {"received": args.get("value")}

        config = ClientConfig(server_command=["echo", "test"])
        client = Client(config)
        await client.connect()
        client._tools["adder"] = mock_handler
        result = await client.call_tool("adder", {"value": 42})
        assert result == {"received": 42}
        await client.disconnect()

    async def test_read_resource_unknown_uri(self) -> None:
        """Test reading unknown resource raises error."""
        config = ClientConfig(server_command=["echo", "test"])
        client = Client(config)
        await client.connect()
        with pytest.raises(ValueError, match="Unknown resource"):
            await client.read_resource("file://nonexistent.txt")
        await client.disconnect()

    async def test_read_resource_with_content(self) -> None:
        """Test reading resource that exists."""
        config = ClientConfig(server_command=["echo", "test"])
        client = Client(config)
        await client.connect()
        client._resources["file://test.txt"] = "Hello, World!"
        result = await client.read_resource("file://test.txt")
        assert result == "Hello, World!"
        await client.disconnect()

    async def test_list_tools_empty(self) -> None:
        """Test listing tools returns empty list when connected."""
        config = ClientConfig(server_command=["echo", "test"])
        client = Client(config)
        await client.connect()
        tools = await client.list_tools()
        assert tools == []
        await client.disconnect()

    async def test_list_resources_empty(self) -> None:
        """Test listing resources returns empty list when connected."""
        config = ClientConfig(server_command=["echo", "test"])
        client = Client(config)
        await client.connect()
        resources = await client.list_resources()
        assert resources == []
        await client.disconnect()


class TestClientIntegration:
    """Integration tests for Client with mock server."""

    @pytest.mark.asyncio
    async def test_connect_disconnect_cycle(self) -> None:
        """Test connect/disconnect cycle."""
        config = ClientConfig(server_command=["echo", "test"])
        client = Client(config)

        assert not client.is_connected
        await client.connect()
        assert client.is_connected
        await client.disconnect()
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_double_connect_is_noop(self) -> None:
        """Test that connecting twice is safe."""
        config = ClientConfig(server_command=["echo", "test"])
        client = Client(config)
        await client.connect()
        await client.connect()  # Should not raise
        assert client.is_connected
