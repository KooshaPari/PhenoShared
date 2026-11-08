"""MCP data models for tools, resources, prompts, and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Tool:
    """Represents an MCP tool.

    Attributes:
        name: Unique identifier for the tool.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for tool input parameters.
    """

    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the tool to a dictionary.

        Returns:
            Dictionary representation with camelCase keys.
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class Resource:
    """Represents an MCP resource.

    Attributes:
        uri: Unique resource identifier.
        name: Human-readable resource name.
        description: Description of the resource.
        mime_type: MIME type of the resource content.
        contents: Optional resource contents (for inline resources).
    """

    uri: str
    name: str = ""
    description: str = ""
    mime_type: str = "text/plain"
    contents: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the resource to a dictionary.

        Returns:
            Dictionary representation with camelCase keys.
        """
        result: dict[str, Any] = {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }
        if self.contents is not None:
            result["contents"] = self.contents
        return result


@dataclass
class Prompt:
    """Represents an MCP prompt.

    Attributes:
        name: Unique prompt identifier.
        description: Human-readable prompt description.
        arguments: List of prompt argument definitions.
    """

    name: str
    description: str = ""
    arguments: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the prompt to a dictionary.

        Returns:
            Dictionary representation of the prompt.
        """
        return {
            "name": self.name,
            "description": self.description,
            "arguments": list(self.arguments),
        }


@dataclass
class CallToolResult:
    """Result of a tool call.

    Attributes:
        content: List of content items (text, image, or resource).
        is_error: Whether the result represents an error.
    """

    content: list[dict[str, Any]]
    is_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result to a dictionary.

        Returns:
            Dictionary representation with camelCase keys.
        """
        return {
            "content": list(self.content),
            "isError": self.is_error,
        }


@dataclass
class ListResourcesResult:
    """Result of listing resources.

    Attributes:
        resources: List of resource dictionaries.
    """

    resources: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result to a dictionary.

        Returns:
            Dictionary representation with resources under 'resources' key.
        """
        return {
            "resources": self.resources,
        }
