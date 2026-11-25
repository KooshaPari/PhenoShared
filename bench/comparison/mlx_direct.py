"""Minimal stub for mlx_direct module.

Provides MLXDirect class and is_available() for direct MLX model execution
without the bench.adapters wrapper. Used by stock_vs_ours benchmark.
"""

from __future__ import annotations

from typing import Any, cast


def is_available() -> bool:
    """Check if mlx_lm is installed and a model is loadable."""
    try:
        import mlx_lm  # noqa: F401

        return True
    except ImportError:
        return False


class MLXDirect:
    """Direct MLX model wrapper — loads Qwen3.5-0.8B and provides generate()."""

    def __init__(self, model_path: str | None = None, max_tokens: int = 512):
        from mlx_lm.sample_utils import make_sampler

        self._model_path = model_path
        self._max_tokens = max_tokens
        self._sampler = make_sampler(temp=0.0)

        if model_path:
            self._load(model_path)

    @property
    def model_id(self) -> str | None:
        """Public alias for `_model_path` so callers can match by id."""
        return self._model_path

    def _load(self, path: str) -> None:
        import time as _t

        from mlx_lm import load

        t0 = _t.time()
        self._model, self._tokenizer = load(path)
        print(f"[mlx_direct] loaded model in {_t.time() - t0:.1f}s", flush=True)

    def generate(
        self, prompt: str, *, max_tokens: int | None = None, **kwargs: Any
    ) -> str:
        """Send a prompt to the loaded MLX model and return the completion text."""
        from mlx_lm import generate as _gen

        mt = max_tokens or self._max_tokens
        messages = [{"role": "user", "content": prompt}]
        formatted = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        return cast(str, _gen(
            self._model,
            self._tokenizer,
            formatted,
            max_tokens=mt,
            sampler=self._sampler,
            verbose=False,
        ))

    def close(self) -> None:
        """Tear down any cached MLX state (no-op for the direct adapter)."""
        pass
