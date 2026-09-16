"""tests/test_tracera_metrics.py — v0.13 Phase 1 tasks 17 + 18.

Tests for `traces.metrics`:

- `snapshot(bridge)` captures an immutable `BridgeMetrics` from a bridge.
- `alert_error_rate(bridge)` returns a dict with `alert_fired`,
  `error_rate`, `threshold`, `samples`, `severity`, plus pass-through
  counters. Severity ladder: ok / warn / critical.
- `to_prometheus(metrics)` produces Prometheus text format with the
  canonical counters + the `error_rate` gauge labeled with severity.

All tests are hermetic: a `MockAdapter` is wired in; no network calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pheno.trace_store import TraceEvent
from traces.metrics import (
    DEFAULT_ERROR_RATE_THRESHOLD,
    BridgeMetrics,
    alert_error_rate,
    snapshot,
    to_prometheus,
)
from traces.tracera_bridge import TraceraBridge


@dataclass
class MockAdapter:
    """Records every append_event call. Raises on demand for error-rate tests."""

    events: list = field(default_factory=list)
    raises: bool = False

    def append_event(self, event):
        if self.raises:
            raise RuntimeError("simulated Tracera failure")
        self.events.append(event)
        return event.id

    def query(self, session_id: str):
        return [e for e in self.events if e.session_id == session_id]

    def flush(self) -> None:
        return None

    def health(self) -> dict:
        return {"ok": True, "url": "mock://"}


def _ev(kind: str = "test", sid: str = "s1"):
    return TraceEvent(
        id=uuid4(),
        kind=kind,
        ts=datetime.fromisoformat("2026-08-11T00:00:00+00:00"),
        actor="test",
        target=None,
        session_id=sid,
        payload={},
    )


def _bridge(tmp_path: Path, *, raises: bool = False, sample_rate: float = 1.0):
    return TraceraBridge(
        adapter=MockAdapter(raises=raises),
        jsonl_path=tmp_path / "tr.jsonl",
        dual_write=True,
        sample_rate=sample_rate,
    )


# ---------------------------------------------------------------------------
# snapshot()
# ---------------------------------------------------------------------------


def test_snapshot_zero_state(tmp_path: Path) -> None:
    bridge = _bridge(tmp_path)
    metrics = snapshot(bridge)
    assert isinstance(metrics, BridgeMetrics)
    assert metrics.events_total == 0
    assert metrics.events_jsonl == 0
    assert metrics.events_tracera == 0
    assert metrics.events_skipped_kind == 0
    assert metrics.events_skipped_sample == 0
    assert metrics.errors_tracera == 0
    assert metrics.tracera_attempts == 0
    assert metrics.error_rate == 0.0


def test_snapshot_captures_after_emit(tmp_path: Path) -> None:
    bridge = _bridge(tmp_path)
    for _ in range(5):
        bridge.emit(_ev())
    metrics = snapshot(bridge)
    assert metrics.events_total == 5
    assert metrics.events_jsonl == 5
    assert metrics.events_tracera == 5
    assert metrics.tracera_attempts == 5
    assert metrics.error_rate == 0.0


def test_snapshot_includes_sample_skips(tmp_path: Path) -> None:
    bridge = _bridge(tmp_path, sample_rate=0.0)
    for _ in range(10):
        bridge.emit(_ev())
    metrics = snapshot(bridge)
    assert metrics.events_jsonl == 10
    assert metrics.events_tracera == 0
    assert metrics.events_skipped_sample == 10
    assert metrics.tracera_attempts == 10  # sample-skips count


def test_snapshot_includes_errors(tmp_path: Path) -> None:
    bridge = _bridge(tmp_path, raises=True)
    for _ in range(4):
        bridge.emit(_ev())
    metrics = snapshot(bridge)
    assert metrics.events_total == 4
    assert metrics.events_jsonl == 4
    assert metrics.errors_tracera == 4
    assert metrics.error_rate == 1.0


def test_snapshot_is_immutable() -> None:
    metrics = BridgeMetrics(
        events_total=1,
        events_jsonl=1,
        events_tracera=1,
        events_skipped_kind=0,
        events_skipped_sample=0,
        errors_tracera=0,
    )
    # frozen=True rejects assignment
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        metrics.events_total = 99  # type: ignore[misc]


def test_snapshot_to_dict_includes_error_rate(tmp_path: Path) -> None:
    bridge = _bridge(tmp_path)
    bridge.emit(_ev())
    bridge.emit(_ev())
    d = snapshot(bridge).to_dict()
    assert set(d.keys()) >= {
        "events_total",
        "events_jsonl",
        "events_tracera",
        "events_skipped_kind",
        "events_skipped_sample",
        "errors_tracera",
        "tracera_attempts",
        "error_rate",
    }
    assert d["events_total"] == 2
    assert d["error_rate"] == 0.0


# ---------------------------------------------------------------------------
# alert_error_rate()
# ---------------------------------------------------------------------------


def test_alert_no_attempts_returns_ok(tmp_path: Path) -> None:
    bridge = _bridge(tmp_path)
    alert = alert_error_rate(bridge)
    assert alert["alert_fired"] is False
    assert alert["severity"] == "ok"
    assert alert["error_rate"] == 0.0
    assert alert["samples"] == 0
    assert alert["threshold"] == DEFAULT_ERROR_RATE_THRESHOLD


def test_alert_below_threshold_returns_ok(tmp_path: Path) -> None:
    bridge = _bridge(tmp_path)
    for _ in range(100):
        bridge.emit(_ev())
    alert = alert_error_rate(bridge)
    assert alert["alert_fired"] is False
    assert alert["severity"] == "ok"
    assert alert["error_rate"] == 0.0
    assert alert["samples"] == 100


def test_alert_above_threshold_returns_warn(tmp_path: Path) -> None:
    """When error rate is between threshold and 2*threshold, severity = warn."""
    # ~7% error rate: above 5% threshold but below 10% (2x threshold).
    bridge = TraceraBridge(
        adapter=_flaky_adapter(error_every=14),  # 1/14 ≈ 7.1%
        jsonl_path=tmp_path / "tr.jsonl",
        dual_write=True,
    )
    for _ in range(140):
        bridge.emit(_ev())
    alert = alert_error_rate(bridge, threshold=0.05)
    # 10 errors / 140 attempts ≈ 7.1% → warn
    assert alert["alert_fired"] is True
    assert alert["severity"] == "warn"
    assert alert["error_rate"] == pytest.approx(10 / 140, abs=1e-6)


def test_alert_at_2x_threshold_returns_critical(tmp_path: Path) -> None:
    bridge = _bridge(tmp_path, raises=True)
    for _ in range(20):
        bridge.emit(_ev())
    alert = alert_error_rate(bridge, threshold=0.05)
    assert alert["alert_fired"] is True
    assert alert["severity"] == "critical"
    assert alert["error_rate"] == 1.0


def test_alert_custom_threshold(tmp_path: Path) -> None:
    """Operators can tighten the threshold for prod."""
    bridge = TraceraBridge(
        adapter=_flaky_adapter(error_every=5),  # 20% error rate
        jsonl_path=tmp_path / "tr.jsonl",
        dual_write=True,
    )
    for _ in range(50):
        bridge.emit(_ev())
    # 10 errors / 50 attempts = 0.20. With threshold 0.05, severity = critical
    # because 0.20 >= 2*0.05 = 0.10.
    alert = alert_error_rate(bridge, threshold=0.05)
    assert alert["alert_fired"] is True
    assert alert["severity"] == "critical"


# ---------------------------------------------------------------------------
# to_prometheus()
# ---------------------------------------------------------------------------


def test_prometheus_contains_all_counters() -> None:
    metrics = BridgeMetrics(
        events_total=100,
        events_jsonl=100,
        events_tracera=80,
        events_skipped_kind=10,
        events_skipped_sample=5,
        errors_tracera=5,
    )
    out = to_prometheus(metrics)
    assert "tracera_bridge_events_total 100" in out
    assert "tracera_bridge_events_jsonl 100" in out
    assert "tracera_bridge_events_tracera 80" in out
    assert "tracera_bridge_events_skipped_kind 10" in out
    assert "tracera_bridge_events_skipped_sample 5" in out
    assert "tracera_bridge_errors_tracera 5" in out


def test_prometheus_error_rate_gauge() -> None:
    metrics = BridgeMetrics(
        events_total=10,
        events_jsonl=10,
        events_tracera=9,
        events_skipped_kind=0,
        events_skipped_sample=0,
        errors_tracera=1,
    )
    out = to_prometheus(metrics)
    # 1 error / (9 + 0 + 0 + 1) attempts = 0.1
    assert re.search(
        r'tracera_bridge_error_rate\{severity="computed"\} 0\.1+\d*', out
    ), f"error_rate gauge not found in:\n{out}"


def test_prometheus_custom_prefix() -> None:
    metrics = BridgeMetrics(0, 0, 0, 0, 0, 0)
    out = to_prometheus(metrics, prefix="myapp_tracera_")
    assert "myapp_tracera_events_total" in out


def test_prometheus_has_help_and_type_lines() -> None:
    metrics = BridgeMetrics(0, 0, 0, 0, 0, 0)
    out = to_prometheus(metrics)
    assert "# HELP tracera_bridge_events_total" in out
    assert "# TYPE tracera_bridge_events_total counter" in out
    assert "# TYPE tracera_bridge_error_rate gauge" in out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _FlakyAdapter:
    """Adapter that raises every Nth call to test error-rate alert ladder."""

    error_every: int
    events: list = field(default_factory=list)
    counter: int = 0

    def append_event(self, event):
        self.counter += 1
        if self.counter % self.error_every == 0:
            raise RuntimeError("flaky")
        self.events.append(event)
        return event.id

    def query(self, session_id: str):
        return [e for e in self.events if e.session_id == session_id]

    def flush(self) -> None:
        return None

    def health(self) -> dict:
        return {"ok": True, "url": "mock://"}


def _flaky_adapter(*, error_every: int) -> _FlakyAdapter:
    return _FlakyAdapter(error_every=error_every)


import pytest  # noqa: E402  (pytest import at module bottom for fixture use)
