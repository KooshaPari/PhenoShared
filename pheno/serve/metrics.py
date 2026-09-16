"""In-process counters for pheno-serve-dev."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class Metrics:
    """In-process thread-safe counters for pheno-serve-dev."""

    request_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    by_engine: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._lock = Lock()

    def observe(self, engine: str, latency_ms: float, error: bool = False) -> None:
        """Record a single proxy request observation (thread-safe)."""
        with self._lock:
            self.request_count += 1
            if error:
                self.error_count += 1
            self.total_latency_ms += latency_ms
            self.by_engine[engine] = self.by_engine.get(engine, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-friendly snapshot of the current counters."""
        with self._lock:
            avg = (
                self.total_latency_ms / self.request_count
                if self.request_count
                else 0.0
            )
            return {
                "request_count": self.request_count,
                "error_count": self.error_count,
                "avg_latency_ms": avg,
                "by_engine": dict(self.by_engine),
            }

    def prometheus(self) -> str:
        """Render the metrics in Prometheus text exposition format."""
        snap = self.snapshot()
        lines = [
            "# HELP pheno_serve_requests_total Total proxied requests.",
            "# TYPE pheno_serve_requests_total counter",
            f"pheno_serve_requests_total {snap['request_count']}",
            "# HELP pheno_serve_errors_total Total proxied request errors.",
            "# TYPE pheno_serve_errors_total counter",
            f"pheno_serve_errors_total {snap['error_count']}",
            "# HELP pheno_serve_avg_latency_ms Average proxy latency in milliseconds.",
            "# TYPE pheno_serve_avg_latency_ms gauge",
            f"pheno_serve_avg_latency_ms {snap['avg_latency_ms']:.3f}",
        ]
        for engine, count in snap["by_engine"].items():
            lines.append(
                f'pheno_serve_requests_by_engine_total{{engine="{engine}"}} {count}'
            )
        return "\n".join(lines) + "\n"
