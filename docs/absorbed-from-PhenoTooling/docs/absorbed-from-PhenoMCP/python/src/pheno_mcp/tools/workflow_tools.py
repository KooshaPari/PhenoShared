"""Workflow MCP tools.

Wraps Parpoura workflow API:
  - POST   /workflows/{workflow_id}/execute  -> {execution_id, status}
  - GET    /workflows/{workflow_id}           -> full workflow state
  - POST   /workflows/{workflow_id}/cancel   -> cancelled workflow
  - GET    /workflows                        -> list of workflows
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

TOOL_WORKFLOW_EXECUTE = {
    "name": "workflow_execute",
    "description": (
        "Trigger execution of a workflow. "
        "The workflow must be in PENDING or SUSPENDED status. "
        "Returns an execution identifier and initial status."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "workflow_id": {
                "type": "string",
                "description": "ID of the workflow to execute",
            },
            "workflow_type": {
                "type": "string",
                "description": "Optional workflow execution type",
                "default": "default",
            },
        },
        "required": ["workflow_id"],
    },
}


TOOL_WORKFLOW_STATUS = {
    "name": "workflow_status",
    "description": (
        "Get the current status and details of a workflow. "
        "Statuses: PENDING | RUNNING | SUSPENDED | COMPLETED | FAILED | CANCELLED"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "workflow_id": {
                "type": "string",
                "description": "ID of the workflow to query",
            },
        },
        "required": ["workflow_id"],
    },
}


TOOL_WORKFLOW_CANCEL = {
    "name": "workflow_cancel",
    "description": "Cancel a running or pending workflow.",
    "input_schema": {
        "type": "object",
        "properties": {
            "workflow_id": {
                "type": "string",
                "description": "ID of the workflow to cancel",
            },
        },
        "required": ["workflow_id"],
    },
}


TOOL_WORKFLOW_LIST = {
    "name": "workflow_list",
    "description": "List all workflows with their current status.",
    "input_schema": {
        "type": "object",
        "properties": {},
    },
}


WORKFLOW_TOOLS = [
    TOOL_WORKFLOW_EXECUTE,
    TOOL_WORKFLOW_STATUS,
    TOOL_WORKFLOW_CANCEL,
    TOOL_WORKFLOW_LIST,
]


# ---------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------


async def handle_workflow_execute(args: dict[str, Any]) -> dict[str, Any]:
    """POST /workflows/{workflow_id}/execute"""
    workflow_id: str = args["workflow_id"]
    workflow_type: str = args.get("workflow_type", "default")

    async with _client() as client:
        try:
            response = await client.post(
                f"/workflows/{workflow_id}/execute",
                params={"workflow_type": workflow_type},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {
                "error": exc.response.text,
                "status_code": exc.response.status_code,
            }


async def handle_workflow_status(args: dict[str, Any]) -> dict[str, Any]:
    """GET /workflows/{workflow_id}"""
    workflow_id: str = args["workflow_id"]

    async with _client() as client:
        try:
            response = await client.get(f"/workflows/{workflow_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {
                "error": exc.response.text,
                "status_code": exc.response.status_code,
            }


async def handle_workflow_cancel(args: dict[str, Any]) -> dict[str, Any]:
    """POST /workflows/{workflow_id}/cancel"""
    workflow_id: str = args["workflow_id"]

    async with _client() as client:
        try:
            response = await client.post(f"/workflows/{workflow_id}/cancel")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {
                "error": exc.response.text,
                "status_code": exc.response.status_code,
            }


async def handle_workflow_list(_args: dict[str, Any]) -> dict[str, Any]:
    """GET /workflows"""
    async with _client() as client:
        try:
            response = await client.get("/workflows")
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


def register_workflow_tools(server: Any) -> None:
    """Register all workflow tools with an MCP server.

    Args:
        server: An MCP Server instance with register_tool method.
    """
    from pheno_mcp.server import Tool

    for tool_def in WORKFLOW_TOOLS:
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
