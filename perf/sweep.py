"""Concurrency sweep orchestration."""

from __future__ import annotations

import concurrent.futures
import time
from collections.abc import Callable, Iterable
from typing import Any

from .streaming import percentile


def run_level(
    caller: Callable[[dict[str, Any]], dict[str, Any]],
    tasks: Iterable[dict[str, Any]],
    concurrency: int,
) -> dict[str, Any]:
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    work = list(tasks)
    started = time.perf_counter()

    def invoke(task: dict[str, Any]) -> dict[str, Any]:
        try:
            result = caller(task)
            return (
                result
                if isinstance(result, dict)
                else {"error": "caller returned non-object"}
            )
        except Exception as exc:  # preserve partial sweeps for server failures
            return {"error": f"caller exception: {type(exc).__name__}: {exc}"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(invoke, task) for task in work]
        results = [future.result() for future in futures]
    wall_ms = (time.perf_counter() - started) * 1000.0
    ok = [result for result in results if "error" not in result]
    latencies = [float(result["elapsed_ms"]) for result in ok if "elapsed_ms" in result]
    tokens = sum(int(result.get("completion_tokens") or 0) for result in ok)
    return {
        "concurrency": concurrency,
        "request_count": len(results),
        "success_count": len(ok),
        "error_count": len(results) - len(ok),
        "wall_ms": wall_ms,
        "aggregate_tokens": tokens,
        "aggregate_tokens_per_s": tokens / (wall_ms / 1000.0) if wall_ms else 0.0,
        "latency_ms_p50": percentile(latencies, 0.50),
        "latency_ms_p95": percentile(latencies, 0.95),
        "results": results,
    }


def run_sweep(
    caller: Callable[[dict[str, Any]], dict[str, Any]],
    tasks: list[dict[str, Any]],
    levels: list[int],
    warmup: int = 0,
) -> dict[str, Any]:
    warmup_results = []
    warmup_task = (
        tasks[0] if tasks else {"prompt": "warmup", "max_tokens": 8, "temperature": 0.0}
    )
    for _ in range(max(0, warmup)):
        try:
            result = caller(warmup_task)
            warmup_results.append(
                result
                if isinstance(result, dict)
                else {"error": "caller returned non-object"}
            )
        except Exception as exc:
            warmup_results.append(
                {"error": f"caller exception: {type(exc).__name__}: {exc}"}
            )
    return {
        "warmup": {
            "requested": max(0, warmup),
            "results": warmup_results,
            "error_count": sum("error" in item for item in warmup_results),
        },
        "levels": [run_level(caller, tasks, level) for level in levels],
    }


__all__ = ["run_level", "run_sweep"]
