"""Tests for bench/runner/model_adapter_openai.py — coverage push from 41.0% to >=80%.

Covers OpenAIAdapter construction, _resolve_openai_class, complete() with
success/error paths, token counting, system message handling, extra kwargs,
MissingDependencyError, and the monkeypatching fallback logic.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bench.runner import model_adapter_openai as openai_mod
from bench.runner.model_adapter import Completion, MissingDependencyError

# ---------------------------------------------------------------------------
# _resolve_openai_class
# ---------------------------------------------------------------------------


class TestResolveOpenAIClass:
    """_resolve_openai_class returns the OpenAI class from globals or fresh import."""

    def test_returns_from_globals(self):
        import bench.runner.model_adapter_openai as mod
        mock_mod = MagicMock()
        mock_cls = MagicMock()
        mock_mod.OpenAI = mock_cls
        old_openai = mod.openai
        try:
            mod.openai = mock_mod
            result = mod._resolve_openai_class()
            assert result is mock_cls
        finally:
            mod.openai = old_openai

    def test_returns_fresh_import(self):
        import bench.runner.model_adapter_openai as mod
        old_openai = mod.openai
        try:
            mod.openai = None
            mock_openai_module = MagicMock()
            with patch.dict("sys.modules", {"openai": mock_openai_module}):
                result = mod._resolve_openai_class()
                assert result is mock_openai_module.OpenAI
        finally:
            mod.openai = old_openai

    def test_import_error_returns_none(self):
        import bench.runner.model_adapter_openai as mod
        old_openai = mod.openai
        try:
            mod.openai = None
            with patch.dict("sys.modules", {"openai": None}):
                result = mod._resolve_openai_class()
                assert result is None
        finally:
            mod.openai = old_openai

    def test_globals_openai_none_fresh_import_fail(self):
        """When globals().get('openai') is None and import fails, returns None."""
        import bench.runner.model_adapter_openai as mod
        old_openai = mod.openai
        try:
            mod.openai = None
            # Make sure fresh import also fails
            with patch.dict("sys.modules", {"openai": None}):
                with patch("builtins.__import__", side_effect=ImportError("no openai")):
                    result = mod._resolve_openai_class()
                    assert result is None
        finally:
            mod.openai = old_openai


# ---------------------------------------------------------------------------
# OpenAIAdapter construction
# ---------------------------------------------------------------------------


class TestOpenAIAdapterConstruction:
    """OpenAIAdapter.__init__ creates an OpenAI client."""

    def _make_adapter(self, **kwargs):
        """Create an OpenAIAdapter with a mocked client."""
        from bench.runner.model_adapter_openai import OpenAIAdapter
        mock_openai_cls = MagicMock()
        with patch.object(openai_mod, "_resolve_openai_class", return_value=mock_openai_cls):
            return OpenAIAdapter(model_id="gpt-4", **kwargs), mock_openai_cls

    def test_basic_construction(self):
        adapter, mock_cls = self._make_adapter()
        assert adapter._model == "gpt-4"
        mock_cls.assert_called_once()

    def test_with_api_key(self):
        adapter, mock_cls = self._make_adapter(api_key="sk-test")
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["api_key"] == "sk-test"

    def test_with_base_url(self):
        adapter, mock_cls = self._make_adapter(base_url="http://localhost:8000/v1")
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["base_url"] == "http://localhost:8000/v1"

    def test_env_key_fallback(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")
        adapter, mock_cls = self._make_adapter()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["api_key"] == "sk-env-key"

    def test_no_key_default(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        adapter, mock_cls = self._make_adapter()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["api_key"] == "sk-bench-runner-no-key"

    def test_env_base_url_fallback(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OPENAI_BASE_URL", "http://env-host:1234/v1")
        adapter, mock_cls = self._make_adapter()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["base_url"] == "http://env-host:1234/v1"

    def test_missing_openai_raises(self):
        from bench.runner.model_adapter_openai import OpenAIAdapter
        with patch.object(openai_mod, "_resolve_openai_class", return_value=None):
            with pytest.raises(MissingDependencyError, match="openai SDK not installed"):
                OpenAIAdapter(model_id="gpt-4")


# ---------------------------------------------------------------------------
# OpenAIAdapter.complete
# ---------------------------------------------------------------------------


class TestOpenAIAdapterComplete:
    """OpenAIAdapter.complete() calls the Chat Completions API."""

    def _make_adapter_with_mock_client(self):
        from bench.runner.model_adapter_openai import OpenAIAdapter
        mock_client = MagicMock()
        mock_openai_cls = MagicMock(return_value=mock_client)
        with patch.object(openai_mod, "_resolve_openai_class", return_value=mock_openai_cls):
            adapter = OpenAIAdapter(model_id="gpt-4")
        return adapter, mock_client

    def _mock_response(self, text="hello", prompt_tokens=10, completion_tokens=5):
        resp = MagicMock()
        resp.id = "chatcmpl-123"
        resp.model = "gpt-4"
        msg = MagicMock()
        msg.content = text
        choice = MagicMock()
        choice.message = msg
        resp.choices = [choice]
        usage = MagicMock()
        usage.prompt_tokens = prompt_tokens
        usage.completion_tokens = completion_tokens
        resp.usage = usage
        return resp

    def test_successful_completion(self):
        adapter, mock_client = self._make_adapter_with_mock_client()
        mock_client.chat.completions.create.return_value = self._mock_response("hi there")
        comp = adapter.complete("say hi")
        assert comp.text == "hi there"
        assert comp.prompt_tokens == 10
        assert comp.completion_tokens == 5
        assert comp.latency_ms >= 0

    def test_with_system_message(self):
        adapter, mock_client = self._make_adapter_with_mock_client()
        mock_client.chat.completions.create.return_value = self._mock_response("ok")
        adapter.complete("test", system="You are a helper.")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helper."
        assert messages[1]["role"] == "user"

    def test_without_system_message(self):
        adapter, mock_client = self._make_adapter_with_mock_client()
        mock_client.chat.completions.create.return_value = self._mock_response("ok")
        adapter.complete("test")
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    def test_max_tokens_zero_omitted(self):
        adapter, mock_client = self._make_adapter_with_mock_client()
        mock_client.chat.completions.create.return_value = self._mock_response()
        adapter.complete("test", max_tokens=0)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "max_tokens" not in call_kwargs

    def test_extra_kwargs_merged(self):
        adapter, mock_client = self._make_adapter_with_mock_client()
        mock_client.chat.completions.create.return_value = self._mock_response()
        adapter.complete("test", extra={"stop": ["\n"]})
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["stop"] == ["\n"]

    def test_api_error_records_failure(self):
        adapter, mock_client = self._make_adapter_with_mock_client()
        mock_client.chat.completions.create.side_effect = RuntimeError("API error")
        with pytest.raises(RuntimeError, match="API error"):
            adapter.complete("test")
        assert adapter.error_count == 1
        assert adapter.call_count == 0

    def test_no_choices_returns_empty(self):
        adapter, mock_client = self._make_adapter_with_mock_client()
        resp = MagicMock()
        resp.choices = []
        resp.usage = None
        resp.id = "x"
        resp.model = "gpt-4"
        mock_client.chat.completions.create.return_value = resp
        comp = adapter.complete("test")
        assert comp.text == ""
        assert comp.prompt_tokens == 0
        assert comp.completion_tokens == 0

    def test_choices_without_message(self):
        adapter, mock_client = self._make_adapter_with_mock_client()
        resp = MagicMock()
        choice = MagicMock()
        choice.message = None
        resp.choices = [choice]
        resp.usage = None
        resp.id = "x"
        resp.model = "gpt-4"
        mock_client.chat.completions.create.return_value = resp
        comp = adapter.complete("test")
        assert comp.text == ""

    def test_none_message_content(self):
        adapter, mock_client = self._make_adapter_with_mock_client()
        resp = MagicMock()
        choice = MagicMock()
        choice.message.content = None
        resp.choices = [choice]
        resp.usage = None
        resp.id = "x"
        resp.model = "gpt-4"
        mock_client.chat.completions.create.return_value = resp
        comp = adapter.complete("test")
        assert comp.text == ""

    def test_counter_increments(self):
        adapter, mock_client = self._make_adapter_with_mock_client()
        mock_client.chat.completions.create.return_value = self._mock_response()
        adapter.complete("one")
        adapter.complete("two")
        assert adapter.call_count == 2
        assert adapter.total_tokens == 30  # (10+5) * 2

    def test_call_count_in_model_id(self):
        adapter, _ = self._make_adapter_with_mock_client()
        assert adapter.model_id == "gpt-4"


# ---------------------------------------------------------------------------
# Completion dataclass
# ---------------------------------------------------------------------------


class TestCompletion:
    """Completion to_dict() works correctly."""

    def test_to_dict(self):
        comp = Completion(text="hi", prompt_tokens=10, completion_tokens=5, latency_ms=100.0)
        d = comp.to_dict()
        assert d["text"] == "hi"
        assert d["prompt_tokens"] == 10
        assert d["extra"] == {}
