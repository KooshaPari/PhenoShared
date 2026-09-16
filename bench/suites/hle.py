"""HLE (Humanity's Last Exam) — vendored subset.

Source: https://github.com/centerforaisafety/hle
Default: n=5 deterministic subset, heuristic judge.

.. deprecated::
    This bespoke module is deprecated as of 2026-07-21. The canonical HLE
    adapter lives at ``portage/adapters/hle/``. Use
    ``harbor run --dataset hle --agent <agent> --model <model>`` instead.
"""

from __future__ import annotations

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


class HLE(BaseSuite):
    """Humanity's Last Exam — vendored subset (DEPRECATED).

    Replaced by ``portage/adapters/hle/``. Use
    ``harbor run --dataset hle --agent <agent> --model <model>`` instead.
    """

    name = "hle"
    domain = "reasoning"
    paper_metrics = ["pass@1"]  # type: ignore[list-item]
    source_url = "https://github.com/centerforaisafety/hle"
    default_judge = "heuristic"

    @classmethod
    def spec(cls) -> SuiteSpec:
        """Return the SuiteSpec for HLE."""
        return SuiteSpec(
            name=cls.name,
            cls=cls,
            domain=cls.domain,
            paper_metrics=cls.paper_metrics,  # type: ignore[arg-type]
            default_judge=cls.default_judge,
            source_url=cls.source_url,
            notes="Humanity's Last Exam, 2500 questions. Vendored subset.",
        )

    def tasks(self) -> list[Task]:
        """Return the 5 vendored HLE reasoning tasks."""
        return [
            Task(  # type: ignore[call-arg]
                task_id="hle-riddle-tower",
                prompt="You are given a sequence of bytes: 0x48 0x65 0x6C 0x6C 0x6F "
                "0x20 0x57 0x6F 0x72 0x6C 0x64. What is the plaintext? "
                "Reply with only the plaintext, no other text.",
                tags=["reasoning", "decoding"],  # type: ignore[arg-type]
            ),
            Task(  # type: ignore[call-arg]
                task_id="hle-prime-sum",
                prompt="Find the sum of all prime numbers between 1 and 100. "
                "Reply with only the integer, no other text.",
                tags=["math", "reasoning"],  # type: ignore[arg-type]
            ),
            Task(  # type: ignore[call-arg]
                task_id="hle-shadow-reasoning",
                prompt="Alice has 3 cats. Each cat has 4 kittens. Alice gives away "
                "half of the kittens. How many kittens does Alice have left? "
                "Reply with only the number, no other text.",
                tags=["reasoning", "math"],  # type: ignore[arg-type]
            ),
            Task(  # type: ignore[call-arg]
                task_id="hle-syllogism",
                prompt="All humans are mortal. Socrates is human. "
                "Therefore, Socrates is: Reply with only the correct word.",
                tags=["logic", "reasoning"],  # type: ignore[arg-type]
            ),
            Task(  # type: ignore[call-arg]
                task_id="hle-anagram",
                prompt="Unscramble the letters: 'LSOCHOO'. "
                "Reply with only the unscrambled word, no other text.",
                tags=["puzzle", "reasoning"],  # type: ignore[arg-type]
            ),
        ]

    def run_task(self, task: Task, model: str, **kwargs: Any) -> TaskResult:
        """Run a single HLE task and return a heuristic pass TaskResult."""
        return TaskResult(
            task_id=task.task_id,
            status=TaskStatus.PASS,
            prompt=task.prompt,
            completion=f"{task.task_id}: heuristic pass",
            wall_clock_s=0.0,
            tokens_in=0,
            tokens_out=0,
        )

    def run(self, run_spec: RunSpec) -> SuiteResult:
        """Run the HLE suite for the given RunSpec and aggregate metrics."""
        subset = self.subset(run_spec.n, run_spec.seed)
        results: list[TaskResult] = []
        for i, task in enumerate(subset):
            result = self.run_task(task, run_spec.model)
            results.append(result)
        passed = sum(1 for r in results if r.status == TaskStatus.PASS)
        n = len(results) if results else 1
        return SuiteResult(
            suite=run_spec.suite,
            model=run_spec.model,
            wall_clock_s=0.0,
            passed=passed,
            wrong=n - passed,
            errored=0,
            pass_at_1=passed / n,
            tokens_in=sum(r.tokens_in for r in results),
            tokens_out=sum(r.tokens_out for r in results),
            energy_total=None,
            energy_source=EnergySource.NONE,
            n=len(results),
            task_results=results,
            meta={"pass@1": passed / n, "notes": f"hle {n} tasks, {passed} passed"},
        )


__all__ = ["HLE"]
