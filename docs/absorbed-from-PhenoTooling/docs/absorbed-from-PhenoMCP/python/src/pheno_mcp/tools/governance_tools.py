"""Governance and ledger MCP tools.

Wraps Parpoura governance/ledger API:
  - GET  /api/v1/governance/ledger         -> ledger entries (filterable)
  - POST /api/v1/governance/ledger/verify  -> hash-chain integrity check
"""

from __future__ import annotations

import os
from typing import Any

import httpx

# ---------------------------------------------------------------------
# Shared HTTP client
# ---------------------------------------------------------------------

_BASE_URL = os.environ.get("PARPOURA_BASE_URL", "http://localhost:8001")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=_BASE_URL, timeout=30.0)


# ---------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------

TOOL_LEDGER_QUERY = {
    "name": "ledger_query",
    "description": (
        "Query the governance ledger with optional filters. "
        "Returns entries with checksums and hash-chain metadata."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "from_entry": {
                "type": "string",
                "description": "Filter entries starting from this ledger entry ID",
            },
            "to_entry": {
                "type": "string",
                "description": "Filter entries up to this ledger entry ID",
            },
            "action": {
                "type": "string",
                "description": "Filter by event action type (e.g. 'money.ledger_entry.created.v1')",
            },
            "actor": {
                "type": "string",
                "description": "Filter by actor/agent name",
            },
            "workflow_id": {
                "type": "string",
                "description": "Filter by associated workflow ID",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of entries to return",
                "default": 100,
            },
        },
        "required": [],
    },
}


TOOL_LEDGER_VERIFY = {
    "name": "ledger_verify",
    "description": (
        "Verify the integrity of the ledger hash chain between two entry IDs. "
        "Checks that each entry's checksum correctly chains to the previous one. "
        "Returns validation status and any chain-break details."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "from_entry": {
                "type": "string",
                "description": "Starting ledger entry ID (inclusive)",
            },
            "to_entry": {
                "type": "string",
                "description": "Ending ledger entry ID (inclusive)",
            },
        },
        "required": ["from_entry", "to_entry"],
    },
}


GOVERNANCE_TOOLS = [TOOL_LEDGER_QUERY, TOOL_LEDGER_VERIFY]


# ---------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------


async def handle_ledger_query(args: dict[str, Any]) -> dict[str, Any]:
    """GET /api/v1/governance/ledger with query params"""
    params: dict[str, Any] = {}
    for key in ("from_entry", "to_entry", "action", "actor", "workflow_id", "limit"):
        if key in args and args[key] is not None:
            params[key] = args[key]

    async with _client() as client:
        try:
            response = await client.get("/api/v1/governance/ledger", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {
                "error": exc.response.text,
                "status_code": exc.response.status_code,
            }


async def handle_ledger_verify(args: dict[str, Any]) -> dict[str, Any]:
    """POST /api/v1/governance/ledger/verify"""
    payload = {
        "from_entry": args["from_entry"],
        "to_entry": args["to_entry"],
    }

    async with _client() as client:
        try:
            response = await client.post(
                "/api/v1/governance/ledger/verify",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {
                "error": exc.response.text,
                "status_code": exc.response.status_code,
            }


# ---------------------------------------------------------------------
# Server registration helpers
# ---------------------------------------------------------------------


def register_governance_tools(server: Any) -> None:
    """Register all governance/ledger tools with an MCP server.

    Args:
        server: An MCP Server instance with register_tool method.
    """
    from pheno_mcp.server import Tool

    for tool_def in GOVERNANCE_TOOLS:
        handler_name = f"handle_{tool_def['name']}"
        handler = globals().get(handler_name)
        server.register_tool(
            Tool(
                name=tool_def["name"],
                description=tool_def["description"],
                input_schema=tool_def["input_schema"],
                handler=handler,
            )
        )
