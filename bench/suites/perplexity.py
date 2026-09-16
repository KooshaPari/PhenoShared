"""Perplexity — held-out language-model evaluation.

Follows the spec: WikiText-103 / SlimPajama-6B subset, sliding-window PPL,
limited to mock-model execution for smoke runs.

.. deprecated::
    This bespoke module is deprecated as of 2026-07-21. Perplexity is a
    custom scorer in portage's analyze backend
    (``portage/src/harbor/analyze/checker.py``); implement it there and
    invoke via ``harbor analyze``.
"""

from __future__ import annotations

import time
from typing import Any

from bench.suites._stub import BaseSuite, Task
from bench.types import (
    EnergySource,
    RunSpec,
    SuiteResult,
    SuiteSpec,
    TaskResult,
    TaskStatus,
)


class Perplexity(BaseSuite):
    """Perplexity — held-out language-model evaluation (DEPRECATED).

    Replaced by a scorer in portage's analyze backend
    (``portage/src/harbor/analyze/checker.py``). Invoke via ``harbor analyze``.
    """

    name = "perplexity"
    domain = "nlm"
    paper_metrics = ["perplexity"]  # type: ignore[list-item]
    source_url = "https://huggingface.co/datasets/Salesforce/wikitext"
    default_judge = "heuristic"

    @classmethod
    def spec(cls) -> SuiteSpec:
        """Return the SuiteSpec for Perplexity."""
        return SuiteSpec(
            name=cls.name,
            cls=cls,
            domain=cls.domain,
            paper_metrics=cls.paper_metrics,  # type: ignore[arg-type]
            default_judge=cls.default_judge,
            source_url=cls.source_url,
            notes="Perplexity on WikiText-103 / SlimPajama-6B subset.",
        )

    def tasks(self) -> list[Task]:
        """Return 5 mock perplexity tasks (wikitext, slimpajama, code, long-ctx, math)."""
        return [
            Task(  # type: ignore[call-arg]
                task_id="ppl-wikitext-103",
                prompt="The cat sat on the mat. The dog ran in the park. "
                "The bird flew over the tree. The fish swam in the pond. "
                "The sun shone brightly in the clear blue sky.",
                tags=["perplexity", "wikitext"],  # type: ignore[arg-type]
            ),
            Task(  # type: ignore[call-arg]
                task_id="ppl-slimpajama-sample",
                prompt="In the beginning, the universe was created. "
                "This has made a lot of people very angry and been widely "
                "regarded as a bad move.",
                tags=["perplexity", "slimpajama"],  # type: ignore[arg-type]
            ),
            Task(  # type: ignore[call-arg]
                task_id="ppl-code-sample",
                prompt="def factorial(n: int) -> int:\n    "
                "if n <= 1:\n        return 1\n    "
                "return n * factorial(n - 1)",
                tags=["perplexity", "code"],  # type: ignore[arg-type]
            ),
            Task(  # type: ignore[call-arg]
                task_id="ppl-long-context",
                prompt="The quick brown fox jumps over the lazy dog. " * 20,
                tags=["perplexity", "long-context"],  # type: ignore[arg-type]
            ),
            Task(  # type: ignore[call-arg]
                task_id="ppl-math-reasoning",
                prompt="The derivative of x^2 is 2x. The integral of 2x dx is x^2 + C. "
                "The limit as x approaches 0 of sin(x)/x is 1.",
                tags=["perplexity", "math"],  # type: ignore[arg-type]
            ),
        ]

    def run_task(self, task: Task, model: str, **kwargs: Any) -> TaskResult:
        """Run a single perplexity task and return a heuristic pass TaskResult."""
        return TaskResult(
            task_id=task.task_id,
            status=TaskStatus.PASS,
            wall_clock_s=0.0,
            tokens_in=0,
            tokens_out=0,
            completion=f"mock: {task.prompt[:40]}",
        )

    def run(self, run_spec: RunSpec) -> SuiteResult:
        """Run the Perplexity suite for the given RunSpec and aggregate metrics."""
        subset = self.subset(run_spec.n, run_spec.seed)
        results: list[TaskResult] = []
        for i, task in enumerate(subset):
            result = self.run_task(task, run_spec.model)
            results.append(result)
        time.time()
        passed = sum(1 for r in results if r.status == TaskStatus.PASS)
        return SuiteResult(
            suite=run_spec.suite,
            model=run_spec.model,
            wall_clock_s=0.0,
            passed=passed,
            wrong=len(results) - passed,
            errored=0,
            pass_at_1=passed / len(results) if results else 0.0,
            tokens_in=0,
            tokens_out=0,
            energy_total=None,
            energy_source=EnergySource.NONE,
            n=len(results),
            task_results=results,
            meta={
                "pass@1": passed / len(results) if results else 0.0,
                "notes": f"perplexity {len(results)} tasks, {passed} passed",
            },
        )


__all__ = ["Perplexity"]
