"""tests/test_tracera_dual_write_sample.py — v0.13 Phase 1 task 10.

Tests for the v0.13 sample-rate / cohort / per-environment rollout
controls added to `pheno.runtime_config.TraceBridgesConfig` and
`traces.tracera_bridge.TraceraBridge`.

Coverage:

1. `TraceBridgesConfig.from_raw` honors `dual_write_default` and
   `dual_write_sample_rate` from YAML.
2. The `TRACERA_DUAL_WRITE_DEFAULT` env var overrides YAML.
3. The `TRACERA_DUAL_WRITE_SAMPLE_RATE` env var overrides YAML.
4. `active_environment()` selects the active env from `PHENO_ENV`,
   defaulting to "dev" when unset or unknown.
5. `cohort_policies` is filled with canonical keys (dev/staging/prod)
   even when the YAML omits some.
6. `TraceraBridge._sample_rate` resolves in priority order: explicit
   arg > env > config.
7. `TraceraBridge.emit` skips events when sample_rate < 1.0 (random).
8. `TraceraBridge.active_cohort` returns the cohort for the active env.
9. `TraceraBridge.emit` correctly increments `skipped_sample` when an
   event is sampled out.
10. When `dual_write=False`, no sampling happens (events only go to JSONL).

All tests are hermetic: no network calls, no live TraceraAdapter
required (a `MockAdapter` is wired in).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

from pheno.runtime_config import (
    TraceBridgesConfig,
    active_environment,
)
from traces.tracera_bridge import (
    SINK_JSONL,
    SINK_TRACERA,
    TraceraBridge,
)


@dataclass
class MockAdapter:
    """Minimal TraceStoreAdapter mock — records every append_event call."""

    events: list = field(default_factory=list)
    raises: bool = False

    def append_event(self, event):  # noqa: ARG002 - protocol signature
        if self.raises:
            raise RuntimeError("simulated Tracera failure")
        self.events.append(event)
        return event.id

    def query(self, session_id: str) -> list:  # noqa: ARG002 - protocol signature
        return [e for e in self.events if e.session_id == session_id]

    def flush(self) -> None:
        return None

    def health(self) -> dict:
        return {"ok": True, "url": "mock://"}


def _ev(kind: str = "test", sid: str = "s1", **extra):
    """Build a TraceEvent with the dataclass's real signature."""
    from datetime import datetime
    from uuid import uuid4

    from pheno.trace_store import TraceEvent

    return TraceEvent(
        id=uuid4(),
        kind=kind,
        ts=datetime.fromisoformat("2026-08-11T00:00:00+00:00"),
        actor="test",
        target=extra.pop("target", None),
        session_id=sid,
        payload=extra.pop("payload", {}),
    )


# ---------------------------------------------------------------------------
# 1. Config — YAML field parsing
# ---------------------------------------------------------------------------


def test_trace_bridges_config_parses_dual_write_default() -> None:
    raw = {
        "dual_write_default": True,
        "dual_write_sample_rate": 0.5,
        "include_kinds": ["eval_cell"],
    }
    cfg = TraceBridgesConfig.from_raw(raw, active_environment="dev")
    assert cfg.dual_write_default is True
    assert cfg.dual_write_sample_rate == 0.5
    assert cfg.include_kinds == ["eval_cell"]
    # When `dual_write` is omitted, fall back to dual_write_default.
    assert cfg.dual_write is True


def test_trace_bridges_config_explicit_dual_write_wins() -> None:
    raw = {
        "dual_write": False,
        "dual_write_default": True,
    }
    cfg = TraceBridgesConfig.from_raw(raw, active_environment="dev")
    assert cfg.dual_write is False


def test_trace_bridges_config_sample_rate_clamped() -> None:
    raw = {"dual_write_sample_rate": 5.0}
    cfg = TraceBridgesConfig.from_raw(raw)
    assert cfg.dual_write_sample_rate == 1.0

    raw = {"dual_write_sample_rate": -0.3}
    cfg = TraceBridgesConfig.from_raw(raw)
    assert cfg.dual_write_sample_rate == 0.0


def test_trace_bridges_config_cohort_defaults() -> None:
    cfg = TraceBridgesConfig.from_raw({}, active_environment="staging")
    # Canonical keys filled even when YAML omits them.
    assert set(cfg.cohort_policies.keys()) >= {"dev", "staging", "prod"}
    # All defaults are "off" unless overridden.
    assert cfg.cohort_policies["staging"] == "off"


def test_trace_bridges_config_cohort_override() -> None:
    raw = {"cohort_policies": {"dev": "off", "staging": "on", "prod": "on"}}
    cfg = TraceBridgesConfig.from_raw(raw, active_environment="prod")
    assert cfg.cohort_policies["prod"] == "on"
    assert cfg.cohort_policies["staging"] == "on"


def test_trace_bridges_config_active_environment_from_arg() -> None:
    cfg = TraceBridgesConfig.from_raw({}, active_environment="prod")
    assert cfg.active_environment == "prod"


def test_trace_bridges_config_active_environment_default(monkeypatch) -> None:
    monkeypatch.delenv("PHENO_ENV", raising=False)
    cfg = TraceBridgesConfig.from_raw({})
    assert cfg.active_environment == "dev"


def test_trace_bridges_config_env_default_override(monkeypatch) -> None:
    monkeypatch.setenv("TRACERA_DUAL_WRITE_DEFAULT", "true")
    cfg = TraceBridgesConfig.from_raw({}, active_environment="dev")
    assert cfg.dual_write_default is True


def test_trace_bridges_config_env_sample_rate_override(monkeypatch) -> None:
    monkeypatch.setenv("TRACERA_DUAL_WRITE_SAMPLE_RATE", "0.25")
    cfg = TraceBridgesConfig.from_raw({}, active_environment="dev")
    assert cfg.dual_write_sample_rate == 0.25


# ---------------------------------------------------------------------------
# 2. active_environment()
# ---------------------------------------------------------------------------


def test_active_environment_default(monkeypatch) -> None:
    monkeypatch.delenv("PHENO_ENV", raising=False)
    assert active_environment() == "dev"


def test_active_environment_known(monkeypatch) -> None:
    monkeypatch.setenv("PHENO_ENV", "staging")
    assert active_environment() == "staging"


def test_active_environment_unknown_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("PHENO_ENV", "qa-temp")
    assert active_environment() == "dev"


# ---------------------------------------------------------------------------
# 3. Bridge — sample-rate emission
# ---------------------------------------------------------------------------


def _make_bridge(
    tmp_path: Path,
    *,
    adapter: MockAdapter | None = None,
    sample_rate: float | None = None,
    dual_write: bool = True,
    rng: random.Random | None = None,
) -> TraceraBridge:
    return TraceraBridge(
        adapter=adapter if adapter is not None else MockAdapter(),
        jsonl_path=tmp_path / "tr.jsonl",
        dual_write=dual_write,
        sample_rate=sample_rate,
        rng=rng,
    )


def test_bridge_sample_rate_full(tmp_path: Path) -> None:
    adapter = MockAdapter()
    bridge = _make_bridge(
        tmp_path, adapter=adapter, sample_rate=1.0, rng=random.Random(42)
    )
    for _ in range(20):
        bridge.emit(_ev())
    assert bridge.emitted_tracera == 20
    assert bridge.skipped_sample == 0


def test_bridge_sample_rate_zero(tmp_path: Path) -> None:
    adapter = MockAdapter()
    bridge = _make_bridge(
        tmp_path, adapter=adapter, sample_rate=0.0, rng=random.Random(42)
    )
    for _ in range(20):
        bridge.emit(_ev())
    assert bridge.emitted_tracera == 0
    assert bridge.skipped_sample == 20
    # JSONL still received every event (source of truth).
    assert bridge.emitted_jsonl == 20


def test_bridge_sample_rate_half(tmp_path: Path) -> None:
    """With rate=0.5 and 1000 events, sampled events should be ~500 ± tolerance."""
    adapter = MockAdapter()
    bridge = _make_bridge(
        tmp_path, adapter=adapter, sample_rate=0.5, rng=random.Random(0)
    )
    for _ in range(1000):
        bridge.emit(_ev())
    # Tolerance: 5% of 1000 = 50. With rate=0.5 we expect ~500 ± 50.
    assert 400 <= bridge.emitted_tracera <= 600
    assert 400 <= bridge.skipped_sample <= 600
    assert bridge.emitted_tracera + bridge.skipped_sample == 1000


def test_bridge_sample_rate_deterministic_with_seed(tmp_path: Path) -> None:
    """Same RNG seed → same sampling decisions."""
    a = _make_bridge(tmp_path, sample_rate=0.3, rng=random.Random(7))
    b = _make_bridge(tmp_path, sample_rate=0.3, rng=random.Random(7))
    for _ in range(50):
        ev = _ev()
        a.emit(ev)
        b.emit(ev)
    assert a.emitted_tracera == b.emitted_tracera
    assert a.skipped_sample == b.skipped_sample


def test_bridge_dual_write_false_skips_sampling(tmp_path: Path) -> None:
    """When dual_write is off, no events reach the adapter regardless of rate."""
    adapter = MockAdapter()
    bridge = _make_bridge(
        tmp_path,
        adapter=adapter,
        sample_rate=1.0,
        dual_write=False,
        rng=random.Random(0),
    )
    for _ in range(10):
        bridge.emit(_ev())
    assert adapter.events == []
    assert bridge.emitted_tracera == 0
    assert bridge.skipped_sample == 0
    # JSONL still received them.
    assert bridge.emitted_jsonl == 10


def test_bridge_active_cohort_default(tmp_path: Path) -> None:
    """Without an explicit cohort, default is "off"."""
    bridge = _make_bridge(tmp_path, sample_rate=1.0)
    assert bridge.active_cohort() == "off"


def test_bridge_active_cohort_explicit(tmp_path: Path) -> None:
    """Per-env cohort policy propagates through bridge.active_cohort()."""
    from pheno.runtime_config import RuntimeConfig

    cfg = RuntimeConfig(
        path=tmp_path / "cfg.yaml",
        schema_version=2,
        tracera=None,  # type: ignore[arg-type]
        evidence=None,  # type: ignore[arg-type]
        trace_bridges=TraceBridgesConfig.from_raw(
            {"cohort_policies": {"dev": "off", "staging": "on", "prod": "on"}},
            active_environment="prod",
        ),
    )
    bridge = TraceraBridge(
        adapter=MockAdapter(),
        jsonl_path=tmp_path / "tr.jsonl",
        config=cfg,
    )
    assert bridge.active_cohort() == "on"


def test_bridge_env_sample_rate_overrides_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TRACERA_DUAL_WRITE_SAMPLE_RATE", "0.1")
    bridge = _make_bridge(tmp_path, sample_rate=None)
    assert bridge._sample_rate() == 0.1


def test_bridge_explicit_sample_rate_wins(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TRACERA_DUAL_WRITE_SAMPLE_RATE", "0.9")
    bridge = _make_bridge(tmp_path, sample_rate=0.1)
    assert bridge._sample_rate() == 0.1


def test_bridge_sampled_out_emits_hook(tmp_path: Path) -> None:
    seen_sinks: list[str] = []
    bridge = _make_bridge(tmp_path, sample_rate=0.0)
    bridge.add_hook(lambda _ev, sink: seen_sinks.append(sink))
    bridge.emit(_ev())
    # First hook fires for JSONL, second for the sample-skip sink.
    assert seen_sinks == [SINK_JSONL, SINK_TRACERA + ":sampled_out"]
    assert bridge.skipped_sample == 1
