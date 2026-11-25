"""Reusable mock backend harness for protocol compliance tests.

W2.1 of the V5 plan: ``MockBackend`` simulates a tier response so
``dispatch_mcp.server`` can be exercised end-to-end in subsequent W2.x
plans without a real provider.

This module is intentionally self-contained (stdlib + pytest only) and
must not import from ``dispatch_mcp.server`` to avoid import cycles when
the server itself is being patched in other tests.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest


class MockBackend:
    """Mock implementation of a tier backend.

    Mirrors the wire shape that the real providers (Forge/Codex/etc.)
    return over HTTP:

    * ``tier``              - the tier name this backend represents
    * ``status_code``       - HTTP-style status; >= 400 signals failure
    * ``response_delay_ms`` - artificial delay before returning
    * ``response_body``     - dict to return on success / payload to inspect on failure
    """

    DEFAULT_BODY: dict[str, Any] = {"ok": True}

    def __init__(
        self,
        tier: str = "main",
        status_code: int = 200,
        response_delay_ms: int = 0,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        self.tier = tier
        self.status_code = status_code
        self.response_delay_ms = response_delay_ms
        self.response_body: dict[str, Any] = (
            response_body if response_body is not None else dict(self.DEFAULT_BODY)
        )

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return the configured body, honoring delay and error semantics.

        Raises ``RuntimeError`` when ``status_code >= 400`` *and* the
        body is a dict containing an ``error`` key - matching the shape
        the real providers return on failure.
        """
        if self.response_delay_ms > 0:
            await asyncio.sleep(self.response_delay_ms / 1000.0)
        if (
            self.status_code >= 400
            and isinstance(self.response_body, dict)
            and "error" in self.response_body
        ):
            detail = self.response_body["error"]
            raise RuntimeError(
                f"mock backend error: tier={self.tier!r} "
                f"status={self.status_code} detail={detail!r}"
            )
        return self.response_body


@pytest.fixture
def mock_backend() -> MockBackend:
    """Yield a fresh ``MockBackend`` with default configuration.

    The instance is fresh per-test so individual tests can mutate it
    without leaking state across cases.
    """
    return MockBackend()
