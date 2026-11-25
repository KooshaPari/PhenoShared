"""tests/test_tracera_bridge_thread_safety.py — v0.13 Phase 6 concurrency.

Exercises the TraceraBridge under concurrent emission from multiple
threads. Validates:
1. emitted_total matches actual emission count under concurrency.
2. Public counters never go negative under race.
3. emitted_total is monotonically non-decreasing across snapshots.
4. metrics.BridgeMetrics is frozen.
"""

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from pheno.trace_store.protocols import TraceEvent
from traces.metrics import BridgeMetrics
from traces.tracera_bridge import TraceraBridge


def _minimal_bridge(jsonl_path: Path | None = None) -> TraceraBridge:
    """Construct a TraceraBridge with safe defaults (no live Tracera)."""
    return TraceraBridge(
        dual_write=False,
        jsonl_path=jsonl_path,
        sample_rate=1.0,
    )


def _emit(bridge: TraceraBridge, **kwargs) -> None:
    bridge.emit(
        TraceEvent(
            id=uuid4(),
            kind=kwargs.get("kind", "claim"),
            ts=datetime.now(UTC),
            actor=kwargs.get("actor", "agent-a"),
            target="target-x",
            payload=kwargs.get("payload", {"x": 1}),
        )
    )


def test_concurrent_emit_counts_match(tmp_path: Path) -> None:
    """50 emits across 10 threads increment emitted_total by exactly 50."""
    bridge = _minimal_bridge(jsonl_path=tmp_path / "sink.jsonl")
    n_threads = 10
    n_per_thread = 5

    def emit_n() -> None:
        for _ in range(n_per_thread):
            _emit(bridge)

    threads = [threading.Thread(target=emit_n) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert bridge.emitted_total == n_threads * n_per_thread


def test_no_negative_counters_under_concurrency(tmp_path: Path) -> None:
    """Counters never go negative when many threads emit at once."""
    bridge = _minimal_bridge(jsonl_path=tmp_path / "sink.jsonl")
    n_threads = 20

    def emit_many() -> None:
        for i in range(50):
            _emit(bridge, payload={"x": i})

    threads = [threading.Thread(target=emit_many) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert bridge.emitted_total >= 0
    assert bridge.emitted_jsonl >= 0
    assert bridge.emitted_tracera >= 0


def test_emitted_total_is_monotonic(tmp_path: Path) -> None:
    """Two consecutive emit runs show non-decreasing emitted_total."""
    bridge = _minimal_bridge(jsonl_path=tmp_path / "sink.jsonl")
    for _ in range(10):
        _emit(bridge)
    after_first = bridge.emitted_total
    for _ in range(10):
        _emit(bridge)
    after_second = bridge.emitted_total
    assert after_second >= after_first
    assert after_second == after_first + 10


def test_bridge_metrics_dataclass_is_frozen() -> None:
    """BridgeMetrics is a frozen dataclass (immutable)."""
    snap = BridgeMetrics(
        events_total=10,
        events_jsonl=10,
        events_tracera=10,
        events_skipped_kind=0,
        events_skipped_sample=0,
        errors_tracera=0,
    )
    with pytest.raises(FrozenInstanceError):
        snap.events_total = 999  # type: ignore[misc]
