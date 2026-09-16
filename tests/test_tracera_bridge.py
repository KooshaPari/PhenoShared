"""Tests for traces.tracera_bridge — TraceraBridge dual-write bridge.

v0.12 task 16 (Phase 1 — Tracera dual-write bridge). All tests use
hermetic mocks (no network, no real Tracera). The bridge is wired
through a `MockAdapter` that records `append_event` calls so we can
assert what reached the backend.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from pheno.trace_store import TraceEvent
from pheno.trace_store.protocols import TraceStoreError
from traces.tracera_bridge import (
    SINK_JSONL,
    SINK_TRACERA,
    TraceraBridge,
    install_bridge,
)

# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------


class MockAdapter:
    """In-memory TraceStoreAdapter for hermetic tests.

    Records every append_event call on `mock.records` so tests can
    assert which events reached the backend. Optional `raise_on_append`
    simulates an unreachable Tracera server.
    """

    def __init__(self, *, raise_on_append: bool = False) -> None:
        self.records: list[TraceEvent] = []
        self.flush_calls: int = 0
        self.raise_on_append = raise_on_append
        self.is_healthy: bool = True

    def append_event(self, event: TraceEvent) -> str:
        if self.raise_on_append:
            raise TraceStoreError("mock: backend unreachable")
        self.records.append(event)
        return str(event.id)

    def query(self, session_id: str) -> list[TraceEvent]:
        return [r for r in self.records if r.session_id == session_id]

    def flush(self) -> None:
        self.flush_calls += 1

    def health(self) -> dict[str, Any]:
        return {"status": "ok" if self.is_healthy else "down"}


def _make_event(
    *,
    kind: str = "claim",
    actor: str = "agent-test",
    session_id: str = "session-1",
    payload: dict[str, Any] | None = None,
) -> TraceEvent:
    """Helper to build a deterministic TraceEvent."""
    return TraceEvent.make(
        kind=kind,
        actor=actor,
        session_id=session_id,
        payload=payload or {"score": 0.5},
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read all JSONL lines into a list of dicts."""
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def jsonl_path(tmp_path: Path) -> Path:
    """Provide a fresh JSONL sink path for each test."""
    return tmp_path / "traces.jsonl"


@pytest.fixture
def reachable_adapter() -> MockAdapter:
    """A mock TraceraAdapter that accepts append_event calls."""
    return MockAdapter(raise_on_append=False)


@pytest.fixture
def unreachable_adapter() -> MockAdapter:
    """A mock TraceraAdapter that raises TraceStoreError on append_event."""
    return MockAdapter(raise_on_append=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDualWriteTrue:
    """dual_write=True: both backends receive the event."""

    def test_event_reaches_both_jsonl_and_tracera(
        self, jsonl_path: Path, reachable_adapter: MockAdapter
    ) -> None:
        bridge = TraceraBridge(
            adapter=reachable_adapter,
            jsonl_path=jsonl_path,
            dual_write=True,
        )
        event = _make_event(kind="claim", session_id="S1")
        bridge.emit(event)

        # --- JSONL assertion ---
        rows = _read_jsonl(jsonl_path)
        assert len(rows) == 1
        assert rows[0]["kind"] == "claim"
        assert rows[0]["session_id"] == "S1"
        assert rows[0]["id"] == str(event.id)

        # --- Tracera assertion ---
        assert len(reachable_adapter.records) == 1
        assert reachable_adapter.records[0].id == event.id
        assert reachable_adapter.records[0].kind == "claim"

        # --- Counters ---
        assert bridge.emitted_total == 1
        assert bridge.emitted_jsonl == 1
        assert bridge.emitted_tracera == 1
        assert bridge.tracera_errors == 0

    def test_multiple_events_dual_write(
        self, jsonl_path: Path, reachable_adapter: MockAdapter
    ) -> None:
        bridge = TraceraBridge(
            adapter=reachable_adapter,
            jsonl_path=jsonl_path,
            dual_write=True,
        )
        for i in range(3):
            bridge.emit(_make_event(kind="trace", session_id=f"S{i}"))

        rows = _read_jsonl(jsonl_path)
        assert len(rows) == 3
        assert len(reachable_adapter.records) == 3
        assert bridge.emitted_total == 3
        assert bridge.emitted_tracera == 3


class TestDualWriteFalse:
    """dual_write=False: only JSONL gets the event."""

    def test_event_reaches_only_jsonl(
        self, jsonl_path: Path, reachable_adapter: MockAdapter
    ) -> None:
        bridge = TraceraBridge(
            adapter=reachable_adapter,
            jsonl_path=jsonl_path,
            dual_write=False,
        )
        event = _make_event(kind="evidence", session_id="S2")
        bridge.emit(event)

        # JSONL has the event.
        rows = _read_jsonl(jsonl_path)
        assert len(rows) == 1
        assert rows[0]["kind"] == "evidence"

        # Tracera adapter is NOT touched.
        assert reachable_adapter.records == []
        assert bridge.emitted_jsonl == 1
        assert bridge.emitted_tracera == 0
        assert bridge.tracera_errors == 0


class TestAdapterUnreachable:
    """When the adapter raises: JSONL still receives the event, error logged."""

    def test_unreachable_adapter_does_not_break_emit(
        self,
        jsonl_path: Path,
        unreachable_adapter: MockAdapter,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        bridge = TraceraBridge(
            adapter=unreachable_adapter,
            jsonl_path=jsonl_path,
            dual_write=True,
        )
        event = _make_event(kind="trace", session_id="S3")

        with caplog.at_level(logging.ERROR, logger="traces.tracera_bridge"):
            # Must NOT raise — fail-soft semantics.
            bridge.emit(event)

        # JSONL still got the event.
        rows = _read_jsonl(jsonl_path)
        assert len(rows) == 1
        assert rows[0]["kind"] == "trace"
        assert rows[0]["session_id"] == "S3"

        # Tracera recorded the error but didn't crash the emit.
        assert bridge.emitted_jsonl == 1
        assert bridge.emitted_tracera == 0
        assert bridge.tracera_errors == 1

        # The error was logged with the event id.
        assert any("mock: backend unreachable" in rec.message for rec in caplog.records)
        assert any(str(event.id) in rec.message for rec in caplog.records)


class TestIncludeKindsFilter:
    """include_kinds: events with non-matching kind are skipped on Tracera."""

    def test_kind_not_in_include_kinds_skipped_on_tracera(
        self, jsonl_path: Path, reachable_adapter: MockAdapter
    ) -> None:
        bridge = TraceraBridge(
            adapter=reachable_adapter,
            jsonl_path=jsonl_path,
            dual_write=True,
            include_kinds=["wandb_step", "eval_cell"],
        )

        # This kind is NOT in include_kinds → Tracera skip.
        skipped_event = _make_event(kind="trace", session_id="S")
        bridge.emit(skipped_event)

        # This kind IS in include_kinds → Tracera receives.
        keep_event = _make_event(kind="wandb_step", session_id="S")
        bridge.emit(keep_event)

        # JSONL gets both.
        rows = _read_jsonl(jsonl_path)
        assert len(rows) == 2
        assert {r["kind"] for r in rows} == {"trace", "wandb_step"}

        # Tracera only gets the matching kind.
        assert len(reachable_adapter.records) == 1
        assert reachable_adapter.records[0].kind == "wandb_step"
        assert bridge.skipped_kind == 1
        assert bridge.emitted_tracera == 1

    def test_empty_include_kinds_mirrors_all_kinds(
        self, jsonl_path: Path, reachable_adapter: MockAdapter
    ) -> None:
        """Empty include_kinds list = no filter (mirror all)."""
        bridge = TraceraBridge(
            adapter=reachable_adapter,
            jsonl_path=jsonl_path,
            dual_write=True,
            include_kinds=[],
        )
        for kind in ("claim", "evidence", "trace", "sprint"):
            bridge.emit(_make_event(kind=kind, session_id="S"))

        assert len(reachable_adapter.records) == 4
        assert bridge.skipped_kind == 0


class TestMockAdapterInjection:
    """Mock adapter injection: tests don't hit the network."""

    def test_no_network_access(self, jsonl_path: Path) -> None:
        """The bridge must accept an injected adapter and never reach the network."""
        adapter = MockAdapter()
        bridge = TraceraBridge(
            adapter=adapter,
            jsonl_path=jsonl_path,
            dual_write=True,
        )
        # No network calls should have happened yet.
        assert adapter.flush_calls == 0
        assert adapter.records == []

        # Emitting an event only touches the injected adapter.
        bridge.emit(_make_event(kind="claim"))
        assert len(adapter.records) == 1
        assert adapter.records[0].kind == "claim"

    def test_flush_on_emit_calls_adapter_flush(
        self, jsonl_path: Path, reachable_adapter: MockAdapter
    ) -> None:
        """When flush_on_emit=True, adapter.flush() runs after each append_event."""
        bridge = TraceraBridge(
            adapter=reachable_adapter,
            jsonl_path=jsonl_path,
            dual_write=True,
            flush_on_emit=True,
        )
        bridge.emit(_make_event(kind="claim"))
        bridge.emit(_make_event(kind="evidence"))
        assert reachable_adapter.flush_calls == 2

    def test_hooks_observe_both_backends(
        self, jsonl_path: Path, reachable_adapter: MockAdapter
    ) -> None:
        """Registered hooks fire after each backend write."""
        bridge = TraceraBridge(
            adapter=reachable_adapter,
            jsonl_path=jsonl_path,
            dual_write=True,
        )
        seen: list[tuple[str, str, str]] = []

        def hook(event: TraceEvent, sink: str) -> None:
            seen.append((str(event.id), sink, event.kind))

        bridge.add_hook(hook)
        event = _make_event(kind="claim")
        bridge.emit(event)

        # Two hook fires: JSONL first, then Tracera.
        sinks = [s for _, s, _ in seen]
        assert SINK_JSONL in sinks
        assert SINK_TRACERA in sinks
        # Both fired for the same event id.
        assert all(eid == str(event.id) for eid, _, _ in seen)


class TestInstallBridge:
    """install_bridge(trace_collector) attaches the bridge."""

    def test_install_bridge_attaches_bridge_attribute(self, jsonl_path: Path) -> None:
        # Minimal collector stub — install_bridge only needs attribute support.
        class _Stub:
            pass

        collector = _Stub()
        bridge = install_bridge(collector, jsonl_path=jsonl_path)
        assert collector.bridge is bridge  # type: ignore[attr-defined]
        assert isinstance(bridge, TraceraBridge)

    def test_install_bridge_with_explicit_bridge(self, jsonl_path: Path) -> None:
        class _Stub:
            pass

        collector = _Stub()
        existing = TraceraBridge(
            adapter=MockAdapter(),
            jsonl_path=jsonl_path,
            dual_write=True,
        )
        returned = install_bridge(collector, bridge=existing)
        assert returned is existing
        assert collector.bridge is existing  # type: ignore[attr-defined]

    def test_install_bridge_into_real_collector(self, jsonl_path: Path) -> None:
        """Wire into the actual TraceCollector from traces.ingest.

        `collect_all` is a module-level function (not a method), so we
        just verify the bridge attaches cleanly to a real instance and
        that the collector's own data-source iterators remain usable.
        """
        from traces.ingest import TraceCollector

        collector = TraceCollector()
        bridge = install_bridge(collector, jsonl_path=jsonl_path)
        assert collector.bridge is bridge  # type: ignore[attr-defined]
        # The collector's per-source iterators are still accessible.
        assert hasattr(collector, "omniroute")
        assert hasattr(collector, "all_sources")
        # The bridge is wired but emit() can still be called directly.
        event = _make_event(kind="trace")
        bridge.emit(event)
        rows = _read_jsonl(jsonl_path)
        assert len(rows) == 1
        assert rows[0]["kind"] == "trace"
