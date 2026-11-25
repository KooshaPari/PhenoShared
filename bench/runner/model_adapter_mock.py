"""Deterministic mock / stub adapter for tests and smoke runs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

from bench.runner.model_adapter import Completion, ModelAdapter


class MLXStubAdapter(ModelAdapter):
    """Deterministic local stub for tests + smoke runs.

    Echoes a deterministic completion derived from the prompt so repeated
    runs always produce the same ``TaskResult`` text (which lets the cache TTL
    tests have a chance of passing too).
    """

    name: ClassVar[str] = "mlx-stub"

    def __init__(self, *, model_id: str = "mlx-stub") -> None:
        super().__init__(model_id=model_id)

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
        """Return a deterministic echo completion for ``prompt``."""
        import time as _t

        t0 = _t.monotonic()
        # Echo a tiny payload derived from the prompt; deterministic per prompt.
        words = prompt.strip().split()
        key = words[0] if words else "empty"
        text = f"stub-completion[{key}]: {len(words)} tokens -> ok"
        # Crude token estimate so reports have non-zero values.
        pt = max(1, len(words) + (len(system.split()) if system else 0))
        ct = len(text.split())
        comp = Completion(
            text=text,
            prompt_tokens=pt,
            completion_tokens=ct,
            latency_ms=(_t.monotonic() - t0) * 1000.0,
            extra={"provider": "mlx-stub", "deterministic": True},
        )
        return self._record(comp, ok=True)
