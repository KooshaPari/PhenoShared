"""Metric framework for the benchmark harness — covers the full spec §4 matrix."""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Metric:
    """One named measurement with explicit units and provenance."""

    name: str
    value: float
    source: str
    units: str
    higher_is_better: bool = True
    sample_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return asdict(self)


@dataclass
class MetricSet:
    """Collection of Metric records keyed by name with optional aggregation."""

    metrics: dict[str, Metric] = field(default_factory=dict)

    def add(self, metric: Metric) -> None:
        """Add or overwrite a metric by name."""
        self.metrics[metric.name] = metric

    def get(self, name: str) -> Metric | None:
        """Look up a metric by name (case-sensitive)."""
        return self.metrics.get(name)

    def merge(self, other: MetricSet, *, prefix: str = "") -> None:
        """Merge another MetricSet, optionally prefixing keys to avoid collisions."""
        for key, value in other.metrics.items():
            target = f"{prefix}{key}" if prefix else key
            self.metrics[target] = value

    def to_dict(self) -> dict[str, Any]:
        """Return a dict-of-dicts for serialization, keyed by metric name."""
        return {name: m.to_dict() for name, m in self.metrics.items()}

    @classmethod
    def coerce(cls, raw: dict[str, Any]) -> MetricSet:
        """Build a MetricSet from a dict of {name: {value, source, units, ...}}."""
        out = cls()
        for name, entry in raw.items():
            if isinstance(entry, Metric):
                out.add(entry)
                continue
            if isinstance(entry, (int, float)):
                out.add(
                    Metric(
                        name=name,
                        value=float(entry),
                        source="manual",
                        units="",
                        higher_is_better=True,
                    )
                )
                continue
            if not isinstance(entry, dict):
                raise TypeError(f"Cannot coerce metric value for {name!r}: {entry!r}")
            if "value" not in entry:
                raise ValueError(
                    f"Metric dict for {name!r} missing required 'value' field"
                )
            try:
                value = float(entry["value"])
            except (TypeError, ValueError) as exc:
                raise TypeError(
                    f"Cannot coerce metric value for {name!r}: {entry!r}"
                ) from exc
            if not math.isfinite(value):
                raise ValueError(f"Metric value for {name!r} is not finite: {value!r}")
            out.add(
                Metric(
                    name=name,
                    value=value,
                    source=str(entry.get("source", "manual")),
                    units=str(entry.get("units", "")),
                    higher_is_better=bool(entry.get("higher_is_better", True)),
                    sample_size=int(entry.get("sample_size", 0)),
                )
            )
        return out

    def to_jsonable(self) -> dict[str, float | dict[str, Any]]:
        """Flatten to {name: value} for compact UI rendering."""
        return {name: m.value for name, m in self.metrics.items()}


# Spec §4 metric catalog. Keep this list synchronized with the spec.
SPEC_Q4_METRICS: tuple[str, ...] = (
    # 4.1 Quality
    "pass@1",
    "pass@1_ci95",
    "pass@4",
    "perplexity",
    # 4.2 Tool-call stability
    "tool_call_success_rate",
    "tool_call_latency_p50",
    "tool_call_latency_p95",
    "dead_end_rate",
    "retry_rate",
    "format_error_rate",
    # 4.3 HW/SW performance
    "wall_clock_total",
    "time_to_first_token_p50",
    "time_to_first_token_p95",
    "tokens_per_sec_throughput",
    "peak_RSS_MB",
    "peak_GPU_mem_MB",
    "energy_proxy_joules",
    # 4.4 Speed
    "first_token_latency_p95",
    "time_per_task_p50",
    "time_per_task_p95",
    # 4.5 Conciseness
    "mean_tokens_per_completion",
    "mean_tool_calls_per_task",
    "redundant_tool_call_rate",
    # 4.6 Long-horizon stability
    "semantic_drift_p99",
    "context_window_saturation_pct",
)


def percentile(values: Sequence[float], pct: float) -> float:
    """Compute pct-th percentile (0-100 inclusive) using linear interpolation."""
    if not values:
        return float("nan")
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return float(sorted_vals[int(k)])
    return float(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo))


def mean(values: Iterable[float]) -> float:
    """Mean with empty-input guard (returns NaN)."""
    items = [float(v) for v in values]
    if not items:
        return float("nan")
    return statistics.fmean(items)


def wilson_ci(passes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% binomial CI; returns (center, half-width)."""
    if total <= 0:
        return (float("nan"), float("nan"))
    p = passes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = (z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))) / denom
    return (center, margin)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity between two equal-length non-zero vectors."""
    if len(a) != len(b):
        raise ValueError(f"Length mismatch: {len(a)} vs {len(b)}")
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    na = math.sqrt(sum(float(x) * float(x) for x in a))
    nb = math.sqrt(sum(float(y) * float(y) for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def semantic_drift(original: Sequence[float], current: Sequence[float]) -> float:
    """Drift = 1 - cosine(original, current), bounded in [0, 2]."""
    return 1.0 - cosine_similarity(original, current)
