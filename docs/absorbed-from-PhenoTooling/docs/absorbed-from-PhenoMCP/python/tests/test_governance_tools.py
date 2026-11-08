"""Tests for governance/ledger MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pheno_mcp.server import Server
from pheno_mcp.tools.governance_tools import (
    GOVERNANCE_TOOLS,
    TOOL_LEDGER_QUERY,
    TOOL_LEDGER_VERIFY,
    handle_ledger_query,
    handle_ledger_verify,
    register_governance_tools,
)


class TestGovernanceToolSchemas:
    """Tests for governance tool schemas."""

    def test_ledger_query_schema(self) -> None:
        """Test ledger_query tool schema is correctly defined."""
        assert TOOL_LEDGER_QUERY["name"] == "ledger_query"
        assert "from_entry" in TOOL_LEDGER_QUERY["input_schema"]["properties"]
        assert "limit" in TOOL_LEDGER_QUERY["input_schema"]["properties"]

    def test_ledger_verify_schema(self) -> None:
        """Test ledger_verify tool schema is correctly defined."""
        assert TOOL_LEDGER_VERIFY["name"] == "ledger_verify"
        assert "from_entry" in TOOL_LEDGER_VERIFY["input_schema"]["properties"]
        assert "to_entry" in TOOL_LEDGER_VERIFY["input_schema"]["properties"]
        assert TOOL_LEDGER_VERIFY["input_schema"]["required"] == ["from_entry", "to_entry"]

    def test_governance_tools_list(self) -> None:
        """Test GOVERNANCE_TOOLS contains both tools."""
        assert len(GOVERNANCE_TOOLS) == 2
        tool_names = {t["name"] for t in GOVERNANCE_TOOLS}
        assert tool_names == {"ledger_query", "ledger_verify"}


class TestGovernanceToolsRegistration:
    """Tests for governance tools registration with Server."""

    def test_register_governance_tools(self) -> None:
        """Test register_governance_tools adds both tools to server."""
        server = Server()
        register_governance_tools(server)

        tools = server.list_tools()
        assert len(tools) == 2
        tool_names = {t["name"] for t in tools}
        assert tool_names == {"ledger_query", "ledger_verify"}

    def test_registered_tools_have_descriptions(self) -> None:
        """Test registered tools have descriptions."""
        server = Server()
        register_governance_tools(server)

        tools = server.list_tools()
        for tool in tools:
            assert "description" in tool
            assert len(tool["description"]) > 0


class TestLedgerQueryHandler:
    """Tests for ledger_query handler."""

    @pytest.mark.asyncio
    async def test_handle_ledger_query_success(self) -> None:
        """Test successful ledger query."""
        mock_response = {
            "entries": [
                {"id": "entry-1", "action": "money.ledger_entry.created.v1"},
                {"id": "entry-2", "action": "money.ledger_entry.created.v1"},
            ]
        }

        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.governance_tools._client", return_value=mock_client):
            result = await handle_ledger_query({"action": "money.ledger_entry.created.v1"})

            assert len(result["entries"]) == 2

    @pytest.mark.asyncio
    async def test_handle_ledger_query_http_error(self) -> None:
        """Test ledger_query handles HTTP errors gracefully."""
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "Bad request"
        mock_response_obj.status_code = 400

        exc = httpx.HTTPStatusError(
            "400 Bad Request",
            request=AsyncMock(),
            response=mock_response_obj,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.governance_tools._client", return_value=mock_client):
            result = await handle_ledger_query({})

            assert "error" in result
            assert result["status_code"] == 400


class TestLedgerVerifyHandler:
    """Tests for ledger_verify handler."""

    @pytest.mark.asyncio
    async def test_handle_ledger_verify_success(self) -> None:
        """Test successful ledger verification."""
        mock_response = {
            "valid": True,
            "from_entry": "entry-1",
            "to_entry": "entry-10",
            "chain_length": 10,
        }

        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.governance_tools._client", return_value=mock_client):
            result = await handle_ledger_verify({"from_entry": "entry-1", "to_entry": "entry-10"})

            assert result["valid"] is True
            assert result["chain_length"] == 10

    @pytest.mark.asyncio
    async def test_handle_ledger_verify_http_error(self) -> None:
        """Test ledger_verify handles HTTP errors gracefully."""
        mock_response_obj = AsyncMock()
        mock_response_obj.text = "Chain verification failed"
        mock_response_obj.status_code = 422

        exc = httpx.HTTPStatusError(
            "422 Unprocessable Entity",
            request=AsyncMock(),
            response=mock_response_obj,
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=exc)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pheno_mcp.tools.governance_tools._client", return_value=mock_client):
            result = await handle_ledger_verify({"from_entry": "entry-1", "to_entry": "entry-99"})

            assert "error" in result
            assert result["status_code"] == 422


class TestGovernanceToolsServerIntegration:
    """Integration tests for governance tools with Server."""

    @pytest.mark.asyncio
    async def test_server_calls_ledger_query_handler(self) -> None:
        """Test server correctly calls ledger_query handler."""
        server = Server()
        register_governance_tools(server)

        mock_response = {"entries": [{"id": "entry-1"}]}

        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.governance_tools._client", return_value=mock_client):
            result = await server.handle_request(
                "tools/call",
                {"name": "ledger_query", "arguments": {"limit": 10}},
            )

            assert len(result["entries"]) == 1

    @pytest.mark.asyncio
    async def test_server_calls_ledger_verify_handler(self) -> None:
        """Test server correctly calls ledger_verify handler."""
        server = Server()
        register_governance_tools(server)

        mock_response = {
            "valid": True,
            "from_entry": "entry-1",
            "to_entry": "entry-5",
        }

        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("pheno_mcp.tools.governance_tools._client", return_value=mock_client):
            result = await server.handle_request(
                "tools/call",
                {"name": "ledger_verify", "arguments": {"from_entry": "entry-1", "to_entry": "entry-5"}},
            )

            assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_server_lists_governance_tools(self) -> None:
        """Test tools/list returns governance tools."""
        server = Server()
        register_governance_tools(server)

        result = await server.handle_request("tools/list")

        assert "tools" in result
        tool_names = {t["name"] for t in result["tools"]}
        assert "ledger_query" in tool_names
        assert "ledger_verify" in tool_names
