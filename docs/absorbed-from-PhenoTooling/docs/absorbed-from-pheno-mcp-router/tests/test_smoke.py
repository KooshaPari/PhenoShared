from __future__ import annotations

import pytest

from pheno_mcp_router import McpRouter


def test_add_tier_and_sanitize_payload() -> None:
    router = McpRouter("test-router", "http://example.test/v1/chat/completions")
    router.add_tier("default", {"model": "test/model"})

    payload = router._sanitize_payload({"messages": [], "api_key": "secret", "temperature": 0})

    assert payload == {"messages": [], "temperature": 0}
    assert "default" in router._tiers


def test_add_tool_requires_known_tier() -> None:
    router = McpRouter("test-router", "http://example.test/v1/chat/completions")

    with pytest.raises(ValueError, match="unknown tier"):
        router.add_tool("missing", lambda: {"ok": True})


def test_response_allowlist() -> None:
    router = McpRouter("test-router", "http://example.test/v1/chat/completions")

    response = router._allowlist_response({"id": "1", "choices": [], "internal": "drop"})

    assert response == {"id": "1", "choices": []}
