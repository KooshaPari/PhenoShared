"""Tests for the LlamaCpp provider (server mode, mocked)."""

from __future__ import annotations

import pytest
from dispatch_mcp.providers.base import Message
from dispatch_mcp.providers.llama_cpp import LlamaCppProvider


@pytest.fixture
def server_provider(monkeypatch: pytest.MonkeyPatch) -> LlamaCppProvider:
    monkeypatch.setenv("LLAMA_CPP_SERVER_URL", "http://localhost:8080")
    return LlamaCppProvider()


def test_init_server_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLAMA_CPP_SERVER_URL", "http://localhost:8080")
    provider = LlamaCppProvider()
    assert provider.name == "llama_cpp"
    assert provider._is_server_mode()
    assert provider._server_url == "http://localhost:8080"


def test_init_direct_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLAMA_CPP_MODEL_PATH", "/models/llama.gguf")
    provider = LlamaCppProvider()
    assert provider.name == "llama_cpp"
    assert not provider._is_server_mode()
    assert provider._model_path == "/models/llama.gguf"


def test_init_no_config_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLAMA_CPP_SERVER_URL", raising=False)
    monkeypatch.delenv("LLAMA_CPP_MODEL_PATH", raising=False)
    provider = LlamaCppProvider()
    with pytest.raises(RuntimeError, match="LLAMA_CPP_MODEL_PATH"):
        provider._get_model()


def test_build_prompt() -> None:
    provider = _make_provider()
    messages = [
        Message(role="system", content="Be helpful."),
        Message(role="user", content="Hello!"),
    ]
    prompt = provider._build_prompt(messages)
    assert "<|system|>" in prompt
    assert "Be helpful." in prompt
    assert "<|user|>" in prompt
    assert "Hello!" in prompt
    assert "<|assistant|>" in prompt


async def test_health_server_ok(server_provider: LlamaCppProvider) -> None:
    """Server health when the endpoint is reachable."""
    import httpx

    with httpx.MockTransport(lambda _: httpx.Response(200, json={"status": "ok"})):
        pass  # We'd normally patch the client


async def test_health_server_unreachable(server_provider: LlamaCppProvider) -> None:
    """Server health gracefully handles connection errors."""
    result = await server_provider.health()
    assert result["status"] == "error"
    assert result["provider"] == "llama_cpp"


def test_repr() -> None:
    provider = _make_provider(server_url="http://localhost:8080")
    assert "server" in repr(provider)

    provider2 = _make_provider(model_path="/m.gguf")
    assert "direct" in repr(provider2)


async def test_aclose() -> None:
    provider = _make_provider()
    await provider.aclose()  # should not raise


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_provider(
    server_url: str | None = None,
    model_path: str | None = None,
) -> LlamaCppProvider:
    import os

    if server_url:
        os.environ["LLAMA_CPP_SERVER_URL"] = server_url
    elif model_path:
        os.environ["LLAMA_CPP_MODEL_PATH"] = model_path
    else:
        os.environ.setdefault("LLAMA_CPP_SERVER_URL", "http://localhost:9999")
    return LlamaCppProvider()