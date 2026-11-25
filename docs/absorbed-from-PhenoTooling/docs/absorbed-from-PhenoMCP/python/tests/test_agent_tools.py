"""Tests for agent MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pheno_mcp.server import Server
from pheno_mcp.tools.agent_tools import (
    AGENT_TOOLS,
    TOOL_AGENT_CREATE,
    TOOL_AGENT_LIST,
    TOOL_AGENT_GET,
    TOOL_AGENT_DELETE,
    handle_agent_create,
    handle_agent_list,
    handle_agent_get,
    handle_agent_delete,
    register_agent_tools,
)


class TestAgentToolSchemas:
    def test_agent_create_schema(self) -> None:
        assert TOOL_AGENT_CREATE["name"] == "agent_create"
        assert "name" in TOOL_AGENT_CREATE["input_schema"]["properties"]
        assert TOOL_AGENT_CREATE["input_schema"]["required"] == ["name"]

    def test_agent_list_schema(self) -> None:
        assert TOOL_AGENT_LIST["name"] == "agent_list"
        assert TOOL_AGENT_LIST["input_schema"]["properties"] == {}

    def test_agent_get_schema(self) -> None:
        assert TOOL_AGENT_GET["name"] == "agent_get"
        assert "agent_id" in TOOL_AGENT_GET["input_schema"]["properties"]
        assert TOOL_AGENT_GET["input_schema"]["required"] == ["agent_id"]

    def test_agent_delete_schema(self) -> None:
        assert TOOL_AGENT_DELETE["name"] == "agent_delete"
        assert "agent_id" in TOOL_AGENT_DELETE["input_schema"]["properties"]
        assert TOOL_AGENT_DELETE["input_schema"]["required"] == ["agent_id"]

    def test_agent_tools_list(self) -> None:
        assert len(AGENT_TOOLS) == 4
        assert {tool["name"] for tool in AGENT_TOOLS} == {
            "agent_create",
            "agent_list",
            "agent_get",
            "agent_delete",
        }


class TestAgentToolsRegistration:
    def test_register_agent_tools(self) -> None:
        server = Server()
        register_agent_tools(server)

        tools = server.list_tools()
        assert len(tools) == 4
        assert {tool["name"] for tool in tools} == {
            "agent_create",
            "agent_list",
            "agent_get",
            "agent_delete",
        }


class TestAgentHandlers:
    @pytest.mark.asyncio
    async def test_handle_agent_create_success(self) -> None:
        mock_response = {"agent_id": "agent-1", "name": "Agent One"}
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.agent_tools._client", return_value=mock_client):
            result = await handle_agent_create({"name": "Agent One"})

        assert result["agent_id"] == "agent-1"
        mock_client.post.assert_awaited_once_with("/api/v1/agents", json={"name": "Agent One"})

    @pytest.mark.asyncio
    async def test_handle_agent_create_http_error(self) -> None:
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "bad request"
        mock_response_obj.status_code = 400
        exc = httpx.HTTPStatusError("400 Bad Request", request=AsyncMock(), response=mock_response_obj)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.agent_tools._client", return_value=mock_client):
            result = await handle_agent_create({"name": "Agent One"})

        assert result == {"error": "bad request", "status_code": 400}

    @pytest.mark.asyncio
    async def test_handle_agent_list_success(self) -> None:
        mock_response = {"agents": [{"id": "agent-1"}]}
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.agent_tools._client", return_value=mock_client):
            result = await handle_agent_list({})

        assert result["agents"][0]["id"] == "agent-1"

    @pytest.mark.asyncio
    async def test_handle_agent_list_http_error(self) -> None:
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "boom"
        mock_response_obj.status_code = 500
        exc = httpx.HTTPStatusError("500 Server Error", request=AsyncMock(), response=mock_response_obj)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.agent_tools._client", return_value=mock_client):
            result = await handle_agent_list({})

        assert result == {"error": "boom", "status_code": 500}

    @pytest.mark.asyncio
    async def test_handle_agent_get_success(self) -> None:
        mock_response = {"agent_id": "agent-1"}
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.agent_tools._client", return_value=mock_client):
            result = await handle_agent_get({"agent_id": "agent-1"})

        assert result["agent_id"] == "agent-1"
        mock_client.get.assert_awaited_once_with("/api/v1/agents/agent-1")

    @pytest.mark.asyncio
    async def test_handle_agent_get_http_error(self) -> None:
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "missing"
        mock_response_obj.status_code = 404
        exc = httpx.HTTPStatusError("404 Not Found", request=AsyncMock(), response=mock_response_obj)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.agent_tools._client", return_value=mock_client):
            result = await handle_agent_get({"agent_id": "missing"})

        assert result == {"error": "missing", "status_code": 404}

    @pytest.mark.asyncio
    async def test_handle_agent_delete_success(self) -> None:
        mock_response = {"deleted": True}
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.delete.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.agent_tools._client", return_value=mock_client):
            result = await handle_agent_delete({"agent_id": "agent-1"})

        assert result["deleted"] is True
        mock_client.delete.assert_awaited_once_with("/api/v1/agents/agent-1")

    @pytest.mark.asyncio
    async def test_handle_agent_delete_http_error(self) -> None:
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "gone"
        mock_response_obj.status_code = 409
        exc = httpx.HTTPStatusError("409 Conflict", request=AsyncMock(), response=mock_response_obj)

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.agent_tools._client", return_value=mock_client):
            result = await handle_agent_delete({"agent_id": "agent-1"})

        assert result == {"error": "gone", "status_code": 409}


class TestAgentToolsServerIntegration:
    @pytest.mark.asyncio
    async def test_server_lists_agent_tools(self) -> None:
        server = Server()
        register_agent_tools(server)

        result = await server.handle_request("tools/list")
        assert "tools" in result
        assert {tool["name"] for tool in result["tools"]} == {
            "agent_create",
            "agent_list",
            "agent_get",
            "agent_delete",
        }
