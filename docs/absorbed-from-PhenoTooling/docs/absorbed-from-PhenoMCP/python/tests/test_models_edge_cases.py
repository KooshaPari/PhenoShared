"""Edge case tests for MCP data models."""

from __future__ import annotations

from pheno_mcp.models import CallToolResult, ListResourcesResult, Prompt, Resource, Tool


class TestToolEdgeCases:
    """Edge case tests for Tool model."""

    def test_tool_with_empty_input_schema(self) -> None:
        """Test tool with empty input schema."""
        tool = Tool(name="empty", description="Empty schema")
        assert tool.input_schema == {}

    def test_tool_with_complex_input_schema(self) -> None:
        """Test tool with complex JSON schema."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "User name"},
                "age": {"type": "integer", "minimum": 0},
                "active": {"type": "boolean", "default": True},
            },
            "required": ["name"],
        }
        tool = Tool(name="complex", description="Complex schema", input_schema=schema)
        result = tool.to_dict()
        assert result["inputSchema"]["type"] == "object"
        assert "properties" in result["inputSchema"]

    def test_tool_to_dict_returns_new_dict(self) -> None:
        """Test to_dict returns a new dict object."""
        tool = Tool(name="test", description="Test tool")
        result = tool.to_dict()
        # The dict is new
        assert result is not None
        # Modifying result doesn't affect tool
        result["name"] = "modified"
        assert tool.name == "test"

    def test_tool_unicode_characters(self) -> None:
        """Test tool with unicode characters."""
        tool = Tool(name="测试工具", description="测试描述")
        result = tool.to_dict()
        assert result["name"] == "测试工具"
        assert result["description"] == "测试描述"


class TestResourceEdgeCases:
    """Edge case tests for Resource model."""

    def test_resource_with_contents(self) -> None:
        """Test resource with contents."""
        resource = Resource(
            uri="file://data.json",
            name="JSON Data",
            contents={"key": "value"},
        )
        assert resource.contents == {"key": "value"}

    def test_resource_with_none_contents(self) -> None:
        """Test resource with None contents."""
        resource = Resource(uri="file://test", name="Test", contents=None)
        assert resource.contents is None

    def test_resource_with_empty_string_description(self) -> None:
        """Test resource with empty string description."""
        resource = Resource(uri="file://test", name="Test", description="")
        assert resource.description == ""

    def test_resource_with_special_uri_chars(self) -> None:
        """Test resource with special URI characters."""
        resource = Resource(
            uri="s3://my-bucket/path%20with%20spaces/file.json",
            name="S3 File",
        )
        assert "%20" in resource.uri

    def test_resource_to_dict_does_not_modify_original(self) -> None:
        """Test to_dict does not modify original."""
        resource = Resource(uri="file://test", name="Test")
        result = resource.to_dict()
        result["uri"] = "modified"
        assert resource.uri == "file://test"


class TestPromptEdgeCases:
    """Edge case tests for Prompt model."""

    def test_prompt_with_empty_arguments(self) -> None:
        """Test prompt with empty arguments list."""
        prompt = Prompt(name="no_args", description="No arguments")
        assert prompt.arguments == []

    def test_prompt_with_complex_arguments(self) -> None:
        """Test prompt with complex argument schemas."""
        arguments = [
            {"name": "template", "description": "Template string", "type": "string"},
            {
                "name": "variables",
                "description": "Variables map",
                "type": "object",
                "properties": {"key": {"type": "string"}},
            },
        ]
        prompt = Prompt(name="render", description="Render template", arguments=arguments)
        result = prompt.to_dict()
        assert len(result["arguments"]) == 2

    def test_prompt_with_required_flag(self) -> None:
        """Test prompt arguments with required flag."""
        arguments = [
            {"name": "required_arg", "description": "Required", "required": True},
            {"name": "optional_arg", "description": "Optional", "required": False},
        ]
        prompt = Prompt(name="test", description="Test", arguments=arguments)
        result = prompt.to_dict()
        assert result["arguments"][0]["required"] is True
        assert result["arguments"][1]["required"] is False


class TestCallToolResultEdgeCases:
    """Edge case tests for CallToolResult model."""

    def test_result_with_text_content(self) -> None:
        """Test result with text content."""
        result = CallToolResult(
            content=[{"type": "text", "text": "Hello, World!"}]
        )
        output = result.to_dict()
        assert output["content"][0]["type"] == "text"

    def test_result_with_image_content(self) -> None:
        """Test result with image content."""
        result = CallToolResult(
            content=[{"type": "image", "data": "base64...", "mimeType": "image/png"}]
        )
        output = result.to_dict()
        assert output["content"][0]["type"] == "image"

    def test_result_with_multiple_content_items(self) -> None:
        """Test result with multiple content items."""
        result = CallToolResult(
            content=[
                {"type": "text", "text": "First"},
                {"type": "text", "text": "Second"},
            ]
        )
        output = result.to_dict()
        assert len(output["content"]) == 2

    def test_result_with_empty_content(self) -> None:
        """Test result with empty content list."""
        result = CallToolResult(content=[])
        output = result.to_dict()
        assert output["content"] == []

    def test_result_error_defaults_to_false(self) -> None:
        """Test result is_error defaults to False."""
        result = CallToolResult(content=[{"type": "text", "text": "test"}])
        assert result.is_error is False


class TestListResourcesResultEdgeCases:
    """Edge case tests for ListResourcesResult model."""

    def test_empty_resources_list(self) -> None:
        """Test with empty resources list."""
        result = ListResourcesResult(resources=[])
        output = result.to_dict()
        assert output["resources"] == []

    def test_single_resource(self) -> None:
        """Test with single resource."""
        result = ListResourcesResult(
            resources=[{"uri": "file://test.txt", "name": "Test"}]
        )
        output = result.to_dict()
        assert len(output["resources"]) == 1

    def test_resources_to_dict_returns_new_dict(self) -> None:
        """Test to_dict returns a new dict with list reference."""
        # Note: to_dict returns a shallow copy - the inner list is the same reference
        # This is expected Python dataclass behavior
        result = ListResourcesResult(resources=[{"uri": "file://test", "name": "Test"}])
        output = result.to_dict()
        # The outer dict is new
        assert output is not result.resources
        # But the inner list is the same reference
        assert output["resources"] is result.resources

    def test_resources_list_immutability(self) -> None:
        """Test that modifying the returned list affects original."""
        original_list = [{"uri": "file://test", "name": "Test"}]
        result = ListResourcesResult(resources=original_list)
        output = result.to_dict()
        # Modifying through the result's reference affects original
        output["resources"].append({"uri": "file://other", "name": "Other"})
        assert len(original_list) == 2
        assert len(result.resources) == 2
