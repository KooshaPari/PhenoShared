"""Tests for policy MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pheno_mcp.server import Server
from pheno_mcp.tools.policy_tools import (
    POLICY_TOOLS,
    TOOL_POLICY_LIST,
    TOOL_POLICY_GET,
    TOOL_POLICY_EVALUATE,
    handle_policy_list,
    handle_policy_get,
    handle_policy_evaluate,
    register_policy_tools,
)


class TestPolicyToolSchemas:
    def test_policy_list_schema(self) -> None:
        assert TOOL_POLICY_LIST["name"] == "policy_list"
        assert TOOL_POLICY_LIST["input_schema"]["properties"] == {}

    def test_policy_get_schema(self) -> None:
        assert TOOL_POLICY_GET["name"] == "policy_get"
        assert "policy_id" in TOOL_POLICY_GET["input_schema"]["properties"]
        assert TOOL_POLICY_GET["input_schema"]["required"] == ["policy_id"]

    def test_policy_evaluate_schema(self) -> None:
        assert TOOL_POLICY_EVALUATE["name"] == "policy_evaluate"
        assert "policy_id" in TOOL_POLICY_EVALUATE["input_schema"]["properties"]
        assert "context" in TOOL_POLICY_EVALUATE["input_schema"]["properties"]
        assert TOOL_POLICY_EVALUATE["input_schema"]["required"] == ["policy_id", "context"]

    def test_policy_tools_list(self) -> None:
        assert len(POLICY_TOOLS) == 3
        assert {tool["name"] for tool in POLICY_TOOLS} == {
            "policy_list",
            "policy_get",
            "policy_evaluate",
        }


class TestPolicyToolsRegistration:
    def test_register_policy_tools(self) -> None:
        server = Server()
        register_policy_tools(server)

        tools = server.list_tools()
        assert len(tools) == 3
        assert {tool["name"] for tool in tools} == {
            "policy_list",
            "policy_get",
            "policy_evaluate",
        }


class TestPolicyHandlers:
    @pytest.mark.asyncio
    async def test_handle_policy_list_success(self) -> None:
        mock_response = {"policies": [{"id": "policy-1"}]}
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.policy_tools._client", return_value=mock_client):
            result = await handle_policy_list({})

        assert result["policies"][0]["id"] == "policy-1"
        mock_client.get.assert_awaited_once_with("/api/v1/policies")

    @pytest.mark.asyncio
    async def test_handle_policy_list_http_error(self) -> None:
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "boom"
        mock_response_obj.status_code = 500
        exc = httpx.HTTPStatusError("500 Server Error", request=AsyncMock(), response=mock_response_obj)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.policy_tools._client", return_value=mock_client):
            result = await handle_policy_list({})

        assert result == {"error": "boom", "status_code": 500}

    @pytest.mark.asyncio
    async def test_handle_policy_get_success(self) -> None:
        mock_response = {"policy_id": "policy-1"}
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.policy_tools._client", return_value=mock_client):
            result = await handle_policy_get({"policy_id": "policy-1"})

        assert result["policy_id"] == "policy-1"
        mock_client.get.assert_awaited_once_with("/api/v1/policies/policy-1")

    @pytest.mark.asyncio
    async def test_handle_policy_get_http_error(self) -> None:
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "missing"
        mock_response_obj.status_code = 404
        exc = httpx.HTTPStatusError("404 Not Found", request=AsyncMock(), response=mock_response_obj)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.policy_tools._client", return_value=mock_client):
            result = await handle_policy_get({"policy_id": "policy-1"})

        assert result == {"error": "missing", "status_code": 404}

    @pytest.mark.asyncio
    async def test_handle_policy_evaluate_success(self) -> None:
        mock_response = {"policy_id": "policy-1", "allowed": True}
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.policy_tools._client", return_value=mock_client):
            result = await handle_policy_evaluate({"policy_id": "policy-1", "context": {}})

        assert result["allowed"] is True
        mock_client.post.assert_awaited_once_with(
            "/api/v1/policies/evaluate",
            json={"policy_id": "policy-1", "context": {}},
        )

    @pytest.mark.asyncio
    async def test_handle_policy_evaluate_http_error(self) -> None:
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "denied"
        mock_response_obj.status_code = 422
        exc = httpx.HTTPStatusError("422 Unprocessable Entity", request=AsyncMock(), response=mock_response_obj)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.policy_tools._client", return_value=mock_client):
            result = await handle_policy_evaluate({"policy_id": "policy-1", "context": {}})

        assert result == {"error": "denied", "status_code": 422}


class TestPolicyToolsServerIntegration:
    @pytest.mark.asyncio
    async def test_server_lists_policy_tools(self) -> None:
        server = Server()
        register_policy_tools(server)

        result = await server.handle_request("tools/list")
        assert "tools" in result
        assert {tool["name"] for tool in result["tools"]} == {
            "policy_list",
            "policy_get",
            "policy_evaluate",
        }
