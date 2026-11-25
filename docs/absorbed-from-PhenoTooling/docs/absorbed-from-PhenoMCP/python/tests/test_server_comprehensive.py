"""Comprehensive tests for MCP server."""

from __future__ import annotations

import pytest
from pheno_mcp.server import Prompt, Resource, Server, ServerConfig, Tool


def _assert_jsonrpc_error(result: dict, code: int, message: str) -> None:
    assert result["jsonrpc"] == "2.0"
    assert result["id"] is None
    assert result["error"]["code"] == code
    assert result["error"]["message"] == message


class TestServerComprehensive:
    """Comprehensive tests for Server class."""

    def test_register_multiple_tools(self) -> None:
        """Test registering multiple tools."""
        server = Server()
        for i in range(3):
            tool = Tool(name=f"tool_{i}", description=f"Tool {i}")
            server.register_tool(tool)
        tools = server.list_tools()
        assert len(tools) == 3

    def test_register_multiple_resources(self) -> None:
        """Test registering multiple resources."""
        server = Server()
        for i in range(3):
            resource = Resource(uri=f"file://resource_{i}", name=f"Resource {i}")
            server.register_resource(resource)
        resources = server.list_resources()
        assert len(resources) == 3

    def test_register_multiple_prompts(self) -> None:
        """Test registering multiple prompts."""
        server = Server()
        for i in range(3):
            prompt = Prompt(name=f"prompt_{i}", description=f"Prompt {i}")
            server.register_prompt(prompt)
        prompts = server.list_prompts()
        assert len(prompts) == 3

    def test_register_duplicate_tool_replaces(self) -> None:
        """Test registering tool with same name replaces existing."""
        server = Server()
        tool1 = Tool(name="tool", description="First")
        tool2 = Tool(name="tool", description="Second")
        server.register_tool(tool1)
        server.register_tool(tool2)
        tools = server.list_tools()
        assert len(tools) == 1
        assert tools[0]["description"] == "Second"

    def test_register_duplicate_resource_replaces(self) -> None:
        """Test registering resource with same URI replaces existing."""
        server = Server()
        resource1 = Resource(uri="file://test", name="First")
        resource2 = Resource(uri="file://test", name="Second")
        server.register_resource(resource1)
        server.register_resource(resource2)
        resources = server.list_resources()
        assert len(resources) == 1
        assert resources[0]["name"] == "Second"

    def test_register_duplicate_prompt_replaces(self) -> None:
        """Test registering prompt with same name replaces existing."""
        server = Server()
        prompt1 = Prompt(name="prompt", description="First")
        prompt2 = Prompt(name="prompt", description="Second")
        server.register_prompt(prompt1)
        server.register_prompt(prompt2)
        prompts = server.list_prompts()
        assert len(prompts) == 1
        assert prompts[0]["description"] == "Second"


class TestServerRequestHandling:
    """Tests for Server request handling."""

    @pytest.fixture
    def server_with_tools(self) -> Server:
        """Create a server with registered tools."""
        server = Server()
        server.register_tool(Tool(name="echo", description="Echo input"))
        server.register_tool(
            Tool(
                name="add",
                description="Add numbers",
                input_schema={"type": "object", "properties": {"a": {}, "b": {}}},
            )
        )
        return server

    @pytest.fixture
    def server_with_resources(self) -> Server:
        """Create a server with registered resources."""
        server = Server()
        server.register_resource(Resource(uri="file://data.csv", name="CSV Data"))
        server.register_resource(Resource(uri="file://config.json", name="Config"))
        return server

    @pytest.fixture
    def server_with_prompts(self) -> Server:
        """Create a server with registered prompts."""
        server = Server()
        server.register_prompt(Prompt(name="greet", description="Generate greeting"))
        return server

    async def test_handle_request_prompts_list(
        self, server_with_prompts: Server
    ) -> None:
        """Test handling prompts/list request."""
        result = await server_with_prompts.handle_request("prompts/list")
        assert "prompts" in result
        assert len(result["prompts"]) == 1

    async def test_handle_request_tools_call_without_handler(
        self, server_with_tools: Server
    ) -> None:
        """Test calling tool without handler returns None."""
        result = await server_with_tools.handle_request(
            "tools/call", {"name": "echo", "arguments": {}}
        )
        assert result is None

    async def test_handle_request_tools_call_with_handler(self) -> None:
        """Test calling tool with handler returns handler result."""
        server = Server()

        async def my_handler(args: dict) -> str:
            return f"Hello, {args.get('name', 'World')}!"

        tool = Tool(name="greet", description="Greet someone", handler=my_handler)
        server.register_tool(tool)

        result = await server.handle_request(
            "tools/call", {"name": "greet", "arguments": {"name": "Alice"}}
        )
        assert result == "Hello, Alice!"

    async def test_handle_request_tools_call_unknown_tool(
        self, server_with_tools: Server
    ) -> None:
        """Test calling unknown tool returns a JSON-RPC error object."""
        result = await server_with_tools.handle_request(
            "tools/call", {"name": "nonexistent", "arguments": {}}
        )
        _assert_jsonrpc_error(result, -32601, "Method not found")
        assert result["error"]["data"]["tool"] == "nonexistent"

    async def test_handle_request_tools_call_no_name_returns_none(
        self, server_with_tools: Server
    ) -> None:
        """Test calling tool without name in params returns an error object."""
        result = await server_with_tools.handle_request("tools/call", {})
        _assert_jsonrpc_error(result, -32602, "Invalid params")
        assert (
            result["error"]["data"]["reason"] == "tool name must be a non-empty string"
        )

    async def test_handle_request_tools_call_no_params(
        self, server_with_tools: Server
    ) -> None:
        """Test calling tool with no params returns an error object."""
        result = await server_with_tools.handle_request("tools/call")
        _assert_jsonrpc_error(result, -32602, "Invalid params")
        assert (
            result["error"]["data"]["reason"] == "tool name must be a non-empty string"
        )

    async def test_handle_request_with_none_params(
        self, server_with_tools: Server
    ) -> None:
        """Test handling request with None params."""
        result = await server_with_tools.handle_request("tools/list", None)
        assert "tools" in result


class TestServerConfigEdgeCases:
    """Tests for ServerConfig edge cases."""

    def test_config_with_special_chars_in_name(self) -> None:
        """Test config with special characters in name."""
        config = ServerConfig(name="test-server_v1.0", version="1.0.0")
        assert config.name == "test-server_v1.0"

    def test_config_with_unicode_name(self) -> None:
        """Test config with unicode characters."""
        config = ServerConfig(name="测试服务器", version="1.0.0")
        assert config.name == "测试服务器"

    def test_config_empty_name(self) -> None:
        """Test config with empty name."""
        config = ServerConfig(name="", version="1.0.0")
        assert config.name == ""

    def test_config_empty_version(self) -> None:
        """Test config with empty version."""
        config = ServerConfig(name="test", version="")
        assert config.version == ""


class TestToolWithHandler:
    """Tests for Tool with handler."""

    async def test_tool_handler_receives_arguments(self) -> None:
        """Test tool handler receives correct arguments."""
        received_args = {}

        async def capture_handler(args: dict) -> dict:
            received_args.update(args)
            return {"status": "ok"}

        server = Server()
        tool = Tool(name="capture", description="Capture args", handler=capture_handler)
        server.register_tool(tool)

        await server.handle_request(
            "tools/call", {"name": "capture", "arguments": {"key": "value"}}
        )
        assert received_args == {"key": "value"}

    async def test_tool_handler_returns_complex_result(self) -> None:
        """Test tool handler can return complex results."""

        async def complex_handler(args: dict) -> dict:
            return {
                "status": "success",
                "data": {"items": [1, 2, 3], "nested": {"key": "value"}},
            }

        server = Server()
        tool = Tool(
            name="complex", description="Return complex", handler=complex_handler
        )
        server.register_tool(tool)

        result = await server.handle_request(
            "tools/call", {"name": "complex", "arguments": {}}
        )
        assert result["status"] == "success"
        assert result["data"]["nested"]["key"] == "value"
