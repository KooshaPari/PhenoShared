# Tests for pheno.runtime — the orchestrator for the dual-write integration.
#
# v0.12 WBS-PERT-100 task 17 (Phase 1 — Tracera dual-write integration) ac_v1.

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pheno.runtime import current_state, dual_write, start, stop
from pheno.runtime_config import (
    EvidenceConfig,
    RuntimeConfig,
    TraceBridgesConfig,
    TraceraConfig,
    reload,
)


def _make_config(
    *,
    tracera_enabled: bool = False,
    dual_write: bool = False,
    health_check_on_init: bool = False,
    include_kinds: list[str] | None = None,
    host: str = "tracera.test",
    port: int = 8080,
    base_url: str | None = None,
) -> RuntimeConfig:
    return RuntimeConfig(
        path=__import__("pathlib").Path("/tmp/_test_config.yaml"),  # nosec B108 — explicit test fixture path, not user input
        schema_version=1,
        tracera=TraceraConfig(
            host=host,
            port=port,
            base_url=base_url,
            api_token=None,
            enabled=tracera_enabled,
            flush_interval_s=30,
            batch_size=10,
            retry_max=3,
            health_check_on_init=health_check_on_init,
            timeout_s=5,
        ),
        evidence=EvidenceConfig(
            base_url=None,
            rate_limit_per_min=60,
            circuit_breaker_threshold=5,
        ),
        trace_bridges=TraceBridgesConfig(
            dual_write=dual_write,
            dual_write_default=dual_write,
            dual_write_sample_rate=1.0,
            include_kinds=list(include_kinds or []),
            cohort_policies={
                "dev": "on" if dual_write else "off",
                "staging": "off",
                "prod": "off",
            },
            env_overrides={
                "dev": "config/dev.yaml",
                "staging": "config/staging.yaml",
                "prod": "config/prod.yaml",
            },
            active_environment="dev",
        ),
    )


@pytest.fixture(autouse=True)
def _reset_state() -> Any:
    """Reset module-level _LAST_STATE between tests."""
    import pheno.runtime as runtime_mod

    runtime_mod._LAST_STATE = None
    reload()  # also clear the lru_cache on runtime_config.load_config
    yield
    runtime_mod._LAST_STATE = None


class TestStartDisabled:
    """When dual_write is off, start() returns a disabled state with no adapter."""

    def test_dual_write_false_returns_disabled(self) -> None:
        cfg = _make_config(dual_write=False, tracera_enabled=True)
        state = start(config=cfg)
        assert state.disabled is True
        assert state.adapter is None
        assert state.bridge is None
        assert state.is_dual_writing is False

    def test_tracera_disabled_means_no_bridge(self) -> None:
        cfg = _make_config(dual_write=True, tracera_enabled=False)
        state = start(config=cfg)
        assert state.disabled is True
        assert state.adapter is None
        assert state.bridge is None

    def test_both_disabled_returns_disabled(self) -> None:
        cfg = _make_config(dual_write=False, tracera_enabled=False)
        state = start(config=cfg)
        assert state.disabled is True
        assert state.summary()["tracera_endpoint"] == "http://tracera.test:8080"


class TestStartEnabled:
    """When dual_write + tracera.enabled are both True, start() wires the bridge."""

    def test_wires_adapter_and_bridge(self) -> None:
        cfg = _make_config(
            dual_write=True,
            tracera_enabled=True,
            health_check_on_init=False,
        )
        # Stub the health check so the test doesn't need a live server.
        state = start(config=cfg)
        assert state.disabled is False
        assert state.adapter is not None
        assert state.bridge is not None
        assert state.is_dual_writing is True

    def test_health_check_runs_when_enabled(self) -> None:
        cfg = _make_config(
            dual_write=True,
            tracera_enabled=True,
            health_check_on_init=True,
        )
        # Patch TraceraAdapter.health to return 'down' so we exercise the
        # health-check failure path without needing a live server.
        with patch(
            "pheno.trace_store.tracera.TraceraAdapter.health",
            return_value={"status": "down", "error": "test"},
        ):
            state = start(config=cfg)
        assert state.disabled is False
        assert state.health_ok is False
        assert state.error is not None
        # Bridge is still wired — flush() errors will be logged but not raised.
        assert state.bridge is not None

    def test_override_dual_write_enables(self) -> None:
        cfg = _make_config(
            dual_write=False,
            tracera_enabled=True,
            health_check_on_init=False,
        )
        state = start(config=cfg, override_dual_write=True)
        assert state.disabled is False
        assert state.bridge is not None

    def test_include_kinds_propagates(self) -> None:
        cfg = _make_config(
            dual_write=True,
            tracera_enabled=True,
            health_check_on_init=False,
            include_kinds=["claim", "evidence"],
        )
        state = start(config=cfg)
        assert state.bridge is not None
        assert state.bridge._include_kinds() == ["claim", "evidence"]  # noqa: SLF001 — TraceraBridge method  # noqa: SLF001 — TraceraBridge exposes via property

    def test_collector_attached_when_provided(self) -> None:
        cfg = _make_config(
            dual_write=True,
            tracera_enabled=True,
            health_check_on_init=False,
        )
        # Provide a mock collector; verify bridge.install happens.
        mock_collector = MagicMock()
        with patch("traces.tracera_bridge.install_bridge") as mock_install:
            state = start(config=cfg, collector=mock_collector)
        assert state.collector is mock_collector
        assert mock_install.called
        # install_bridge receives (collector, bridge).
        args = mock_install.call_args[0]
        assert args[0] is mock_collector
        assert args[1] is state.bridge


class TestStop:
    """stop() tears down the bridge (drain buffer + flush)."""

    def test_stop_disabled_is_noop(self) -> None:
        cfg = _make_config(dual_write=False)
        state = start(config=cfg)
        # No exception; no side effects.
        stop(state)
        # _LAST_STATE should remain set for disabled (intentional — caller
        # can still inspect via current_state()).
        assert current_state() is not None

    def test_stop_enabled_flushes_bridge(self) -> None:
        cfg = _make_config(
            dual_write=True,
            tracera_enabled=True,
            health_check_on_init=False,
        )
        state = start(config=cfg)
        with patch.object(state.bridge, "flush") as mock_flush:
            stop(state)
        assert mock_flush.called
        # _LAST_STATE should be cleared after stop.
        assert current_state() is None

    def test_stop_continues_on_flush_failure(self) -> None:
        cfg = _make_config(
            dual_write=True,
            tracera_enabled=True,
            health_check_on_init=False,
        )
        state = start(config=cfg)
        # Make flush raise TraceStoreError — stop should log + not propagate.
        from pheno.trace_store.protocols import TraceStoreError

        with patch.object(
            state.bridge,
            "flush",
            side_effect=TraceStoreError("transport down"),
        ):
            stop(state)  # should not raise
        assert current_state() is None


class TestSummary:
    def test_summary_fields(self) -> None:
        cfg = _make_config(
            dual_write=True,
            tracera_enabled=True,
            health_check_on_init=False,
        )
        state = start(config=cfg)
        summary = state.summary()
        assert summary["disabled"] is False
        assert summary["dual_write"] is True
        assert summary["tracera_enabled"] is True
        assert summary["adapter_present"] is True
        assert summary["bridge_present"] is True
        assert summary["collector_present"] is False
        assert summary["health_ok"] is True
        assert summary["tracera_endpoint"] == "http://tracera.test:8080"


class TestDualWriteContextManager:
    """dual_write() context manager wraps start()/stop() with cleanup guarantee."""

    def test_disabled_state_yields_disabled(self) -> None:
        cfg = _make_config(dual_write=False)
        with dual_write(config=cfg) as state:
            assert state.disabled is True
            assert state.adapter is None

    def test_enabled_state_yields_bridge(self) -> None:
        cfg = _make_config(
            dual_write=True,
            tracera_enabled=True,
            health_check_on_init=False,
        )
        with dual_write(config=cfg) as state:
            assert state.disabled is False
            assert state.bridge is not None

    def test_stop_runs_on_exception(self) -> None:
        cfg = _make_config(
            dual_write=True,
            tracera_enabled=True,
            health_check_on_init=False,
        )
        sentinel = False
        with pytest.raises(ValueError), dual_write(config=cfg):
            sentinel = True
            raise ValueError("oops")
        assert sentinel is True
        # state was stopped on exit; current_state returns None.
        assert current_state() is None

    def test_stop_runs_on_normal_exit(self) -> None:
        cfg = _make_config(
            dual_write=True,
            tracera_enabled=True,
            health_check_on_init=False,
        )
        with dual_write(config=cfg) as state:
            assert state.disabled is False
        assert current_state() is None


class TestCurrentState:
    def test_current_state_returns_latest(self) -> None:
        cfg = _make_config(dual_write=False)
        state = start(config=cfg)
        assert current_state() is state

    def test_current_state_none_before_start(self) -> None:
        # Reset state explicitly via the autouse fixture.
        assert current_state() is None
