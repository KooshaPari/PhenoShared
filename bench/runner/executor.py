"""Executor: the main run loop that orchestrates everything.

Sequence:

1. Resolve the suite class via the registry (`bench.registry.get_suite`).
2. Apply `seeds.sample` to deterministically pick `n` tasks (spec §7).
3. Fan out via `parallel.ParallelRunner.run_sync` — each adapter call runs
   on a thread executor because all four adapters expose sync APIs.
4. Reduce each Completion to a `TaskResult` (verifier or pass-through).
5. Optional LLM-judge pass (`judge_runner.run_judge`).
6. Optional stability pass (`stability.analyze_conversation`).
7. Aggregate into `SuiteResult` and emit to disk + cache.

Design rules (per spec):

* Async-first; per-task timeout default 600s (§2).
* Cache key includes `(suite, task_id, model, prompt_hash, temperature)` (§6).
* Deterministic subset per `--seed` (§7).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from bench.registry import get_suite
from bench.runner import __version__ as RUNNER_VERSION
from bench.runner.cache import ResponseCache, make_cache_key
from bench.runner.energy import EnergyTotal, detect_source, make_source
from bench.runner.executor_verify import (  # noqa: F401
    _tool_call_count,
    build_cached_result,
    build_error_result,
    build_task_result,
)
from bench.runner.executor_verify import (
    percentile as _percentile,
)
from bench.runner.executor_verify import (
    verify_task as _verify_task_fn,
)
from bench.runner.judge_runner import run_judge
from bench.runner.model_adapter import ModelAdapter, build_adapter
from bench.runner.parallel import ParallelRunner, default_workers
from bench.runner.perf import TimedSection, aggregate, measure_task
from bench.runner.seeds import sample as sample_subset
from bench.runner.stability import Turn, analyze_conversation
from bench.types import (
    EnergySource,
    JudgeMode,
    RunSpec,
    SuiteResult,
    TaskResult,
    TaskStatus,
)

_LOG = logging.getLogger("bench.runner.executor")


# ---------------------------------------------------------------------------
# Task descriptors
# ---------------------------------------------------------------------------


@dataclass
class TaskDescriptor:
    """A normalized descriptor for a single task within a suite.

    Concretely this is the dict-like object the executor hands to the
    adapter. Suite implementations can subclass or return proxies as needed.

    Fields:
        task_id: Stable identifier used for cache keys + report rows.
        prompt: The user-side prompt fed into the model.
        expected: Optional ground truth / verifier payload.
        meta: Free-form metadata (subject, difficulty, multi-turn seed, ...).
        synthetic: True when the task was synthesised (stub / placeholder),
            not drawn from a real suite definition.  Synthetic tasks must
            never inflate pass rates.
    """

    task_id: str
    prompt: str
    expected: Any = None
    meta: dict[str, Any] = field(default_factory=dict)
    conversation_seed: list[Turn] | None = None
    synthetic: bool = False


def _coerce_task_descriptor(
    raw: Any, index: int, suite_name: str, seed: int
) -> TaskDescriptor:
    """Convert whatever a suite returns into a TaskDescriptor.

    Suites owned by Forge-2/Forge-3 may return:

    * a `TaskDescriptor` instance,
    * a dict with at minimum `task_id` + `prompt`,
    * a tuple `(prompt, answer)`,
    * a bare string `prompt` (task_id is synthesised).

    Anything else falls back to a stringified synthetic descriptor.
    """
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
        prompt = str(raw.get("prompt", ""))
        return TaskDescriptor(
            task_id=str(raw.get("task_id") or f"{suite_name}-{index:03d}"),
            prompt=prompt,
            expected=raw.get("expected"),
            meta=meta,
            synthetic=bool(synthetic),
        )
    if isinstance(raw, tuple) and len(raw) >= 2:
        prompt = str(raw[0])
        return TaskDescriptor(
            task_id=str(raw[2]) if len(raw) >= 3 else f"{suite_name}-{index:03d}",
            prompt=prompt,
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
# Iteration over a suite
# ---------------------------------------------------------------------------


def iter_task_descriptors(
    spec: RunSpec,
    *,
    suite_class: type | None = None,
) -> list[TaskDescriptor]:
    """Build a deterministic, ordered list of `TaskDescriptor` for `spec`.

    Workflow:

    1. Look up the suite class. Missing-suit raises.
    2. Call `suite.iter_tasks(spec)` (preferred) or a synthetic fallback.
    3. Coerce each item to `TaskDescriptor`.
    4. Apply `seeds.sample(spec.suite, spec.seed, n=spec.n)` to deterministically
       pick `n` items. This is the "respect the subset size" guarantee.
    """
    if suite_class is None:
        suite_class = get_suite(spec.suite)
    suite = suite_class()  # may instantiate the suite (cheap, no IO)
    # Preferred: suite has `iter_tasks`.
    raw: list[Any]
    if hasattr(suite, "iter_tasks"):
        raw = list(suite.iter_tasks(spec))
    elif hasattr(suite, "tasks"):
        # Many suites will expose their task list directly.
        raw = list(suite.tasks)
    else:
        # Synthetic fallback: produce n=spec.n placeholder descriptors so the
        # executor remains exercisable before Forge-2/3 ship their suites.
        raw = [
            {"prompt": f"{spec.suite} placeholder task #{i:03d} (seed={spec.seed})"}
            for i in range(max(1, spec.n))
        ]
    coerced = [
        _coerce_task_descriptor(r, i, spec.suite, spec.seed) for i, r in enumerate(raw)
    ]
    # Apply deterministic subset sampling.
    list(range(len(coerced)))
    subset = sample_subset(spec.suite, spec.seed, count=len(coerced), n=spec.n)
    chosen = [coerced[i] for i in subset.ordered_indices]
    # Re-stamp task_ids with deterministic synthetic ones if they were none.
    for idx, td in enumerate(chosen):
        if not td.task_id or td.task_id == "synth":
            td.task_id = f"{spec.suite}-synth-{idx:03d}"
    return chosen


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


@dataclass
class ExecutorConfig:
    """Configuration for `Executor` (CLI args + defaults)."""

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
    verify_task: Callable[[TaskDescriptor, str, ModelAdapter], bool] | None = None


class Executor:
    """Main run-loop entry point. Use `await executor.run()` to drive a SuiteSpec."""

    def __init__(self, config: ExecutorConfig) -> None:
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
        # Set during run(); used by `_build_suite_result()`.
        self.energy_total: EnergyTotal | None = None

    # ----------------------------------------------------------------- main

    async def run(self) -> SuiteResult:
        """Run the configured RunSpec; return the resulting SuiteResult."""
        spec = self.config.spec
        adapter = self.config.adapter_factory(spec.model)
        tasks = iter_task_descriptors(spec)
        n = len(tasks)
        # Use real energy source (auto-detected when EnergySource.NONE).
        energy_source = (
            spec.energy_source
            if spec.energy_source != EnergySource.NONE
            else detect_source()
        )
        energy_poller = make_source(energy_source, gpu_index=self.config.gpu_index)
        started = time.monotonic()
        energy_poller.start()
        wall_clock_start = started
        try:
            task_results = await self._execute_all(tasks, adapter, energy_source)
        finally:
            self.energy_total = energy_poller.stop()
        wall_clock = time.monotonic() - wall_clock_start
        # Build a SuiteResult with rolled-up metrics.
        result = self._build_suite_result(task_results, wall_clock, energy_source, n)
        # Optional judge pass.
        if spec.judge_mode == JudgeMode.LLM:
            self._run_llm_judge(result)
        # Optional stability pass.
        if self.config.stability_metric:
            self._compute_stability(result)
        self.cache.close()
        # Final cleanup on the adapter.
        try:
            await adapter.aclose()
        except Exception:  # noqa: BLE001  # nosec B110
            pass
        return result

    # ------------------------------------------------------ core fan-out

    async def _execute_all(
        self,
        tasks: list[TaskDescriptor],
        adapter: ModelAdapter,
        energy_source: EnergySource,
    ) -> list[TaskResult]:
        spec = self.config.spec
        # Cache hint per task (we only *use* the cache when there's a hit;
        # writing back fresh completions is handled below).
        cache_keys: list[str] = [self._key_for(td, spec) for td in tasks]
        results: list[TaskResult | None] = [None] * len(tasks)
        # Try cache first.
        if not self.config.no_cache:
            for i, key in enumerate(cache_keys):
                hit = self.cache.get(key)
                if hit is None:
                    continue
                results[i] = build_cached_result(tasks[i], hit)
        # Fan out the missing ones.
        missing = [i for i, r in enumerate(results) if r is None]
        if missing:
            logger = _LOG
            logger.info(
                "executor: %d/%d cached; running %d live",
                len(results) - len(missing),
                len(results),
                len(missing),
            )
            self.energy_total = None
            asyncio.get_running_loop()

            def _call(idx: int) -> TaskResult:
                td = tasks[idx]
                with TimedSection(
                    task_id=td.task_id, gpu_index=self.config.gpu_index
                ) as ts:
                    try:
                        comp = adapter.complete(
                            td.prompt,
                            temperature=0.0,
                            max_tokens=512,
                            extra={"task_id": td.task_id},
                        )
                    except Exception as exc:  # noqa: BLE001
                        return build_error_result(
                            td.task_id, exc, time.monotonic() - ts._t0
                        )
                verified = _verify_task_fn(
                    td,
                    comp.text,
                    adapter,
                    verify_callback=self.config.verify_task,
                )
                return build_task_result(
                    td,
                    comp,
                    ts,
                    verified,
                    cache_keys,
                    idx,
                    spec,
                    self.config,
                    self.cache,
                )

            live_results = await self.parallel.run_sync(
                list(missing),
                _call,
            )
            for i, result in zip(missing, live_results):
                if isinstance(result, Exception):
                    results[i] = build_error_result(tasks[i].task_id, result, 0.0)
                else:
                    results[i] = result
        # Coerce `None` to a defensive TaskStatus.SKIP row.
        for i, r in enumerate(results):
            if r is None:
                results[i] = TaskResult(
                    task_id=tasks[i].task_id,
                    status=TaskStatus.SKIP,
                    duration_s=0.0,
                    message="no completion produced",
                )
        # Tag additional metadata into each task's metrics.
        for r in results:
            assert r is not None  # nosec B101
            r.metrics["run_id"] = spec.run_id
        return [r for r in results if r is not None]

    # ------------------------------------------------------- helpers

    def _key_for(self, td: TaskDescriptor, spec: RunSpec) -> str:
        return make_cache_key(
            suite=spec.suite,
            task_id=td.task_id,
            model=spec.model,
            prompt=td.prompt,
            temperature=0.0,
            extra={"seed": spec.seed, "n": spec.n, **self.config.extra_meta},
        )

    def _verify(
        self, td: TaskDescriptor, completion: str, adapter: ModelAdapter
    ) -> bool:
        """Run a per-suite verifier; default = non-empty completion."""
        return _verify_task_fn(
            td,
            completion,
            adapter,
            verify_callback=self.config.verify_task,
        )

    def _build_suite_result(
        self,
        task_results: list[TaskResult],
        wall_clock_s: float,
        energy_source: EnergySource,
        total_tasks: int,
    ) -> SuiteResult:
        spec = self.config.spec
        ok = sum(1 for t in task_results if t.status == TaskStatus.PASS)
        total = max(1, total_tasks)
        pass1 = ok / float(total)
        readings = [
            measure_task(
                tr.task_id,
                prompt_tokens=tr.prompt_tokens,
                completion_tokens=tr.completion_tokens,
                duration_s=tr.duration_s if tr.duration_s > 0 else 1e-6,
            )
            for tr in task_results
        ]
        agg = aggregate(readings, wall_clock_s=wall_clock_s)
        energy_total = getattr(self, "energy_total", None)
        energy_joules = float(energy_total.joules) if energy_total is not None else 0.0
        mean_latency_ms = (
            sum(t.metrics.get("latency_ms", 0.0) for t in task_results) / total
        )
        metrics: dict[str, float | str] = {
            "pass@1": float(pass1),
            "wall_clock_total": float(wall_clock_s),
            "peak_RSS_MB": float(agg.peak_rss_mb),
            "peak_GPU_mem_MB": float(agg.peak_gpu_mem_mb),
            "tokens_per_sec_throughput": float(agg.throughput_tok_per_s),
            "energy_proxy_joules": float(energy_joules),
            "time_per_task_p50": float(
                _percentile([t.duration_s for t in task_results], 50)
            ),
            "time_per_task_p95": float(
                _percentile([t.duration_s for t in task_results], 95)
            ),
            "mean_tokens_per_completion": float(
                sum(t.completion_tokens for t in task_results) / total
            ),
            "dead_end_rate": float(
                sum(1 for t in task_results if t.status == TaskStatus.TIMEOUT) / total
            ),
            "retry_rate": float(
                sum(1 for t in task_results if t.status == TaskStatus.ERROR) / total
            ),
            "format_error_rate": float(
                sum(
                    1
                    for t in task_results
                    if "format" in t.message.lower() and t.status != TaskStatus.PASS
                )
                / total
            ),
            "tool_call_success_rate": float(
                sum(
                    1
                    for t in task_results
                    if _tool_call_count(t) > 0 and t.status == TaskStatus.PASS
                )
                / max(1, sum(1 for t in task_results if _tool_call_count(t) > 0))
            ),
            "latency_ms_mean": float(mean_latency_ms),
            "runner_version": RUNNER_VERSION,
        }
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return SuiteResult(
            run_id=spec.run_id,
            suite=spec.suite,
            model=spec.model,
            started_at=ts,
            stopped_at=ts,
            tasks=task_results,
            metrics=metrics,
        )

    def _run_llm_judge(self, result: SuiteResult) -> None:
        spec = self.config.spec
        blocks = [
            (
                next(
                    (t.task_id for t in result.tasks if t.task_id == tr.task_id),
                    tr.task_id,
                ),
                tr.message,
            )
            for tr in result.tasks
        ]
        try:
            run_judge(
                result.tasks,
                blocks=[(p, "") for p, _ in blocks],
                judge_model=self.config.judge_model or spec.judge_model or "",
                judge_mode=spec.judge_mode,
            )
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("judge pass failed: %s", exc)

    def _compute_stability(self, result: SuiteResult) -> None:
        """Compute stability metrics per task (drift, dead-ends)."""
        for tr in result.tasks:
            conversation = [
                Turn(role="user", content=tr.task_id),
                Turn(role="assistant", content=tr.message),
            ]
            stats = analyze_conversation(conversation, stability_metric=True)
            tr.metrics["stability_dead_ends"] = float(stats.get("dead_end_count", 0))
            tr.metrics["stability_intent_drift"] = float(
                stats["intent_drift"]["drift_mean"]
            )
        # Aggregate into the SuiteResult
        drifts = [t.metrics.get("stability_intent_drift", 0.0) for t in result.tasks]
        result.metrics["semantic_drift_p99"] = float(_percentile(drifts, 99))


# Public surface ----------------------------------------------------------

__all__ = [
    "Executor",
    "ExecutorConfig",
    "TaskDescriptor",
    "iter_task_descriptors",
]
