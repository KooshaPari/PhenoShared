"""HTTP-style health and readiness probe helpers for cheap-llm-mcp.

Traces to: docs/remediation/OBSERVABILITY.md, docs/remediation/OPS.md, SIDE-OPS-004
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

HealthState = Literal["ok", "degraded", "unhealthy"]
ReadyState = Literal["ready", "not_ready"]


@dataclass
class ComponentProbe:
    name: str
    status: HealthState
    latency_ms: int | None = None
    detail: str | None = None


@dataclass
class HealthResponse:
    """Shape for GET /health (liveness)."""

    status: HealthState
    service: str = "cheap-llm-mcp"
    version: str = "0.4.0"
    uptime_secs: int = 0
    checks: list[ComponentProbe] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReadinessResponse:
    """Shape for GET /ready (readiness)."""

    status: ReadyState
    service: str = "cheap-llm-mcp"
    checks: list[ComponentProbe] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def aggregate_health(checks: list[ComponentProbe]) -> HealthState:
    if not checks:
        return "ok"
    if any(c.status == "unhealthy" for c in checks):
        return "unhealthy"
    if any(c.status == "degraded" for c in checks):
        return "degraded"
    return "ok"


def aggregate_readiness(checks: list[ComponentProbe]) -> ReadyState:
    if not checks:
        return "ready"
    if any(c.status != "ok" for c in checks):
        return "not_ready"
    return "ready"


def build_health_response(
    checks: list[ComponentProbe],
    *,
    service: str = "cheap-llm-mcp",
    version: str = "0.4.0",
    started_at: float | None = None,
) -> HealthResponse:
    uptime = int(time.monotonic() - started_at) if started_at is not None else 0
    return HealthResponse(
        status=aggregate_health(checks),
        service=service,
        version=version,
        uptime_secs=uptime,
        checks=checks,
    )


def build_readiness_response(
    checks: list[ComponentProbe],
    *,
    service: str = "cheap-llm-mcp",
) -> ReadinessResponse:
    return ReadinessResponse(
        status=aggregate_readiness(checks),
        service=service,
        checks=checks,
    )


# Route paths for future HTTP wrapper or reverse-proxy health checks.
HEALTH_PATH = "/health"
READY_PATH = "/ready"
