"""Concurrent work across independently served local workers."""

from __future__ import annotations

import concurrent.futures
import time
from collections import Counter
from collections.abc import Callable, Iterable
from typing import Any

from .streaming import percentile


def run_heterogeneous(
    workers: list[dict[str, str]],
    tasks: Iterable[dict[str, Any]],
    concurrency: int,
    caller: Callable[[dict[str, str], dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    if not workers:
        raise ValueError("at least one worker is required")
    if concurrency < 1:
        raise ValueError("concurrency must be at least one")
    work = list(tasks)
    # Assign proportionally to measured capacity.  With no capacity metadata,
    # every worker has weight one and this remains deterministic least-load.
    loads = [0.0] * len(workers)
    weights = []
    for worker in workers:
        weight = float(worker.get("capacity_weight", 1.0) or 1.0)
        if weight <= 0:
            raise ValueError("worker capacity_weight must be positive")
        weights.append(weight)
    assignments = []
    for task in work:
        index = min(
            range(len(workers)),
            key=lambda item: (loads[item], item),
        )
        worker = workers[index]
        assignments.append(worker)
        loads[index] += 1.0 / weights[index]
    started = time.perf_counter()

    def invoke(item: tuple[dict[str, str], dict[str, Any]]) -> dict[str, Any]:
        worker, task = item
        try:
            result = caller(worker, task)
            if not isinstance(result, dict):
                result = {"error": "caller returned non-object"}
        except Exception as exc:  # preserve partial multi-worker evidence
            result = {"error": f"caller exception: {type(exc).__name__}: {exc}"}
        result["worker"] = worker.get("id", "unknown")
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(invoke, zip(assignments, work)))
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    successful = [item for item in results if "error" not in item]
    latencies = [
        float(item["elapsed_ms"]) for item in successful if "elapsed_ms" in item
    ]
    tokens = sum(int(item.get("completion_tokens") or 0) for item in successful)
    by_worker: dict[str, dict[str, Any]] = {}
    for worker_id in sorted({item["worker"] for item in results}):
        subset = [item for item in successful if item["worker"] == worker_id]
        subset_tokens = sum(int(item.get("completion_tokens") or 0) for item in subset)
        subset_latencies = [
            float(item["elapsed_ms"]) for item in subset if "elapsed_ms" in item
        ]
        by_worker[worker_id] = {
            "request_count": sum(item["worker"] == worker_id for item in results),
            "success_count": len(subset),
            "error_count": sum(
                item["worker"] == worker_id and "error" in item for item in results
            ),
            "tokens": subset_tokens,
            "latency_ms_p50": percentile(subset_latencies, 0.50),
            "latency_ms_p95": percentile(subset_latencies, 0.95),
        }
    return {
        "concurrency": concurrency,
        "worker_count": len(workers),
        "scheduler": "capacity_weighted_least_normalized_load",
        "request_count": len(results),
        "success_count": len(successful),
        "error_count": len(results) - len(successful),
        "worker_assignments": dict(Counter(item["worker"] for item in results)),
        "capacity_weights": {
            worker.get("id", "unknown"): weight
            for worker, weight in zip(workers, weights)
        },
        "normalized_load_by_worker": {
            worker.get("id", "unknown"): load for worker, load in zip(workers, loads)
        },
        "wall_ms": elapsed_ms,
        "aggregate_tokens": tokens,
        "aggregate_tokens_per_s": tokens / (elapsed_ms / 1000.0) if elapsed_ms else 0.0,
        "latency_ms_p50": percentile(latencies, 0.50),
        "latency_ms_p95": percentile(latencies, 0.95),
        "by_worker": by_worker,
        "results": results,
    }


__all__ = ["run_heterogeneous"]
