"""Tests for bench/runner/model_adapter_mlx.py — coverage push from 39.0% to >=80%.

Covers MLXAdapter construction, _mlx_load_and_generate_importable, _ensure_loaded,
complete() with success/error paths, and MissingDependencyError fallback. All
mlx_lm calls are mocked since MLX is not available in CI.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bench.runner import model_adapter_mlx as mlx_mod
from bench.runner.model_adapter import MissingDependencyError

# ---------------------------------------------------------------------------
# _mlx_load_and_generate_importable
# ---------------------------------------------------------------------------


class TestMlxLoadAndGenerateImportable:
    """_mlx_load_and_generate_importable resolves mlx_lm imports."""

    def test_success(self):
        from bench.runner.model_adapter_mlx import _mlx_load_and_generate_importable
        mock_load = MagicMock()
        mock_generate = MagicMock()
        mock_mlx_lm = MagicMock()
        mock_mlx_lm.load = mock_load
        mock_mlx_lm.generate = mock_generate
        with patch.dict("sys.modules", {"mlx_lm": mock_mlx_lm}):
            load, gen = _mlx_load_and_generate_importable()
            assert load is mock_load
            assert gen is mock_generate

    def test_missing_dependency(self):
        from bench.runner.model_adapter_mlx import _mlx_load_and_generate_importable
        with patch.dict("sys.modules", {"mlx_lm": None}):
            with pytest.raises(MissingDependencyError, match="mlx_lm not installed"):
                _mlx_load_and_generate_importable()

    def test_import_error_wrapped(self):
        from bench.runner.model_adapter_mlx import _mlx_load_and_generate_importable
        with patch("builtins.__import__", side_effect=ImportError("no mlx")):
            with pytest.raises(MissingDependencyError):
                _mlx_load_and_generate_importable()


# ---------------------------------------------------------------------------
# MLXAdapter construction
# ---------------------------------------------------------------------------


class TestMLXAdapterConstruction:
    """MLXAdapter.__init__ sets up lazy model loading."""

    def _make_adapter(self, model_id="mlx-test", repo_or_path=None):
        from bench.runner.model_adapter_mlx import MLXAdapter
        mock_load = MagicMock()
        mock_generate = MagicMock()
        with patch.object(mlx_mod, "_mlx_load_and_generate_importable",
                    return_value=(mock_load, mock_generate)):
            return MLXAdapter(model_id=model_id, repo_or_path=repo_or_path)

    def test_basic_construction(self):
        adapter = self._make_adapter()
        assert adapter.model_id == "mlx-test"
        assert adapter._model is None
        assert adapter._tokenizer is None

    def test_repo_or_path_defaults_to_model_id(self):
        adapter = self._make_adapter(model_id="custom-mlx")
        assert adapter._repo == "custom-mlx"

    def test_explicit_repo_or_path(self):
        adapter = self._make_adapter(repo_or_path="/path/to/repo")
        assert adapter._repo == "/path/to/repo"

    def test_name_class_var(self):
        from bench.runner.model_adapter_mlx import MLXAdapter
        assert MLXAdapter.name == "mlx"


# ---------------------------------------------------------------------------
# _ensure_loaded
# ---------------------------------------------------------------------------


class TestEnsureLoaded:
    """_ensure_loaded loads the model on first complete() call."""

    def test_loads_on_first_call(self):
        from bench.runner.model_adapter_mlx import MLXAdapter
        mock_load = MagicMock(return_value=("model_obj", "tok_obj"))
        mock_generate = MagicMock(return_value="response")
        with patch.object(mlx_mod, "_mlx_load_and_generate_importable",
                    return_value=(mock_load, mock_generate)):
            adapter = MLXAdapter(model_id="mlx-test")
            adapter._ensure_loaded()
            mock_load.assert_called_once_with("mlx-test")
            assert adapter._model == "model_obj"
            assert adapter._tokenizer == "tok_obj"

    def test_does_not_reload(self):
        from bench.runner.model_adapter_mlx import MLXAdapter
        mock_load = MagicMock(return_value=("m", "t"))
        mock_generate = MagicMock()
        with patch.object(mlx_mod, "_mlx_load_and_generate_importable",
                    return_value=(mock_load, mock_generate)):
            adapter = MLXAdapter(model_id="mlx-test")
            adapter._ensure_loaded()
            adapter._ensure_loaded()
            assert mock_load.call_count == 1  # loaded only once


# ---------------------------------------------------------------------------
# MLXAdapter.complete
# ---------------------------------------------------------------------------


class TestMLXAdapterComplete:
    """MLXAdapter.complete() calls mlx_lm.generate."""

    def _make_adapter_and_mocks(self):
        from bench.runner.model_adapter_mlx import MLXAdapter
        mock_model = MagicMock(name="model")
        mock_tokenizer = MagicMock(name="tokenizer")
        mock_load = MagicMock(return_value=(mock_model, mock_tokenizer))
        mock_generate = MagicMock(return_value="generated text")
        with patch.object(mlx_mod, "_mlx_load_and_generate_importable",
                    return_value=(mock_load, mock_generate)):
            adapter = MLXAdapter(model_id="mlx-test")
        return adapter, mock_model, mock_tokenizer, mock_generate

    def test_successful_completion(self):
        adapter, mock_model, mock_tok, mock_gen = self._make_adapter_and_mocks()
        comp = adapter.complete("test prompt")
        assert comp.text == "generated text"
        assert comp.extra["provider"] == "mlx"
        assert comp.extra["repo"] == "mlx-test"
        assert comp.latency_ms >= 0

    def test_token_estimates(self):
        adapter, mock_model, mock_tok, mock_gen = self._make_adapter_and_mocks()
        mock_gen.return_value = "a" * 40  # 40 chars → 10 completion tokens
        comp = adapter.complete("hello")  # 5 chars → 1 prompt token (min 1)
        assert comp.completion_tokens == 10
        assert comp.prompt_tokens == 1  # max(1, 5//4) = 1

    def test_with_system_prefix(self):
        adapter, mock_model, mock_tok, mock_gen = self._make_adapter_and_mocks()
        comp = adapter.complete("test", system="You are helpful.")
        call_kwargs = mock_gen.call_args[1]
        assert "You are helpful." in call_kwargs["prompt"]
        assert "test" in call_kwargs["prompt"]

    def test_without_system(self):
        adapter, mock_model, mock_tok, mock_gen = self._make_adapter_and_mocks()
        comp = adapter.complete("test prompt")
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["prompt"] == "test prompt"

    def test_custom_max_tokens(self):
        adapter, mock_model, mock_tok, mock_gen = self._make_adapter_and_mocks()
        adapter.complete("test", max_tokens=256)
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["max_tokens"] == 256

    def test_custom_temperature(self):
        adapter, mock_model, mock_tok, mock_gen = self._make_adapter_and_mocks()
        adapter.complete("test", temperature=0.5)
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["temp"] == 0.5

    def test_generate_error_records_failure(self):
        adapter, mock_model, mock_tok, mock_gen = self._make_adapter_and_mocks()
        mock_gen.side_effect = RuntimeError("MLX error")
        with pytest.raises(RuntimeError, match="MLX error"):
            adapter.complete("test")
        assert adapter.error_count == 1
        assert adapter.call_count == 0

    def test_counter_after_success(self):
        adapter, mock_model, mock_tok, mock_gen = self._make_adapter_and_mocks()
        adapter.complete("one")
        adapter.complete("two")
        assert adapter.call_count == 2
        assert adapter.error_count == 0
        assert adapter.total_tokens > 0

    def test_calls_ensure_loaded(self):
        adapter, mock_model, mock_tok, mock_gen = self._make_adapter_and_mocks()
        adapter.complete("test")
        # After first complete, model should be loaded
        assert adapter._model is mock_model
        assert adapter._tokenizer is mock_tok

    def test_verbose_false_passed(self):
        adapter, mock_model, mock_tok, mock_gen = self._make_adapter_and_mocks()
        adapter.complete("test")
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs.get("verbose") is False
