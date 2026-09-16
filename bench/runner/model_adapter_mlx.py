"""MLX adapter for the model-adapter layer (Apple Silicon)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

from bench.runner.model_adapter import (
    Completion,
    MissingDependencyError,
    ModelAdapter,
)


def _mlx_load_and_generate_importable() -> tuple[Any, Any]:
    """Resolve ``mlx_lm.load`` and ``mlx_lm.generate``.

    Exposed at module level so tests can monkeypatch this symbol and exercise
    the ``MLXAdapter`` constructor without requiring ``mlx_lm`` to be installed.
    """
    try:
        from mlx_lm import generate as _mlx_generate  # noqa: F401
        from mlx_lm import load as _mlx_load  # noqa: F401
    except Exception as exc:
        raise MissingDependencyError(
            "mlx_lm not installed; `pip install mlx-lm`"
        ) from exc
    return _mlx_load, _mlx_generate


class MLXAdapter(ModelAdapter):
    """Apple-MLX adapter (uses ``mlx_lm.load`` + ``mlx_lm.generate``).

    Only available on Apple Silicon.  Raises ``MissingDependencyError`` on other
    platforms at construction.
    """

    name: ClassVar[str] = "mlx"

    def __init__(
        self,
        *,
        model_id: str,
        repo_or_path: str | None = None,
    ) -> None:
        super().__init__(model_id=model_id)
        load, generate = _mlx_load_and_generate_importable()
        self._load = load
        self._generate = generate
        self._repo = repo_or_path or model_id
        # Lazy: do not load weights at import time; load on first complete().
        self._model = None
        self._tokenizer = None

    def _ensure_loaded(self) -> None:
        if self._model is None or self._tokenizer is None:
            self._model, self._tokenizer = self._load(self._repo)

    def complete(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        system: str | None = None,
        timeout_s: float = 120.0,
        extra: Mapping[str, Any] | None = None,
    ) -> Completion:
        """Run mlx_lm.generate and return the Completion."""
        import time as _t

        self._ensure_loaded()
        prefix = f"{system}\n\n" if system else ""
        t0 = _t.monotonic()
        try:
            text = self._generate(
                self._model,
                self._tokenizer,
                prompt=prefix + prompt,
                max_tokens=int(max_tokens),
                temp=float(temperature),
                verbose=False,
            )
        except Exception:  # noqa: BLE001
            self._record(Completion(text=""), ok=False)
            raise
        dt = (_t.monotonic() - t0) * 1000.0
        # MLX doesn't surface tokens; rough estimate (4 chars/token).
        ct = max(1, len(text) // 4)
        pt = max(1, len(prefix + prompt) // 4)
        comp = Completion(
            text=text,
            prompt_tokens=pt,
            completion_tokens=ct,
            latency_ms=dt,
            extra={"provider": "mlx", "repo": self._repo},
        )
        return self._record(comp, ok=True)
