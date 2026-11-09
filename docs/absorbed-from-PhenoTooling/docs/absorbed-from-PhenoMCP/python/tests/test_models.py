"""Tests for pheno_mcp.models data classes."""

from __future__ import annotations

import pytest

from pheno_mcp.models import CallToolResult, ListResourcesResult, Prompt, Resource, Tool


class TestToolToDict:
    """Tests for Tool.to_dict()."""

    def test_tool_to_dict_basic(self) -> None:
        """Tool.to_dict() serializes name, description, and input_schema."""
        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
        )
        result = tool.to_dict()
        assert result == {
            "name": "test_tool",
            "description": "A test tool",
            "inputSchema": {"type": "object", "properties": {}},
        }

    def test_tool_to_dict_defaults(self) -> None:
        """Tool.to_dict() uses default values for optional fields."""
        tool = Tool(name="minimal_tool")
        result = tool.to_dict()
        assert result["name"] == "minimal_tool"
        assert result["description"] == ""
        assert result["inputSchema"] == {}


class TestResourceToDict:
    """Tests for Resource.to_dict()."""

    def test_resource_to_dict_with_contents(self) -> None:
        """Resource.to_dict() includes contents when present."""
        resource = Resource(
            uri="file:///tmp/test.txt",
            name="test.txt",
            description="A test file",
            mime_type="text/plain",
            contents={"text": "hello"},
        )
        result = resource.to_dict()
        assert result == {
            "uri": "file:///tmp/test.txt",
            "name": "test.txt",
            "description": "A test file",
            "mimeType": "text/plain",
            "contents": {"text": "hello"},
        }

    def test_resource_to_dict_omits_none_contents(self) -> None:
        """Resource.to_dict() omits contents key when None."""
        resource = Resource(uri="res://empty")
        result = resource.to_dict()
        assert "contents" not in result
        assert result["mimeType"] == "text/plain"


class TestPromptToDict:
    """Tests for Prompt.to_dict()."""

    def test_prompt_to_dict(self) -> None:
        """Prompt.to_dict() serializes all fields."""
        prompt = Prompt(
            name="greet",
            description="Greeting prompt",
            arguments=[{"name": "name", "required": True}],
        )
        result = prompt.to_dict()
        assert result == {
            "name": "greet",
            "description": "Greeting prompt",
            "arguments": [{"name": "name", "required": True}],
        }


class TestCallToolResultToDict:
    """Tests for CallToolResult.to_dict()."""

    def test_call_tool_result_to_dict(self) -> None:
        """CallToolResult.to_dict() serializes content and is_error."""
        result = CallToolResult(
            content=[{"type": "text", "text": "hello"}],
            is_error=False,
        )
        assert result.to_dict() == {
            "content": [{"type": "text", "text": "hello"}],
            "isError": False,
        }

    def test_call_tool_result_defaults(self) -> None:
        """CallToolResult defaults is_error to False."""
        result = CallToolResult(content=[])
        assert result.to_dict()["isError"] is False


class TestListResourcesResultToDict:
    """Tests for ListResourcesResult.to_dict()."""

    def test_list_resources_result_to_dict(self) -> None:
        """ListResourcesResult.to_dict() wraps resources list."""
        result = ListResourcesResult(resources=[{"uri": "res://a"}])
        assert result.to_dict() == {"resources": [{"uri": "res://a"}]}
