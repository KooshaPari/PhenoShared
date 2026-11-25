"""Tests for Tracera dual-write integration in traces/ingest.py.

v0.12 task 20 (Phase 1 — Tracera dual-write in production path).

The production collect_all() flow is exercised end-to-end with:

- ``dual_write=False`` (default config + no env var) → JSONL only,
  no TraceraAdapter constructed.
- ``dual_write=True`` (config) with a mock TraceraAdapter → both
  backends receive every event.
- ``TRACERA_DUAL_WRITE=1`` env var → forces dual-write ON even when
  the config says off.
- Adapter construction failure → log a warning + fall back to
  JSONL-only mode (fail-soft).

All tests are hermetic: no network, no real Tracera, no real harness
log sources. The TraceCollector source iterators are replaced with
deterministic stubs; the home directory is untouched.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from pheno.trace_store import TraceEvent as BridgeTraceEvent
from traces.ingest import (
    TRACERA_DUAL_WRITE_ENV,
    _build_dual_write_bridge,
    _dual_write_enabled,
    _has_tracera_endpoint,
    _to_bridge_event,
    collect_all,
)
from traces.ingest import (
    TraceEvent as IngestTraceEvent,
)

# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------


class MockAdapter:
    """In-memory TraceStoreAdapter for hermetic tests.

    Records every ``append_event`` call on ``records`` so tests can
    assert which events reached the (mock) backend. Mirrors the
    `tests.test_tracera_bridge.MockAdapter` contract.
    """

    instances: list[MockAdapter] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.records: list[BridgeTraceEvent] = []
        self.append_calls: int = 0
        self.flush_calls: int = 0
        self.construct_args: dict[str, Any] = dict(kwargs)
        # Track every construction for cross-test introspection.
        MockAdapter.instances.append(self)

    def append_event(self, event: BridgeTraceEvent) -> str:
        self.append_calls += 1
        self.records.append(event)
        return str(event.id)

    def query(self, session_id: str) -> list[BridgeTraceEvent]:
        return [r for r in self.records if r.session_id == session_id]

    def flush(self) -> None:
        self.flush_calls += 1

    def health(self) -> dict[str, Any]:
        return {"status": "ok"}


class FailingAdapter:
    """A drop-in for TraceraAdapter whose constructor raises — simulates invalid config."""

    instances: list[FailingAdapter] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        FailingAdapter.instances.append(self)
        raise RuntimeError("simulated TraceraAdapter construction failure")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(
    path: Path, *, dual_write: bool, host: str = "127.0.0.1", port: int = 8080
) -> Path:
    """Write a minimal pheno_runtime.yaml with the given flags."""
    path.write_text(
        "schema_version: 1\n"
        f"trace_bridges:\n"
        f"  dual_write: {str(dual_write).lower()}\n"
        f"  include_kinds: []\n"
        f"tracera:\n"
        f'  host: "{host}"\n'
        f"  port: {port}\n"
        "  base_url: null\n"
        "  api_token: null\n"
        "  enabled: false\n"
        "  flush_interval_s: 30\n"
        "  batch_size: 100\n"
        "  retry_max: 3\n"
        "  health_check_on_init: false\n"
        "  timeout_s: 10\n",
        encoding="utf-8",
    )
    return path


def _stub_event(
    *,
    kind: str = "config_snapshot",
    source: str = "stub",
    session_id: str = "S1",
    harness: str = "stub-harness",
) -> IngestTraceEvent:
    """Deterministic ingest-side TraceEvent for the production path."""
    return IngestTraceEvent(
        source=source,
        event_type=kind,
        timestamp="2026-01-01T00:00:00+00:00",
        tokens_in=11,
        tokens_out=22,
        tokens_cache_read=3,
        duration_ms=123,
        model="stub-model",
        provider="stub-provider",
        harness=harness,
        session_id=session_id,
        motion_hint="forward",
        meta={"k": "v"},
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read all JSONL lines into a list of dicts."""
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _patch_collector_sources(monkeypatch, events: list[IngestTraceEvent]) -> None:
    """Replace ``TraceCollector.all_sources`` with a deterministic stub.

    The stub yields ``events`` in order, ignoring kwargs. This is the
    key to hermetic tests — the production source iterators read from
    paths under the user's home directory, which on the dev
    workstation contain real data.
    """
    from traces.ingest import TraceCollector

    def stub(self: Any, **kwargs: Any):
        yield from events

    monkeypatch.setattr(TraceCollector, "all_sources", stub)


def _reset_runtime_config_cache(monkeypatch, cfg_path: Path) -> None:
    """Point the runtime config loader at ``cfg_path`` and clear its cache.

    ``pheno.runtime_config.load_config`` caches on the path string, so
    we only have to point ``DEFAULT_CONFIG_PATH`` at the new file;
    the cache will rebuild on the next ``load_config()`` call.

    Uses direct module-attribute access (rather than a string path)
    to avoid pytest's monkeypatch attribute-resolution pathway, which
    occasionally fails when other tests in the same session have
    perturbed module globals.
    """
    import pheno.runtime_config as _rc

    monkeypatch.setattr(_rc, "DEFAULT_CONFIG_PATH", cfg_path)
    # Also clear the lru_cache so a different path string from a
    # previous test doesn't leak.
    _rc.reload()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_mock_adapter_state() -> None:
    """Reset the MockAdapter class-level instance list per test."""
    MockAdapter.instances = []
    FailingAdapter.instances = []
    yield
    MockAdapter.instances = []
    FailingAdapter.instances = []


# ---------------------------------------------------------------------------
# 1. dual_write=False: JSONL only, no TraceraAdapter constructed
# ---------------------------------------------------------------------------


class TestDualWriteOff:
    """When dual-write is disabled, ``collect_all`` behaves as before."""

    def test_dual_write_off_default_config_emits_only_jsonl(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Default config (dual_write=False) + no env var → JSONL only."""
        cfg_path = _write_config(tmp_path / "pheno_runtime.yaml", dual_write=False)
        _reset_runtime_config_cache(monkeypatch, cfg_path)

        # Patch TraceraAdapter to a MockAdapter so we can detect construction.
        import pheno.trace_store as _ts

        monkeypatch.setattr(_ts, "TraceraAdapter", MockAdapter)

        event = _stub_event()
        _patch_collector_sources(monkeypatch, [event])

        out_path, n = collect_all(out_dir=tmp_path)

        # JSONL has the event.
        assert n == 1
        assert out_path.exists()
        rows = _read_jsonl(out_path)
        assert len(rows) == 1
        assert rows[0]["event_type"] == "config_snapshot"
        assert rows[0]["session_id"] == "S1"

        # No TraceraAdapter was constructed (no Tracera writes).
        assert MockAdapter.instances == []
        assert len(MockAdapter.instances) == 0

    def test_dual_write_enabled_check_returns_false_when_no_env_no_config(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``_dual_write_enabled()`` is False when config says off and env is unset."""
        cfg_path = _write_config(tmp_path / "pheno_runtime.yaml", dual_write=False)
        _reset_runtime_config_cache(monkeypatch, cfg_path)
        monkeypatch.delenv(TRACERA_DUAL_WRITE_ENV, raising=False)

        assert _dual_write_enabled() is False

    def test_build_bridge_returns_none_when_dual_write_off(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``_build_dual_write_bridge`` returns None when dual-write is off."""
        cfg_path = _write_config(tmp_path / "pheno_runtime.yaml", dual_write=False)
        _reset_runtime_config_cache(monkeypatch, cfg_path)
        import pheno.trace_store as _ts

        monkeypatch.setattr(_ts, "TraceraAdapter", MockAdapter)
        monkeypatch.delenv(TRACERA_DUAL_WRITE_ENV, raising=False)

        bridge = _build_dual_write_bridge(tmp_path / "out.jsonl")
        assert bridge is None
        assert MockAdapter.instances == []


# ---------------------------------------------------------------------------
# 2. dual_write=True with mock TraceraAdapter: both backends receive
# ---------------------------------------------------------------------------


class TestDualWriteOn:
    """When dual-write is enabled, both backends receive every event."""

    def test_dual_write_on_via_config_emits_to_both_backends(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Config says dual_write=True → JSONL + TraceraAdapter both receive.

        When dual-write is enabled, the JSONL is written by the bridge
        using the bridge's ``TraceEvent`` schema (``id`` / ``kind`` /
        ``actor`` / ``target`` / ``session_id`` / ``payload``). The
        legacy ``event_type`` / ``source`` fields are preserved inside
        the bridge's ``payload`` so downstream consumers can still
        read them via the same field names.
        """
        cfg_path = _write_config(tmp_path / "pheno_runtime.yaml", dual_write=True)
        _reset_runtime_config_cache(monkeypatch, cfg_path)

        import pheno.trace_store as _ts

        monkeypatch.setattr(_ts, "TraceraAdapter", MockAdapter)
        monkeypatch.delenv(TRACERA_DUAL_WRITE_ENV, raising=False)

        events = [
            _stub_event(kind="llm_call", session_id="S-a"),
            _stub_event(kind="history_line", session_id="S-b"),
            _stub_event(kind="session_log", session_id="S-c"),
        ]
        _patch_collector_sources(monkeypatch, events)

        out_path, n = collect_all(out_dir=tmp_path)

        # All events went through to JSONL (with bridge schema).
        assert n == 3
        assert out_path.exists()
        rows = _read_jsonl(out_path)
        assert len(rows) == 3
        # Bridge's schema (pheno.trace_store.TraceEvent).
        assert {r["kind"] for r in rows} == {
            "llm_call",
            "history_line",
            "session_log",
        }
        # Legacy fields are preserved in the payload for downstream
        # consumers that prefer the legacy schema.
        assert {r["payload"]["source"] for r in rows} == {"stub"}

        # All events went through to the TraceraAdapter (mock).
        assert len(MockAdapter.instances) == 1
        adapter = MockAdapter.instances[0]
        assert adapter.append_calls == 3
        assert len(adapter.records) == 3
        kinds = {r.kind for r in adapter.records}
        assert kinds == {"llm_call", "history_line", "session_log"}
        # Session ids round-trip.
        assert {r.session_id for r in adapter.records} == {"S-a", "S-b", "S-c"}

    def test_event_id_is_unique_per_emit(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Each emitted bridge event has a unique UUID v4 id."""
        cfg_path = _write_config(tmp_path / "pheno_runtime.yaml", dual_write=True)
        _reset_runtime_config_cache(monkeypatch, cfg_path)
        import pheno.trace_store as _ts

        monkeypatch.setattr(_ts, "TraceraAdapter", MockAdapter)
        monkeypatch.delenv(TRACERA_DUAL_WRITE_ENV, raising=False)

        events = [_stub_event(session_id=f"S-{i}") for i in range(5)]
        _patch_collector_sources(monkeypatch, events)

        collect_all(out_dir=tmp_path)

        adapter = MockAdapter.instances[0]
        ids = [str(r.id) for r in adapter.records]
        assert len(ids) == 5
        assert len(set(ids)) == 5  # all unique

    def test_event_payload_preserves_harness_fields(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Tokens, model, provider, meta, etc. are preserved in payload."""
        cfg_path = _write_config(tmp_path / "pheno_runtime.yaml", dual_write=True)
        _reset_runtime_config_cache(monkeypatch, cfg_path)
        import pheno.trace_store as _ts

        monkeypatch.setattr(_ts, "TraceraAdapter", MockAdapter)
        monkeypatch.delenv(TRACERA_DUAL_WRITE_ENV, raising=False)

        original = IngestTraceEvent(
            source="omniroute",
            event_type="llm_call",
            timestamp="2026-01-01T12:00:00+00:00",
            tokens_in=10,
            tokens_out=20,
            tokens_cache_read=5,
            duration_ms=500,
            model="omniroute-test",
            provider="openai",
            harness="omniroute",
            session_id="S1",
            motion_hint="forward",
            meta={"combo": "x", "extra": 42},
        )
        _patch_collector_sources(monkeypatch, [original])

        collect_all(out_dir=tmp_path)

        adapter = MockAdapter.instances[0]
        record = adapter.records[0]
        assert record.kind == "llm_call"
        assert record.actor == "omniroute"
        assert record.target == "omniroute"
        assert record.session_id == "S1"
        assert record.payload["tokens_in"] == 10
        assert record.payload["tokens_out"] == 20
        assert record.payload["tokens_cache_read"] == 5
        assert record.payload["duration_ms"] == 500
        assert record.payload["model"] == "omniroute-test"
        assert record.payload["provider"] == "openai"
        assert record.payload["motion_hint"] == "forward"
        assert record.payload["meta"] == {"combo": "x", "extra": 42}


# ---------------------------------------------------------------------------
# 3. TRACERA_DUAL_WRITE=1 env override forces dual-write ON
# ---------------------------------------------------------------------------


class TestEnvOverride:
    """``TRACERA_DUAL_WRITE=1`` forces dual-write on, overriding config."""

    def test_env_var_overrides_config_off(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TRACERA_DUAL_WRITE=1 wins over config saying dual_write=False."""
        # Config says OFF.
        cfg_path = _write_config(tmp_path / "pheno_runtime.yaml", dual_write=False)
        _reset_runtime_config_cache(monkeypatch, cfg_path)

        # Env var says ON.
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, "1")
        import pheno.trace_store as _ts

        monkeypatch.setattr(_ts, "TraceraAdapter", MockAdapter)

        event = _stub_event(kind="env_forced_event")
        _patch_collector_sources(monkeypatch, [event])

        out_path, n = collect_all(out_dir=tmp_path)

        # Both backends received the event.
        assert n == 1
        assert out_path.exists()
        rows = _read_jsonl(out_path)
        assert len(rows) == 1
        # Bridge schema: kind/event_type maps to the bridge's "kind".
        assert rows[0]["kind"] == "env_forced_event"

        assert len(MockAdapter.instances) == 1
        adapter = MockAdapter.instances[0]
        assert adapter.append_calls == 1
        assert adapter.records[0].kind == "env_forced_event"

    @pytest.mark.parametrize("truthy", ["1", "true", "TRUE", "yes", "on"])
    def test_truthy_env_values_force_on(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        truthy: str,
    ) -> None:
        """Various truthy values for TRACERA_DUAL_WRITE all force dual-write on."""
        cfg_path = _write_config(tmp_path / "pheno_runtime.yaml", dual_write=False)
        _reset_runtime_config_cache(monkeypatch, cfg_path)
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, truthy)
        import pheno.trace_store as _ts

        monkeypatch.setattr(_ts, "TraceraAdapter", MockAdapter)

        _patch_collector_sources(monkeypatch, [_stub_event()])

        out_path, _ = collect_all(out_dir=tmp_path)

        assert out_path.exists()
        assert len(MockAdapter.instances) == 1
        assert MockAdapter.instances[0].append_calls == 1

    @pytest.mark.parametrize("falsy", ["0", "false", "no", "off", ""])
    def test_falsy_env_values_do_not_force_on(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        falsy: str,
    ) -> None:
        """Falsy values for TRACERA_DUAL_WRITE do NOT force dual-write on."""
        cfg_path = _write_config(tmp_path / "pheno_runtime.yaml", dual_write=False)
        _reset_runtime_config_cache(monkeypatch, cfg_path)
        monkeypatch.setenv(TRACERA_DUAL_WRITE_ENV, falsy)
        import pheno.trace_store as _ts

        monkeypatch.setattr(_ts, "TraceraAdapter", MockAdapter)

        _patch_collector_sources(monkeypatch, [_stub_event()])

        out_path, _ = collect_all(out_dir=tmp_path)

        # JSONL has the event; no TraceraAdapter was constructed.
        assert out_path.exists()
        assert MockAdapter.instances == []


# ---------------------------------------------------------------------------
# 4. Fail-soft: TraceraAdapter construction failure → JSONL only + warning
# ---------------------------------------------------------------------------


class TestFailSoft:
    """When TraceraAdapter construction fails, fall back to JSONL only."""

    def test_adapter_construction_failure_falls_back_to_jsonl(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """If TraceraAdapter.__init__ raises, ingest still writes JSONL."""
        cfg_path = _write_config(tmp_path / "pheno_runtime.yaml", dual_write=True)
        _reset_runtime_config_cache(monkeypatch, cfg_path)
        monkeypatch.delenv(TRACERA_DUAL_WRITE_ENV, raising=False)

        # Replace TraceraAdapter with a class that raises on construction.
        import pheno.trace_store as _ts

        monkeypatch.setattr(_ts, "TraceraAdapter", FailingAdapter)

        _patch_collector_sources(monkeypatch, [_stub_event()])

        with caplog.at_level(logging.WARNING, logger="traces.ingest"):
            out_path, n = collect_all(out_dir=tmp_path)

        # JSONL still has the event.
        assert n == 1
        assert out_path.exists()
        rows = _read_jsonl(out_path)
        assert len(rows) == 1

        # A warning was logged with the failure reason.
        assert any(
            "TraceraAdapter construction failed" in rec.message
            for rec in caplog.records
        )

    def test_no_usable_endpoint_falls_back_to_jsonl(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When the TraceraConfig has no usable host, fall back to JSONL.

        Direct unit test of ``_build_dual_write_bridge``: the YAML
        runtime config's ``host`` field defaults to ``127.0.0.1`` via
        an env var fallback, so reproducing the "no host" case via
        YAML alone is brittle. Instead, we patch the runtime config
        loader to return a config whose host is None and assert
        that the bridge-build helper bails out + logs a warning.
        """
        from pheno.runtime_config import (
            EvidenceConfig,
            RuntimeConfig,
            TraceBridgesConfig,
            TraceraConfig,
        )

        cfg = RuntimeConfig(
            path=tmp_path / "pheno_runtime.yaml",
            schema_version=1,
            tracera=TraceraConfig(
                host=None,  # type: ignore[arg-type]
                port=8080,
                base_url=None,
                api_token=None,
                enabled=True,
                flush_interval_s=30,
                batch_size=100,
                retry_max=3,
                health_check_on_init=True,
                timeout_s=10,
            ),
            evidence=EvidenceConfig(
                base_url=None,
                rate_limit_per_min=60,
                circuit_breaker_threshold=5,
            ),
            trace_bridges=TraceBridgesConfig(
                dual_write=True,
                dual_write_default=True,
                dual_write_sample_rate=1.0,
                include_kinds=[],
                cohort_policies={"dev": "on", "staging": "off", "prod": "off"},
                env_overrides={
                    "dev": "config/dev.yaml",
                    "staging": "config/staging.yaml",
                    "prod": "config/prod.yaml",
                },
                active_environment="dev",
            ),
        )
        import pheno.runtime_config as _rc

        monkeypatch.setattr(_rc, "load_config", lambda: cfg)
        monkeypatch.delenv(TRACERA_DUAL_WRITE_ENV, raising=False)

        with caplog.at_level(logging.WARNING, logger="traces.ingest"):
            bridge = _build_dual_write_bridge(tmp_path / "out.jsonl")

        assert bridge is None
        assert any("no usable host/port" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# 5. Helper unit tests
# ---------------------------------------------------------------------------


class TestHelpers:
    """Direct unit tests for the helper functions."""

    def test_to_bridge_event_field_mapping(self) -> None:
        """Verify the traces.ingest → pheno.trace_store field mapping."""
        ingest_ev = IngestTraceEvent(
            source="codex",
            event_type="agent_job",
            timestamp="2026-02-01T03:04:05+00:00",
            tokens_in=7,
            tokens_out=9,
            tokens_cache_read=2,
            duration_ms=400,
            model="codex-spark",
            provider="openai",
            harness="agent_runner",
            session_id="job-42",
            motion_hint="forward",
            meta={"state": "completed"},
        )
        bridge_ev = _to_bridge_event(ingest_ev)

        assert isinstance(bridge_ev, BridgeTraceEvent)
        assert bridge_ev.kind == "agent_job"
        assert bridge_ev.actor == "codex"
        assert bridge_ev.target == "agent_runner"
        assert bridge_ev.session_id == "job-42"
        assert bridge_ev.ts == datetime(2026, 2, 1, 3, 4, 5, tzinfo=UTC)
        # Payload round-trip.
        assert bridge_ev.payload["source"] == "codex"
        assert bridge_ev.payload["tokens_in"] == 7
        assert bridge_ev.payload["tokens_out"] == 9
        assert bridge_ev.payload["tokens_cache_read"] == 2
        assert bridge_ev.payload["duration_ms"] == 400
        assert bridge_ev.payload["model"] == "codex-spark"
        assert bridge_ev.payload["provider"] == "openai"
        assert bridge_ev.payload["motion_hint"] == "forward"
        assert bridge_ev.payload["meta"] == {"state": "completed"}

    def test_to_bridge_event_handles_empty_timestamp(self) -> None:
        """Empty timestamp falls back to ``datetime.now(UTC)``."""
        ingest_ev = IngestTraceEvent(
            source="x",
            event_type="y",
            timestamp="",
            session_id="S",
        )
        before = datetime.now(UTC)
        bridge_ev = _to_bridge_event(ingest_ev)
        after = datetime.now(UTC)
        assert before <= bridge_ev.ts <= after

    def test_to_bridge_event_handles_z_suffix(self) -> None:
        """'Z' suffix is normalized to '+00:00' for fromisoformat."""
        ingest_ev = IngestTraceEvent(
            source="x",
            event_type="y",
            timestamp="2026-03-01T00:00:00Z",
        )
        bridge_ev = _to_bridge_event(ingest_ev)
        assert bridge_ev.ts == datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)

    def test_has_tracera_endpoint_valid(self) -> None:
        """A populated host + port is treated as a valid endpoint."""
        from pheno.runtime_config import TraceraConfig

        cfg = TraceraConfig(
            host="127.0.0.1",
            port=8080,
            base_url=None,
            api_token=None,
            enabled=True,
            flush_interval_s=30,
            batch_size=100,
            retry_max=3,
            health_check_on_init=True,
            timeout_s=10,
        )

        class _Stub:
            tracera = cfg

        assert _has_tracera_endpoint(_Stub()) is True

    def test_has_tracera_endpoint_empty_host(self) -> None:
        """Empty host is treated as no endpoint."""
        from pheno.runtime_config import TraceraConfig

        cfg = TraceraConfig(
            host="",
            port=8080,
            base_url=None,
            api_token=None,
            enabled=True,
            flush_interval_s=30,
            batch_size=100,
            retry_max=3,
            health_check_on_init=True,
            timeout_s=10,
        )

        class _Stub:
            tracera = cfg

        assert _has_tracera_endpoint(_Stub()) is False

    def test_has_tracera_endpoint_zero_port(self) -> None:
        """Port 0 is treated as no endpoint."""
        from pheno.runtime_config import TraceraConfig

        cfg = TraceraConfig(
            host="127.0.0.1",
            port=0,
            base_url=None,
            api_token=None,
            enabled=True,
            flush_interval_s=30,
            batch_size=100,
            retry_max=3,
            health_check_on_init=True,
            timeout_s=10,
        )

        class _Stub:
            tracera = cfg

        assert _has_tracera_endpoint(_Stub()) is False

    def test_to_bridge_event_uuid_is_unique(self) -> None:
        """Two conversions produce two distinct event ids."""
        ingest_ev = IngestTraceEvent(
            source="x", event_type="y", timestamp="2026-01-01T00:00:00+00:00"
        )
        ev1 = _to_bridge_event(ingest_ev)
        ev2 = _to_bridge_event(ingest_ev)
        assert ev1.id != ev2.id
