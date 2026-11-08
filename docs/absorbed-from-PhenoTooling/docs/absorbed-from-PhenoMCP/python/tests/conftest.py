"""Shared pytest fixtures and configuration."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_tool_data() -> dict:
    """Fixture providing sample tool data."""
    return {
        "name": "test_tool",
        "description": "A test tool",
        "input_schema": {"type": "object", "properties": {}},
    }


@pytest.fixture
def sample_resource_data() -> dict:
    """Fixture providing sample resource data."""
    return {
        "uri": "file://test.txt",
        "name": "Test File",
        "description": "A test file",
        "mime_type": "text/plain",
    }


@pytest.fixture
def sample_prompt_data() -> dict:
    """Fixture providing sample prompt data."""
    return {
        "name": "test_prompt",
        "description": "A test prompt",
        "arguments": [{"name": "arg1", "type": "string"}],
    }
