"""bench.mlx_stub — deterministic MLX stub adapter for tests + dry-runs.

DAG task 9: provide a typed, protocol-driven stub adapter that:

  1. Registers as the ``mlx-stub`` model name in the adapter registry.
  2. Echoes the last user message with a stable hash, like MockModel.
  3. Carries a ``verify_task`` callback so the executor marks any
     non-empty completion as PASS even when ``td.expected is None`` —
     this unblocks the LLM-host test fixture restoration (the
     ``test_executor_runs_end_to_end_with_stub`` test was failing
     because the strict executor._verify required a non-None expected).
  4. Stays hermetic — no network, no MLX runtime, no fork, no subprocess.

Importing this module side-effect-registers the adapter with
``bench.adapters.register_adapter`` so the rest of the suite can
do ``make_adapter("mlx-stub")`` without any wiring.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from bench.adapters import (
    ModelAdapter,
    ModelResponse,
    register_adapter,
)

# ---------------------------------------------------------------------------
# Stub verify_task — accepts any non-empty completion as PASS
# ---------------------------------------------------------------------------


def stub_verify_task(td: Any, text: str, adapter: ModelAdapter) -> bool:
    """Default verification for stub/smoke runs.

    Returns True for any non-empty completion that is not the
    ``[error] ...`` sentinel. Used by ``MLXStubAdapter`` as its
    default verify_task so the executor doesn't require
    ``td.expected`` to be set (which is the default in synthetic
    test fixtures).

    The function is exported as ``stub_verify_task`` so callers
    who want a stricter policy can pass it explicitly to
    ``RunConfig.verify_task=stub_verify_task`` or override it.
    """
    if text is None:
        return False
    if not text:
        return False
    return not text.startswith("[error]")


# ---------------------------------------------------------------------------
# MLXStubAdapter
# ---------------------------------------------------------------------------


class MLXStubAdapter(ModelAdapter):
    """Deterministic stub modelled on MockModel + bench-skeleton semantics.

    Used by:
      - tests/test_bench_runner.py::TestExecutor::test_executor_runs_end_to_end_with_stub
      - any ``make_adapter("mlx-stub")`` caller wanting a hermetic echo

    Differences from MockModel:
      - Name is ``mlx-stub`` (the registry key used by tests).
      - Carries ``verify_task = stub_verify_task`` so the executor
        marks the task as PASS whenever the stub emitted any text.
      - Token counts use len//4 like MockModel but also record
        ``adapter_kind="mlx-stub"`` in the raw envelope for
        downstream consumers (Argis oMLX consumer, etc.).
    """

    name = "mlx-stub"
    verify_task = staticmethod(stub_verify_task)

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

    def generate(self, messages: list[dict[str, str]], **kw: Any) -> ModelResponse:
        """Deterministic MLX-stub echo with optional fail-rate hook."""
        t0 = time.perf_counter()
        self.n_calls += 1
        if self.sleep_ms:
            time.sleep(self.sleep_ms / 1000.0)
        # The fail_rate knob is honoured (deterministic via n_calls) so
        # negative tests can exercise the executor's error path.
        if self.fail_rate > 0 and (self.n_calls * 0.314159) % 1 < self.fail_rate:
            return ModelResponse(
                latency_ms=(time.perf_counter() - t0) * 1000,
                finish_reason="error",
                error="mlx-stub: simulated failure",
            )
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        h = hashlib.sha256(last_user.encode("utf-8")).hexdigest()[:8]
        text = self.response_prefix + (last_user if self.echo else f"mlx-stub:{h}")
        prompt_tokens = max(1, sum(len(m.get("content", "")) for m in messages) // 4)
        completion_tokens = max(1, len(text) // 4)
        return ModelResponse(
            text=text,
            raw={
                "adapter_kind": "mlx-stub",
                "seed": self.seed,
                "n": self.n_calls,
                "echo": self.echo,
            },
            latency_ms=(time.perf_counter() - t0) * 1000,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason="stop",
        )


# ---------------------------------------------------------------------------
# Auto-register on import
# ---------------------------------------------------------------------------

register_adapter("mlx-stub", MLXStubAdapter)


__all__ = [
    "MLXStubAdapter",
    "stub_verify_task",
]
