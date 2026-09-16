"""Tests for bench/comparison/mlx_direct.py — coverage push from 40.0% to >=80%.

Covers is_available(), MLXDirect class (model_id property, _load, generate, close),
and the various import-error / mock paths. MLX is not available in CI so all
mlx_lm interactions are mocked.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bench.comparison.mlx_direct import MLXDirect, is_available

# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------


class TestIsAvailable:
    """is_available() returns True when mlx_lm is importable."""

    def test_mlx_lm_present(self):
        mock_mlx = MagicMock()
        with patch.dict("sys.modules", {"mlx_lm": mock_mlx}):
            assert is_available() is True

    def test_mlx_lm_missing(self):
        with patch.dict("sys.modules", {"mlx_lm": None}):
            assert is_available() is False


# ---------------------------------------------------------------------------
# Helper to build a fully-mocked mlx_lm in sys.modules
# ---------------------------------------------------------------------------


def _make_mlx_modules() -> dict[str, Any]:
    """Return a sys.modules dict with mlx_lm and mlx_lm.sample_utils mocked."""
    mock_mlx_lm = MagicMock()
    mock_mlx_lm.load.return_value = (MagicMock(name="model"), MagicMock(name="tokenizer"))
    mock_sample_utils = MagicMock(make_sampler=MagicMock(return_value=MagicMock(name="sampler")))
    return {"mlx_lm": mock_mlx_lm, "mlx_lm.sample_utils": mock_sample_utils}


# ---------------------------------------------------------------------------
# MLXDirect — construction
# ---------------------------------------------------------------------------


class TestMLXDirectConstruction:
    """MLXDirect.__init__ loads the model when model_path is given."""

    def test_construction_without_model_path(self):
        """When model_path is None, _load is not called."""
        mods = _make_mlx_modules()
        with patch.dict("sys.modules", mods):
            direct = MLXDirect(model_path=None, max_tokens=256)
            assert direct.model_id is None
            assert direct._max_tokens == 256
            mods["mlx_lm"].load.assert_not_called()

    def test_construction_with_model_path(self):
        """When model_path is given, _load is called."""
        mods = _make_mlx_modules()
        with patch.dict("sys.modules", mods):
            direct = MLXDirect(model_path="/path/to/model")
            assert direct.model_id == "/path/to/model"
            mods["mlx_lm"].load.assert_called_once_with("/path/to/model")

    def test_model_id_property(self):
        mods = _make_mlx_modules()
        with patch.dict("sys.modules", mods):
            direct = MLXDirect(model_path="test-model")
            assert direct.model_id == "test-model"


# ---------------------------------------------------------------------------
# MLXDirect.generate
# ---------------------------------------------------------------------------


class TestMLXDirectGenerate:
    """MLXDirect.generate sends a prompt to the loaded MLX model."""

    def _make_direct(self):
        """Create an MLXDirect with mocked mlx_lm, returning (direct, mock_mlx_lm)."""
        mods = _make_mlx_modules()
        mock_mlx_lm = mods["mlx_lm"]
        with patch.dict("sys.modules", mods):
            direct = MLXDirect(model_path="/path/to/model")
            direct._tokenizer = MagicMock()
            direct._tokenizer.apply_chat_template.return_value = "<formatted prompt>"
        # Return the direct object — it still holds references to the model/tokenizer
        # but generate() needs mlx_lm in sys.modules for its local import.
        return direct, mock_mlx_lm, mods

    def test_generate_calls_mlx(self):
        direct, mock_mlx_lm, mods = self._make_direct()
        mock_mlx_lm.generate.return_value = "generated text"
        with patch.dict("sys.modules", mods):
            result = direct.generate("test prompt")
        assert result == "generated text"
        mock_mlx_lm.generate.assert_called_once()

    def test_generate_uses_max_tokens(self):
        direct, mock_mlx_lm, mods = self._make_direct()
        mock_mlx_lm.generate.return_value = "output"
        with patch.dict("sys.modules", mods):
            direct.generate("test", max_tokens=128)
        call_kwargs = mock_mlx_lm.generate.call_args[1]
        assert call_kwargs["max_tokens"] == 128

    def test_generate_uses_default_max_tokens(self):
        direct, mock_mlx_lm, mods = self._make_direct()
        mock_mlx_lm.generate.return_value = "output"
        with patch.dict("sys.modules", mods):
            direct.generate("test")
        call_kwargs = mock_mlx_lm.generate.call_args[1]
        assert call_kwargs["max_tokens"] == 512

    def test_generate_applies_chat_template(self):
        direct, mock_mlx_lm, mods = self._make_direct()
        mock_mlx_lm.generate.return_value = "ok"
        with patch.dict("sys.modules", mods):
            direct.generate("hello")
        direct._tokenizer.apply_chat_template.assert_called_once()
        call_args = direct._tokenizer.apply_chat_template.call_args
        assert call_args[0][0] == [{"role": "user", "content": "hello"}]

    def test_generate_passes_sampler(self):
        direct, mock_mlx_lm, mods = self._make_direct()
        mock_mlx_lm.generate.return_value = "ok"
        with patch.dict("sys.modules", mods):
            direct.generate("test")
        call_kwargs = mock_mlx_lm.generate.call_args[1]
        assert "sampler" in call_kwargs


# ---------------------------------------------------------------------------
# MLXDirect.close
# ---------------------------------------------------------------------------


class TestMLXDirectClose:
    """MLXDirect.close() is a no-op."""

    def test_close_does_not_raise(self):
        mods = _make_mlx_modules()
        with patch.dict("sys.modules", mods):
            direct = MLXDirect()
            direct.close()  # should not raise
