"""Session suspend/resume MCP tools.

Wraps Parpoura session bundle API:
  - POST /api/v1/sessions/{session_id}/suspend  -> bundle_ref
  - POST /api/v1/sessions/resume                -> new session_id
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

TOOL_SESSION_SUSPEND: dict[str, Any] = {
    "name": "session_suspend",
    "description": (
        "Suspend a running session, producing a serialised session bundle "
        "that can be used to resume the session later. "
        "The session process is terminated but its state is preserved."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "ID of the session to suspend",
            },
        },
        "required": ["session_id"],
    },
}


TOOL_SESSION_RESUME: dict[str, Any] = {
    "name": "session_resume",
    "description": (
        "Resume a previously suspended session from its bundle reference. "
        "Returns a new session_id for the restored session."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "bundle_ref": {
                "type": "string",
                "description": "Bundle reference returned by session_suspend",
            },
        },
        "required": ["bundle_ref"],
    },
}

SESSION_TOOLS = [TOOL_SESSION_SUSPEND, TOOL_SESSION_RESUME]


# ---------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------


async def handle_session_suspend(args: dict[str, Any]) -> dict[str, Any]:
    """POST /api/v1/sessions/{session_id}/suspend"""
    session_id: str = args["session_id"]

    async with _client() as client:
        try:
            response = await client.post(f"/api/v1/sessions/{session_id}/suspend")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {
                "error": exc.response.text,
                "status_code": exc.response.status_code,
            }


async def handle_session_resume(args: dict[str, Any]) -> dict[str, Any]:
    """POST /api/v1/sessions/resume with bundle_ref"""
    bundle_ref: str = args["bundle_ref"]

    async with _client() as client:
        try:
            response = await client.post(
                "/api/v1/sessions/resume",
                json={"bundle_ref": bundle_ref},
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


def register_session_tools(server: Any) -> None:
    """Register all session tools with an MCP server.

    Args:
        server: An MCP Server instance with register_tool method.
    """
    from pheno_mcp.server import Tool

    # session_suspend tool
    server.register_tool(
        Tool(
            name=TOOL_SESSION_SUSPEND["name"],
            description=TOOL_SESSION_SUSPEND["description"],
            input_schema=TOOL_SESSION_SUSPEND["input_schema"],
            handler=handle_session_suspend,
        )
    )

    # session_resume tool
    server.register_tool(
        Tool(
            name=TOOL_SESSION_RESUME["name"],
            description=TOOL_SESSION_RESUME["description"],
            input_schema=TOOL_SESSION_RESUME["input_schema"],
            handler=handle_session_resume,
        )
    )
