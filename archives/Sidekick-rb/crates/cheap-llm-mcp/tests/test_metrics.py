"""Tests for metrics module (SIDE-OBS-005)."""

from __future__ import annotations

from cheap_llm_mcp.metrics import (
    METRIC_LLM_COST_USD,
    METRIC_LLM_REQUESTS,
    MetricsRegistry,
    RequestTimer,
)


def test_metrics_counter_increments() -> None:
    reg = MetricsRegistry()
    reg.inc(METRIC_LLM_REQUESTS, labels={"provider": "minimax"})
    reg.inc(METRIC_LLM_REQUESTS, labels={"provider": "minimax"})
    snap = reg.snapshot()
    assert snap.counters[f'{METRIC_LLM_REQUESTS}{{provider="minimax"}}'] == 2


def test_metrics_histogram_observes() -> None:
    reg = MetricsRegistry()
    with RequestTimer(reg, labels={"op": "complete"}):
        pass
    snap = reg.snapshot()
    assert len(snap.histograms) == 1


def test_prometheus_text_export() -> None:
    reg = MetricsRegistry()
    reg.inc(METRIC_LLM_COST_USD, value=0.001)
    text = reg.to_prometheus_text()
    assert METRIC_LLM_COST_USD in text
