"""Policy MCP tools backed by Parpoura."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import httpx

_BASE_URL = os.environ.get("PARPOURA_BASE_URL", "http://localhost:8001")
POLICY_ID_DESCRIPTION = "Policy identifier"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=_BASE_URL, timeout=30.0)


TOOL_POLICY_LIST: dict[str, Any] = {
    "name": "policy_list",
    "description": "List available policies.",
    "input_schema": {"type": "object", "properties": {}},
}

TOOL_POLICY_GET: dict[str, Any] = {
    "name": "policy_get",
    "description": "Fetch a policy by identifier.",
    "input_schema": {
        "type": "object",
        "properties": {
            "policy_id": {"type": "string", "description": POLICY_ID_DESCRIPTION},
        },
        "required": ["policy_id"],
    },
}

TOOL_POLICY_EVALUATE: dict[str, Any] = {
    "name": "policy_evaluate",
    "description": "Evaluate a policy against the supplied context.",
    "input_schema": {
        "type": "object",
        "properties": {
            "policy_id": {"type": "string", "description": POLICY_ID_DESCRIPTION},
            "context": {"type": "object", "description": "Evaluation context"},
        },
        "required": ["policy_id", "context"],
    },
}

POLICY_TOOLS = [
    TOOL_POLICY_LIST,
    TOOL_POLICY_GET,
    TOOL_POLICY_EVALUATE,
]


async def handle_policy_list(_args: dict[str, Any]) -> dict[str, Any]:
    async with _client() as client:
        try:
            response = await client.get("/api/v1/policies")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {"error": exc.response.text, "status_code": exc.response.status_code}


async def handle_policy_get(args: dict[str, Any]) -> dict[str, Any]:
    async with _client() as client:
        try:
            policy_id = quote(args["policy_id"], safe="")
            response = await client.get(f"/api/v1/policies/{policy_id}")
            response.raise_for_status()
            return response.json()
        except KeyError:
            return {"error": "missing policy_id", "status_code": 400}
        except httpx.HTTPStatusError as exc:
            return {"error": exc.response.text, "status_code": exc.response.status_code}


async def handle_policy_evaluate(args: dict[str, Any]) -> dict[str, Any]:
    async with _client() as client:
        try:
            response = await client.post("/api/v1/policies/evaluate", json=args)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {"error": exc.response.text, "status_code": exc.response.status_code}


def register_policy_tools(server: Any) -> None:
    from pheno_mcp.server import Tool

    for tool_def in POLICY_TOOLS:
        handler = globals()[f"handle_{tool_def['name']}"]
        server.register_tool(
            Tool(
                name=tool_def["name"],
                description=tool_def["description"],
                input_schema=tool_def["input_schema"],
                handler=handler,
            )
        )
