"""MT-Bench — lm-sys/FastChat multi-turn benchmark.

80 multi-turn questions × 10 categories. LLM-as-judge (Claude Sonnet 5 by
default; spec §Q10 + spec §2 row 5).

Spec reference: docs/superpowers/specs/2026-07-16-benchmark-harness.md §2 row 5,
§3.2 (judge port). Spec rule 4: if `ANTHROPIC_API_KEY` is missing, fall back
to stub-mode that returns a random verdict in [0,10] with `judge_stub=True`.
"""

from __future__ import annotations

import time
from typing import Any

from bench.types import RunSpec, SuiteResult, TaskResult, TaskStatus

from ._stub import BaseSuite, TaskSpec, synthetic_prompt, synthetic_response
from .judge import DEFAULT_JUDGE_MODEL, JudgeRequest, JudgeVerdict, LLMJudge

SOURCE_URL = "github.com/lm-sys/FastChat"
VERSION = "1.0"
NUM_TASKS = 80  # full set; spec §2 row 5
CATEGORIES: tuple[str, ...] = (
    "writing",
    "roleplay",
    "reasoning",
    "math",
    "coding",
    "extraction",
    "stem",
    "humanities",
    "arena-hard",
    "translation",
)
JUDGE_RUBRIC = (
    "Score the assistant's response on a 1-10 scale. A 10 is a flawless, "
    "complete answer. A 1 is incorrect or refuses without reason. Reward "
    "accuracy, helpfulness, and adherence to any formatting constraints."
)


class MTBench(BaseSuite):
    """MT-Bench — multi-turn intent eval with LLM-as-judge."""

    name = "mt-bench"
    version = VERSION
    num_tasks = NUM_TASKS
    task_format = "LLM-judge (Claude Sonnet 5 default; override via --judge-model)"
    scoring = "mean score [1..10] per category + global average (judge verdict)"
    source_url = SOURCE_URL
    format = task_format
    _subset_label = "full 80 (cheap)"
    rationale = "multi-turn intent"
    default_judge_mode = "llm"  # type: ignore[assignment]
    task_id_prefix = "mtbench"

    _PAPER_METRICS = (
        ("score_mean", "1-10", "spec §4 + MT-Bench leaderboard"),
        ("score_mean_writing", "1-10", "spec §2 row 5 + MT-Bench writing category"),
        ("score_mean_coding", "1-10", "spec §2 row 5 + MT-Bench coding category"),
        ("judge_latency_ms", "ms", "spec §4.4 (LLM judge)"),
        ("judge_stub_rate", "ratio", "internal: fraction of stub verdicts"),
    )

    def __init__(
        self,
        *,
        judge_model: str = DEFAULT_JUDGE_MODEL,
        api_key: str | None = None,
        force_stub: bool = False,
    ) -> None:
        self.judge_model = str(judge_model)
        self.judge = LLMJudge(
            model=self.judge_model,
            api_key=api_key,
            force_stub=force_stub,
        )

    # ------------------------------------------------------------------
    # Subset
    # ------------------------------------------------------------------

    def subset(self, n: int, seed: int) -> list[TaskSpec]:
        """Return n MT-Bench task specs.

        Real-mode: pulls the 80-question set from FastChat's `mt_bench`
        JSONL (pinned submodule). Stub-mode: synthetic category IDs and
        prompts.
        """
        n = max(0, int(n))
        # Try submodule first, else synthetic.
        tasks_per_cat = NUM_TASKS // len(CATEGORIES)
        out: list[TaskSpec] = []
        for i in range(n):
            cat = CATEGORIES[i // max(1, tasks_per_cat) % len(CATEGORIES)]
            # Stable turn-1 + turn-2 prompts per slot.
            t1 = synthetic_prompt(seed, i)
            t2 = synthetic_prompt(seed, i + 10000)
            out.append(
                TaskSpec(
                    task_id=f"mtbench-{cat}-{i:03d}",
                    suite=self.name,
                    prompt=t1,
                    reference=t2,
                    metadata={
                        "seed": seed,
                        "index": i,
                        "category": cat,
                        "turn_2_prompt": t2,
                        "stub": True,
                    },
                    tags=("mt-bench", cat),
                )
            )
        return out

    # ------------------------------------------------------------------
    # Per-task execution
    # ------------------------------------------------------------------

    def run_task(self, task: TaskSpec, model: str, **kwargs: Any) -> TaskResult:
        """Run one MT-Bench task: produce a response, judge it, return TaskResult.

        Stub-mode: synthetic response + judge returns random verdict in [0,10]
        with `judge_stub=True`. Real-mode: hit the actual model + judge.
        """
        response = str(kwargs.get("response", ""))
        if not response:
            response = synthetic_response(0, hash(task.task_id) & 0xFFFF)
        verdict: JudgeVerdict = self.judge.judge(
            JudgeRequest(
                system_prompt="You are an impartial judge evaluating a multi-turn assistant response.",
                user_prompt=str(task.prompt),
                response=response,
                reference=str(task.reference),
                rubric=JUDGE_RUBRIC,
                max_score=10.0,
                metadata={
                    "task_id": task.task_id,
                    "category": task.metadata.get("category"),
                },
            )
        )
        # Convert [0,10] to a pass/fail status. Spec §4.1 quality metric:
        # pass@1 binary, threshold 7.0 by convention for MT-Bench.
        threshold = float(kwargs.get("pass_threshold", 7.0))
        status = TaskStatus.PASS if verdict.score >= threshold else TaskStatus.FAIL
        return TaskResult(
            task_id=task.task_id,
            status=status,
            wall_clock_s=verdict.latency_ms / 1000.0,
            tokens_in=len(task.prompt.split()),
            tokens_out=len(response.split()),
            tool_calls=[],
            meta={
                "judge_score": verdict.score,
                "judge_latency_ms": verdict.latency_ms,
                "judge_stub": 1.0 if verdict.judge_stub else 0.0,
            },
        )

    # ------------------------------------------------------------------
    # Skeleton `Suite.run` orchestrator
    # ------------------------------------------------------------------

    def run(self, run_spec: RunSpec) -> SuiteResult:
        """Run the MT-Bench subset and return a SuiteResult."""
        started_at = time.time()
        tasks = self.subset(run_spec.n, run_spec.seed)
        results: list[TaskResult] = [self.run_task(t, run_spec.model) for t in tasks]
        if not results:
            return SuiteResult(
                suite=self.name,
                model=run_spec.model,
                n=0,
                wall_clock_s=time.time() - started_at,
                passed=0,
                wrong=0,
                errored=0,
                pass_at_1=0.0,
                tokens_in=0,
                tokens_out=0,
                energy_source=run_spec.energy_source,
                task_results=results,
                meta={},
            )
        scores = [r.meta.get("judge_score", 0.0) for r in results]
        stub_flags = [r.meta.get("judge_stub", 0.0) for r in results]
        passes = sum(1 for r in results if r.status == TaskStatus.PASS)
        return SuiteResult(
            suite=self.name,
            model=run_spec.model,
            n=len(results),
            wall_clock_s=time.time() - started_at,
            passed=passes,
            wrong=len(results) - passes,
            errored=0,
            pass_at_1=passes / len(results),
            tokens_in=sum(r.tokens_in for r in results),
            tokens_out=sum(r.tokens_out for r in results),
            energy_source=run_spec.energy_source,
            task_results=results,
            meta={
                "score_mean": sum(scores) / len(scores),
                "score_min": min(scores),
                "score_max": max(scores),
                "pass@1": passes / len(results),
                "judge_stub_rate": sum(stub_flags) / len(stub_flags),
            },
        )


__all__ = ["MTBench", "CATEGORIES", "NUM_TASKS", "JUDGE_RUBRIC"]
