"""End-to-end tests: exercise MCP tools via FastMCP's in-memory Client."""

from __future__ import annotations

import pytest
from fastmcp import Client

from cheap_llm_mcp.server import mcp


@pytest.mark.asyncio
@pytest.mark.requirement("FR-LLM-070")
async def test_providers_tool_lists_defaults():
    async with Client(mcp) as client:
        result = await client.call_tool("cheapllm_list_providers", {})
        data = result.data
        assert data["default_provider"] == "minimax"
        assert "minimax" in data["providers"]
        assert data["providers"]["minimax"]["default_model"] == "MiniMax-M2.7-highspeed"


@pytest.mark.asyncio
@pytest.mark.requirement("FR-LLM-071")
async def test_list_tools_complete_is_exposed():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        assert "cheapllm_complete_prompt" in names
        assert "cheapllm_stream_completion" in names
        assert "cheapllm_list_providers" in names
        assert "cheapllm_list_models" in names
        assert "cheapllm_check_health" in names
        assert "cheapllm_get_cost" in names


@pytest.mark.asyncio
@pytest.mark.requirement("FR-LLM-072")
async def test_cost_summary_tool_empty_ledger(tmp_path, monkeypatch):
    # Redirect ledger to a temp dir so we don't read real usage.
    monkeypatch.setenv("HOME", str(tmp_path))
    # Reset global singleton to force reload with new HOME.
    import cheap_llm_mcp.server as s

    s._ledger = None
    s._router = None
    async with Client(mcp) as client:
        result = await client.call_tool("cheapllm_get_cost", {})
        data = result.data
        assert data["calls"] == 0
        assert data["total_usd"] == 0.0
