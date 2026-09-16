"""Suite executor — orchestrates a run using a RunSpec.

.. deprecated::
    This bespoke executor is deprecated as of 2026-07-21. The canonical
    orchestrator is ``portage/src/harbor/orchestrators/``, invoked via
    ``harbor run --dataset <name> --agent <name> --model <name>``. The
    ``pheno-harness`` repo remains for smoke-test pipelines only.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from bench.adapters import ModelAdapter, build_adapter
from bench.cache import ResponseCache
from bench.energy import detect_source, make_source
from bench.parallel import ParallelRunner, default_workers
from bench.registry import get_suite
from bench.seeds import sample
from bench.types import (
    EnergySource,
    JudgeMode,
    RunSpec,
    SuiteResult,
    TaskResult,
    TaskStatus,
)

# ---------------------------------------------------------------------------
# Task descriptor + coercion
# ---------------------------------------------------------------------------


@dataclass
class TaskDescriptor:
    """A normalized descriptor for a single task within a suite."""

    task_id: str
    prompt: str
    expected: Any = None
    meta: dict[str, Any] = field(default_factory=dict)
    conversation_seed: list[Any] | None = None
    synthetic: bool = False


def _coerce_task_descriptor(
    raw: Any, index: int, suite_name: str, seed: int
) -> TaskDescriptor:
    if raw is None:
        return TaskDescriptor(
            task_id=f"{suite_name}-synth-{index:03d}", prompt="", synthetic=True
        )
    if isinstance(raw, TaskDescriptor):
        return raw
    if isinstance(raw, dict):
        meta = dict(raw.get("meta", {}) or {})
        synthetic = (
            meta.get("stub", False)
            or meta.get("synthetic", False)
            or raw.get("synthetic", False)
        )
        return TaskDescriptor(
            task_id=str(raw.get("task_id") or f"{suite_name}-{index:03d}"),
            prompt=str(raw.get("prompt", "")),
            expected=raw.get("expected"),
            meta=meta,
            synthetic=bool(synthetic),
        )
    if isinstance(raw, tuple) and len(raw) >= 2:
        return TaskDescriptor(
            task_id=str(raw[2]) if len(raw) >= 3 else f"{suite_name}-{index:03d}",
            prompt=str(raw[0]),
            expected=raw[1],
        )
    if isinstance(raw, str):
        return TaskDescriptor(
            task_id=f"{suite_name}-{index:03d}", prompt=raw, synthetic=True
        )
    return TaskDescriptor(
        task_id=f"{suite_name}-{index:03d}", prompt=str(raw), synthetic=True
    )


# ---------------------------------------------------------------------------
# Iteration
# ---------------------------------------------------------------------------


def iter_task_descriptors(
    spec: RunSpec,
    suite_class: type | None = None,
    cache: Any | None = None,
) -> list[TaskDescriptor]:
    """Resolve ``spec`` to a deterministically-sampled list of TaskDescriptors."""
    if suite_class is None:
        suite_class = get_suite(spec.suite)
    suite = suite_class()
    if hasattr(suite, "iter_tasks"):
        raw = list(suite.iter_tasks(spec))
    elif hasattr(suite, "tasks"):
        raw = list(suite.tasks)
    else:
        raw = [
            {"prompt": f"{spec.suite} placeholder task #{i:03d} (seed={spec.seed})"}
            for i in range(max(1, spec.n))
        ]
    coerced = [
        _coerce_task_descriptor(r, i, spec.suite, spec.seed) for i, r in enumerate(raw)
    ]
    subset = sample(spec.suite, spec.seed, count=len(coerced), n=spec.n)
    chosen = [coerced[i] for i in subset.ordered_indices]
    for idx, td in enumerate(chosen):
        if not td.task_id or td.task_id == "synth":
            td.task_id = f"{spec.suite}-synth-{idx:03d}"
    return chosen


# ---------------------------------------------------------------------------
# Run configuration + Executor
# ---------------------------------------------------------------------------


@dataclass
class RunConfig:
    """Top-level runtime configuration for a single suite run.

    The CLI constructs a `RunConfig` from parsed argv + defaults and hands
    it to `Executor(config).run()`. Same fields as the legacy
    `ExecutorConfig` (kept as a back-compat alias).
    """

    spec: RunSpec
    workers: int = field(default_factory=default_workers)
    per_task_timeout_s: float = 600.0
    cache_path: str | None = None
    no_cache: bool = False
    cache_ttl_s: float = 7 * 24 * 60 * 60.0
    judge_model: str | None = None
    stability_metric: bool = False
    gpu_index: int = 0
    extra_meta: dict[str, Any] = field(default_factory=dict)
    adapter_factory: Callable[[str], ModelAdapter] = field(
        default_factory=lambda: build_adapter
    )
    verify_task: Callable[..., bool] | None = None


# Back-compat alias.
ExecutorConfig = RunConfig


class Executor:
    """Main run-loop entry point."""

    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.cache = ResponseCache(
            path=config.cache_path or None,
            ttl_s=config.cache_ttl_s,
            no_cache=config.no_cache,
        )
        self.parallel = ParallelRunner(
            workers=config.workers,
            per_task_timeout_s=config.per_task_timeout_s,
        )
        self.energy_total: Any = None

    # ----------------------------------------------------------------- main

    async def run(self) -> SuiteResult:
        """Execute the configured suite against the model adapter."""
        spec = self.config.spec
        adapter = self.config.adapter_factory(spec.model)
        tasks = iter_task_descriptors(spec)
        n = len(tasks)
        energy_source = (
            spec.energy_source
            if spec.energy_source != EnergySource.NONE
            else detect_source()
        )
        energy_poller = make_source(energy_source, gpu_index=self.config.gpu_index)
        wall_clock_start = time.monotonic()
        energy_poller.start()
        try:
            task_results = await self._execute_all(tasks, adapter, energy_source)
        finally:
            self.energy_total = energy_poller.stop()
        wall_clock = time.monotonic() - wall_clock_start
        result = self._build_suite_result(task_results, wall_clock, energy_source, n)
        if spec.judge_mode == JudgeMode.LLM:
            self._run_llm_judge(result)
        if self.config.stability_metric:
            self._compute_stability(result)
        self.cache.close()
        try:
            close_result = adapter.aclose()
            if inspect.isawaitable(close_result):
                await close_result
        except Exception:  # nosec B110
            pass
        return result

    # ------------------------------------------------------ core fan-out

    async def _execute_all(
        self,
        tasks: list[TaskDescriptor],
        adapter: ModelAdapter,
        energy_source: EnergySource,
    ) -> list[TaskResult]:
        """Fan out `tasks` over `self.parallel`; return completed TaskResults.

        Each task is dispatched through the adapter via the parallel runner.
        Failures are captured as `TaskResult` with `TaskStatus.ERROR`
        rather than raised — callers can inspect the rollup.
        """
        if not tasks:
            return []
        loop = asyncio.get_running_loop()
        results: list[TaskResult | None] = [None] * len(tasks)
        sem = asyncio.Semaphore(self.config.workers)

        async def _run_one(idx: int, td: TaskDescriptor) -> None:
            async with sem:
                cache_key = self._key_for(td)
                cached = self.cache.get(cache_key)
                started = time.monotonic()
                if cached is not None:
                    completion_text, cached_meta = cached
                    results[idx] = TaskResult(
                        task_id=td.task_id,
                        status=TaskStatus.OK,
                        prompt=td.prompt,
                        completion=completion_text,
                        expected=td.expected,
                        meta=dict(td.meta),
                        started_at_s=started,
                        wall_clock_s=0.0,
                        tokens_in=0,
                        tokens_out=0,
                        cached=True,
                        synthetic=td.synthetic,
                        metrics={"from_cache": 1.0},
                    )
                    return
                try:
                    completion = await loop.run_in_executor(
                        None,
                        lambda: adapter.complete(
                            prompt=td.prompt,
                            meta=td.meta,
                            conversation_seed=td.conversation_seed,
                        ),
                    )
                    text = (
                        getattr(completion, "text", None)
                        or getattr(completion, "content", None)
                        or str(completion)
                    )
                    tokens_in = getattr(completion, "tokens_in", 0) or 0
                    tokens_out = getattr(completion, "tokens_out", 0) or 0
                    elapsed = time.monotonic() - started
                    passed = self._verify(td, text, adapter)
                    results[idx] = TaskResult(
                        task_id=td.task_id,
                        status=TaskStatus.OK if passed else TaskStatus.WRONG,
                        prompt=td.prompt,
                        completion=text,
                        expected=td.expected,
                        meta=dict(td.meta),
                        started_at_s=started,
                        wall_clock_s=elapsed,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cached=False,
                        synthetic=td.synthetic,
                    )
                    self.cache.put(
                        cache_key,
                        (text, {"tokens_in": tokens_in, "tokens_out": tokens_out}),
                    )
                except Exception as e:
                    elapsed = time.monotonic() - started
                    results[idx] = TaskResult(
                        task_id=td.task_id,
                        status=TaskStatus.ERROR,
                        prompt=td.prompt,
                        completion=f"[error] {type(e).__name__}: {e}",
                        expected=td.expected,
                        meta=dict(td.meta),
                        started_at_s=started,
                        wall_clock_s=elapsed,
                        tokens_in=0,
                        tokens_out=0,
                        cached=False,
                    )

        await asyncio.gather(*[_run_one(i, td) for i, td in enumerate(tasks)])
        return [r for r in results if r is not None]

    # ------------------------------------------------------ result rollup

    def _build_suite_result(
        self,
        task_results: list[TaskResult],
        wall_clock: float,
        energy_source: EnergySource,
        n: int,
    ) -> SuiteResult:
        passed = sum(1 for r in task_results if r.status == TaskStatus.OK)
        errored = sum(1 for r in task_results if r.status == TaskStatus.ERROR)
        wrong = sum(1 for r in task_results if r.status == TaskStatus.WRONG)
        total_tokens_out = sum(r.tokens_out for r in task_results)
        total_tokens_in = sum(r.tokens_in for r in task_results)
        duration_values = sorted(
            r.wall_clock_s for r in task_results if r.wall_clock_s > 0
        )
        cached_count = sum(1 for r in task_results if r.cached)
        metrics = {
            "pass@1": (passed / n) if n else 0.0,
            "wall_clock_total": wall_clock,
            "peak_RSS_MB": 0.0,
            "peak_GPU_mem_MB": 0.0,
            "tokens_per_sec_throughput": (total_tokens_out / wall_clock)
            if wall_clock > 0
            else 0.0,
            "energy_proxy_joules": 0.0,
            "time_per_task_p50": duration_values[len(duration_values) // 2]
            if duration_values
            else 0.0,
            "dead_end_rate": (errored / n) if n else 0.0,
            "retry_rate": 0.0,
            "cache_hit_rate": (cached_count / n) if n else 0.0,
        }
        return SuiteResult(
            suite=self.config.spec.suite,
            model=self.config.spec.model,
            n=n,
            wall_clock_s=wall_clock,
            passed=passed,
            wrong=wrong,
            errored=errored,
            pass_at_1=(passed / n) if n else 0.0,
            tokens_in=total_tokens_in,
            tokens_out=total_tokens_out,
            energy_total=self.energy_total,
            energy_source=energy_source,
            task_results=task_results,
            meta={**metrics, **dict(self.config.extra_meta)},
        )

    def _run_llm_judge(self, result: SuiteResult) -> None:
        """Run an LLM judge pass over the suite. No-op unless overridden."""

    def _compute_stability(self, result: SuiteResult) -> None:
        """Compute the long-horizon stability vector. No-op unless overridden."""

    # ------------------------------------------------------------- helpers

    def _key_for(self, td: TaskDescriptor) -> str:
        return f"{self.config.spec.suite}::{self.config.spec.model}::{td.task_id}::{self.config.spec.seed}"

    def _verify(
        self,
        td: TaskDescriptor,
        text: str,
        adapter: ModelAdapter,
    ) -> bool:
        """Verify a single task completion. Returns True if passed.

        Verification precedence (highest to lowest):
          1. ``RunConfig.verify_task`` — explicit caller override.
          2. ``adapter.verify_task`` — adapter-declared policy (used by
             ``bench.mlx_stub.MLXStubAdapter`` so smoke tests with no
             ``td.expected`` still mark PASS).
          3. Default: require non-empty completion that is not the
             ``[error] ...`` sentinel. When ``td.expected`` is set, the
             expected string must appear in the completion text.
          4. When ``expected is None`` **and** neither callback is
             registered, the task is marked as WRONG (not vacuously
             passed). This prevents synthetic / stub tasks from
             inflating pass rates unless they explicitly opted in.
        """
        if self.config.verify_task is not None:
            try:
                return bool(self.config.verify_task(td, text, adapter))
            except Exception:
                return False
        adapter_verify = getattr(adapter, "verify_task", None)
        if adapter_verify is not None:
            try:
                return bool(adapter_verify(td, text, adapter))
            except Exception:
                return False
        if not text or text.startswith("[error]"):
            return False
        if td.expected is None:
            return False
        return str(td.expected).strip().lower() in text.strip().lower()


__all__ = [
    "RunConfig",
    "ExecutorConfig",
    "TaskDescriptor",
    "iter_task_descriptors",
    "Executor",
    "_coerce_task_descriptor",
]


async def run_suite(
    spec: RunSpec,
    *,
    workers: int | None = None,
    per_task_timeout_s: float | None = None,
    cache_path: str | None = None,
    no_cache: bool | None = None,
    cache_ttl_s: float | None = None,
    judge_model: str | None = None,
    stability_metric: bool | None = None,
    gpu_index: int | None = None,
    extra_meta: dict[str, Any] | None = None,
    adapter_factory: Callable[[str], ModelAdapter] | None = None,
    verify_task: Callable[..., bool] | None = None,
) -> SuiteResult:
    """Convenience coroutine — builds a `RunConfig` from `spec` and runs.

    Used by the CLI and by ad-hoc harnesses that don't want to wire
    `Executor` themselves. All kwargs are optional and fall back to
    `RunConfig` defaults when not provided.
    """
    defaults = RunConfig(spec=spec)
    cfg = RunConfig(
        spec=spec,
        workers=workers if workers is not None else defaults.workers,
        per_task_timeout_s=(
            per_task_timeout_s
            if per_task_timeout_s is not None
            else defaults.per_task_timeout_s
        ),
        cache_path=cache_path,
        no_cache=no_cache if no_cache is not None else defaults.no_cache,
        cache_ttl_s=cache_ttl_s if cache_ttl_s is not None else defaults.cache_ttl_s,
        judge_model=judge_model if judge_model is not None else defaults.judge_model,
        stability_metric=(
            stability_metric
            if stability_metric is not None
            else defaults.stability_metric
        ),
        gpu_index=gpu_index if gpu_index is not None else defaults.gpu_index,
        extra_meta=extra_meta if extra_meta is not None else defaults.extra_meta,
        adapter_factory=adapter_factory
        if adapter_factory is not None
        else defaults.adapter_factory,
        verify_task=verify_task if verify_task is not None else defaults.verify_task,
    )
    return await Executor(cfg).run()


__all__.append("run_suite")
