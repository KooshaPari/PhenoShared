from __future__ import annotations

import asyncio

from unittest.mock import patch

import pytest

from dispatch_mcp.core.types import JobResult
from dispatch_mcp import server


class _FakeRouter:
    """A minimal Router stand-in for server-level dispatch tests.

    Implements the :class:`dispatch_mcp.core.port.Router` protocol's
    :meth:`dispatch_message` entrypoint (the keyword-only async
    coroutine the MCP server actually awaits in
    :func:`dispatch_mcp.server.dispatch_custom`). Returns a typed
    :class:`JobResult` so the server's ``to_dict()`` serialization
    round-trip is exercised end-to-end.
    """

    async def dispatch_message(
        self, *, tier: str, message: str, payload: dict | None = None
    ) -> JobResult:
        return JobResult(ok=True, tier=tier, message=message)


def test_job_result_to_dict_omits_none_values() -> None:
    result = JobResult(ok=True, message="ok")

    assert result.to_dict() == {"ok": True, "message": "ok"}


def test_job_result_to_dict_includes_cost_tracking_fields() -> None:
    """Cost-tracking fields are surfaced to MCP when populated."""
    result = JobResult(
        ok=True,
        message="ok",
        cost_usd=0.0001234567,
        input_tokens=100,
        output_tokens=50,
        model="gpt-4",
        request_id="req-abc",
    )

    payload = result.to_dict()
    assert payload["ok"] is True
    assert payload["message"] == "ok"
    assert payload["cost_usd"] == 0.00012346  # rounded to 8 dp
    assert payload["input_tokens"] == 100
    assert payload["output_tokens"] == 50
    assert payload["model"] == "gpt-4"
    assert payload["request_id"] == "req-abc"


def test_dispatch_custom_rejects_invalid_tier() -> None:
    with pytest.raises(ValueError, match="Invalid tier 'invalid-tier'"):
        asyncio.run(server.dispatch_custom("invalid-tier", "hello"))


def test_dispatch_custom_returns_serialized_result() -> None:
    with patch("dispatch_mcp.server._router", new=_FakeRouter()):
        result = asyncio.run(server.dispatch_custom("worker", "hello"))

    assert result == {"ok": True, "tier": "worker", "message": "hello"}
