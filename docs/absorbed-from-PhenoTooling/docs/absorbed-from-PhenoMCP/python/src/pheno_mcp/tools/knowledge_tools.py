"""Knowledge MCP tools backed by Parpoura."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import httpx

_BASE_URL = os.environ.get("PARPOURA_BASE_URL", "http://localhost:8001")
KNOWLEDGE_ID_DESCRIPTION = "Knowledge identifier"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=_BASE_URL, timeout=30.0)


TOOL_KNOWLEDGE_STORE: dict[str, Any] = {
    "name": "knowledge_store",
    "description": "Store a knowledge item in Parpoura.",
    "input_schema": {
        "type": "object",
        "properties": {
            "knowledge_id": {"type": "string", "description": KNOWLEDGE_ID_DESCRIPTION},
            "content": {"type": "string", "description": "Knowledge content"},
            "metadata": {"type": "object", "description": "Optional knowledge metadata"},
        },
        "required": ["knowledge_id", "content"],
    },
}

TOOL_KNOWLEDGE_RETRIEVE: dict[str, Any] = {
    "name": "knowledge_retrieve",
    "description": "Retrieve a knowledge item by identifier.",
    "input_schema": {
        "type": "object",
        "properties": {
            "knowledge_id": {"type": "string", "description": KNOWLEDGE_ID_DESCRIPTION},
        },
        "required": ["knowledge_id"],
    },
}

TOOL_KNOWLEDGE_SEARCH: dict[str, Any] = {
    "name": "knowledge_search",
    "description": "Search knowledge items.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Maximum number of results", "default": 20},
        },
        "required": ["query"],
    },
}

TOOL_KNOWLEDGE_DELETE: dict[str, Any] = {
    "name": "knowledge_delete",
    "description": "Delete a knowledge item by identifier.",
    "input_schema": {
        "type": "object",
        "properties": {
            "knowledge_id": {"type": "string", "description": KNOWLEDGE_ID_DESCRIPTION},
        },
        "required": ["knowledge_id"],
    },
}

KNOWLEDGE_TOOLS = [
    TOOL_KNOWLEDGE_STORE,
    TOOL_KNOWLEDGE_RETRIEVE,
    TOOL_KNOWLEDGE_SEARCH,
    TOOL_KNOWLEDGE_DELETE,
]


async def handle_knowledge_store(args: dict[str, Any]) -> dict[str, Any]:
    async with _client() as client:
        try:
            response = await client.post("/api/v1/knowledge", json=args)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {"error": exc.response.text, "status_code": exc.response.status_code}


async def handle_knowledge_retrieve(args: dict[str, Any]) -> dict[str, Any]:
    async with _client() as client:
        try:
            knowledge_id = quote(args["knowledge_id"], safe="")
            response = await client.get(f"/api/v1/knowledge/{knowledge_id}")
            response.raise_for_status()
            return response.json()
        except KeyError:
            return {"error": "missing knowledge_id", "status_code": 400}
        except httpx.HTTPStatusError as exc:
            return {"error": exc.response.text, "status_code": exc.response.status_code}


async def handle_knowledge_search(args: dict[str, Any]) -> dict[str, Any]:
    params = {key: value for key, value in args.items() if value is not None}

    async with _client() as client:
        try:
            response = await client.get("/api/v1/knowledge/search", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {"error": exc.response.text, "status_code": exc.response.status_code}


async def handle_knowledge_delete(args: dict[str, Any]) -> dict[str, Any]:
    async with _client() as client:
        try:
            knowledge_id = quote(args["knowledge_id"], safe="")
            response = await client.delete(f"/api/v1/knowledge/{knowledge_id}")
            response.raise_for_status()
            return response.json()
        except KeyError:
            return {"error": "missing knowledge_id", "status_code": 400}
        except httpx.HTTPStatusError as exc:
            return {"error": exc.response.text, "status_code": exc.response.status_code}


def register_knowledge_tools(server: Any) -> None:
    from pheno_mcp.server import Tool

    for tool_def in KNOWLEDGE_TOOLS:
        handler = globals()[f"handle_{tool_def['name']}"]
        server.register_tool(
            Tool(
                name=tool_def["name"],
                description=tool_def["description"],
                input_schema=tool_def["input_schema"],
                handler=handler,
            )
        )
