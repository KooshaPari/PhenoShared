"""Verification and metric helpers for the bench executor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bench.runner.cache import ResponseCache
from bench.runner.model_adapter import ModelAdapter
from bench.runner.perf import TimedSection
from bench.types import TaskResult, TaskStatus

if TYPE_CHECKING:
    from bench.runner.executor import TaskDescriptor


def _tool_call_count(tr: TaskResult) -> int:
    tc = tr.tool_calls
    if isinstance(tc, int):
        return tc
    if isinstance(tc, (list, tuple)):
        return len(tc)
    return 0


def verify_task(
    td: TaskDescriptor,
    completion: str,
    adapter: ModelAdapter,
    *,
    verify_callback: Any | None = None,
) -> bool:
    """Run a per-suite verifier; default = non-empty completion.

    When ``expected`` is ``None`` **and** no custom ``verify_task``
    callback is registered, the task is marked as failed (not vacuously
    passed).  This prevents synthetic / stub tasks from inflating pass
    rates.
    """
    if verify_callback is not None:
        try:
            return bool(verify_callback(td, completion, adapter))
        except Exception:
            return False
    if not completion or completion.startswith("[error]"):
        return False
    if td.expected is None:
        return False
    return str(td.expected).strip().lower() in completion.strip().lower()


def build_task_result(
    td: TaskDescriptor,
    comp: Any,
    ts: TimedSection,
    verified: bool,
    cache_keys: list[str],
    idx: int,
    spec: Any,
    config: Any,
    cache: ResponseCache,
) -> TaskResult:
    """Build a TaskResult from a completion, writing to cache."""
    reading = ts.to_reading(
        prompt_tokens=comp.prompt_tokens,
        completion_tokens=comp.completion_tokens,
    )
    tr = TaskResult(
        task_id=td.task_id,
        status=TaskStatus.PASS if verified else TaskStatus.FAIL,
        duration_s=ts.duration_s,
        prompt_tokens=comp.prompt_tokens,
        completion_tokens=comp.completion_tokens,
        tool_calls=int(td.meta.get("tool_calls", 0)),
        reward=1.0 if verified else 0.0,
        message=f"ok (latency_ms={comp.latency_ms:.1f})",
        metrics={
            "latency_ms": comp.latency_ms,
            "peak_rss_mb": reading.peak_rss_mb,
            "peak_gpu_mem_mb": reading.peak_gpu_mem_mb,
            "tokens_per_sec": reading.tokens_per_sec,
        },
    )
    if not config.no_cache:
        cache.put(
            key=cache_keys[idx],
            suite=spec.suite,
            task_id=td.task_id,
            model=spec.model,
            temperature=0.0,
            value={
                "text": comp.text,
                "prompt_tokens": comp.prompt_tokens,
                "completion_tokens": comp.completion_tokens,
                "latency_ms": comp.latency_ms,
                "status": tr.status.value,
            },
        )
    return tr


def build_error_result(task_id: str, exc: Exception, duration_s: float) -> TaskResult:
    """Build an error TaskResult."""
    return TaskResult(
        task_id=task_id,
        status=TaskStatus.ERROR,
        duration_s=duration_s,
        message=f"{type(exc).__name__}: {exc}",
    )


def build_cached_result(td: TaskDescriptor, hit: Any) -> TaskResult:
    """Build a TaskResult from a cache hit."""
    v = hit.value
    from bench.types import TaskStatus as TS

    return TaskResult(
        task_id=td.task_id,
        status=TS(v.get("status", TS.PASS.value)),
        duration_s=float(v.get("latency_ms", 0.0)) / 1000.0,
        prompt_tokens=int(v.get("prompt_tokens", 0)),
        completion_tokens=int(v.get("completion_tokens", 0)),
        reward=1.0 if v.get("status") == TS.PASS.value else 0.0,
        message="cache hit",
        metrics={"from_cache": 1.0},
    )


def percentile(values: list[float], pct: int) -> float:
    """Local percentile wrapper that returns NaN for empty input."""
    from bench.metric import percentile as _p

    if not values:
        return float("nan")
    return _p(list(values), float(pct))
