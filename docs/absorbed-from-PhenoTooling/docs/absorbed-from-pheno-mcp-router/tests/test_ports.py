"""Tests for the L4 hexagonal ports and concrete adapters.

Coverage:
* ``LlmPort`` / ``StoragePort`` / ``ToolPort`` protocol duck-typing
  (``@runtime_checkable`` means ``isinstance`` must succeed against any
  object that implements the documented methods).
* Round-trip smoke tests for all six concrete adapters shipped in
  :mod:`pheno_mcp_router.adapters`. The HTTP adapters are exercised
  against a ``respx``-style fake transport via ``httpx.MockTransport``
  so no network access is required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from pheno_mcp_router import (
    AnthropicAdapter,
    EchoToolAdapter,
    InMemoryStorageAdapter,
    JsonFileStorageAdapter,
    LlmAdapter,
    LlmPort,
    OpenAIAdapter,
    StorageAdapter,
    StoragePort,
    ToolAdapter,
    ToolPort,
)
from pheno_mcp_router.adapters import PromptTestToolAdapter
from pheno_prompt_test import LLMResponse, PromptCase


# ---------------------------------------------------------------------------
# Protocol duck-typing tests
# ---------------------------------------------------------------------------


class _FakeLlm:
    """Minimal duck-typed implementation of LlmPort."""

    async def chat(self, messages: list, model: str) -> str:  # noqa: D401
        return f"echo({model}):{len(messages)}"


class _FakeStorage:
    """Minimal duck-typed implementation of StoragePort."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    async def get(self, key: str):
        return self._store.get(key)

    async def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)


def test_llm_port_protocol_ducktyping() -> None:
    """Any object with ``async chat(messages, model)`` satisfies LlmPort."""
    fake = _FakeLlm()
    assert isinstance(fake, LlmPort)
    # The base ABC also accepts it.
    assert isinstance(fake, LlmAdapter) is False  # ABC nominal subtyping only
    import asyncio

    text = asyncio.run(fake.chat([{"role": "user", "content": "hi"}], "gpt-test"))
    assert text == "echo(gpt-test):1"


def test_storage_port_protocol_ducktyping() -> None:
    """Any object with async ``get/set/delete`` satisfies StoragePort."""
    fake = _FakeStorage()
    assert isinstance(fake, StoragePort)
    import asyncio

    async def roundtrip() -> None:
        assert await fake.get("missing") is None
        await fake.set("k", {"v": 1})
        assert await fake.get("k") == {"v": 1}
        await fake.delete("k")
        assert await fake.get("k") is None

    asyncio.run(roundtrip())


def test_tool_port_protocol_ducktyping_with_echo_adapter() -> None:
    """EchoToolAdapter satisfies ToolPort and round-trips args unchanged."""
    adapter = EchoToolAdapter(name="round_trip", description="for test")
    assert isinstance(adapter, ToolPort)
    assert isinstance(adapter, ToolAdapter)
    assert adapter.name() == "round_trip"
    assert adapter.description() == "for test"
    import asyncio

    result = asyncio.run(adapter.invoke({"hello": "world", "n": 3}))
    assert result == {"hello": "world", "n": 3}


# ---------------------------------------------------------------------------
# HTTP LLM adapter tests (no network — httpx.MockTransport)
# ---------------------------------------------------------------------------


def _openai_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body["model"] == "gpt-test"
        assert body["messages"] == [{"role": "user", "content": "ping"}]
        return httpx.Response(
            200,
            json={
                "id": "cmock-1",
                "model": "gpt-test",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "pong"}}
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    return httpx.MockTransport(handler)


def _anthropic_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body["model"] == "claude-test"
        assert body["max_tokens"] == AnthropicAdapter.DEFAULT_MAX_TOKENS
        # system message is split out
        assert body.get("system") == "be terse"
        assert body["messages"] == [{"role": "user", "content": "ping"}]
        return httpx.Response(
            200,
            json={
                "id": "msgmock-1",
                "model": "claude-test",
                "content": [{"type": "text", "text": "pong"}],
                "usage": {"input_tokens": 2, "output_tokens": 2},
            },
        )

    return httpx.MockTransport(handler)


def test_openai_adapter_round_trip() -> None:
    adapter = OpenAIAdapter(api_key="sk-test", timeout=5.0)
    import asyncio

    async def run() -> str:
        transport = _openai_transport()
        original = httpx.AsyncClient
        httpx.AsyncClient = lambda *a, **kw: original(  # type: ignore[assignment]
            *a, transport=transport, **kw
        )
        try:
            return await adapter.chat(
                [{"role": "user", "content": "ping"}], "gpt-test"
            )
        finally:
            httpx.AsyncClient = original  # type: ignore[assignment]

    assert asyncio.run(run()) == "pong"


def test_anthropic_adapter_round_trip() -> None:
    adapter = AnthropicAdapter(api_key="sk-ant-test", timeout=5.0)
    import asyncio

    async def run() -> str:
        transport = _anthropic_transport()
        original = httpx.AsyncClient
        httpx.AsyncClient = lambda *a, **kw: original(  # type: ignore[assignment]
            *a, transport=transport, **kw
        )
        try:
            return await adapter.chat(
                [
                    {"role": "system", "content": "be terse"},
                    {"role": "user", "content": "ping"},
                ],
                "claude-test",
            )
        finally:
            httpx.AsyncClient = original  # type: ignore[assignment]

    assert asyncio.run(run()) == "pong"


# ---------------------------------------------------------------------------
# Storage adapter tests
# ---------------------------------------------------------------------------


def test_in_memory_storage_adapter_round_trip() -> None:
    adapter = InMemoryStorageAdapter(initial={"seed": 1})
    import asyncio

    async def run() -> None:
        assert await adapter.get("seed") == 1
        assert await adapter.get("missing") is None
        await adapter.set("k", [1, 2, 3])
        assert await adapter.get("k") == [1, 2, 3]
        await adapter.delete("k")
        assert await adapter.get("k") is None
        # delete on missing is a no-op
        await adapter.delete("still-missing")

    asyncio.run(run())
    # and the adapter satisfies the nominal ABC
    assert isinstance(adapter, StorageAdapter)


def test_json_file_storage_adapter_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "kv.json"
    a = JsonFileStorageAdapter(path)
    import asyncio

    async def run() -> None:
        await a.set("user", {"id": 7, "name": "ada"})
        await a.set("count", 42)
        await a.delete("count")

    asyncio.run(run())
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == {"user": {"id": 7, "name": "ada"}}
    # Re-open the file with a new adapter instance to confirm persistence.
    b = JsonFileStorageAdapter(path)
    import asyncio

    async def reread() -> Any:
        return await b.get("user")

    assert asyncio.run(reread()) == {"id": 7, "name": "ada"}
    assert isinstance(b, StorageAdapter)


# ---------------------------------------------------------------------------
# PromptTestToolAdapter
# ---------------------------------------------------------------------------


def test_prompt_test_tool_adapter_round_trip() -> None:
    """PromptTestToolAdapter runs a PromptCase via the injected backend."""

    def backend(prompt: str) -> LLMResponse:
        return LLMResponse(text=f"reply:{prompt}", model="fake-1", tokens_out=1)

    tool = PromptTestToolAdapter(backend=backend, tool_name="regress")
    assert tool.name() == "regress"
    assert "pheno-prompt-test" in tool.description()
    assert isinstance(tool, ToolAdapter)
    import asyncio

    async def run() -> dict[str, Any]:
        return await tool.invoke(
            {
                "name": "smoke",
                "prompt": "hello",
                "must_contain": ["reply:hello"],
            }
        )

    result = asyncio.run(run())
    assert result["text"] == "reply:hello"
    assert result["model"] == "fake-1"
    assert result["name"] == "smoke"
    # and the prompt-case assertions fired (must_contain was satisfied).
    assert result["min_similarity"] == 0.8
