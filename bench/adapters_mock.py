"""bench.adapters_mock — MockModel.

Deterministic stub for tests + smoke runs.
"""

from __future__ import annotations

import hashlib
import random
import time
from typing import Any

from bench.adapters import ModelAdapter, ModelResponse


class MockModel(ModelAdapter):
    """Deterministic mock.

    Default behaviour:
      - Echo the last user message
      - Provide a stable, hashable response so test assertions work
      - Track ``n_calls`` for sanity checks
      - Configurable sleep to simulate latency
      - Configurable failure rate for negative testing
    """

    name = "mock"

    def __init__(
        self,
        echo: bool = True,
        sleep_ms: float = 0.0,
        fail_rate: float = 0.0,
        seed: int = 0,
        response_prefix: str = "",
        **opts: Any,
    ) -> None:
        super().__init__(**opts)
        self.echo = echo
        self.sleep_ms = sleep_ms
        self.fail_rate = fail_rate
        self.seed = seed
        self.response_prefix = response_prefix
        self.n_calls = 0
        self._rng = random.Random(seed)  # nosec B311

    def generate(self, messages: list[dict[str, str]], **kw: Any) -> ModelResponse:
        """Deterministic echo mock — returns a hash-stable response."""
        t0 = time.perf_counter()
        self.n_calls += 1
        if self.sleep_ms:
            time.sleep(self.sleep_ms / 1000.0)
        if self.fail_rate > 0 and self._rng.random() < self.fail_rate:
            return ModelResponse(
                latency_ms=(time.perf_counter() - t0) * 1000,
                finish_reason="error",
                error="mock: simulated failure",
            )
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        h = hashlib.sha256(last_user.encode("utf-8")).hexdigest()[:8]
        text = self.response_prefix + (last_user if self.echo else f"mock:{h}")
        prompt_tokens = sum(len(m.get("content", "")) for m in messages) // 4
        completion_tokens = max(1, len(text) // 4)
        return ModelResponse(
            text=text,
            raw={"mock": True, "seed": self.seed, "n": self.n_calls},
            latency_ms=(time.perf_counter() - t0) * 1000,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason="stop",
        )


__all__ = ["MockModel"]
