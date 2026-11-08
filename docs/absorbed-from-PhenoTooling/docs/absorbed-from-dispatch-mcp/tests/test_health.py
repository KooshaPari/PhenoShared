"""Tests for dispatch_mcp.health.

The health module is pure-Python (no FastMCP coupling) so these tests
do not need to patch the HTTP client the way test_server.py does.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from dispatch_mcp import health


class TestLiveness:
    """Tests for the liveness probe."""

    def test_liveness_returns_alive(self) -> None:
        result = health.liveness()
        assert result["status"] == "alive"
        assert result["server"] == "dispatch-mcp"

    def test_liveness_reports_uptime(self) -> None:
        result = health.liveness()
        assert "uptime_seconds" in result
        assert isinstance(result["uptime_seconds"], (int, float))
        assert result["uptime_seconds"] >= 0.0


class TestReadiness:
    """Tests for the readiness probe."""

    def test_ready_when_omniroute_url_set(self) -> None:
        with patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}):
            result = health.readiness()
        assert result["status"] == "ready"
        assert result["checks"]["omniroute_url"]["ok"] is True
        assert result["checks"]["omniroute_url"]["scheme"] == "http"

    def test_not_ready_when_omniroute_url_missing(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = health.readiness()
        assert result["status"] == "not_ready"
        assert result["checks"]["omniroute_url"]["ok"] is False
        assert "not set" in result["checks"]["omniroute_url"]["detail"]

    def test_readiness_does_not_contact_omniroute_by_default(self) -> None:
        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}),
            patch("dispatch_mcp.health.httpx.get") as mock_get,
        ):
            health.readiness()
            mock_get.assert_not_called()

    def test_readiness_reports_reachable_when_upstream_ok(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}),
            patch("dispatch_mcp.health.httpx.get", return_value=mock_response) as mock_get,
        ):
            result = health.readiness(check_omniroute=True)
        assert result["status"] == "ready"
        assert result["checks"]["omniroute_reachable"]["ok"] is True
        mock_get.assert_called_once()

    def test_readiness_reports_unreachable_when_upstream_fails(self) -> None:
        with (
            patch.dict("os.environ", {"OMNIROUTE_URL": "http://localhost:8080"}),
            patch(
                "dispatch_mcp.health.httpx.get",
                side_effect=httpx.ConnectError("refused"),
            ),
        ):
            result = health.readiness(check_omniroute=True)
        assert result["status"] == "not_ready"
        assert result["checks"]["omniroute_reachable"]["ok"] is False


class TestMetrics:
    """Tests for the Prometheus text-format metrics endpoint."""

    def test_metrics_returns_prometheus_text(self) -> None:
        payload = health.metrics()
        assert "# HELP dispatch_mcp_up" in payload
        assert "# TYPE dispatch_mcp_up gauge" in payload
        assert "dispatch_mcp_up 1" in payload
        assert "dispatch_mcp_uptime_seconds" in payload
        assert "dispatch_mcp_dispatches_total" in payload
        assert "dispatch_mcp_dispatch_errors_total" in payload

    def test_metrics_ends_with_newline(self) -> None:
        assert health.metrics().endswith("\n")
