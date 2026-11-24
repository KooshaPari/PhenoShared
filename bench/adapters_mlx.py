"""bench.adapters_mlx — MLXModelAdapter.

Local MLX model adapter. Loads any HuggingFace-format causal LM via
``mlx_lm.load`` once, then exposes ``generate(messages, **kw)`` for the
suite runner. Greedy sampler by default for deterministic pass@1 measurement.
"""

from __future__ import annotations

import glob
import os
import time
from typing import Any, cast

from bench.adapters import ModelAdapter, ModelResponse


class MLXModelAdapter(ModelAdapter):
    """Local MLX model adapter.

    No cloud API keys, no agent runtime — pure on-device inference.
    Compatible with all Apple Silicon (M1/M2/M3/M4).
    """

    name = "mlx"
    _model: Any = None
    _tokenizer: Any = None
    _sampler: Any = None

    def __init__(
        self,
        model_path: str | None = None,
        max_tokens: int = 256,
        timeout_s: float = 120.0,
        enable_thinking: bool = False,
        use_chat_template: bool = True,
        **opts: Any,
    ) -> None:
        super().__init__(**opts)
        if model_path is None:
            default = (
                "kernels/qwen3.5-0.8b/weights/build/hf-cache/"
                "models--Qwen--Qwen3.5-0.8B/snapshots"
            )
            snaps = glob.glob(default + "/*")
            snaps = [s for s in snaps if os.path.isdir(s)]
            if snaps:
                model_path = snaps[0]
            else:
                model_path = "Qwen/Qwen3.5-0.8B"
        self.model_path = model_path
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self.enable_thinking = enable_thinking
        self.use_chat_template = use_chat_template
        self._model: Any = None
        self._tokenizer: Any = None
        self._sampler: Any = None
        self.n_calls = 0

    def _ensure(self) -> None:
        if self._model is not None:
            return
        from mlx_lm import load  # noqa: F401
        from mlx_lm.sample_utils import make_sampler  # noqa: F401

        self._model, self._tokenizer = load(self.model_path)
        self._sampler = make_sampler(temp=0.0)

    def _format_prompt(self, messages: list[dict[str, str]]) -> str:
        if self.use_chat_template:
            return cast(str, self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=self.enable_thinking,
            ))
        parts = [f"{m['role'].capitalize()}: {m['content']}" for m in messages]
        return "\n".join(parts)

    def generate(self, messages: list[dict[str, str]], **kw: Any) -> ModelResponse:
        """Run MLX greedy generation and return a ModelResponse."""
        t0 = time.perf_counter()
        try:
            self._ensure()
        except Exception as e:
            return ModelResponse(
                latency_ms=(time.perf_counter() - t0) * 1000,
                finish_reason="error",
                error=f"mlx_load: {type(e).__name__}: {e}",
            )

        from mlx_lm import generate as _gen  # noqa: F401

        self.n_calls += 1
        prompt = self._format_prompt(messages)
        max_tok = int(kw.get("max_tokens", self.max_tokens))
        try:
            import signal as _sig

            def _handler(*_: Any) -> None:
                raise TimeoutError("mlx_generate timeout")

            # SIGALRM/alarm are POSIX-only (`signal.SIGALRM` and
            # `signal.alarm` do not exist on Windows builds of CPython's
            # `signal` module). mypy on a non-POSIX host flags both as
            # `attr-defined`. The adapter docstring restricts this class
            # to Apple Silicon (POSIX), so the SIGALRM-based timeout is
            # a no-op on hosts without it; semantics on POSIX are
            # unchanged.
            sigalrm: int | None = getattr(_sig, "SIGALRM", None)
            alarm_fn = getattr(_sig, "alarm", None)
            old_handler: Any = None
            if sigalrm is not None and alarm_fn is not None:
                old_handler = _sig.signal(sigalrm, _handler)
                alarm_fn(max(1, int(self.timeout_s)))
            try:
                response = _gen(
                    self._model,
                    self._tokenizer,
                    prompt,
                    max_tokens=max_tok,
                    verbose=False,
                    sampler=self._sampler,
                )
            finally:
                if sigalrm is not None and alarm_fn is not None:
                    alarm_fn(0)
                    _sig.signal(sigalrm, old_handler)
        except TimeoutError as te:
            return ModelResponse(
                latency_ms=(time.perf_counter() - t0) * 1000,
                finish_reason="timeout",
                error=f"mlx_timeout: {te}",
            )
        except Exception as e:
            return ModelResponse(
                latency_ms=(time.perf_counter() - t0) * 1000,
                finish_reason="error",
                error=f"mlx_generate: {type(e).__name__}: {e}",
            )

        prompt_tok = len(self._tokenizer.encode(prompt))
        completion_tok = len(self._tokenizer.encode(response))
        return ModelResponse(
            text=response,
            raw={"model_path": self.model_path, "n": self.n_calls},
            latency_ms=(time.perf_counter() - t0) * 1000,
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            finish_reason="stop",
        )


__all__ = ["MLXModelAdapter"]
