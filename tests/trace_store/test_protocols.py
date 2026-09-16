# Tests for trace_store.protocols — TraceEvent dataclass + protocol.
#
# v0.12 task 8 (Phase 1 — Tracera adapter skeleton) ac_v1.
# Tasks 9-11 will add TraceraAdapter-specific tests once the
# implementation lands.

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from pheno.trace_store import TraceEvent, TraceStoreError
from pheno.trace_store.protocols import TraceStoreAdapter


class TestTraceEvent:
    def test_make_defaults(self) -> None:
        event = TraceEvent.make(kind="claim", actor="agent-test")
        assert event.kind == "claim"
        assert event.actor == "agent-test"
        assert event.target is None
        assert event.session_id is None
        assert event.payload == {}
        assert isinstance(event.id, UUID)
        assert event.ts.tzinfo is not None

    def test_make_with_kwargs(self) -> None:
        ts = datetime(2026, 8, 10, 12, 0, 0, tzinfo=UTC)
        event = TraceEvent.make(
            kind="evidence",
            actor="daemon-x",
            target="repo/y#123",
            session_id="session-abc",
            payload={"k": "v"},
            ts=ts,
        )
        assert event.kind == "evidence"
        assert event.target == "repo/y#123"
        assert event.session_id == "session-abc"
        assert event.payload == {"k": "v"}
        assert event.ts == ts

    def test_roundtrip(self) -> None:
        original = TraceEvent.make(
            kind="trace",
            actor="a",
            target="t",
            session_id="s",
            payload={"x": 1, "nested": {"y": [2, 3]}},
        )
        blob = json.dumps(original.to_dict())
        restored = TraceEvent.from_dict(json.loads(blob))
        assert restored == original

    def test_to_dict_json_safe(self) -> None:
        event = TraceEvent.make(kind="k", actor="a")
        # to_dict output is JSON-serializable (no UUID/datetime leakage).
        json.dumps(event.to_dict())


class TestProtocols:
    def test_tracestoreerror_carries_cause(self) -> None:
        original = RuntimeError("boom")
        err = TraceStoreError("wrapped", cause=original)
        assert err.cause is original
        assert "wrapped" in str(err)

    def test_tracestoreadapter_is_runtime_checkable(self) -> None:
        # Runtime-checkable means isinstance works against the protocol.
        # A bare TraceEvent is not an adapter; verify the negative case.
        event = TraceEvent.make(kind="k", actor="a")
        assert not isinstance(event, TraceStoreAdapter)


class TestTraceraAdapterSkeleton:
    """Skeleton verification — task 8 ac_v1."""

    def test_tracera_adapter_importable(self) -> None:
        from pheno.trace_store import TraceraAdapter

        assert TraceraAdapter is not None

    def test_default_base_url(self) -> None:
        from pheno.trace_store import TraceraAdapter

        adapter = TraceraAdapter(base_url="http://example:9999")
        assert adapter.base_url == "http://example:9999"

    def test_health_returns_status(self) -> None:
        from pheno.trace_store import TraceraAdapter

        adapter = TraceraAdapter(base_url="http://127.0.0.1:1")
        # No server on port 1 — expect "down" status.
        result = adapter.health()
        assert result["status"] == "down"
        assert "error" in result

    def test_query_is_implemented(self) -> None:
        # Both append_event (task 9) and query (task 10) are implemented.
        from pheno.trace_store import TraceraAdapter

        adapter = TraceraAdapter(base_url="http://127.0.0.1:1")
        # query should now raise TraceStoreError (transport), NOT
        # NotImplementedError (skeleton).
        with __import__("pytest").raises(Exception) as exc_info:
            adapter.query("session-x")
        assert not isinstance(exc_info.value, NotImplementedError)
