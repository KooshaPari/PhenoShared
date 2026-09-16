# Tests for trace_store.tracera — TraceraAdapter HTTP client.
#
# v0.12 task 9 (Phase 1 — Tracera adapter append_event) ac_test.
# Uses unittest.mock to patch urllib.request.urlopen (since respx only
# intercepts httpx; TraceraAdapter uses stdlib urllib). Tests cover:
# - successful POST /evidence round-trip (id echo)
# - request body shape (artifact_id, kind, url, metadata, links, actor)
# - transport error → TraceStoreError
# - non-2xx status → TraceStoreError
# - url construction for target / unscoped events
# - fallback when response.evidence.id is missing

from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from pheno.trace_store import TraceEvent, TraceraAdapter
from pheno.trace_store.tracera import TRACERA_HEALTH_PATH

# Test artifact_ids must be valid UUIDs since they're round-tripped
# through UUID(artifact_id) during reconstruction.
# Using a deterministic uuid5 namespace so test runs are reproducible.
_TEST_NS = UUID("12345678-1234-5678-1234-567812345678")


def _tid(label: str) -> str:
    """Generate a deterministic UUID string from a short label."""
    import uuid

    return str(uuid.uuid5(_TEST_NS, label))


def _make_response(status: int, body: dict[str, Any] | str) -> MagicMock:
    """Construct a context-manager mock for urllib's urlopen return."""
    response = MagicMock()
    response.read.return_value = (
        json.dumps(body).encode("utf-8")
        if isinstance(body, dict)
        else body.encode("utf-8")
    )
    response.status = status
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)

    # Simulate HTTPError behavior for non-2xx status codes.
    if status >= 400:
        response.code = status
        response.fp = BytesIO(
            (json.dumps(body) if isinstance(body, dict) else body).encode("utf-8")
        )
    return response


@pytest.fixture
def adapter() -> TraceraAdapter:
    return TraceraAdapter(base_url="http://tracera.test:8080")


@pytest.fixture
def sample_event() -> TraceEvent:
    return TraceEvent.make(
        kind="claim",
        actor="agent-test",
        target="repo/y#123",
        session_id="session-abc",
        payload={"custom": "value", "score": 0.95},
    )


class TestAppendEvent:
    def test_success_returns_evidence_id(
        self, adapter: TraceraAdapter, sample_event: TraceEvent
    ) -> None:
        captured: dict[str, Any] = {}
        evidence_id = "tracera-evidence-id-xyz"

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            captured["url"] = req.full_url if hasattr(req, "full_url") else req
            captured["method"] = (
                req.get_method() if hasattr(req, "get_method") else "POST"
            )
            captured["body"] = req.data.decode("utf-8") if req.data else None
            return _make_response(
                201,
                {
                    "evidence": {
                        "id": evidence_id,
                        "artifact_id": str(sample_event.id),
                        "kind": "claim",
                        "url": "ignored",
                        "metadata": {},
                        "created_at": "2026-08-10T12:00:00Z",
                    },
                    "links": [],
                    "audit": {
                        "id": "audit-1",
                        "actor": "agent-test",
                        "action": "record",
                        "entity_type": "evidence",
                        "entity_id": evidence_id,
                        "metadata": {},
                        "occurred_at": "2026-08-10T12:00:00Z",
                    },
                },
            )

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            result = adapter.append_event(sample_event)

        assert result == evidence_id
        assert captured["method"] == "POST"
        assert captured["url"] == "http://tracera.test:8080/evidence"
        body = json.loads(captured["body"])
        assert body["artifact_id"] == str(sample_event.id)
        assert body["kind"] == "claim"
        assert body["url"].startswith("pheno://repo/y#123/")
        assert body["actor"] == "agent-test"
        assert body["links"] == []
        metadata: dict[str, Any] = body["metadata"]
        assert metadata["session_id"] == "session-abc"
        assert metadata["target"] == "repo/y#123"
        assert metadata["pheno_event_kind"] == "claim"
        assert metadata["custom"] == "value"
        assert metadata["score"] == 0.95

    def test_unscoped_event_url(self, adapter: TraceraAdapter) -> None:
        event = TraceEvent.make(kind="trace", actor="a")  # no target
        captured: dict[str, Any] = {}

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _make_response(
                201, {"evidence": {"id": "ignored"}, "links": [], "audit": {}}
            )

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            adapter.append_event(event)

        body = captured["body"]
        assert body["url"].startswith("pheno://unscoped/")
        assert "target" not in body["metadata"]

    def test_no_session_id_omits_key(self, adapter: TraceraAdapter) -> None:
        event = TraceEvent.make(kind="evidence", actor="a", target="t")
        captured: dict[str, Any] = {}

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _make_response(
                201, {"evidence": {"id": "ignored"}, "links": [], "audit": {}}
            )

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            adapter.append_event(event)

        assert "session_id" not in captured["body"]["metadata"]

    def test_transport_error_raises_tracestoreerror(
        self, adapter: TraceraAdapter, sample_event: TraceEvent
    ) -> None:
        from pheno.trace_store.protocols import TraceStoreError

        def fake_urlopen(req: Any, timeout: float = 5.0) -> Any:
            # Raise a real HTTPError so the adapter's HTTPError branch
            # handles it (rather than the JSONDecodeError branch on a
            # mocked 503 that just returns text).
            raise urllib.error.HTTPError(
                url=req.full_url,
                code=503,
                msg="Service Unavailable",
                hdrs={},  # type: ignore[arg-type]
                fp=BytesIO(b"upstream down"),
            )

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            with pytest.raises(TraceStoreError) as exc_info:
                adapter.append_event(sample_event)
        assert "503" in str(exc_info.value)

    def test_response_without_evidence_id_returns_event_id(
        self, adapter: TraceraAdapter, sample_event: TraceEvent
    ) -> None:
        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            return _make_response(201, {"evidence": {}, "links": [], "audit": {}})

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            result = adapter.append_event(sample_event)
        assert result == str(sample_event.id)

    def test_uses_bearer_token_when_set(self) -> None:
        adapter = TraceraAdapter(
            base_url="http://tracera.test:8080", token="secret-token-abc"
        )
        event = TraceEvent.make(kind="claim", actor="a")
        captured: dict[str, Any] = {}

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            captured["headers"] = dict(req.headers)
            return _make_response(
                201, {"evidence": {"id": "x"}, "links": [], "audit": {}}
            )

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            adapter.append_event(event)

        assert captured["headers"]["Authorization"] == "Bearer secret-token-abc"

    def test_canonical_grapheon_env_vars_configure_adapter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GRAPHEON_* is the canonical adapter configuration namespace."""
        monkeypatch.setenv("GRAPHEON_HOST", "grapheon.test")
        monkeypatch.setenv("GRAPHEON_PORT", "9443")
        monkeypatch.setenv("GRAPHEON_BASE_URL", "https://grapheon.test/api")
        monkeypatch.setenv("GRAPHEON_API_TOKEN", "grapheon-token")

        adapter = TraceraAdapter()

        assert adapter.base_url == "https://grapheon.test/api"
        assert adapter.token == "grapheon-token"

    def test_canonical_grapheon_host_and_port_are_used_without_base_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GRAPHEON_HOST/PORT form the endpoint when BASE_URL is absent."""
        monkeypatch.setenv("GRAPHEON_HOST", "grapheon.test")
        monkeypatch.setenv("GRAPHEON_PORT", "9443")
        monkeypatch.delenv("GRAPHEON_BASE_URL", raising=False)

        adapter = TraceraAdapter()

        assert adapter.base_url == "http://grapheon.test:9443"


def test_destination_configuration_precedes_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRACERA_BASE_URL", "https://destination.test")
    monkeypatch.setenv("GRAPHEON_BASE_URL", "https://source.test")
    monkeypatch.setenv("TRACERA_API_TOKEN", "destination-token")
    monkeypatch.setenv("GRAPHEON_API_TOKEN", "source-token")
    adapter = TraceraAdapter()
    assert adapter.base_url == "https://destination.test"
    assert adapter.token == "destination-token"
    explicit = TraceraAdapter(base_url="https://explicit.test", token="explicit-token")
    assert explicit.base_url == "https://explicit.test"
    assert explicit.token == "explicit-token"


class TestQuery:
    """Tests for TraceraAdapter.query (task 10)."""

    def _evidence_record(
        self,
        *,
        artifact_id: str,
        kind: str = "claim",
        session_id: str | None = None,
        actor: str = "agent-x",
        target: str | None = None,
        ts: str | None = None,
        created_at: str = "2026-08-10T12:00:00Z",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "pheno_event_id": artifact_id,
            "pheno_event_kind": kind,
            "actor": actor,
        }
        if ts is not None:
            metadata["pheno_event_ts"] = ts
        if session_id is not None:
            metadata["session_id"] = session_id
        if target is not None:
            metadata["target"] = target
        if payload:
            metadata.update(payload)
        return {
            "id": "tracera-" + artifact_id,
            "artifact_id": artifact_id,
            "kind": kind,
            "url": "pheno://unscoped/" + artifact_id,
            "metadata": metadata,
            "created_at": created_at,
        }

    def test_filters_by_session_id(self, adapter: TraceraAdapter) -> None:
        records = [
            self._evidence_record(artifact_id=_tid("a-1"), session_id="session-A"),
            self._evidence_record(artifact_id=_tid("b-1"), session_id="session-B"),
            self._evidence_record(artifact_id=_tid("a-2"), session_id="session-A"),
        ]

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            return _make_response(200, {"items": records, "count": len(records)})

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            result = adapter.query("session-A")

        assert len(result) == 2
        assert {str(e.id) for e in result} == {_tid("a-1"), _tid("a-2")}

    def test_returns_empty_when_no_matches(self, adapter: TraceraAdapter) -> None:
        records = [
            self._evidence_record(artifact_id=_tid("a-1"), session_id="session-A"),
        ]

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            return _make_response(200, {"items": records, "count": 1})

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            result = adapter.query("session-X")
        assert result == []

    def test_skips_records_without_session_id_metadata(
        self, adapter: TraceraAdapter
    ) -> None:
        records = [
            self._evidence_record(artifact_id=_tid("legacy-1")),  # no session_id
            self._evidence_record(artifact_id=_tid("modern-1"), session_id="session-A"),
        ]

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            return _make_response(200, {"items": records, "count": len(records)})

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            result = adapter.query("session-A")
        assert len(result) == 1
        assert str(result[0].id) == _tid("modern-1")

    def test_results_sorted_by_ts_ascending(self, adapter: TraceraAdapter) -> None:
        records = [
            self._evidence_record(
                artifact_id=_tid("c-1"),
                session_id="S",
                ts="2026-08-10T12:02:00+00:00",
            ),
            self._evidence_record(
                artifact_id=_tid("a-1"),
                session_id="S",
                ts="2026-08-10T12:00:00+00:00",
            ),
            self._evidence_record(
                artifact_id=_tid("b-1"),
                session_id="S",
                ts="2026-08-10T12:01:00+00:00",
            ),
        ]

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            return _make_response(200, {"items": records, "count": 3})

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            result = adapter.query("S")
        assert [str(e.id) for e in result] == [_tid("a-1"), _tid("b-1"), _tid("c-1")]

    def test_reconstruction_uses_metadata_fields(self, adapter: TraceraAdapter) -> None:
        record = self._evidence_record(
            artifact_id=_tid("a-1"),
            kind="evidence",
            session_id="S",
            actor="agent-z",
            target="repo/q#7",
            ts="2026-08-10T11:59:00+00:00",
            payload={"custom": "value", "score": 0.7},
        )

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            return _make_response(200, {"items": [record], "count": 1})

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            result = adapter.query("S")
        assert len(result) == 1
        event = result[0]
        assert str(event.id) == _tid("a-1")
        assert event.kind == "evidence"
        assert event.actor == "agent-z"
        assert event.target == "repo/q#7"
        assert event.session_id == "S"
        assert event.payload == {"custom": "value", "score": 0.7}

    def test_falls_back_to_created_at_when_pheno_ts_missing(
        self, adapter: TraceraAdapter
    ) -> None:
        # Legacy record without pheno_event_ts in metadata.
        record = self._evidence_record(
            artifact_id=_tid("legacy-1"),
            session_id="S",
            ts=None,  # type: ignore[arg-type]
            created_at="2026-08-10T11:30:00+00:00",
        )

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            return _make_response(200, {"items": [record], "count": 1})

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            result = adapter.query("S")
        assert len(result) == 1
        assert result[0].ts.isoformat().startswith("2026-08-10T11:30:00")

    def test_empty_evidence_list_returns_empty(self, adapter: TraceraAdapter) -> None:
        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            return _make_response(200, {"items": [], "count": 0})

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            result = adapter.query("S")
        assert result == []

    def test_handles_z_suffix_isoformat(self, adapter: TraceraAdapter) -> None:
        # Tracera's created_at uses 'Z' suffix; fromisoformat needs '+00:00'.
        record = self._evidence_record(
            artifact_id=_tid("z-1"),
            session_id="S",
            ts="2026-08-10T12:00:00Z",
        )

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            return _make_response(200, {"items": [record], "count": 1})

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            result = adapter.query("S")
        assert result[0].ts.tzinfo is not None


class TestHealthEndpointPath:
    def test_healthz_constant(self) -> None:
        # The Tracera health path is /healthz (per docs/integrations/tracera-api.md).
        # This guards against accidental drift to /health (which is also valid).
        assert TRACERA_HEALTH_PATH == "/healthz"


class TestEnqueueAndFlush:
    """Tests for TraceraAdapter batched async write path (task 11)."""

    def test_enqueue_appends_to_buffer(self, adapter: TraceraAdapter) -> None:
        assert adapter.buffer_size() == 0
        eid = adapter.enqueue_event(TraceEvent.make(kind="claim", actor="a"))
        assert isinstance(eid, str) and len(eid) == 36  # UUID string
        assert adapter.buffer_size() == 1
        adapter.enqueue_event(TraceEvent.make(kind="evidence", actor="b"))
        assert adapter.buffer_size() == 2

    def test_flush_empty_buffer_is_noop(self, adapter: TraceraAdapter) -> None:
        # Should not raise and should not call HTTP.
        called = []

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            called.append(req)
            return _make_response(200, {"items": [], "count": 0})

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            adapter.flush()
        assert called == []

    def test_flush_posts_each_buffered_event(self, adapter: TraceraAdapter) -> None:
        e1 = TraceEvent.make(kind="claim", actor="a", session_id="S")
        e2 = TraceEvent.make(kind="evidence", actor="b", session_id="S")
        e3 = TraceEvent.make(kind="trace", actor="c", session_id="S")
        adapter.enqueue_event(e1)
        adapter.enqueue_event(e2)
        adapter.enqueue_event(e3)
        assert adapter.buffer_size() == 3

        captured: list[dict[str, Any]] = []

        def fake_urlopen(req: Any, timeout: float = 5.0) -> MagicMock:
            captured.append(json.loads(req.data.decode("utf-8")))
            return _make_response(
                201,
                {
                    "evidence": {"id": "tracera-" + str(len(captured))},
                    "links": [],
                    "audit": {},
                },
            )

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            adapter.flush()

        assert len(captured) == 3
        assert captured[0]["artifact_id"] == str(e1.id)
        assert captured[1]["artifact_id"] == str(e2.id)
        assert captured[2]["artifact_id"] == str(e3.id)
        # Buffer should be drained on success.
        assert adapter.buffer_size() == 0

    def test_flush_preserves_remainder_on_failure(
        self, adapter: TraceraAdapter
    ) -> None:
        e1 = TraceEvent.make(kind="claim", actor="a")
        e2 = TraceEvent.make(kind="evidence", actor="b")
        e3 = TraceEvent.make(kind="trace", actor="c")
        adapter.enqueue_event(e1)
        adapter.enqueue_event(e2)
        adapter.enqueue_event(e3)

        def fake_urlopen(req: Any, timeout: float = 5.0) -> Any:
            payload = json.loads(req.data.decode("utf-8"))
            if payload["artifact_id"] == str(e2.id):
                raise urllib.error.HTTPError(
                    url=req.full_url,
                    code=503,
                    msg="Service Unavailable",
                    hdrs={},  # type: ignore[arg-type]
                    fp=BytesIO(b"down"),
                )
            return _make_response(
                201, {"evidence": {"id": "ok"}, "links": [], "audit": {}}
            )

        with patch("pheno.trace_store.tracera.urllib.request.urlopen", fake_urlopen):
            with pytest.raises(Exception) as exc_info:
                adapter.flush()
        assert "503" in str(exc_info.value)
        # e1 succeeded (removed); e2 failed + e3 not attempted → still buffered.
        assert adapter.buffer_size() == 2
        # Verify e2 is at the front of the buffer (resume from failure).
        remaining = [adapter._buffer[0], adapter._buffer[1]]
        assert str(remaining[0].id) == str(e2.id)
        assert str(remaining[1].id) == str(e3.id)

    def test_batch_size_default(self, adapter: TraceraAdapter) -> None:
        # Default batch_size should be 32 (sanity bound).
        assert adapter.batch_size == 32

    def test_batch_size_configurable(self) -> None:
        adapter = TraceraAdapter(base_url="http://x.test:9", batch_size=8)
        assert adapter.batch_size == 8

    def test_batch_size_minimum_one(self) -> None:
        adapter = TraceraAdapter(base_url="http://x.test:9", batch_size=0)
        assert adapter.batch_size == 1
        adapter = TraceraAdapter(base_url="http://x.test:9", batch_size=-3)
        assert adapter.batch_size == 1
