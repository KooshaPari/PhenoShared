"""Health, readiness, and metrics endpoints for dispatch-mcp.

This module is the production-hardening surface for the dispatch-mcp service.
It exposes three pure-Python functions that can be wired into FastMCP, an
HTTP wrapper, or invoked directly by tests:

- :func:`liveness` — process liveness probe. Cheap, no I/O.
- :func:`readiness` — readiness probe. Verifies that required dependencies
  (configuration and outbound HTTP reachability to OmniRoute) are usable.
- :func:`metrics` — Prometheus text-format metrics placeholder.

The module is intentionally side-effect-free at import time. The
``readiness`` probe may contact OmniRoute when explicitly requested via
the ``check_omniroute=True`` flag, but defaults to a pure-config check so
that frequent probes do not stampede the backend.
"""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlparse

import httpx

# Process start time captured at import. Used by liveness() to report
# process uptime without spawning a clock per probe.
_START_TIME = time.monotonic()


def liveness() -> dict[str, Any]:
    """Return process liveness status.

    Always returns ``{"status": "alive", ...}`` when the interpreter is
    responsive. Includes server identity and uptime seconds so that
    operators can confirm process identity in aggregated logs.
    """
    return {
        "status": "alive",
        "server": "dispatch-mcp",
        "uptime_seconds": round(time.monotonic() - _START_TIME, 3),
    }


def readiness(*, check_omniroute: bool = False, timeout: float = 2.0) -> dict[str, Any]:
    """Return readiness status, including a dependency check.

    By default this is a configuration-only check (presence and shape of
    ``OMNIROUTE_URL``). Set ``check_omniroute=True`` to also issue a
    lightweight ``GET`` against ``<OMNIROUTE_URL>/health`` to confirm
    upstream reachability. Outbound checks are off by default to keep
    kubelet probes from stampeding the dispatch backend.

    Returns a dict with at minimum ``status`` (``"ready"`` or
    ``"not_ready"``) and a ``checks`` mapping describing each dependency
    and its outcome. Never raises — failures are reported in the
    payload so that probe consumers can render them.
    """
    checks: dict[str, dict[str, Any]] = {}
    overall_ok = True

    base = os.environ.get("OMNIROUTE_URL", "")
    if not base:
        checks["omniroute_url"] = {
            "ok": False,
            "detail": "OMNIROUTE_URL environment variable is not set",
        }
        overall_ok = False
    else:
        parsed = urlparse(base)
        if parsed.scheme not in ("http", "https"):
            checks["omniroute_url"] = {
                "ok": False,
                "detail": f"OMNIROUTE_URL must use http or https scheme, got: {parsed.scheme!r}",
            }
            overall_ok = False
        else:
            checks["omniroute_url"] = {"ok": True, "scheme": parsed.scheme, "host": parsed.hostname}

    if check_omniroute and overall_ok:
        # Outbound reachability check. Isolated so that a misconfigured
        # URL above cannot mask a transport failure.
        try:
            response = httpx.get(
                f"{base.rstrip('/')}/health",
                timeout=timeout,
                follow_redirects=False,
            )
            response.raise_for_status()
            checks["omniroute_reachable"] = {"ok": True, "status_code": response.status_code}
        except (httpx.HTTPError, httpx.RequestError) as exc:
            checks["omniroute_reachable"] = {"ok": False, "detail": str(exc)}
            overall_ok = False

    return {
        "status": "ready" if overall_ok else "not_ready",
        "server": "dispatch-mcp",
        "checks": checks,
    }


def metrics() -> str:
    """Return metrics in Prometheus text exposition format.

    This is a placeholder implementation that returns static gauge
    values for process up and uptime. Counter metrics are zeroed
    and will be wired to real dispatch instrumentation in a future
    release.
    """
    lines = [
        "# HELP dispatch_mcp_up 1 if the dispatch-mcp process is up, 0 otherwise.",
        "# TYPE dispatch_mcp_up gauge",
        "dispatch_mcp_up 1",
        "# HELP dispatch_mcp_uptime_seconds Seconds since the dispatch-mcp process started.",
        "# TYPE dispatch_mcp_uptime_seconds gauge",
        f"dispatch_mcp_uptime_seconds {round(time.monotonic() - _START_TIME, 3)}",
        "# HELP dispatch_mcp_dispatches_total Number of dispatch calls handled since process start.",
        "# TYPE dispatch_mcp_dispatches_total counter",
        "dispatch_mcp_dispatches_total 0",
        "# HELP dispatch_mcp_dispatch_errors_total Number of dispatch calls that failed since process start.",
        "# TYPE dispatch_mcp_dispatch_errors_total counter",
        "dispatch_mcp_dispatch_errors_total 0",
    ]
    return "\n".join(lines) + "\n"
