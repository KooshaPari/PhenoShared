"""Tests for bench.runner.model_adapter_anthropic — target 80%+ coverage."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

from bench.runner.model_adapter import Completion, MissingDependencyError
from bench.runner.model_adapter_anthropic import (
    AnthropicAdapter,
    _resolve_anthropic_class,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MODULE = "bench.runner.model_adapter_anthropic"
# Direct module reference for monkeypatch (avoids string-path resolution issues)
import bench.runner.model_adapter_anthropic as _mod


def _make_mock_response(
    text: str = "hello world",
    input_tokens: int = 10,
    output_tokens: int = 20,
    stop_reason: str = "end_turn",
    msg_id: str = "msg_123",
    model: str = "claude-sonnet-5",
) -> MagicMock:
    """Build a mock Anthropic messages.create response."""
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    resp.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    resp.stop_reason = stop_reason
    resp.id = msg_id
    resp.model = model
    return resp


def _make_adapter(
    monkeypatch: pytest.MonkeyPatch,
    *,
    api_key: str | None = "test-key",
    base_url: str | None = None,
    mock_cls: MagicMock | None = None,
) -> tuple[AnthropicAdapter, MagicMock]:
    """Create an AnthropicAdapter with mocked internals.

    Returns (adapter, mock_client) so callers can configure
    mock_client.messages.create behaviour.
    """
    if mock_cls is None:
        mock_cls = MagicMock()
    mock_client = MagicMock()
    mock_cls.return_value = mock_client

    monkeypatch.setattr(_mod, "_resolve_anthropic_class", lambda: mock_cls)
    # Clear cached module-level Anthropic so _resolve doesn't pick it up
    monkeypatch.setattr(_mod, "Anthropic", None)

    adapter = AnthropicAdapter(model_id="claude-sonnet-5", api_key=api_key, base_url=base_url)
    return adapter, mock_client


# ===================================================================
# _resolve_anthropic_class
# ===================================================================


class TestResolveAnthropicClass:
    """Tests for the _resolve_anthropic_class() helper."""

    def test_from_globals(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When globals()['Anthropic'] is set, it is returned."""
        sentinel = type("FakeAnthropic", (), {})
        monkeypatch.setattr(_mod, "Anthropic", sentinel)
        assert _resolve_anthropic_class() is sentinel

    def test_from_import_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When globals Anthropic is None, falls back to import."""
        monkeypatch.setattr(_mod, "Anthropic", None)
        fake_mod = MagicMock()
        fake_cls = type("FallbackCls", (), {})
        fake_mod.Anthropic = fake_cls
        # Inject fake anthropic module into sys.modules instead of patching builtins.__import__
        monkeypatch.setitem(sys.modules, "anthropic", fake_mod)
        result = _resolve_anthropic_class()
        assert result is fake_cls

    def test_none_when_both_fail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When globals is None and import fails, returns None."""
        monkeypatch.setattr(_mod, "Anthropic", None)
        # Remove anthropic from sys.modules so import raises ImportError
        monkeypatch.delitem(sys.modules, "anthropic", raising=False)
        # Also ensure a fresh import would fail by making it unavailable
        import importlib as _il

        original_import = _il.__import__

        def _failing_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "anthropic":
                raise ImportError("no anthropic")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _failing_import)
        assert _resolve_anthropic_class() is None


# ===================================================================
# AnthropicAdapter.__init__
# ===================================================================


class TestAnthropicAdapterInit:
    """Tests for AnthropicAdapter construction."""

    def test_init_with_explicit_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """api_key param is forwarded to the client constructor."""
        mock_cls = MagicMock()
        monkeypatch.setattr(_mod, "_resolve_anthropic_class", lambda: mock_cls)
        monkeypatch.setattr(_mod, "Anthropic", None)
        adapter = AnthropicAdapter(model_id="claude-sonnet-5", api_key="sk-explicit")
        mock_cls.assert_called_once_with(api_key="sk-explicit")
        assert adapter._model == "claude-sonnet-5"

    def test_init_with_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no api_key param, falls back to ANTHROPIC_API_KEY env var."""
        mock_cls = MagicMock()
        monkeypatch.setattr(_mod, "_resolve_anthropic_class", lambda: mock_cls)
        monkeypatch.setattr(_mod, "Anthropic", None)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-key")
        AnthropicAdapter(model_id="claude-haiku")
        mock_cls.assert_called_once_with(api_key="sk-env-key")

    def test_init_with_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """base_url param is forwarded to the client constructor."""
        mock_cls = MagicMock()
        monkeypatch.setattr(_mod, "_resolve_anthropic_class", lambda: mock_cls)
        monkeypatch.setattr(_mod, "Anthropic", None)
        AnthropicAdapter(
            model_id="claude-opus",
            api_key="sk-x",
            base_url="https://custom.anthropic.com",
        )
        mock_cls.assert_called_once_with(
            api_key="sk-x", base_url="https://custom.anthropic.com"
        )

    def test_init_no_key_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no api_key param and no env var, client is created without api_key."""
        mock_cls = MagicMock()
        monkeypatch.setattr(_mod, "_resolve_anthropic_class", lambda: mock_cls)
        monkeypatch.setattr(_mod, "Anthropic", None)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        AnthropicAdapter(model_id="claude-sonnet-5")
        mock_cls.assert_called_once_with()

    def test_init_missing_sdk(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raises MissingDependencyError when SDK is not available."""
        monkeypatch.setattr(_mod, "_resolve_anthropic_class", lambda: None)
        monkeypatch.setattr(_mod, "Anthropic", None)
        with pytest.raises(MissingDependencyError, match="anthropic SDK not installed"):
            AnthropicAdapter(model_id="claude-sonnet-5")


# ===================================================================
# AnthropicAdapter class attributes
# ===================================================================


class TestAnthropicAdapterAttributes:
    """Tests for static attributes and properties."""

    def test_name(self) -> None:
        """name class variable is 'anthropic'."""
        assert AnthropicAdapter.name == "anthropic"


# ===================================================================
# AnthropicAdapter.complete()
# ===================================================================


class TestAnthropicAdapterComplete:
    """Tests for the complete() method."""

    def test_basic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Basic completion returns correct Completion fields."""
        resp = _make_mock_response(text="hello world")
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        comp = adapter.complete("What is 2+2?")

        assert isinstance(comp, Completion)
        assert comp.text == "hello world"
        assert comp.prompt_tokens == 10
        assert comp.completion_tokens == 20

    def test_with_system(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """system param is passed to messages.create."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        adapter.complete("hi", system="You are a helpful assistant.")

        _, kwargs = client.messages.create.call_args
        assert kwargs["system"] == "You are a helpful assistant."

    def test_with_extra(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """extra dict is merged into messages.create kwargs."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        adapter.complete("hi", extra={"top_k": 5, "stream": False})

        _, kwargs = client.messages.create.call_args
        assert kwargs["top_k"] == 5
        assert kwargs["stream"] is False

    def test_with_empty_content(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Response with no content blocks yields empty text."""
        resp = MagicMock()
        resp.content = []
        resp.usage = MagicMock(input_tokens=5, output_tokens=5)
        resp.stop_reason = "end_turn"
        resp.id = "msg_empty"
        resp.model = "claude-haiku"

        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        comp = adapter.complete("empty")
        assert comp.text == ""

    def test_with_no_content_attribute(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Response with content=None yields empty text."""
        resp = MagicMock()
        resp.content = None
        resp.usage = MagicMock(input_tokens=5, output_tokens=5)
        resp.stop_reason = "end_turn"
        resp.id = "msg_none"
        resp.model = "claude-haiku"

        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        comp = adapter.complete("test")
        assert comp.text == ""

    def test_with_multiple_blocks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Multiple text content blocks are joined by newline."""
        block1 = MagicMock(text="first part")
        block2 = MagicMock(text="second part")
        block3 = MagicMock(text="third part")
        resp = MagicMock()
        resp.content = [block1, block2, block3]
        resp.usage = MagicMock(input_tokens=10, output_tokens=30)
        resp.stop_reason = "end_turn"
        resp.id = "msg_multi"
        resp.model = "claude-sonnet-5"

        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        comp = adapter.complete("multi")
        assert comp.text == "first part\nsecond part\nthird part"

    def test_with_block_without_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Blocks without a text attribute (e.g. tool_use) are skipped."""
        block_no_text = MagicMock(spec=[])  # no 'text' attr
        block_with_text = MagicMock(text="visible text")
        resp = MagicMock()
        resp.content = [block_no_text, block_with_text]
        resp.usage = MagicMock(input_tokens=5, output_tokens=10)
        resp.stop_reason = "end_turn"
        resp.id = "msg_block"
        resp.model = "claude-sonnet-5"

        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        comp = adapter.complete("block test")
        assert comp.text == "visible text"

    def test_records_tokens(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt_tokens and completion_tokens are correctly extracted."""
        resp = _make_mock_response(input_tokens=42, output_tokens=84)
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        comp = adapter.complete("count tokens")
        assert comp.prompt_tokens == 42
        assert comp.completion_tokens == 84

    def test_records_latency(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """latency_ms is positive after a complete() call."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        comp = adapter.complete("timed call")
        assert comp.latency_ms >= 0.0

    def test_records_extra(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """extra dict contains stop_reason, id, and model."""
        resp = _make_mock_response(
            stop_reason="end_turn",
            msg_id="msg_extra",
            model="claude-opus-4",
        )
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        comp = adapter.complete("extra fields")
        assert comp.extra["stop_reason"] == "end_turn"
        assert comp.extra["id"] == "msg_extra"
        assert comp.extra["model"] == "claude-opus-4"

    def test_extra_model_fallback_to_self_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When resp.model is missing, extra.model falls back to self._model."""
        resp = MagicMock()
        resp.content = [MagicMock(text="x")]
        resp.usage = MagicMock(input_tokens=1, output_tokens=1)
        resp.stop_reason = None
        resp.id = None
        # Remove model attribute so getattr falls back
        del resp.model

        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        comp = adapter.complete("fallback model")
        assert comp.extra["model"] == "claude-sonnet-5"

    def test_api_error_records_and_reraises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """On API error, _error_count increments and exception re-raises."""
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.side_effect = RuntimeError("API down")

        with pytest.raises(RuntimeError, match="API down"):
            adapter.complete("fail")

        assert adapter.error_count == 1
        assert adapter.call_count == 0

    def test_max_tokens_coerced_to_int(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """max_tokens float is coerced to int in kwargs."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        adapter.complete("coerce", max_tokens=512.0)

        _, kwargs = client.messages.create.call_args
        assert isinstance(kwargs["max_tokens"], int)
        assert kwargs["max_tokens"] == 512

    def test_max_tokens_floor_at_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """max_tokens of 0 is coerced to 1 (max(1, int(...)))."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        adapter.complete("floor", max_tokens=0)

        _, kwargs = client.messages.create.call_args
        assert kwargs["max_tokens"] == 1

    def test_temperature_is_float(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """temperature is passed as float."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        adapter.complete("temp", temperature=0.7)

        _, kwargs = client.messages.create.call_args
        assert isinstance(kwargs["temperature"], float)
        assert kwargs["temperature"] == 0.7

    def test_messages_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """messages kwarg has correct user role format."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        adapter.complete("hello prompt")

        _, kwargs = client.messages.create.call_args
        assert kwargs["messages"] == [{"role": "user", "content": "hello prompt"}]

    def test_model_in_kwargs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """model kwarg matches self._model."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        adapter.complete("model check")

        _, kwargs = client.messages.create.call_args
        assert kwargs["model"] == "claude-sonnet-5"

    def test_timeout_forwarded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """timeout_s is forwarded as the timeout positional kwarg."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        adapter.complete("timeout", timeout_s=30.0)

        call_kwargs = client.messages.create.call_args[1]
        assert call_kwargs["timeout"] == 30.0

    def test_no_system_when_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """system is not included in kwargs when None."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        adapter.complete("no system", system=None)

        _, kwargs = client.messages.create.call_args
        assert "system" not in kwargs

    def test_no_extra_when_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """extra is not merged into kwargs when None."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        adapter.complete("no extra", extra=None)

        _, kwargs = client.messages.create.call_args
        # Should only have model, max_tokens, temperature, messages, timeout
        expected_keys = {"model", "max_tokens", "temperature", "messages", "timeout"}
        assert set(kwargs.keys()) == expected_keys


# ===================================================================
# Counter tracking
# ===================================================================


class TestCounters:
    """Tests for call_count, error_count, and total_tokens tracking."""

    def test_call_count_increments_on_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Successful complete() increments _call_count."""
        resp = _make_mock_response(input_tokens=10, output_tokens=20)
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        assert adapter.call_count == 0
        adapter.complete("first")
        assert adapter.call_count == 1
        adapter.complete("second")
        assert adapter.call_count == 2

    def test_error_count_increments_on_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Failed complete() increments _error_count."""
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.side_effect = ValueError("boom")

        assert adapter.error_count == 0
        with pytest.raises(ValueError):
            adapter.complete("fail1")
        assert adapter.error_count == 1
        with pytest.raises(ValueError):
            adapter.complete("fail2")
        assert adapter.error_count == 2

    def test_call_count_not_incremented_on_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """call_count stays at 0 when complete() raises."""
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.side_effect = RuntimeError("err")

        with pytest.raises(RuntimeError):
            adapter.complete("err")
        assert adapter.call_count == 0

    def test_total_tokens_tracked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """total_tokens sums prompt + completion tokens across calls."""
        resp = _make_mock_response(input_tokens=10, output_tokens=20)
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        assert adapter.total_tokens == 0
        adapter.complete("t1")
        assert adapter.total_tokens == 30
        adapter.complete("t2")
        assert adapter.total_tokens == 60


# ===================================================================
# InferencePort bridge (generate)
# ===================================================================


class TestInferencePortBridge:
    """Tests for the generate() bridge method inherited from ModelAdapter."""

    def test_generate_basic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """generate() delegates to complete() with last message content as prompt."""
        resp = _make_mock_response(text="bridge result")
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        messages = [
            {"role": "user", "content": "What is Python?"},
        ]
        comp = adapter.generate(messages)

        assert isinstance(comp, Completion)
        assert comp.text == "bridge result"

    def test_generate_extracts_system(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """generate() extracts system message and passes it to complete()."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        messages = [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Hi"},
        ]
        adapter.generate(messages)

        _, kwargs = client.messages.create.call_args
        assert kwargs["system"] == "Be concise."

    def test_generate_with_kwargs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """generate() forwards temperature, max_tokens, timeout_s from kwargs."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        messages = [{"role": "user", "content": "x"}]
        adapter.generate(
            messages, temperature=0.5, max_tokens=256, timeout_s=60.0
        )

        _, kwargs = client.messages.create.call_args
        assert kwargs["temperature"] == 0.5
        assert kwargs["max_tokens"] == 256
        assert kwargs["timeout"] == 60.0

    def test_generate_empty_messages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """generate() with empty messages list uses empty string prompt."""
        resp = _make_mock_response(text="empty")
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        comp = adapter.generate([])

        _, kwargs = client.messages.create.call_args
        assert kwargs["messages"] == [{"role": "user", "content": ""}]
        assert comp.text == "empty"

    def test_generate_with_extra(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """generate() passes extra dict through."""
        resp = _make_mock_response()
        adapter, client = _make_adapter(monkeypatch)
        client.messages.create.return_value = resp

        messages = [{"role": "user", "content": "hi"}]
        adapter.generate(messages, extra={"stop_sequences": ["END"]})

        _, kwargs = client.messages.create.call_args
        assert kwargs["stop_sequences"] == ["END"]
