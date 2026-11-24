"""Tests for workflow MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pheno_mcp.server import Server
from pheno_mcp.tools.workflow_tools import (
    WORKFLOW_TOOLS,
    TOOL_WORKFLOW_EXECUTE,
    TOOL_WORKFLOW_STATUS,
    TOOL_WORKFLOW_CANCEL,
    TOOL_WORKFLOW_LIST,
    handle_workflow_execute,
    handle_workflow_status,
    handle_workflow_cancel,
    handle_workflow_list,
    register_workflow_tools,
)


class TestWorkflowToolSchemas:
    """Tests for workflow tool schemas."""

    def test_workflow_execute_schema(self) -> None:
        """Test workflow_execute tool schema is correctly defined."""
        assert TOOL_WORKFLOW_EXECUTE["name"] == "workflow_execute"
        assert "workflow_id" in TOOL_WORKFLOW_EXECUTE["input_schema"]["properties"]
        assert TOOL_WORKFLOW_EXECUTE["input_schema"]["required"] == ["workflow_id"]

    def test_workflow_status_schema(self) -> None:
        """Test workflow_status tool schema is correctly defined."""
        assert TOOL_WORKFLOW_STATUS["name"] == "workflow_status"
        assert "workflow_id" in TOOL_WORKFLOW_STATUS["input_schema"]["properties"]
        assert TOOL_WORKFLOW_STATUS["input_schema"]["required"] == ["workflow_id"]

    def test_workflow_cancel_schema(self) -> None:
        """Test workflow_cancel tool schema is correctly defined."""
        assert TOOL_WORKFLOW_CANCEL["name"] == "workflow_cancel"
        assert "workflow_id" in TOOL_WORKFLOW_CANCEL["input_schema"]["properties"]
        assert TOOL_WORKFLOW_CANCEL["input_schema"]["required"] == ["workflow_id"]

    def test_workflow_list_schema(self) -> None:
        """Test workflow_list tool schema is correctly defined."""
        assert TOOL_WORKFLOW_LIST["name"] == "workflow_list"
        assert TOOL_WORKFLOW_LIST["input_schema"]["properties"] == {}

    def test_workflow_tools_list(self) -> None:
        """Test WORKFLOW_TOOLS contains all tools."""
        assert len(WORKFLOW_TOOLS) == 4
        tool_names = {t["name"] for t in WORKFLOW_TOOLS}
        assert tool_names == {"workflow_execute", "workflow_status", "workflow_cancel", "workflow_list"}


class TestWorkflowToolsRegistration:
    """Tests for workflow tools registration with Server."""

    def test_register_workflow_tools(self) -> None:
        """Test register_workflow_tools adds all tools to server."""
        server = Server()
        register_workflow_tools(server)

        tools = server.list_tools()
        assert len(tools) == 4
        tool_names = {t["name"] for t in tools}
        assert tool_names == {"workflow_execute", "workflow_status", "workflow_cancel", "workflow_list"}

    def test_registered_tools_have_descriptions(self) -> None:
        """Test registered tools have descriptions."""
        server = Server()
        register_workflow_tools(server)

        tools = server.list_tools()
        for tool in tools:
            assert "description" in tool
            assert len(tool["description"]) > 0


class TestWorkflowExecuteHandler:
    """Tests for workflow_execute handler."""

    @pytest.mark.asyncio
    async def test_handle_workflow_execute_success(self) -> None:
        """Test successful workflow execution."""
        mock_response = {
            "execution_id": "exec-123",
            "workflow_id": "wf-456",
            "status": "RUNNING",
        }

        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.workflow_tools._client", return_value=mock_client):
            result = await handle_workflow_execute({"workflow_id": "wf-456"})

            assert result["execution_id"] == "exec-123"
            assert result["status"] == "RUNNING"

    @pytest.mark.asyncio
    async def test_handle_workflow_execute_http_error(self) -> None:
        """Test workflow_execute handles HTTP errors gracefully."""
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "Workflow not found"
        mock_response_obj.status_code = 404

        exc = httpx.HTTPStatusError(
            "404 Not Found",
            request=AsyncMock(),
            response=mock_response_obj,
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.workflow_tools._client", return_value=mock_client):
            result = await handle_workflow_execute({"workflow_id": "nonexistent"})

            assert "error" in result
            assert result["status_code"] == 404


class TestWorkflowStatusHandler:
    """Tests for workflow_status handler."""

    @pytest.mark.asyncio
    async def test_handle_workflow_status_success(self) -> None:
        """Test successful workflow status retrieval."""
        mock_response = {
            "workflow_id": "wf-456",
            "status": "COMPLETED",
            "progress": 100,
        }

        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.workflow_tools._client", return_value=mock_client):
            result = await handle_workflow_status({"workflow_id": "wf-456"})

            assert result["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_handle_workflow_status_http_error(self) -> None:
        """Test workflow_status handles HTTP errors gracefully."""
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "Not found"
        mock_response_obj.status_code = 404

        exc = httpx.HTTPStatusError(
            "404 Not Found",
            request=AsyncMock(),
            response=mock_response_obj,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.workflow_tools._client", return_value=mock_client):
            result = await handle_workflow_status({"workflow_id": "nonexistent"})

            assert "error" in result
            assert result["status_code"] == 404


class TestWorkflowCancelHandler:
    """Tests for workflow_cancel handler."""

    @pytest.mark.asyncio
    async def test_handle_workflow_cancel_success(self) -> None:
        """Test successful workflow cancellation."""
        mock_response = {
            "workflow_id": "wf-456",
            "status": "CANCELLED",
        }

        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.workflow_tools._client", return_value=mock_client):
            result = await handle_workflow_cancel({"workflow_id": "wf-456"})

            assert result["status"] == "CANCELLED"

    @pytest.mark.asyncio
    async def test_handle_workflow_cancel_http_error(self) -> None:
        """Test workflow_cancel handles HTTP errors gracefully."""
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "Cannot cancel"
        mock_response_obj.status_code = 409

        exc = httpx.HTTPStatusError(
            "409 Conflict",
            request=AsyncMock(),
            response=mock_response_obj,
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.workflow_tools._client", return_value=mock_client):
            result = await handle_workflow_cancel({"workflow_id": "wf-456"})

            assert "error" in result
            assert result["status_code"] == 409


class TestWorkflowListHandler:
    """Tests for workflow_list handler."""

    @pytest.mark.asyncio
    async def test_handle_workflow_list_success(self) -> None:
        """Test successful workflow listing."""
        mock_response = {
            "workflows": [
                {"id": "wf-1", "status": "RUNNING"},
                {"id": "wf-2", "status": "PENDING"},
            ]
        }

        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.workflow_tools._client", return_value=mock_client):
            result = await handle_workflow_list({})

            assert len(result["workflows"]) == 2

    @pytest.mark.asyncio
    async def test_handle_workflow_list_http_error(self) -> None:
        """Test workflow_list handles HTTP errors gracefully."""
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "Server error"
        mock_response_obj.status_code = 500

        exc = httpx.HTTPStatusError(
            "500 Server Error",
            request=AsyncMock(),
            response=mock_response_obj,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.workflow_tools._client", return_value=mock_client):
            result = await handle_workflow_list({})

            assert "error" in result
            assert result["status_code"] == 500


class TestWorkflowToolsServerIntegration:
    """Integration tests for workflow tools with Server."""

    @pytest.mark.asyncio
    async def test_server_calls_workflow_execute_handler(self) -> None:
        """Test server correctly calls workflow_execute handler."""
        server = Server()
        register_workflow_tools(server)

        mock_response = {
            "execution_id": "exec-abc",
            "workflow_id": "wf-xyz",
            "status": "RUNNING",
        }

        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.workflow_tools._client", return_value=mock_client):
            result = await server.handle_request(
                "tools/call",
                {"name": "workflow_execute", "arguments": {"workflow_id": "wf-xyz"}},
            )

            assert result["execution_id"] == "exec-abc"

    @pytest.mark.asyncio
    async def test_server_lists_workflow_tools(self) -> None:
        """Test tools/list returns workflow tools."""
        server = Server()
        register_workflow_tools(server)

        result = await server.handle_request("tools/list")

        assert "tools" in result
        tool_names = {t["name"] for t in result["tools"]}
        assert "workflow_execute" in tool_names
        assert "workflow_status" in tool_names
        assert "workflow_cancel" in tool_names
        assert "workflow_list" in tool_names
