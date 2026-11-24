"""Concurrent task execution for the runner.

Provides two layers:

* `BoundedSemaphore`: a small `asyncio.Semaphore` wrapper with `async with`-and
  explicit `release()` semantics used by the executor's fan-out loop.
* `ParallelRunner`: wraps `asyncio` with a `ThreadPoolExecutor` for adapter
  calls that prefer the synchronous API (Anthropic, OpenAI sync clients, MLX,
  vLLM). Default worker count is `min(8, cpu_count())` per spec rule §1.

The module deliberately avoids any third-party asyncio libraries so it remains
importable under the minimal harness environment.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, TypeVar

T = TypeVar("T")


def default_workers() -> int:
    """Return the default `--workers` value: `min(8, cpu_count)`.

    Falls back to `4` if `cpu_count()` returns `None` (POSIX edge cases).
    """
    cpu = os.cpu_count() or 4
    return max(1, min(8, cpu))


@dataclass
class ParallelStats:
    """Lightweight counters captured per run for telemetry."""

    submitted: int = 0
    completed: int = 0
    failed: int = 0
    timed_out: int = 0
    wall_clock_s: float = 0.0
    peak_inflight: int = 0

    def as_dict(self) -> dict[str, int | float]:
        """Return a JSON-serializable snapshot for inclusion in the RunReport."""
        return {
            "submitted": self.submitted,
            "completed": self.completed,
            "failed": self.failed,
            "timed_out": self.timed_out,
            "wall_clock_s": self.wall_clock_s,
            "peak_inflight": self.peak_inflight,
        }


class TaskTimeoutError(RuntimeError):
    """Raised when a single task exceeds the per-task deadline (spec rule §2)."""


@asynccontextmanager
async def bounded(limit: int) -> AsyncIterator[Any]:
    """Context manager wrapping `asyncio.Semaphore(limit)` with tracking hook."""
    sem = asyncio.Semaphore(limit)
    inflight = 0
    peak = 0

    class _Tracker:
        async def acquire(self) -> None:
            """Acquire the semaphore and bump the inflight + peak counters."""
            nonlocal inflight, peak
            await sem.acquire()
            inflight += 1
            peak = max(peak, inflight)

        def release(self) -> None:
            """Release the semaphore and decrement the inflight counter."""
            nonlocal inflight
            sem.release()
            inflight = max(0, inflight - 1)

        @property
        def peak(self) -> int:
            """Return the highest observed concurrent inflight count."""
            return peak

    tr = _Tracker()
    try:
        yield tr
    finally:
        # Drain anything still holding (best-effort; should be empty in normal use).
        for _ in range(inflight):
            sem.release()


@dataclass
class ParallelRunner:
    """Run coroutine tasks concurrently with optional sync backing.

    Attributes:
        workers: Maximum number of in-flight tasks (== `--workers`).
        per_task_timeout_s: Per-task deadline in seconds (spec rule §2, default 600s).
        thread_pool: Optional `ThreadPoolExecutor` for adapters that need a
            sync bridge. If omitted a fresh pool sized to `workers` is created
            for the lifetime of one `run()` call.
    """

    workers: int = field(default_factory=default_workers)
    per_task_timeout_s: float = 600.0
    thread_pool_factory: Callable[[int], ThreadPoolExecutor] | None = None

    async def run(
        self,
        items: Sequence[Any],
        async_fn: Callable[[Any], Awaitable[T]],
        *,
        on_done: Callable[[T | Exception, Any], None] | None = None,
    ) -> tuple[list[T | Exception], ParallelStats]:
        """Fan out `async_fn(item)` for every element in `items`.

        Returns a tuple of (results_in_same_order, stats). If a task errors
        (including timeouts) its slot is the raised exception object so callers
        can decide whether to mark the corresponding `TaskResult` as ERROR or
        TIMEOUT. Items that never get a slot fail-soft via `TimeoutError`.
        """
        stats = ParallelStats(submitted=len(items))
        results: list[T | Exception] = [TaskTimeoutError("unstarted") for _ in items]
        if not items:
            return results, stats

        sem = asyncio.Semaphore(self.workers)
        # Limit inflight tasks; record peak.
        live = 0
        peak = 0

        async def _wrap(idx: int, item: Any) -> None:
            nonlocal live, peak
            await sem.acquire()
            live += 1
            peak = max(peak, live)
            started = time.monotonic()
            try:
                value = await asyncio.wait_for(
                    async_fn(item), timeout=self.per_task_timeout_s
                )
            except TimeoutError:
                stats.timed_out += 1
                results[idx] = TaskTimeoutError(
                    f"task timeout after {self.per_task_timeout_s:.1f}s"
                )
                if on_done:
                    try:
                        on_done(results[idx], item)
                    except Exception:  # nosec B110
                        pass
            except Exception as exc:  # noqa: BLE001 — we surface every failure
                stats.failed += 1
                results[idx] = exc
                if on_done:
                    try:
                        on_done(exc, item)
                    except Exception:  # nosec B110
                        pass
            else:
                results[idx] = value
                stats.completed += 1
                if on_done:
                    try:
                        on_done(value, item)
                    except Exception:  # nosec B110
                        pass
            finally:
                stats.wall_clock_s = max(stats.wall_clock_s, time.monotonic() - started)
                live = max(0, live - 1)
                sem.release()

        tasks = [
            asyncio.create_task(_wrap(i, it), name=f"bench-task-{i}")
            for i, it in enumerate(items)
        ]
        t0 = time.monotonic()
        await asyncio.gather(*tasks, return_exceptions=False)
        stats.wall_clock_s = time.monotonic() - t0
        stats.peak_inflight = peak
        return results, stats

    async def run_sync(
        self,
        items: Sequence[Any],
        sync_fn: Callable[[Any], T],
        *,
        executor: ThreadPoolExecutor | None = None,
    ) -> list[T | Exception]:
        """Run a synchronous callable concurrently in a `ThreadPoolExecutor`.

        The executor is created per call unless supplied. This is the path used
        for adapters that wrap a sync SDK (Anthropic Python client, OpenAI,
        MLX) so the asyncio loop never blocks on a sync `requests`-style call.
        """
        if not items:
            return []
        own = executor is None
        pool = executor or ThreadPoolExecutor(
            max_workers=self.workers,
            thread_name_prefix="bench-runner-sync",
        )
        loop = asyncio.get_running_loop()

        async def _wrap(item: Any) -> T | Exception:
            try:
                return await loop.run_in_executor(pool, sync_fn, item)
            except Exception as exc:  # noqa: BLE001
                return exc

        results = await asyncio.gather(*(_wrap(it) for it in items))
        if own:
            pool.shutdown(wait=True)
        return list(results)


async def gather_with_progress[T](
    coros: Iterable[Awaitable[T]],
    *,
    every: int = 16,
    on_tick: Callable[[int], None] | None = None,
) -> list[T]:
    """`asyncio.gather` wrapper that calls `on_tick` every `every` completions.

    Lightweight progress hook for callers that don't want a full `rich.Progress`
    bar but still want a heartbeat (the `console.py` module owns richer UX).
    """
    tasks: list[asyncio.Task[T]] = [
        asyncio.create_task(c)  # type: ignore[arg-type]
        for c in coros
    ]
    total = len(tasks)
    results: list[T | None] = [None] * total
    remaining = total

    async def _wait(i: int) -> None:
        nonlocal remaining
        results[i] = await tasks[i]
        remaining -= 1
        if on_tick and remaining > 0 and (remaining % every == 0):
            try:
                on_tick(remaining)
            except Exception:  # nosec B110
                pass

    await asyncio.gather(*(_wait(i) for i in range(total)))
    return [r for r in results if r is not None]  # all slots filled by gather
