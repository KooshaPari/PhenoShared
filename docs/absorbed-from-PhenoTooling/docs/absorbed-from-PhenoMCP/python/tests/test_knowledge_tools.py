"""Tests for knowledge MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pheno_mcp.server import Server
from pheno_mcp.tools.knowledge_tools import (
    KNOWLEDGE_TOOLS,
    TOOL_KNOWLEDGE_STORE,
    TOOL_KNOWLEDGE_RETRIEVE,
    TOOL_KNOWLEDGE_SEARCH,
    TOOL_KNOWLEDGE_DELETE,
    handle_knowledge_store,
    handle_knowledge_retrieve,
    handle_knowledge_search,
    handle_knowledge_delete,
    register_knowledge_tools,
)


class TestKnowledgeToolSchemas:
    def test_knowledge_store_schema(self) -> None:
        assert TOOL_KNOWLEDGE_STORE["name"] == "knowledge_store"
        assert "knowledge_id" in TOOL_KNOWLEDGE_STORE["input_schema"]["properties"]
        assert "content" in TOOL_KNOWLEDGE_STORE["input_schema"]["properties"]
        assert TOOL_KNOWLEDGE_STORE["input_schema"]["required"] == ["knowledge_id", "content"]

    def test_knowledge_retrieve_schema(self) -> None:
        assert TOOL_KNOWLEDGE_RETRIEVE["name"] == "knowledge_retrieve"
        assert "knowledge_id" in TOOL_KNOWLEDGE_RETRIEVE["input_schema"]["properties"]
        assert TOOL_KNOWLEDGE_RETRIEVE["input_schema"]["required"] == ["knowledge_id"]

    def test_knowledge_search_schema(self) -> None:
        assert TOOL_KNOWLEDGE_SEARCH["name"] == "knowledge_search"
        assert "query" in TOOL_KNOWLEDGE_SEARCH["input_schema"]["properties"]
        assert TOOL_KNOWLEDGE_SEARCH["input_schema"]["required"] == ["query"]

    def test_knowledge_delete_schema(self) -> None:
        assert TOOL_KNOWLEDGE_DELETE["name"] == "knowledge_delete"
        assert "knowledge_id" in TOOL_KNOWLEDGE_DELETE["input_schema"]["properties"]
        assert TOOL_KNOWLEDGE_DELETE["input_schema"]["required"] == ["knowledge_id"]

    def test_knowledge_tools_list(self) -> None:
        assert len(KNOWLEDGE_TOOLS) == 4
        assert {tool["name"] for tool in KNOWLEDGE_TOOLS} == {
            "knowledge_store",
            "knowledge_retrieve",
            "knowledge_search",
            "knowledge_delete",
        }


class TestKnowledgeToolsRegistration:
    def test_register_knowledge_tools(self) -> None:
        server = Server()
        register_knowledge_tools(server)

        tools = server.list_tools()
        assert len(tools) == 4
        assert {tool["name"] for tool in tools} == {
            "knowledge_store",
            "knowledge_retrieve",
            "knowledge_search",
            "knowledge_delete",
        }


class TestKnowledgeHandlers:
    @pytest.mark.asyncio
    async def test_handle_knowledge_store_success(self) -> None:
        mock_response = {"knowledge_id": "k-1", "content": "note"}
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.knowledge_tools._client", return_value=mock_client):
            result = await handle_knowledge_store({"knowledge_id": "k-1", "content": "note"})

        assert result["knowledge_id"] == "k-1"
        mock_client.post.assert_awaited_once_with(
            "/api/v1/knowledge",
            json={"knowledge_id": "k-1", "content": "note"},
        )

    @pytest.mark.asyncio
    async def test_handle_knowledge_store_http_error(self) -> None:
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "bad request"
        mock_response_obj.status_code = 400
        exc = httpx.HTTPStatusError("400 Bad Request", request=AsyncMock(), response=mock_response_obj)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.knowledge_tools._client", return_value=mock_client):
            result = await handle_knowledge_store({"knowledge_id": "k-1", "content": "note"})

        assert result == {"error": "bad request", "status_code": 400}

    @pytest.mark.asyncio
    async def test_handle_knowledge_retrieve_success(self) -> None:
        mock_response = {"knowledge_id": "k-1"}
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.knowledge_tools._client", return_value=mock_client):
            result = await handle_knowledge_retrieve({"knowledge_id": "k-1"})

        assert result["knowledge_id"] == "k-1"
        mock_client.get.assert_awaited_once_with("/api/v1/knowledge/k-1")

    @pytest.mark.asyncio
    async def test_handle_knowledge_retrieve_http_error(self) -> None:
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "missing"
        mock_response_obj.status_code = 404
        exc = httpx.HTTPStatusError("404 Not Found", request=AsyncMock(), response=mock_response_obj)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.knowledge_tools._client", return_value=mock_client):
            result = await handle_knowledge_retrieve({"knowledge_id": "k-1"})

        assert result == {"error": "missing", "status_code": 404}

    @pytest.mark.asyncio
    async def test_handle_knowledge_search_success(self) -> None:
        mock_response = {"results": [{"knowledge_id": "k-1"}]}
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.knowledge_tools._client", return_value=mock_client):
            result = await handle_knowledge_search({"query": "note", "limit": 5})

        assert result["results"][0]["knowledge_id"] == "k-1"
        mock_client.get.assert_awaited_once_with(
            "/api/v1/knowledge/search",
            params={"query": "note", "limit": 5},
        )

    @pytest.mark.asyncio
    async def test_handle_knowledge_search_http_error(self) -> None:
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "boom"
        mock_response_obj.status_code = 500
        exc = httpx.HTTPStatusError("500 Server Error", request=AsyncMock(), response=mock_response_obj)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.knowledge_tools._client", return_value=mock_client):
            result = await handle_knowledge_search({"query": "note"})

        assert result == {"error": "boom", "status_code": 500}

    @pytest.mark.asyncio
    async def test_handle_knowledge_delete_success(self) -> None:
        mock_response = {"deleted": True}
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.delete.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.knowledge_tools._client", return_value=mock_client):
            result = await handle_knowledge_delete({"knowledge_id": "k-1"})

        assert result["deleted"] is True
        mock_client.delete.assert_awaited_once_with("/api/v1/knowledge/k-1")

    @pytest.mark.asyncio
    async def test_handle_knowledge_delete_http_error(self) -> None:
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "gone"
        mock_response_obj.status_code = 404
        exc = httpx.HTTPStatusError("404 Not Found", request=AsyncMock(), response=mock_response_obj)

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.knowledge_tools._client", return_value=mock_client):
            result = await handle_knowledge_delete({"knowledge_id": "k-1"})

        assert result == {"error": "gone", "status_code": 404}


class TestKnowledgeToolsServerIntegration:
    @pytest.mark.asyncio
    async def test_server_lists_knowledge_tools(self) -> None:
        server = Server()
        register_knowledge_tools(server)

        result = await server.handle_request("tools/list")
        assert "tools" in result
        assert {tool["name"] for tool in result["tools"]} == {
            "knowledge_store",
            "knowledge_retrieve",
            "knowledge_search",
            "knowledge_delete",
        }
