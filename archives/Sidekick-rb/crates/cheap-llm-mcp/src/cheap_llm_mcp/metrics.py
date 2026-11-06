"""Prometheus-style metrics hooks for cheap-llm-mcp.

Traces to: docs/remediation/OBSERVABILITY.md, SIDE-OBS-005
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

# Standard metric names (audit contract; wire to prometheus_client in follow-up).
METRIC_LLM_REQUESTS = "sidekick_llm_requests_total"
METRIC_LLM_ERRORS = "sidekick_llm_errors_total"
METRIC_LLM_DURATION = "sidekick_llm_request_duration_seconds"
METRIC_LLM_COST_USD = "sidekick_llm_cost_usd_total"


@dataclass
class MetricsSnapshot:
    counters: dict[str, float] = field(default_factory=dict)
    histograms: dict[str, list[float]] = field(default_factory=dict)


class MetricsRegistry:
    """Thread-safe in-process metrics registry (Prometheus text export ready)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)

    def inc(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        key = _label_key(name, labels)
        with self._lock:
            self._counters[key] += value

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = _label_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            return MetricsSnapshot(
                counters=dict(self._counters),
                histograms={k: list(v) for k, v in self._histograms.items()},
            )

    def to_prometheus_text(self) -> str:
        snap = self.snapshot()
        lines: list[str] = []
        for key, val in sorted(snap.counters.items()):
            name, label_str = _split_key(key)
            lines.append(f"{name}{label_str} {val}")
        for key, vals in sorted(snap.histograms.items()):
            name, label_str = _split_key(key)
            if vals:
                lines.append(f"{name}_count{label_str} {len(vals)}")
                lines.append(f"{name}_sum{label_str} {sum(vals)}")
        return "\n".join(lines) + ("\n" if lines else "")


class RequestTimer:
    """Context manager to observe request duration."""

    def __init__(
        self,
        registry: MetricsRegistry,
        metric: str = METRIC_LLM_DURATION,
        labels: dict[str, str] | None = None,
    ) -> None:
        self._registry = registry
        self._metric = metric
        self._labels = labels
        self._start: float = 0.0

    def __enter__(self) -> RequestTimer:
        self._start = time.monotonic()
        return self

    def __exit__(self, *args: Any) -> None:
        elapsed = time.monotonic() - self._start
        self._registry.observe(self._metric, elapsed, self._labels)


# Process-wide default registry (opt-in; no side effects until used).
default_registry = MetricsRegistry()


def _label_key(name: str, labels: dict[str, str] | None) -> str:
    if not labels:
        return name
    parts = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return f"{name}{{{parts}}}"


def _split_key(key: str) -> tuple[str, str]:
    if "{" not in key:
        return key, ""
    name, rest = key.split("{", 1)
    return name, "{" + rest
