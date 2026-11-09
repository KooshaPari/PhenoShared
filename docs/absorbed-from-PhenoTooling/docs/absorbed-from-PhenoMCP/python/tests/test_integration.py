"""Integration tests for PhenoMCP client-server interaction."""

from __future__ import annotations

import pytest
from pheno_mcp.models import Prompt as ModelPrompt
from pheno_mcp.models import Resource as ModelResource
from pheno_mcp.models import Tool as ModelTool
from pheno_mcp.server import Prompt, Resource, Server, ServerConfig, Tool


class TestClientServerIntegration:
    """Integration tests for client-server workflow."""

    @pytest.fixture
    def configured_server(self) -> Server:
        """Create a configured server with tools, resources, and prompts."""
        server = Server(
            ServerConfig(name="integration-test-server", version="1.0.0")
        )

        # Register tools
        async def process_data(args: dict) -> dict:
            return {"processed": True, "result": f"Processed {args.get('input', 'nothing')}"}

        server.register_tool(
            Tool(
                name="process_data",
                description="Process input data",
                input_schema={
                    "type": "object",
                    "properties": {"input": {"type": "string"}},
                },
                handler=process_data,
            )
        )

        server.register_tool(
            Tool(name="no_handler", description="Tool without handler")
        )

        # Register resources
        server.register_resource(
            Resource(
                uri="file://test.txt",
                name="Test File",
                description="A test file",
                mime_type="text/plain",
            )
        )

        # Register prompts
        server.register_prompt(
            Prompt(
                name="generate_greeting",
                description="Generate a greeting",
                arguments=[{"name": "name", "description": "Name to greet"}],
            )
        )

        return server

    async def test_list_tools_on_server(self, configured_server: Server) -> None:
        """Test listing tools returns registered tools."""
        tools = configured_server.list_tools()
        assert len(tools) == 2
        tool_names = [t["name"] for t in tools]
        assert "process_data" in tool_names
        assert "no_handler" in tool_names

    async def test_list_resources_on_server(self, configured_server: Server) -> None:
        """Test listing resources returns registered resources."""
        resources = configured_server.list_resources()
        assert len(resources) == 1
        assert resources[0]["uri"] == "file://test.txt"

    async def test_list_prompts_on_server(self, configured_server: Server) -> None:
        """Test listing prompts returns registered prompts."""
        prompts = configured_server.list_prompts()
        assert len(prompts) == 1
        assert prompts[0]["name"] == "generate_greeting"

    async def test_handle_tool_call_with_handler(self, configured_server: Server) -> None:
        """Test calling tool with handler executes correctly."""
        result = await configured_server.handle_request(
            "tools/call", {"name": "process_data", "arguments": {"input": "test data"}}
        )
        assert result["processed"] is True
        assert "test data" in result["result"]

    async def test_handle_tool_call_without_handler(self, configured_server: Server) -> None:
        """Test calling tool without handler returns None."""
        result = await configured_server.handle_request(
            "tools/call", {"name": "no_handler", "arguments": {}}
        )
        assert result is None


class TestModelConversions:
    """Tests for model conversions between client and server."""

    def test_tool_model_to_server_conversion(self) -> None:
        """Test converting client Tool model to server Tool."""
        client_tool = ModelTool(
            name="search",
            description="Search for items",
            input_schema={"type": "object"},
        )
        server_tool = Tool(
            name=client_tool.name,
            description=client_tool.description,
            input_schema=client_tool.input_schema,
        )
        assert server_tool.name == "search"
        assert server_tool.to_dict() == client_tool.to_dict()

    def test_resource_model_to_server_conversion(self) -> None:
        """Test converting client Resource model to server Resource."""
        client_resource = ModelResource(
            uri="file://data.csv",
            name="Data CSV",
            description="Data file",
            mime_type="text/csv",
        )
        server_resource = Resource(
            uri=client_resource.uri,
            name=client_resource.name,
            description=client_resource.description,
            mime_type=client_resource.mime_type,
        )
        assert server_resource.uri == "file://data.csv"
        assert server_resource.to_dict() == client_resource.to_dict()

    def test_prompt_model_to_server_conversion(self) -> None:
        """Test converting client Prompt model to server Prompt."""
        client_prompt = ModelPrompt(
            name="summarize",
            description="Summarize text",
            arguments=[{"name": "text", "description": "Text to summarize"}],
        )
        server_prompt = Prompt(
            name=client_prompt.name,
            description=client_prompt.description,
            arguments=client_prompt.arguments,
        )
        assert server_prompt.name == "summarize"
        assert server_prompt.to_dict() == client_prompt.to_dict()


class TestServerRegistrationWorkflow:
    """Tests for common server registration workflows."""

    @pytest.fixture
    def data_processing_server(self) -> Server:
        """Create a data processing server."""
        server = Server(ServerConfig(name="data-processor", version="2.0.0"))

        async def filter_data(args: dict) -> list:
            items = args.get("items", [])
            return [x for x in items if x.get("active", True)]

        async def transform_data(args: dict) -> dict:
            return {
                "transformed": True,
                "items": [f"processed_{item}" for item in args.get("items", [])],
            }

        server.register_tool(
            Tool(name="filter", description="Filter items", handler=filter_data)
        )
        server.register_tool(
            Tool(name="transform", description="Transform items", handler=transform_data)
        )

        server.register_resource(
            Resource(uri="file://raw/input.csv", name="Raw Input", mime_type="text/csv")
        )
        server.register_resource(
            Resource(uri="file://processed/output.csv", name="Processed Output", mime_type="text/csv")
        )

        return server

    async def test_full_data_processing_workflow(self, data_processing_server: Server) -> None:
        """Test complete data processing workflow."""
        # Verify tools registered
        tools = data_processing_server.list_tools()
        assert len(tools) == 2

        # Verify resources registered
        resources = data_processing_server.list_resources()
        assert len(resources) == 2

        # Test transform tool
        result = await data_processing_server.handle_request(
            "tools/call",
            {"name": "transform", "arguments": {"items": ["a", "b", "c"]}},
        )
        assert result["transformed"] is True
        assert result["items"] == ["processed_a", "processed_b", "processed_c"]

    def test_server_properties(self, data_processing_server: Server) -> None:
        """Test server has correct properties."""
        assert data_processing_server.name == "data-processor"
        assert data_processing_server.version == "2.0.0"
