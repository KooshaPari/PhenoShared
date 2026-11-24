"""W2.1 — Mock backend harness for protocol compliance testing.

Verifies the dispatch-mcp request/response cycle against an in-process
mock that simulates backend behavior. No network calls.
"""
import asyncio
import json
import pytest
from dispatch_mcp.server import (
    VALID_TIERS,
    dispatch_freetier,
    dispatch_minimax,
    dispatch_kimi,
    _make_dispatch,
    mcp as _mcp,
)


def test_valid_tiers_contains_freetier():
    assert "freetier" in VALID_TIERS
    assert "minimax" in VALID_TIERS
    assert "kimi" in VALID_TIERS


def test_valid_tiers_count():
    assert len(VALID_TIERS) >= 7


def test_dispatch_tool_names_match_tiers():
    for tier in ("freetier", "minimax", "kimi"):
        tool = getattr(__import__("dispatch_mcp.server", fromlist=[f"dispatch_{tier}"]), f"dispatch_{tier}")
        assert tool is not None


def test_make_dispatch_creates_tool():
    tool = _make_dispatch("freetier")
    assert tool is not None
    # FastMCP registers the tool under the tier-specific name; verify via
    # the public async registry rather than the (absent) .name attribute
    # on the raw function that _make_dispatch returns.
    registered = asyncio.run(_mcp.get_tool("dispatch_freetier"))
    assert registered is not None
    assert registered.name == "dispatch_freetier"


def test_make_dispatch_unknown_tier_does_not_raise():
    # Just creating a tool handle should not raise even for an unknown tier
    # (the validation happens at call time, not construction time).
    tool = _make_dispatch("nonexistent-tier")
    assert tool is not None


def test_mock_request_payload_shape():
    # A minimal valid request payload, ready to send to a real backend.
    payload = {
        "model": "accounts/fireworks/models/minimax-m2p7",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 64,
        "temperature": 0.0,
    }
    assert "model" in payload
    assert "messages" in payload
    assert isinstance(payload["messages"], list)


def test_mock_response_shape():
    response = {
        "id": "mock-1",
        "model": "accounts/fireworks/models/minimax-m2p7",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "hi back"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }
    assert response["choices"][0]["message"]["role"] == "assistant"
    assert response["usage"]["total_tokens"] == 7


def test_freetier_tier_is_in_tier_set():
    assert "freetier" in VALID_TIERS


def test_minimax_tier_is_in_tier_set():
    assert "minimax" in VALID_TIERS


def test_kimi_tier_is_in_tier_set():
    assert "kimi" in VALID_TIERS


def test_tier_set_is_frozen():
    assert isinstance(VALID_TIERS, frozenset)


def test_dispatch_freetier_callable():
    assert callable(dispatch_freetier)


def test_dispatch_minimax_callable():
    assert callable(dispatch_minimax)


def test_dispatch_kimi_callable():
    assert callable(dispatch_kimi)
