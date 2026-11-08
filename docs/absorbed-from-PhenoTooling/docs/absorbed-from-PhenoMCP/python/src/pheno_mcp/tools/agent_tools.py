"""Agent MCP tools backed by Parpoura."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import httpx

_BASE_URL = os.environ.get("PARPOURA_BASE_URL", "http://localhost:8001")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=_BASE_URL, timeout=30.0)


TOOL_AGENT_CREATE: dict[str, Any] = {
    "name": "agent_create",
    "description": "Create a new agent record in Parpoura.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string", "description": "Optional agent identifier"},
            "name": {"type": "string", "description": "Agent name"},
            "description": {"type": "string", "description": "Agent description"},
        },
        "required": ["name"],
    },
}

TOOL_AGENT_LIST: dict[str, Any] = {
    "name": "agent_list",
    "description": "List registered agents.",
    "input_schema": {"type": "object", "properties": {}},
}

TOOL_AGENT_GET: dict[str, Any] = {
    "name": "agent_get",
    "description": "Fetch a single agent by identifier.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string", "description": "Agent identifier"},
        },
        "required": ["agent_id"],
    },
}

TOOL_AGENT_DELETE: dict[str, Any] = {
    "name": "agent_delete",
    "description": "Delete an agent by identifier.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string", "description": "Agent identifier"},
        },
        "required": ["agent_id"],
    },
}

AGENT_TOOLS = [
    TOOL_AGENT_CREATE,
    TOOL_AGENT_LIST,
    TOOL_AGENT_GET,
    TOOL_AGENT_DELETE,
]


async def handle_agent_create(args: dict[str, Any]) -> dict[str, Any]:
    async with _client() as client:
        try:
            response = await client.post("/api/v1/agents", json=args)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {"error": exc.response.text, "status_code": exc.response.status_code}


async def handle_agent_list(_args: dict[str, Any]) -> dict[str, Any]:
    async with _client() as client:
        try:
            response = await client.get("/api/v1/agents")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {"error": exc.response.text, "status_code": exc.response.status_code}


async def handle_agent_get(args: dict[str, Any]) -> dict[str, Any]:
    async with _client() as client:
        try:
            agent_id = quote(args["agent_id"], safe="")
            response = await client.get(f"/api/v1/agents/{agent_id}")
            response.raise_for_status()
            return response.json()
        except KeyError:
            return {"error": "missing agent_id", "status_code": 400}
        except httpx.HTTPStatusError as exc:
            return {"error": exc.response.text, "status_code": exc.response.status_code}


async def handle_agent_delete(args: dict[str, Any]) -> dict[str, Any]:
    async with _client() as client:
        try:
            agent_id = quote(args["agent_id"], safe="")
            response = await client.delete(f"/api/v1/agents/{agent_id}")
            response.raise_for_status()
            return response.json()
        except KeyError:
            return {"error": "missing agent_id", "status_code": 400}
        except httpx.HTTPStatusError as exc:
            return {"error": exc.response.text, "status_code": exc.response.status_code}


def register_agent_tools(server: Any) -> None:
    from pheno_mcp.server import Tool

    for tool_def in AGENT_TOOLS:
        handler = globals()[f"handle_{tool_def['name']}"]
        server.register_tool(
            Tool(
                name=tool_def["name"],
                description=tool_def["description"],
                input_schema=tool_def["input_schema"],
                handler=handler,
            )
        )
