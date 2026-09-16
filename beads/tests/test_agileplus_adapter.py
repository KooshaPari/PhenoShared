"""Tests for agileplus_adapter — bead store skeleton (v0.12 task 22)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from agileplus_adapter import (
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


class TestSkeletonMethodsRaise:
    """Tasks 23-26 implement these; skeleton raises NotImplementedError."""

    def test_append_raises(self) -> None:
        store = AgilePlusBeadStore()
        b = Bead.make(kind="claim", target="x", text="y", agent="a", host="h")
        with pytest.raises(NotImplementedError):
            store.append(b)

    def test_query_raises(self) -> None:
        store = AgilePlusBeadStore()
        with pytest.raises(NotImplementedError):
            store.query("x")

    def test_dedup_check_raises(self) -> None:
        store = AgilePlusBeadStore()
        b = Bead.make(kind="claim", target="x", text="y", agent="a", host="h")
        with pytest.raises(NotImplementedError):
            store.dedup_check(b)

    def test_stats_raises(self) -> None:
        store = AgilePlusBeadStore()
        with pytest.raises(NotImplementedError):
            store.stats()


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
        store = AgilePlusBeadStore(config_path="/tmp/custom-config.json")
        assert store.config_path == Path("/tmp/custom-config.json")


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
