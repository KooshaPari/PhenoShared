"""Tests for MCP server implementation."""

from __future__ import annotations

from typing import Any

import pytest
from pheno_mcp.server import Prompt, Resource, Server, ServerConfig, Tool


def _assert_jsonrpc_error(result: dict, code: int, message: str) -> None:
    assert result["jsonrpc"] == "2.0"
    assert result["id"] is None
    assert result["error"]["code"] == code
    assert result["error"]["message"] == message


class TestServer:
    """Tests for Server class."""

    def test_server_initialization(self) -> None:
        """Test server initializes with defaults."""
        server = Server()
        assert server.name == "pheno-mcp"
        assert server.version == "0.1.0"

    def test_server_initialization_with_config(self) -> None:
        """Test server initializes with custom config."""
        config = ServerConfig(name="test-server", version="1.0.0")
        server = Server(config)
        assert server.name == "test-server"
        assert server.version == "1.0.0"

    def test_register_tool(self) -> None:
        """Test registering a tool."""
        server = Server()
        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"},
        )
        server.register_tool(tool)
        tools = server.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

    def test_register_resource(self) -> None:
        """Test registering a resource."""
        server = Server()
        resource = Resource(
            uri="file://test.txt",
            name="Test File",
            description="A test file",
        )
        server.register_resource(resource)
        resources = server.list_resources()
        assert len(resources) == 1
        assert resources[0]["uri"] == "file://test.txt"

    def test_register_prompt(self) -> None:
        """Test registering a prompt."""
        server = Server()
        prompt = Prompt(
            name="test_prompt",
            description="A test prompt",
            arguments=[{"name": "arg1", "description": "First argument"}],
        )
        server.register_prompt(prompt)
        prompts = server.list_prompts()
        assert len(prompts) == 1
        assert prompts[0]["name"] == "test_prompt"

    async def test_handle_request_tools_list(self) -> None:
        """Test handling tools/list request."""
        server = Server()
        result = await server.handle_request("tools/list")
        assert "tools" in result
        assert result["tools"] == []

    async def test_handle_request_resources_list(self) -> None:
        """Test handling resources/list request."""
        server = Server()
        result = await server.handle_request("resources/list")
        assert "resources" in result
        assert result["resources"] == []

    async def test_handle_request_unknown_method(self) -> None:
        """Test handling unknown request method."""
        server = Server()
        result = await server.handle_request("unknown/method")
        _assert_jsonrpc_error(result, -32601, "Method not found")
        assert result["error"]["data"]["method"] == "unknown/method"


class TestTool:
    """Tests for Tool class."""

    def test_tool_to_dict(self) -> None:
        """Test tool serialization."""
        tool = Tool(
            name="my_tool",
            description="Does something",
            input_schema={"type": "object", "properties": {}},
        )
        result = tool.to_dict()
        assert result["name"] == "my_tool"
        assert result["description"] == "Does something"
        assert result["inputSchema"] == {"type": "object", "properties": {}}


class TestResource:
    """Tests for Resource class."""

    def test_resource_to_dict(self) -> None:
        """Test resource serialization."""
        resource = Resource(
            uri="file://data.json",
            name="Data File",
            description="JSON data file",
            mime_type="application/json",
        )
        result = resource.to_dict()
        assert result["uri"] == "file://data.json"
        assert result["name"] == "Data File"
        assert result["mimeType"] == "application/json"


class TestPrompt:
    """Tests for Prompt class."""

    def test_prompt_to_dict(self) -> None:
        """Test prompt serialization."""
        prompt = Prompt(
            name="greet",
            description="Generate a greeting",
            arguments=[{"name": "name", "description": "Name to greet"}],
        )
        result = prompt.to_dict()
        assert result["name"] == "greet"
        assert len(result["arguments"]) == 1


class TestServerConfig:
    """Tests for ServerConfig class."""

    def test_config_defaults(self) -> None:
        """Test config has correct defaults."""
        config = ServerConfig()
        assert config.name == "pheno-mcp"
        assert config.version == "0.1.0"

    def test_config_custom_values(self) -> None:
        """Test config with custom values."""
        config = ServerConfig(name="custom-server", version="2.0.0")
        assert config.name == "custom-server"
        assert config.version == "2.0.0"


class TestServerIntegration:
    """Integration tests for Server."""

    def test_multiple_tools_registration(self) -> None:
        """Test registering multiple tools."""
        server = Server()
        server.register_tool(Tool(name="tool1", description="Tool 1"))
        server.register_tool(Tool(name="tool2", description="Tool 2"))
        tools = server.list_tools()
        assert len(tools) == 2
        assert {t["name"] for t in tools} == {"tool1", "tool2"}

    def test_multiple_resources_registration(self) -> None:
        """Test registering multiple resources."""
        server = Server()
        server.register_resource(Resource(uri="file://a.txt", name="A"))
        server.register_resource(Resource(uri="file://b.txt", name="B"))
        resources = server.list_resources()
        assert len(resources) == 2

    @pytest.mark.asyncio
    async def test_handle_request_tools_call_with_handler(self) -> None:
        """Test tools/call with a handler."""
        server = Server()

        async def echo_handler(args: dict) -> dict:
            return {"echoed": args}

        tool = Tool(
            name="echo",
            description="Echo arguments",
            handler=echo_handler,
        )
        server.register_tool(tool)

        result = await server.handle_request(
            "tools/call", {"name": "echo", "arguments": {"value": 42}}
        )
        assert result == {"echoed": {"value": 42}}

    @pytest.mark.asyncio
    async def test_handle_request_tools_call_unknown_tool(self) -> None:
        """Test tools/call with unknown tool returns a structured error."""
        server = Server()
        result = await server.handle_request("tools/call", {"name": "nonexistent"})
        _assert_jsonrpc_error(result, -32601, "Method not found")
        assert result["error"]["data"]["tool"] == "nonexistent"

    @pytest.mark.asyncio
    async def test_handle_request_prompts_list(self) -> None:
        """Test handling prompts/list request."""
        server = Server()
        server.register_prompt(
            Prompt(
                name="greet",
                description="Generate greeting",
                arguments=[{"name": "name", "type": "string"}],
            )
        )
        result = await server.handle_request("prompts/list")
        assert "prompts" in result
        assert len(result["prompts"]) == 1


class TestServerAdvancedFeatures:
    """Tests for advanced server features."""

    def test_register_multiple_tools(self) -> None:
        """Test registering multiple tools."""
        server = Server()
        tools = [
            Tool(name="tool1", description="First tool"),
            Tool(name="tool2", description="Second tool"),
            Tool(name="tool3", description="Third tool"),
        ]
        for tool in tools:
            server.register_tool(tool)

        result = server.list_tools()
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_handle_request_tools_call_no_handler(self) -> None:
        """Test tools/call without handler returns None."""
        server = Server()
        tool = Tool(name="noop", description="No operation tool")
        server.register_tool(tool)

        result = await server.handle_request(
            "tools/call",
            {"name": "noop", "arguments": {}},
        )
        assert result is None


class TestServerErrorHandling:
    """Tests for server error handling."""

    @pytest.mark.asyncio
    async def test_handle_request_invalid_params_type(self) -> None:
        """Test handling request with invalid params type."""
        server = Server()
        invalid_params: Any = ["not", "an", "object"]
        result = await server.handle_request("tools/call", invalid_params)
        _assert_jsonrpc_error(result, -32600, "Invalid request")
        assert result["error"]["data"]["reason"] == "params must be an object"

    @pytest.mark.asyncio
    async def test_handle_request_tools_call_invalid_name(self) -> None:
        """Test tools/call with a malformed tool name returns an error object."""
        server = Server()
        result = await server.handle_request("tools/call", {"name": "   "})
        _assert_jsonrpc_error(result, -32602, "Invalid params")
        assert (
            result["error"]["data"]["reason"] == "tool name must be a non-empty string"
        )

    @pytest.mark.asyncio
    async def test_handle_request_tools_call_invalid_arguments(self) -> None:
        """Test tools/call with invalid arguments returns an error object."""
        server = Server()
        server.register_tool(Tool(name="echo", description="Echo"))
        result = await server.handle_request(
            "tools/call", {"name": "echo", "arguments": "bad"}
        )
        _assert_jsonrpc_error(result, -32602, "Invalid params")
        assert result["error"]["data"]["reason"] == "arguments must be an object"

    @pytest.mark.asyncio
    async def test_handle_request_tools_call_handler_exception(self) -> None:
        """Test tool handler exceptions are converted into error objects."""
        server = Server()

        def exploding_handler(_: dict) -> dict:
            raise RuntimeError("boom")

        server.register_tool(
            Tool(name="explode", description="Explode", handler=exploding_handler)
        )
        result = await server.handle_request("tools/call", {"name": "explode"})
        _assert_jsonrpc_error(result, -32603, "Internal error")
        assert result["error"]["data"]["tool"] == "explode"

    def test_tool_overwrite(self) -> None:
        """Test overwriting an existing tool."""
        server = Server()
        tool1 = Tool(name="test", description="First version")
        tool2 = Tool(name="test", description="Second version")
        server.register_tool(tool1)
        server.register_tool(tool2)

        tools = server.list_tools()
        assert len(tools) == 1
        assert tools[0]["description"] == "Second version"

    def test_resource_overwrite(self) -> None:
        """Test overwriting an existing resource."""
        server = Server()
        res1 = Resource(uri="file://test.txt", name="Old")
        res2 = Resource(uri="file://test.txt", name="New")
        server.register_resource(res1)
        server.register_resource(res2)

        resources = server.list_resources()
        assert len(resources) == 1
        assert resources[0]["name"] == "New"
