"""Tests for the LlamaCpp provider direct mode (mocked llama_cpp)."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from dispatch_mcp.providers.base import Message


@pytest.fixture(autouse=True)
def no_server_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLAMA_CPP_SERVER_URL", raising=False)
    monkeypatch.setenv("LLAMA_CPP_MODEL_PATH", "/fake/path/model.gguf")


def test_init_direct_mode() -> None:
    with patch("dispatch_mcp.providers.llama_cpp.Llama") as mock_llama_class:
        mock_model = MagicMock()
        mock_model.return_value = {"choices": [{"text": "hello", "finish_reason": "stop"}], "usage": {"prompt_tokens": 5, "completion_tokens": 3}}
        mock_llama_class.return_value = mock_model

        from dispatch_mcp.providers.llama_cpp import LlamaCppProvider

        provider = LlamaCppProvider()
        assert provider.name == "llama_cpp"
        assert not provider._is_server_mode()


async def test_direct_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    with patch("dispatch_mcp.providers.llama_cpp.Llama") as mock_llama_class:
        mock_model = MagicMock()
        mock_model.return_value = {
            "choices": [{"text": " test response", "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_llama_class.return_value = mock_model

        from dispatch_mcp.providers.llama_cpp import LlamaCppProvider

        provider = LlamaCppProvider()
        messages = [Message(role="user", content="Hello")]
        result = await provider.complete(messages, max_tokens=100, temperature=0.5)

        assert result.text == " test response"
        assert result.provider == "llama_cpp"
        assert result.input_tokens == 10
        assert result.output_tokens == 5


async def test_direct_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    with patch("dispatch_mcp.providers.llama_cpp.Llama") as mock_llama_class:
        mock_model = MagicMock()
        # Simulate streaming chunks
        mock_model.return_value = [
            {"choices": [{"text": "Hel"}]},
            {"choices": [{"text": "lo"}]},
            {"choices": [{"text": " world"}]},
        ]
        mock_llama_class.return_value = mock_model

        from dispatch_mcp.providers.llama_cpp import LlamaCppProvider

        provider = LlamaCppProvider()
        messages = [Message(role="user", content="Hello")]
        tokens = []
        async for token in provider.stream(messages, max_tokens=100):
            tokens.append(token)

        assert tokens == ["Hel", "lo", " world"]


async def test_direct_health_ok() -> None:
    with patch("dispatch_mcp.providers.llama_cpp.Llama") as mock_llama_class:
        mock_llama_class.return_value = MagicMock()

        from dispatch_mcp.providers.llama_cpp import LlamaCppProvider

        provider = LlamaCppProvider()
        result = await provider.health()

        assert result["status"] == "ok"
        assert result["provider"] == "llama_cpp"
        assert result["mode"] == "direct"
        assert result["model"] == "model.gguf"


async def test_direct_health_load_error() -> None:
    with patch("dispatch_mcp.providers.llama_cpp.Llama", side_effect=RuntimeError("load failed")):
        from dispatch_mcp.providers.llama_cpp import LlamaCppProvider

        provider = LlamaCppProvider()
        result = await provider.health()

        assert result["status"] == "error"
        assert "load failed" in result["error"]


async def test_aclose_clears_model() -> None:
    with patch("dispatch_mcp.providers.llama_cpp.Llama") as mock_llama_class:
        mock_llama_class.return_value = MagicMock()

        from dispatch_mcp.providers.llama_cpp import LlamaCppProvider

        provider = LlamaCppProvider()
        # Trigger model load
        _ = provider._get_model()
        assert provider._model is not None

        await provider.aclose()
        assert provider._model is None