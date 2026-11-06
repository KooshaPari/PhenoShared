"""Tests for health_probe module (SIDE-OPS-004)."""

from __future__ import annotations

from cheap_llm_mcp.health_probe import (
    HEALTH_PATH,
    READY_PATH,
    ComponentProbe,
    aggregate_health,
    aggregate_readiness,
    build_health_response,
    build_readiness_response,
)


def test_health_paths_are_documented() -> None:
    assert HEALTH_PATH == "/health"
    assert READY_PATH == "/ready"


def test_aggregate_health_unhealthy_wins() -> None:
    checks = [
        ComponentProbe("a", "ok"),
        ComponentProbe("b", "unhealthy"),
    ]
    assert aggregate_health(checks) == "unhealthy"


def test_aggregate_readiness_not_ready_on_degraded() -> None:
    checks = [ComponentProbe("router", "degraded")]
    assert aggregate_readiness(checks) == "not_ready"


def test_build_health_response_serializes() -> None:
    resp = build_health_response([ComponentProbe("cfg", "ok", latency_ms=1)])
    d = resp.to_dict()
    assert d["status"] == "ok"
    assert d["service"] == "cheap-llm-mcp"
    assert len(d["checks"]) == 1


def test_build_readiness_response_ready() -> None:
    resp = build_readiness_response([ComponentProbe("ledger", "ok")])
    assert resp.to_dict()["status"] == "ready"
