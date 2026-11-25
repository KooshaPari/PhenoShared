"""EvaluationService — orchestrates task evaluation via ports.

Depends on :class:`InferencePort` for model generation and
:class:`JudgePort` for optional LLM-as-judge scoring.  Never
couples to a concrete adapter or judge implementation.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from bench.ports.inference import InferencePort
from bench.ports.judge import JudgePort


@dataclass
class EvalResult:
    """Outcome for a single evaluation step."""

    task_id: str
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    score: float = 0.0
    passed: bool = False
    error: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class EvaluationService:
    """Orchestrate evaluation of tasks through InferencePort + JudgePort."""

    def __init__(
        self,
        inference: InferencePort,
        judge: JudgePort | None = None,
        verify_fn: Callable[[str, str], bool] | None = None,
    ) -> None:
        self.inference = inference
        self.judge = judge
        self.verify_fn = verify_fn

    async def generate_and_score(
        self,
        task_id: str,
        prompt: str,
        expected: str | None = None,
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        system: str | None = None,
    ) -> EvalResult:
        """Generate a completion, then optionally judge it."""
        t0 = time.monotonic()
        try:
            response = await self.inference.agenerate(
                [{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **({"system": system} if system else {}),
            )
        except Exception as exc:  # noqa: BLE001
            return EvalResult(
                task_id=task_id,
                text="",
                error=f"{type(exc).__name__}: {exc}",
            )
        dt = (time.monotonic() - t0) * 1000.0
        text = getattr(response, "text", "") or ""
        pt = getattr(response, "prompt_tokens", 0) or 0
        ct = getattr(response, "completion_tokens", 0) or 0

        score = 0.0
        passed = False
        if expected is not None:
            if self.verify_fn is not None:
                passed = bool(self.verify_fn(text, expected))
            else:
                passed = expected.strip().lower() in text.strip().lower()
            score = 1.0 if passed else 0.0

        if self.judge is not None and expected is not None:
            try:
                score = await self.judge.evaluate(task_id, text, expected)
                passed = score >= 0.5
            except Exception:  # noqa: BLE001  # nosec B110
                pass

        return EvalResult(
            task_id=task_id,
            text=text,
            prompt_tokens=int(pt),
            completion_tokens=int(ct),
            latency_ms=dt,
            score=score,
            passed=passed,
        )
