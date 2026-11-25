"""traces/metrics.py — Tracera bridge + dual-write metrics.

Exposes a small, hermetic-friendly metrics surface for the
`TraceraBridge`. Two consumers are anticipated:

1. **On-call dashboards** (Grafana, Datadog) — the `_to_prometheus()`
   helper serializes counters to Prometheus text format.
2. **In-process introspection** — the `BridgeMetrics` dataclass
   captures counters atomically and exposes them via `.to_dict()`.

Metrics:

- `bridge_events_total` — every event processed by `emit()`
- `bridge_events_jsonl` — events written to the JSONL sink
- `bridge_events_tracera` — events written to Tracera
- `bridge_events_skipped_kind` — events skipped because `kind` was filtered
- `bridge_events_skipped_sample` — events skipped by sample rate
- `bridge_errors_tracera` — Tracera adapter failures (fail-soft)

These counters are also exposed via the existing bridge properties
(`bridge.emitted_total`, etc.). The `BridgeMetrics` dataclass is
intended for cases where callers want a single immutable snapshot.

Refs:
- v0.13 WBS-PERT-100 task 17 (Tracera metrics).
- v0.13 WBS-PERT-100 task 18 (alerting on error rate > 5%).
- `traces/tracera_bridge.py` (the bridge itself).
- `pheno/runtime_config.py` (config knobs the metrics surface).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from traces.tracera_bridge import TraceraBridge


# Alert threshold: when > 5% of attempted Tracera emits fail, surface
# as a warning. Used by `alert_error_rate()` and surfaced to the MCP
# `summary://fleet` dashboard.
DEFAULT_ERROR_RATE_THRESHOLD = 0.05


@dataclass(frozen=True)
class BridgeMetrics:
    """Immutable snapshot of TraceraBridge counters.

    Attributes:
        events_total: total events processed by `emit()`.
        events_jsonl: events written to the JSONL sink.
        events_tracera: events written to the Tracera adapter.
        events_skipped_kind: events skipped because the kind was filtered.
        events_skipped_sample: events skipped by the sample-rate gate.
        errors_tracera: Tracera adapter failures (fail-soft).
    """

    events_total: int
    events_jsonl: int
    events_tracera: int
    events_skipped_kind: int
    events_skipped_sample: int
    errors_tracera: int

    @property
    def tracera_attempts(self) -> int:
        """Total events that *attempted* a Tracera emit.

        Successful Tracera emits + kind-skipped + sample-skipped +
        Tracera-errored. Excludes the JSONL-only fallback when
        `dual_write=False` (those are not Tracera attempts).
        """
        return (
            self.events_tracera
            + self.events_skipped_kind
            + self.events_skipped_sample
            + self.errors_tracera
        )

    @property
    def error_rate(self) -> float:
        """Fraction of Tracera attempts that errored (0.0-1.0).

        Returns 0.0 when there have been no attempts.
        """
        if self.tracera_attempts == 0:
            return 0.0
        return self.errors_tracera / self.tracera_attempts

    def to_dict(self) -> dict[str, int | float]:
        """Return a JSON-serializable snapshot including the error rate."""
        return {
            "events_total": self.events_total,
            "events_jsonl": self.events_jsonl,
            "events_tracera": self.events_tracera,
            "events_skipped_kind": self.events_skipped_kind,
            "events_skipped_sample": self.events_skipped_sample,
            "errors_tracera": self.errors_tracera,
            "tracera_attempts": self.tracera_attempts,
            "error_rate": self.error_rate,
        }


def snapshot(bridge: TraceraBridge) -> BridgeMetrics:
    """Capture an immutable snapshot of the bridge's counters.

    Args:
        bridge: an active TraceraBridge instance.

    Returns:
        A BridgeMetrics dataclass with the current counter values.
    """
    return BridgeMetrics(
        events_total=bridge.emitted_total,
        events_jsonl=bridge.emitted_jsonl,
        events_tracera=bridge.emitted_tracera,
        events_skipped_kind=bridge.skipped_kind,
        events_skipped_sample=bridge.skipped_sample,
        errors_tracera=bridge.tracera_errors,
    )


def alert_error_rate(
    bridge: TraceraBridge,
    *,
    threshold: float = DEFAULT_ERROR_RATE_THRESHOLD,
) -> dict[str, Any]:
    """Check the bridge's error rate against a threshold.

    Args:
        bridge: an active TraceraBridge instance.
        threshold: max acceptable error rate (0.0-1.0). Defaults to
            `DEFAULT_ERROR_RATE_THRESHOLD` (5%).

    Returns:
        A dict with keys:
        - `alert_fired` (bool): True when error_rate > threshold.
        - `error_rate` (float): observed error rate.
        - `threshold` (float): the threshold used.
        - `samples` (int): number of Tracera attempts in the window.
        - `severity` (str): "ok", "warn", or "critical".

        The severity ladder:
        - `error_rate < threshold` → "ok"
        - `threshold <= error_rate < 2*threshold` → "warn"
        - `error_rate >= 2*threshold` → "critical"
    """
    metrics = snapshot(bridge)
    error_rate = metrics.error_rate
    if error_rate < threshold:
        severity = "ok"
    elif error_rate < 2 * threshold:
        severity = "warn"
    else:
        severity = "critical"
    return {
        "alert_fired": error_rate > threshold,
        "error_rate": error_rate,
        "threshold": threshold,
        "samples": metrics.tracera_attempts,
        "severity": severity,
        "events_total": metrics.events_total,
        "events_tracera": metrics.events_tracera,
        "errors_tracera": metrics.errors_tracera,
    }


def to_prometheus(metrics: BridgeMetrics, *, prefix: str = "tracera_bridge_") -> str:
    """Serialize metrics to Prometheus text format.

    Args:
        metrics: a BridgeMetrics snapshot.
        prefix: metric name prefix. Defaults to `tracera_bridge_`.

    Returns:
        Multi-line string in Prometheus exposition format. The
        `error_rate` is exposed as a gauge with a `severity` label
        for downstream alert routing.
    """
    lines = [
        f"# HELP {prefix}events_total Total events processed by TraceraBridge.emit().",
        f"# TYPE {prefix}events_total counter",
        f"{prefix}events_total {metrics.events_total}",
        f"# HELP {prefix}events_jsonl Events written to the JSONL sink.",
        f"# TYPE {prefix}events_jsonl counter",
        f"{prefix}events_jsonl {metrics.events_jsonl}",
        f"# HELP {prefix}events_tracera Events written to Tracera.",
        f"# TYPE {prefix}events_tracera counter",
        f"{prefix}events_tracera {metrics.events_tracera}",
        f"# HELP {prefix}events_skipped_kind Events skipped because kind was filtered.",
        f"# TYPE {prefix}events_skipped_kind counter",
        f"{prefix}events_skipped_kind {metrics.events_skipped_kind}",
        f"# HELP {prefix}events_skipped_sample Events skipped by the sample-rate gate.",
        f"# TYPE {prefix}events_skipped_sample counter",
        f"{prefix}events_skipped_sample {metrics.events_skipped_sample}",
        f"# HELP {prefix}errors_tracera Tracera adapter failures (fail-soft).",
        f"# TYPE {prefix}errors_tracera counter",
        f"{prefix}errors_tracera {metrics.errors_tracera}",
        f"# HELP {prefix}error_rate Fraction of Tracera attempts that errored (0.0-1.0).",
        f"# TYPE {prefix}error_rate gauge",
        f'{prefix}error_rate{{severity="computed"}} {metrics.error_rate:.6f}',
    ]
    return "\n".join(lines) + "\n"


__all__ = [
    "BridgeMetrics",
    "DEFAULT_ERROR_RATE_THRESHOLD",
    "alert_error_rate",
    "asdict",
    "snapshot",
    "to_prometheus",
]
