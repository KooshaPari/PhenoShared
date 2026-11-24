"""Tests for session tools (suspend/resume MCP tools)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from pheno_mcp.server import Server
from pheno_mcp.tools.session_tools import (
    SESSION_TOOLS,
    TOOL_SESSION_SUSPEND,
    TOOL_SESSION_RESUME,
    handle_session_resume,
    handle_session_suspend,
    register_session_tools,
)


class TestSessionToolSchemas:
    """Tests for session tool schemas."""

    def test_session_suspend_schema(self) -> None:
        """Test session_suspend tool schema is correctly defined."""
        assert TOOL_SESSION_SUSPEND["name"] == "session_suspend"
        assert "session_id" in TOOL_SESSION_SUSPEND["input_schema"]["properties"]
        assert TOOL_SESSION_SUSPEND["input_schema"]["required"] == ["session_id"]

    def test_session_resume_schema(self) -> None:
        """Test session_resume tool schema is correctly defined."""
        assert TOOL_SESSION_RESUME["name"] == "session_resume"
        assert "bundle_ref" in TOOL_SESSION_RESUME["input_schema"]["properties"]
        assert TOOL_SESSION_RESUME["input_schema"]["required"] == ["bundle_ref"]

    def test_session_tools_list(self) -> None:
        """Test SESSION_TOOLS contains both tools."""
        assert len(SESSION_TOOLS) == 2
        tool_names = {t["name"] for t in SESSION_TOOLS}
        assert tool_names == {"session_suspend", "session_resume"}


class TestSessionToolsRegistration:
    """Tests for session tools registration with Server."""

    def test_register_session_tools(self) -> None:
        """Test register_session_tools adds both tools to server."""
        server = Server()
        register_session_tools(server)

        tools = server.list_tools()
        assert len(tools) == 2
        tool_names = {t["name"] for t in tools}
        assert tool_names == {"session_suspend", "session_resume"}

    def test_registered_tools_have_correct_schemas(self) -> None:
        """Test registered tools have correct input schemas."""
        server = Server()
        register_session_tools(server)

        # Check session_suspend
        suspend_tool = next(t for t in server.list_tools() if t["name"] == "session_suspend")
        assert "session_id" in suspend_tool["inputSchema"]["properties"]
        assert "required" in suspend_tool["inputSchema"]
        assert "session_id" in suspend_tool["inputSchema"]["required"]

        # Check session_resume
        resume_tool = next(t for t in server.list_tools() if t["name"] == "session_resume")
        assert "bundle_ref" in resume_tool["inputSchema"]["properties"]
        assert "bundle_ref" in resume_tool["inputSchema"]["required"]

    def test_registered_tools_have_descriptions(self) -> None:
        """Test registered tools have descriptions."""
        server = Server()
        register_session_tools(server)

        tools = server.list_tools()
        for tool in tools:
            assert "description" in tool
            assert len(tool["description"]) > 0


class TestSessionSuspendHandler:
    """Tests for session_suspend handler."""

    @pytest.mark.asyncio
    async def test_handle_session_suspend_success(self) -> None:
        """Test successful session suspend."""
        mock_response = {
            "bundle_ref": "bundle-123",
            "session_id": "session-456",
            "suspended_at": "2026-05-06T00:00:00Z",
            "status": "SUSPENDED",
        }

        # Create a mock response object (sync methods)
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        # Create a mock client
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.session_tools._client", return_value=mock_client):
            result = await handle_session_suspend({"session_id": "session-456"})

            assert result["bundle_ref"] == "bundle-123"
            assert result["session_id"] == "session-456"
            assert result["status"] == "SUSPENDED"

    @pytest.mark.asyncio
    async def test_handle_session_suspend_http_error(self) -> None:
        """Test session_suspend handles HTTP errors gracefully."""
        # Create a mock HTTPStatusError
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "Session not found"
        mock_response_obj.status_code = 404

        exc = httpx.HTTPStatusError(
            "404 Not Found",
            request=AsyncMock(),
            response=mock_response_obj,
        )

        # Create a mock client
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.session_tools._client", return_value=mock_client):
            result = await handle_session_suspend({"session_id": "nonexistent"})

            # Handler should return error dict
            assert "error" in result
            assert result["status_code"] == 404


class TestSessionResumeHandler:
    """Tests for session_resume handler."""

    @pytest.mark.asyncio
    async def test_handle_session_resume_success(self) -> None:
        """Test successful session resume."""
        mock_response = {
            "session_id": "new-session-789",
            "bundle_ref": "bundle-123",
            "resumed_at": "2026-05-06T00:00:00Z",
            "original_session_id": "session-456",
        }

        # Create a mock response object (sync methods)
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        # Create a mock client
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.session_tools._client", return_value=mock_client):
            result = await handle_session_resume({"bundle_ref": "bundle-123"})

            assert result["session_id"] == "new-session-789"
            assert result["bundle_ref"] == "bundle-123"
            assert result["original_session_id"] == "session-456"

    @pytest.mark.asyncio
    async def test_handle_session_resume_http_error(self) -> None:
        """Test session_resume handles HTTP errors gracefully."""
        # Create a mock HTTPStatusError
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "Bundle not found"
        mock_response_obj.status_code = 404

        exc = httpx.HTTPStatusError(
            "404 Not Found",
            request=AsyncMock(),
            response=mock_response_obj,
        )

        # Create a mock client
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.session_tools._client", return_value=mock_client):
            result = await handle_session_resume({"bundle_ref": "nonexistent-bundle"})

            # Handler should return error dict
            assert "error" in result
            assert result["status_code"] == 404


class TestSessionToolsServerIntegration:
    """Integration tests for session tools with Server."""

    @pytest.mark.asyncio
    async def test_server_calls_session_suspend_handler(self) -> None:
        """Test server correctly calls session_suspend handler."""
        server = Server()
        register_session_tools(server)

        mock_response = {
            "bundle_ref": "bundle-abc",
            "session_id": "session-xyz",
            "suspended_at": "2026-05-06T00:00:00Z",
            "status": "SUSPENDED",
        }

        # Create mock response (sync methods)
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        # Create mock client
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.session_tools._client", return_value=mock_client):
            result = await server.handle_request(
                "tools/call",
                {"name": "session_suspend", "arguments": {"session_id": "session-xyz"}},
            )

            assert result["bundle_ref"] == "bundle-abc"

    @pytest.mark.asyncio
    async def test_server_calls_session_resume_handler(self) -> None:
        """Test server correctly calls session_resume handler."""
        server = Server()
        register_session_tools(server)

        mock_response = {
            "session_id": "restored-session",
            "bundle_ref": "bundle-abc",
            "resumed_at": "2026-05-06T00:00:00Z",
        }

        # Create mock response (sync methods)
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        # Create mock client
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.session_tools._client", return_value=mock_client):
            result = await server.handle_request(
                "tools/call",
                {"name": "session_resume", "arguments": {"bundle_ref": "bundle-abc"}},
            )

            assert result["session_id"] == "restored-session"

    @pytest.mark.asyncio
    async def test_server_lists_session_tools(self) -> None:
        """Test tools/list returns session tools."""
        server = Server()
        register_session_tools(server)

        result = await server.handle_request("tools/list")

        assert "tools" in result
        tool_names = {t["name"] for t in result["tools"]}
        assert "session_suspend" in tool_names
        assert "session_resume" in tool_names
