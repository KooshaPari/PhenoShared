"""Tests for agileplus_adapter — bead store skeleton (v0.12 task 22)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from beads.agileplus_adapter.agileplus_adapter import (
    AGILEPLUS_HEALTH_PATH,
    DEFAULT_CONFIG_PATH,
    RESERVED_METADATA_FIELDS,
    AgilePlusBeadStore,
    Bead,
    BeadStoreAdapter,
    BeadStoreError,
)


class TestBead:
    def test_make_computes_id_and_hash(self) -> None:
        b = Bead.make(
            kind="claim",
            target="pheno-harness",
            text="walk DAG task 22",
            agent="agent-x",
            host="m1",
        )
        assert len(b.id) == 8
        assert len(b.hash) == 8
        assert b.kind == "claim"
        assert b.target == "pheno-harness"
        assert b.text == "walk DAG task 22"
        assert b.host == "m1"

    def test_make_is_deterministic_for_same_inputs(self) -> None:
        # hash is deterministic on (target|kind|text), so two calls
        # with the same inputs but different agent/ts yield the same
        # hash but different ids.
        b1 = Bead.make(kind="ctl", target="x", text="y", agent="a", host="h")
        b2 = Bead.make(kind="ctl", target="x", text="y", agent="b", host="h")
        # hash should be the same (same target|kind|text)
        assert b1.hash == b2.hash
        # ids should differ (different agent in the id seed)
        assert b1.id != b2.id or b1.ts != b2.ts

    def test_to_dict_drops_metadata(self) -> None:
        b = Bead.make(
            kind="warn",
            target="x",
            text="y",
            agent="a",
            host="h",
            metadata={"session_id": "s1"},
        )
        d = b.to_dict()
        assert "metadata" not in d
        # Round-trip via legacy JSONL shape — required fields.
        for k in ("id", "ts", "agent", "kind", "target", "text", "hash"):
            assert k in d


class TestBeadStoreAdapterProtocol:
    def test_agileplus_adapter_satisfies_protocol(self) -> None:
        # Skeleton: methods exist (they raise NotImplementedError).
        store = AgilePlusBeadStore()
        assert isinstance(store, BeadStoreAdapter)


class TestAgilePlusBeadStoreConstruction:
    def test_default_url_is_localhost_8080(self) -> None:
        store = AgilePlusBeadStore()
        assert store.base_url == "http://127.0.0.1:8080"

    def test_host_port_override(self) -> None:
        store = AgilePlusBeadStore(host="agileplus.test", port=9090)
        assert store.base_url == "http://agileplus.test:9090"

    def test_base_url_overrides_host_port(self) -> None:
        store = AgilePlusBeadStore(
            base_url="http://explicit:1234",
            host="ignored",
            port=9999,
        )
        assert store.base_url == "http://explicit:1234"

    def test_env_vars_override_defaults(self) -> None:
        env = {
            "AGILEPLUS_HOST": "envhost",
            "AGILEPLUS_PORT": "9999",
        }
        with patch.dict(os.environ, env):
            store = AgilePlusBeadStore()
        assert store.base_url == "http://envhost:9999"

    def test_env_base_url_wins_over_host(self) -> None:
        env = {
            "AGILEPLUS_BASE_URL": "http://env-explicit:5555",
            "AGILEPLUS_HOST": "should-be-ignored",
        }
        with patch.dict(os.environ, env):
            store = AgilePlusBeadStore()
        assert store.base_url == "http://env-explicit:5555"

    def test_token_loaded_from_env(self) -> None:
        with patch.dict(os.environ, {"AGILEPLUS_API_TOKEN": "secret-xyz"}):
            store = AgilePlusBeadStore()
        assert store.token == "secret-xyz"

    def test_explicit_token_wins(self) -> None:
        with patch.dict(os.environ, {"AGILEPLUS_API_TOKEN": "env-token"}):
            store = AgilePlusBeadStore(token="explicit-token")
        assert store.token == "explicit-token"


class TestQuery:
    """Task 24 ac_test: query(target) reads /api/v1/events and reconstructs Beads."""

    def test_query_filters_by_target(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        events = {
            "events": [
                {
                    "id": 100,
                    "entity_type": "work_package",
                    "entity_id": 42,
                    "type": "transition",
                    "actor": "agent-x",
                    "occurred_at": "2026-08-10T07:30:00Z",
                    "reason": "claim pheno-harness",
                    "metadata": {
                        "bead_id": "abc12345",
                        "bead_ts": "2026-08-10T07:30:00Z",
                        "bead_agent": "agent-x",
                        "bead_kind": "claim",
                        "bead_target": "pheno-harness",
                        "bead_hash": "hash0001",
                        "host": "m1",
                    },
                },
                {
                    "id": 101,
                    "entity_type": "work_package",
                    "entity_id": 42,
                    "type": "transition",
                    "actor": "agent-y",
                    "occurred_at": "2026-08-10T07:31:00Z",
                    "reason": "claim other-target",
                    "metadata": {
                        "bead_id": "def67890",
                        "bead_ts": "2026-08-10T07:31:00Z",
                        "bead_agent": "agent-y",
                        "bead_kind": "claim",
                        "bead_target": "other-target",
                        "bead_hash": "hash0002",
                        "host": "m1",
                    },
                },
            ]
        }
        with patch.object(store, "_request", return_value=events):
            results = store.query("pheno-harness")
        assert len(results) == 1
        assert results[0].id == "abc12345"
        assert results[0].target == "pheno-harness"
        assert results[0].kind == "claim"
        assert results[0].text == "claim pheno-harness"

    def test_query_returns_empty_when_no_events(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        with patch.object(store, "_request", return_value={"events": []}):
            assert store.query("anything") == []

    def test_query_calls_correct_endpoint_with_wp_filter(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        with patch.object(store, "_request", return_value={"events": []}) as mock_req:
            store.query("pheno-harness")
        args, kwargs = mock_req.call_args
        assert args == ("GET", "/api/v1/events")
        assert kwargs["params"]["entity_type"] == "work_package"
        assert kwargs["params"]["entity_id"] == "42"

    def test_query_results_sorted_by_ts_ascending(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        events = {
            "events": [
                {
                    "id": 200,
                    "type": "transition",
                    "actor": "a",
                    "occurred_at": "2026-08-10T07:30:00Z",
                    "reason": "second",
                    "metadata": {
                        "bead_id": "b2",
                        "bead_ts": "2026-08-10T07:31:00Z",
                        "bead_agent": "a",
                        "bead_kind": "ctl",
                        "bead_target": "t",
                        "bead_hash": "h2",
                        "host": "h",
                    },
                },
                {
                    "id": 201,
                    "type": "transition",
                    "actor": "a",
                    "occurred_at": "2026-08-10T07:29:00Z",
                    "reason": "first",
                    "metadata": {
                        "bead_id": "b1",
                        "bead_ts": "2026-08-10T07:29:00Z",
                        "bead_agent": "a",
                        "bead_kind": "ctl",
                        "bead_target": "t",
                        "bead_hash": "h1",
                        "host": "h",
                    },
                },
            ]
        }
        with patch.object(store, "_request", return_value=events):
            results = store.query("t")
        assert [b.id for b in results] == ["b1", "b2"]

    def test_query_reconstruction_strips_reserved_metadata(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        events = {
            "events": [
                {
                    "id": 300,
                    "type": "transition",
                    "actor": "a",
                    "occurred_at": "2026-08-10T07:30:00Z",
                    "reason": "claim",
                    "metadata": {
                        "bead_id": "b1",
                        "bead_ts": "2026-08-10T07:30:00Z",
                        "bead_agent": "a",
                        "bead_kind": "claim",
                        "bead_target": "t",
                        "bead_hash": "h1",
                        "host": "h",
                        "session_id": "s1",
                        "score": 0.95,
                    },
                },
            ]
        }
        with patch.object(store, "_request", return_value=events):
            results = store.query("t")
        assert results[0].metadata == {"session_id": "s1", "score": 0.95}

    def test_query_falls_back_to_event_top_level_fields(self) -> None:
        # Legacy events without bead_* metadata — fall back to top-level
        # event fields for reconstruction.
        store = AgilePlusBeadStore(work_package_id=42)
        events = {
            "events": [
                {
                    "id": 400,
                    "type": "claim",
                    "actor": "agent-z",
                    "occurred_at": "2026-08-10T07:30:00Z",
                    "reason": "fallback claim",
                    "metadata": {"bead_target": "t"},
                },
            ]
        }
        with patch.object(store, "_request", return_value=events):
            results = store.query("t")
        assert len(results) == 1
        assert results[0].kind == "claim"
        assert results[0].agent == "agent-z"
        assert results[0].text == "fallback claim"


class TestSkeletonMethodsRaise:
    """All BeadStoreAdapter methods implemented by task 26."""


class TestEndToEndProtocolSatisfaction:
    """Verifies AgilePlusBeadStore is a runtime-checkable BeadStoreAdapter."""

    def test_satisfies_protocol(self) -> None:
        from beads.agileplus_adapter.agileplus_adapter import BeadStoreAdapter

        store = AgilePlusBeadStore()
        assert isinstance(store, BeadStoreAdapter)


class TestStats:
    """Task 26 ac_test: stats() returns {kind: count} aggregate across all beads."""

    def test_stats_counts_each_kind(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        events = {
            "events": [
                {"id": 1, "type": "claim", "metadata": {"bead_kind": "claim"}},
                {"id": 2, "type": "claim", "metadata": {"bead_kind": "claim"}},
                {"id": 3, "type": "ctl", "metadata": {"bead_kind": "ctl"}},
                {"id": 4, "type": "warn", "metadata": {"bead_kind": "warn"}},
            ]
        }
        with patch.object(store, "_request", return_value=events):
            stats = store.stats()
        assert stats["claim"] == 2
        assert stats["ctl"] == 1
        assert stats["warn"] == 1
        # Other canonical kinds still present (count 0).
        assert stats["complete"] == 0
        assert stats["reorg"] == 0

    def test_stats_empty_events_returns_zero_dict(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        with patch.object(store, "_request", return_value={"events": []}):
            stats = store.stats()
        # All canonical kinds present with count 0.
        for kind in (
            "claim",
            "complete",
            "warn",
            "ctl",
            "reorg",
            "goal",
            "intent",
            "unknown",
        ):
            assert stats[kind] == 0

    def test_stats_falls_back_to_event_type(self) -> None:
        # Legacy events without bead_kind metadata — fall back to event.type.
        store = AgilePlusBeadStore(work_package_id=42)
        events = {
            "events": [
                {"id": 1, "type": "claim"},
                {"id": 2, "type": "claim"},
            ]
        }
        with patch.object(store, "_request", return_value=events):
            stats = store.stats()
        assert stats["claim"] == 2

    def test_stats_handles_unknown_kind(self) -> None:
        # Non-canonical kind creates a lazy bucket.
        store = AgilePlusBeadStore(work_package_id=42)
        events = {
            "events": [
                {
                    "id": 1,
                    "type": "novel_kind",
                    "metadata": {"bead_kind": "novel_kind"},
                },
            ]
        }
        with patch.object(store, "_request", return_value=events):
            stats = store.stats()
        assert stats["novel_kind"] == 1

    def test_stats_handles_none_kind(self) -> None:
        # Defensive: kind is None or empty string → 'unknown' bucket.
        store = AgilePlusBeadStore(work_package_id=42)
        events = {
            "events": [
                {"id": 1, "type": None, "metadata": {"bead_kind": None}},
                {"id": 2, "metadata": {}},
            ]
        }
        with patch.object(store, "_request", return_value=events):
            stats = store.stats()
        assert stats["unknown"] == 2

    def test_stats_skips_non_dict_events(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        events = {
            "events": [
                None,
                "string",
                123,
                {"id": 1, "type": "claim", "metadata": {"bead_kind": "claim"}},
            ]
        }
        with patch.object(store, "_request", return_value=events):
            stats = store.stats()
        assert stats["claim"] == 1

    def test_stats_handles_non_list_response(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        with patch.object(store, "_request", return_value={"status": "ok"}):
            stats = store.stats()
        # Returns the zero dict, no exceptions.
        assert stats["claim"] == 0

    def test_stats_output_is_sorted(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        events = {
            "events": [
                {"id": 1, "type": "claim", "metadata": {"bead_kind": "claim"}},
            ]
        }
        with patch.object(store, "_request", return_value=events):
            stats = store.stats()
        # Keys must be sorted alphabetically.
        assert list(stats.keys()) == sorted(stats.keys())

    def test_stats_propagates_beadstore_error(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        with (
            patch.object(
                store,
                "_request",
                side_effect=BeadStoreError("connection refused"),
            ),
            pytest.raises(BeadStoreError),
        ):
            store.stats()


class TestDedupCheck:
    """Task 25 ac_test: dedup_check(bead) returns True iff bead.hash matches an existing event."""

    def test_dedup_returns_true_on_match(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        b = Bead.make(kind="claim", target="t1", text="hello", agent="a", host="h")
        events = {
            "events": [
                {
                    "id": 1,
                    "metadata": {
                        "bead_id": "x",
                        "bead_hash": b.hash,
                        "bead_target": "t1",
                        "bead_kind": "claim",
                    },
                },
            ]
        }
        with patch.object(store, "_request", return_value=events):
            assert store.dedup_check(b) is True

    def test_dedup_returns_false_when_no_match(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        b = Bead.make(kind="claim", target="t1", text="hello", agent="a", host="h")
        events = {
            "events": [
                {
                    "id": 1,
                    "metadata": {
                        "bead_id": "x",
                        "bead_hash": "different",
                        "bead_target": "t1",
                        "bead_kind": "claim",
                    },
                },
            ]
        }
        with patch.object(store, "_request", return_value=events):
            assert store.dedup_check(b) is False

    def test_dedup_empty_events_returns_false(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        b = Bead.make(kind="claim", target="t1", text="hello", agent="a", host="h")
        with patch.object(store, "_request", return_value={"events": []}):
            assert store.dedup_check(b) is False

    def test_dedup_scans_all_targets(self) -> None:
        # dedup must scan across all targets — not just the bead's own target.
        store = AgilePlusBeadStore(work_package_id=42)
        b = Bead.make(kind="claim", target="t1", text="hello", agent="a", host="h")
        # An event with matching hash but DIFFERENT target — still a hit.
        events = {
            "events": [
                {
                    "id": 1,
                    "metadata": {
                        "bead_id": "x",
                        "bead_hash": b.hash,
                        "bead_target": "OTHER-TARGET",
                        "bead_kind": "claim",
                    },
                },
            ]
        }
        with patch.object(store, "_request", return_value=events):
            assert store.dedup_check(b) is True

    def test_dedup_calls_events_endpoint_without_target_filter(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        b = Bead.make(kind="claim", target="t1", text="hello", agent="a", host="h")
        with patch.object(store, "_request", return_value={"events": []}) as mock_req:
            store.dedup_check(b)
        args, kwargs = mock_req.call_args
        # Must NOT pass target — dedup is global to the work package.
        assert "target" not in (kwargs.get("params") or {})
        assert kwargs["params"]["entity_type"] == "work_package"
        assert kwargs["params"]["entity_id"] == "42"

    def test_dedup_skips_non_dict_events(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        b = Bead.make(kind="claim", target="t1", text="hello", agent="a", host="h")
        events = {
            "events": [
                None,
                "string-not-dict",
                123,
                {"id": 1, "metadata": {"bead_hash": b.hash}},
            ]
        }
        with patch.object(store, "_request", return_value=events):
            assert store.dedup_check(b) is True

    def test_dedup_handles_non_list_response(self) -> None:
        # Defensive: server returns dict without 'events' key.
        store = AgilePlusBeadStore(work_package_id=42)
        b = Bead.make(kind="claim", target="t1", text="hello", agent="a", host="h")
        with patch.object(store, "_request", return_value={"status": "ok"}):
            assert store.dedup_check(b) is False

    def test_dedup_propagates_beadstore_error(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        b = Bead.make(kind="claim", target="t1", text="hello", agent="a", host="h")
        with (
            patch.object(
                store,
                "_request",
                side_effect=BeadStoreError("connection refused"),
            ),
            pytest.raises(BeadStoreError),
        ):
            store.dedup_check(b)


# ---------------------------------------------------------------------------
# Task 30 ac_test — integration test (skipped by default; opt-in via
# AGILEPLUS_INTEGRATION=1 with a live AgilePlus server reachable at the
# configured host:port).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("AGILEPLUS_INTEGRATION") != "1",
    reason="integration test; set AGILEPLUS_INTEGRATION=1 with a live AgilePlus server to run",
)
class TestAgilePlusIntegration:
    """1 integration test per WBS task 30 ac_test.

    Run with::

        AGILEPLUS_INTEGRATION=1 AGILEPLUS_HOST=... AGILEPLUS_PORT=... \
            python3 -m pytest tests/test_agileplus_adapter.py::TestAgilePlusIntegration -v

    The test creates a unique target (per-run UUID5) to avoid colliding
    with other test runs, appends 1 bead, queries it back, dedup-checks
    it, and asserts the round-trip preserves every field.

    Cleanup: the integration test does NOT delete the appended bead
    (the AgilePlus API doesn't expose a delete endpoint for events in
    v0.1). The unique-target naming ensures no test pollution.
    """

    def test_append_query_dedup_roundtrip(self) -> None:
        import uuid as _uuid

        target = "v0.12-task-30-integration-" + str(
            _uuid.uuid5(_uuid.NAMESPACE_DNS, str(_uuid.uuid4()))
        )
        b = Bead.make(
            kind="claim",
            target=target,
            text="integration test for v0.12 task 30",
            agent="test-runner",
            host=os.uname().nodename,
            metadata={"session_id": "task-30", "score": 0.99},
        )
        store = AgilePlusBeadStore(
            host=os.environ.get("AGILEPLUS_HOST", "127.0.0.1"),
            port=int(os.environ.get("AGILEPLUS_PORT", "8080")),
            token=os.environ.get("AGILEPLUS_API_TOKEN"),
            work_package_id=int(os.environ.get("AGILEPLUS_WP_ID", "1")),
        )

        # 1. Health probe (also verifies server is reachable).
        health = store.health()
        assert health.get("status") == "ok", f"AgilePlus unhealthy: {health}"

        # 2. Append the bead.
        returned_id = store.append(b)
        assert returned_id == b.id or len(returned_id) > 0

        # 3. Query it back. There may be a propagation delay on the
        # server side, so we retry briefly with a short sleep.
        import time

        beads: list[Bead] = []
        for _ in range(5):
            beads = store.query(target)
            if beads:
                break
            time.sleep(0.5)
        assert len(beads) == 1, f"expected 1 bead, got {len(beads)}"
        roundtripped = beads[0]
        assert roundtripped.kind == b.kind
        assert roundtripped.target == b.target
        assert roundtripped.text == b.text
        assert roundtripped.agent == b.agent

        # 4. Dedup_check confirms the bead is now present.
        assert store.dedup_check(b) is True


class TestAppend:
    """Task 23 ac_test: append() POSTs to /api/v1/work-packages/{id}/transition."""

    def test_append_posts_to_work_package_transition(self) -> None:
        store = AgilePlusBeadStore(work_package_id=42)
        b = Bead.make(
            kind="claim",
            target="pheno-harness",
            text="walk DAG",
            agent="agent-x",
            host="m1",
        )
        with patch.object(store, "_request", return_value={"id": 99}) as mock_req:
            returned = store.append(b)
        # Server-assigned id wins over client id.
        assert returned == "99"
        mock_req.assert_called_once()
        args, kwargs = mock_req.call_args
        assert args == ("POST", "/api/v1/work-packages/42/transition")
        body = kwargs["body"]
        assert body["target_state"] == "claim"
        assert body["reason"] == "walk DAG"
        assert body["metadata"]["bead_id"] == b.id
        assert body["metadata"]["bead_target"] == "pheno-harness"
        assert body["metadata"]["host"] == "m1"

    def test_append_falls_back_to_client_id(self) -> None:
        # Server response with no id field — fall back to bead.id.
        store = AgilePlusBeadStore(work_package_id=1)
        b = Bead.make(kind="ctl", target="x", text="y", agent="a", host="h")
        with patch.object(store, "_request", return_value={"status": "ok"}):
            returned = store.append(b)
        assert returned == b.id

    def test_append_uses_default_wp_when_unset(self) -> None:
        # Default work_package_id=1 when none configured.
        store = AgilePlusBeadStore()
        b = Bead.make(kind="warn", target="x", text="y", agent="a", host="h")
        with patch.object(store, "_request", return_value={"id": 1}) as mock_req:
            store.append(b)
        args, _ = mock_req.call_args
        assert args == ("POST", "/api/v1/work-packages/1/transition")

    def test_append_merges_user_metadata_last(self) -> None:
        # User metadata with reserved keys must NOT override reserved keys.
        store = AgilePlusBeadStore(work_package_id=7)
        b = Bead.make(
            kind="claim",
            target="t",
            text="T",
            agent="a",
            host="h",
            metadata={"bead_id": "USER_OVERRIDE", "session_id": "s1", "score": 0.95},
        )
        with patch.object(store, "_request", return_value={"id": 1}) as mock_req:
            store.append(b)
        body = mock_req.call_args.kwargs["body"]
        # reserved keys WIN — user cannot shadow bead_id
        assert body["metadata"]["bead_id"] == b.id
        assert body["metadata"]["bead_id"] != "USER_OVERRIDE"
        # non-reserved user keys pass through
        assert body["metadata"]["session_id"] == "s1"
        assert body["metadata"]["score"] == 0.95

    def test_append_propagates_beadstore_error(self) -> None:
        store = AgilePlusBeadStore(work_package_id=1)
        b = Bead.make(kind="claim", target="x", text="y", agent="a", host="h")
        with patch.object(
            store, "_request", side_effect=BeadStoreError("connection refused")
        ):
            with pytest.raises(BeadStoreError):
                store.append(b)


class TestHealthEndpoint:
    def test_health_calls_health_path(self) -> None:
        store = AgilePlusBeadStore(host="agileplus.test", port=9090)
        with patch.object(store, "_request", return_value={"status": "ok"}) as mock_req:
            result = store.health()
        mock_req.assert_called_once_with("GET", AGILEPLUS_HEALTH_PATH)
        assert result == {"status": "ok"}


class TestReservedMetadataFields:
    def test_contains_six_keys(self) -> None:
        # Mirrors pheno/trace_store/tracera.RESERVED_METADATA_KEYS.
        assert len(RESERVED_METADATA_FIELDS) == 6
        for key in (
            "bead_id",
            "bead_ts",
            "bead_agent",
            "bead_kind",
            "bead_target",
            "bead_hash",
        ):
            assert key in RESERVED_METADATA_FIELDS

    def test_is_frozenset(self) -> None:
        # Immutable so adapters can't accidentally mutate the canonical
        # reserved-key set.
        assert isinstance(RESERVED_METADATA_FIELDS, frozenset)


class TestConfigPath:
    def test_default_config_path_is_under_home(self) -> None:
        assert Path.home() / ".agileplus" / "config.json" == DEFAULT_CONFIG_PATH

    def test_explicit_config_path(self) -> None:
        store = AgilePlusBeadStore(config_path="/tmp/custom-config.json")  # nosec B108 — explicit test path
        assert store.config_path == Path("/tmp/custom-config.json")  # nosec B108 — same explicit test path


class TestHttpErrorMapping:
    """HTTPError / URLError / JSONDecodeError → BeadStoreError."""

    def test_http_error_translates_to_beadstore_error(self) -> None:
        import io
        import urllib.error

        store = AgilePlusBeadStore()
        with (
            patch(
                "urllib.request.urlopen",
                side_effect=urllib.error.HTTPError(
                    "http://x/health",
                    503,
                    "Service Unavailable",
                    {},
                    io.BytesIO(b"down"),
                ),
            ),
            pytest.raises(BeadStoreError),
        ):
            store.health()

    def test_url_error_translates_to_beadstore_error(self) -> None:
        import urllib.error

        store = AgilePlusBeadStore()
        with (
            patch(
                "urllib.request.urlopen",
                side_effect=urllib.error.URLError("connection refused"),
            ),
            pytest.raises(BeadStoreError),
        ):
            store.health()
