"""Tests for the :mod:`dispatch_mcp.core.cost_middleware` middleware.

The :class:`CostAwareRouter` is the integration point that
composes the cost calculator, budget enforcer, quota tracker, and
audit trail around the base :class:`OmniHttpAdapter`. These tests
use a fake inner router so the middleware can be exercised in
isolation from any HTTP transport.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from dispatch_mcp.core.audit import AuditLog
from dispatch_mcp.core.budget import BudgetExceeded, BudgetPolicy, BudgetTracker
from dispatch_mcp.core.cost import CostCalculator
from dispatch_mcp.core.cost_middleware import (
    CostAwareRouter,
    CostMiddlewareConfig,
    TierWorker,
)
from dispatch_mcp.core.protocol import (
    ProtocolInfo,
    ServerCapabilities,
    ServerInfo,
)
from dispatch_mcp.core.quota import (
    QuotaExceeded,
    QuotaPolicy,
    QuotaTracker,
)
from dispatch_mcp.core.tiers import DEFAULT_REGISTRY, TierRegistry
from dispatch_mcp.core.types import JobResult


# ---------------------------------------------------------------------------
# Fake inner router
# ---------------------------------------------------------------------------


class FakeInner:
    """A minimal stand-in for the :class:`OmniHttpAdapter` transport.

    Mirrors the structural surface the middleware delegates to. The
    caller controls the response via the ``responder`` callable so
    every test can dial in a custom response, raise an error, etc.
    """

    def __init__(
        self,
        responder: Any | None = None,
        *,
        protocol_info: ProtocolInfo | None = None,
    ) -> None:
        self._responder = responder or (
            lambda message, tier, payload: {
                "ok": True,
                "tier": tier,
                "message": f"echo: {message}",
                "usage": {"input_tokens": 100, "output_tokens": 50},
            }
        )
        self._protocol_info = protocol_info
        self.client: Any = None  # Router protocol compatibility
        self.dispatched: list[dict[str, Any]] = []

    # Legacy Worker-port shape (positional, sync, returns dict).
    def dispatch(
        self, message: str, tier: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self.dispatched.append(
            {"message": message, "tier": tier, "payload": payload}
        )
        return self._responder(message, tier, payload)

    # Router-port shape (keyword-only, async, returns JobResult).
    async def dispatch_message(
        self,
        *,
        tier: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> JobResult:
        body = self.dispatch(message, tier, payload)
        return JobResult(
            ok=body.get("ok") if isinstance(body.get("ok"), bool) else None,
            tier=str(body.get("tier") or tier),
            message=body.get("message") if isinstance(body.get("message"), str) else None,
        )

    def health(self) -> dict[str, Any]:
        return {"status": "ok"}

    def cancel(self, request_id: str) -> bool:
        return True

    def close(self) -> None:
        pass

    def ping(self) -> JobResult:
        return JobResult(status="alive", message="pong")

    def protocol_info(self) -> ProtocolInfo:
        if self._protocol_info is not None:
            return self._protocol_info
        return ProtocolInfo(
            serverVersion="0.0.0+test",
            supportedVersions=["2025-03-26", "2025-06-18"],
            defaultVersion="2025-03-26",
            negotiatedVersion="2025-03-26",
            capabilities=ServerCapabilities(),
            serverInfo=ServerInfo(name="dispatch-mcp", version="0.0.0+test"),
        )


# ---------------------------------------------------------------------------
# CostMiddlewareConfig
# ---------------------------------------------------------------------------


def test_config_defaults_enable_all_subsystems() -> None:
    """The default config enables cost tracking and instantiates fresh state."""
    config = CostMiddlewareConfig()
    assert config.enabled is True
    assert config.registry is DEFAULT_REGISTRY
    assert isinstance(config.budget, BudgetTracker)
    assert isinstance(config.quota, QuotaTracker)
    assert isinstance(config.audit, AuditLog)


def test_config_uses_custom_subsystems() -> None:
    """Custom subsystems are honored (no copy on read)."""
    registry = TierRegistry()
    budget = BudgetTracker(policy=BudgetPolicy(global_limit_usd=10.0))
    quota = QuotaTracker(
        policy=QuotaPolicy(max_requests_per_window=5)
    )
    audit = AuditLog(max_entries=10)
    config = CostMiddlewareConfig(
        enabled=True,
        registry=registry,
        budget=budget,
        quota=quota,
        audit=audit,
    )
    assert config.registry is registry
    assert config.budget is budget
    assert config.quota is quota
    assert config.audit is audit


# ---------------------------------------------------------------------------
# Basic dispatch (enabled)
# ---------------------------------------------------------------------------


def test_dispatch_message_records_cost_metadata_in_result() -> None:
    """A successful dispatch enriches the JobResult with cost fields."""
    inner = FakeInner()
    router = CostAwareRouter(inner)
    result = asyncio.run(router.dispatch_message(tier="haiku", message="hi"))
    assert isinstance(result, JobResult)
    assert result.ok is True
    assert result.tier == "haiku"
    # The inner FakeInner returned input_tokens=100, output_tokens=50.
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    # haiku: 100 * 0.80/M + 50 * 4.00/M = 0.00008 + 0.0002 = 0.00028.
    assert result.cost_usd == pytest.approx(0.00028)
    assert result.model == "claude-3-5-haiku-20241022"
    assert result.request_id  # auto-generated UUID


def test_dispatch_alias_matches_dispatch_message() -> None:
    """``dispatch`` is a backward-compat alias for ``dispatch_message``."""
    inner = FakeInner()
    router = CostAwareRouter(inner)
    result = asyncio.run(router.dispatch(tier="haiku", message="hello"))
    assert result.ok is True
    assert result.tier == "haiku"


def test_dispatch_message_charges_budget_and_quota() -> None:
    """A successful dispatch advances both budget and quota counters."""
    inner = FakeInner()
    router = CostAwareRouter(inner)
    asyncio.run(router.dispatch_message(tier="haiku", message="hi"))
    # The budget tracker recorded $0.00028 of haiku spend.
    snap = router.config.budget.snapshot("haiku")
    assert snap.spend_usd == pytest.approx(0.00028)
    assert snap.request_count == 1
    # The quota tracker recorded a 150-token dispatch (100+50) to haiku.
    qsnap = router.config.quota.snapshot("haiku")
    assert qsnap.requests_used == 1
    assert qsnap.tokens_used == 150


def test_dispatch_message_appends_audit_entry_allowed() -> None:
    """A successful dispatch records an ``allowed`` audit entry."""
    inner = FakeInner()
    audit = AuditLog()
    config = CostMiddlewareConfig(audit=audit)
    router = CostAwareRouter(inner, config=config)
    asyncio.run(router.dispatch_message(tier="haiku", message="hi"))
    entries = audit.entries()
    assert len(entries) == 1
    e = entries[0]
    assert e.decision == "allowed"
    assert e.reason == "ok"
    assert e.tier == "haiku"
    assert e.model == "claude-3-5-haiku-20241022"
    assert e.cost_usd == pytest.approx(0.00028)
    assert e.is_priced is True


# ---------------------------------------------------------------------------
# Disabled middleware (pass-through)
# ---------------------------------------------------------------------------


def test_dispatch_passthrough_skips_cost_tracking_when_disabled() -> None:
    """``enabled=False`` routes through the inner adapter with no policy."""
    inner = FakeInner()
    config = CostMiddlewareConfig(enabled=False)
    router = CostAwareRouter(inner, config=config)
    result = asyncio.run(router.dispatch_message(tier="haiku", message="hi"))
    assert result.ok is True
    # No cost fields populated in the pass-through path.
    assert result.cost_usd is None
    assert result.input_tokens is None
    # Audit log is untouched.
    assert router.config.audit.entries() == ()
    # Budget/quota were not charged.
    assert router.config.budget.snapshot().spend_usd == 0.0


# ---------------------------------------------------------------------------
# Quota gate
# ---------------------------------------------------------------------------


def test_dispatch_message_quota_exceeded_blocks_dispatch() -> None:
    """A quota-refused dispatch raises ``QuotaExceeded`` and records a blocked audit."""
    inner = FakeInner()
    quota = QuotaTracker(
        policy=QuotaPolicy(max_requests_per_window=1)
    )
    audit = AuditLog()
    config = CostMiddlewareConfig(quota=quota, audit=audit)
    router = CostAwareRouter(inner, config=config)

    # First call consumes the single request slot.
    asyncio.run(router.dispatch_message(tier="haiku", message="first"))

    # Second call hits the quota and is refused.
    with pytest.raises(QuotaExceeded):
        asyncio.run(router.dispatch_message(tier="haiku", message="second"))

    # The audit log has 1 allowed + 1 blocked.
    decisions = [e.decision for e in audit.entries()]
    assert decisions == ["allowed", "blocked"]
    # Blocked entry has the right reason and zero cost.
    blocked = audit.entries()[1]
    assert blocked.reason == "quota"
    assert blocked.cost_usd == 0.0


# ---------------------------------------------------------------------------
# Budget gate
# ---------------------------------------------------------------------------


def test_dispatch_message_budget_exceeded_blocks_dispatch() -> None:
    """A budget-refused dispatch raises ``BudgetExceeded`` and records a blocked audit."""
    inner = FakeInner()
    budget = BudgetTracker(
        policy=BudgetPolicy(global_limit_usd=0.0001)  # absurdly small cap
    )
    audit = AuditLog()
    config = CostMiddlewareConfig(budget=budget, audit=audit)
    router = CostAwareRouter(inner, config=config)

    with pytest.raises(BudgetExceeded):
        asyncio.run(router.dispatch_message(tier="haiku", message="hi"))

    decisions = [e.decision for e in audit.entries()]
    assert decisions == ["blocked"]
    blocked = audit.entries()[0]
    assert blocked.reason == "budget"
    assert blocked.cost_usd == 0.0


def test_dispatch_message_does_not_charge_budget_for_upstream_failure() -> None:
    """An upstream error records a blocked entry but does not charge spend."""
    def failing_responder(message, tier, payload):
        raise RuntimeError("upstream down")

    inner = FakeInner(responder=failing_responder)
    audit = AuditLog()
    config = CostMiddlewareConfig(audit=audit)
    router = CostAwareRouter(inner, config=config)

    with pytest.raises(RuntimeError, match="upstream down"):
        asyncio.run(router.dispatch_message(tier="haiku", message="hi"))

    # Spend was NOT recorded — the dispatch never happened.
    assert router.config.budget.snapshot().spend_usd == 0.0
    # Quota usage was also NOT recorded.
    assert router.config.quota.snapshot().requests_used == 0
    # The audit log still has a blocked entry tagged "upstream_error".
    entries = audit.entries()
    assert len(entries) == 1
    assert entries[0].decision == "blocked"
    assert entries[0].reason == "upstream_error"
    assert entries[0].detail["error"] == "RuntimeError"
    assert "upstream down" in entries[0].detail["message"]


# ---------------------------------------------------------------------------
# Unknown tier
# ---------------------------------------------------------------------------


def test_dispatch_message_unknown_tier_marks_unpriced() -> None:
    """An unregistered tier reports ``is_priced=False`` and zero cost."""
    inner = FakeInner()
    router = CostAwareRouter(inner)
    result = asyncio.run(
        router.dispatch_message(tier="mystery-tier", message="hi")
    )
    assert result.ok is True
    assert result.cost_usd == 0.0
    assert result.model == "unknown"
    # The audit entry is marked unpriced.
    entry = router.config.audit.entries()[0]
    assert entry.is_priced is False
    assert entry.cost_usd == 0.0


# ---------------------------------------------------------------------------
# Per-tier worker
# ---------------------------------------------------------------------------


def test_worker_returns_callable_bound_to_tier() -> None:
    """``worker(tier)`` returns a ``TierWorker`` that dispatches to that tier."""
    inner = FakeInner()
    router = CostAwareRouter(inner)
    w = router.worker("haiku")
    assert isinstance(w, TierWorker)
    assert repr(w) == "TierWorker(tier='haiku')"

    result = asyncio.run(w("hi"))
    assert result.ok is True
    assert result.tier == "haiku"
    # The inner adapter saw the dispatch with the right tier.
    assert inner.dispatched[0]["tier"] == "haiku"


def test_worker_does_not_pass_tier_as_kwarg() -> None:
    """The TierWorker calls the legacy positional ``dispatch`` (not keyword)."""
    inner = FakeInner()
    router = CostAwareRouter(inner)
    asyncio.run(router.worker("opus")("hi"))
    # The inner recorded exactly one dispatch with tier='opus'.
    assert inner.dispatched == [{"message": "hi", "tier": "opus", "payload": None}]


# ---------------------------------------------------------------------------
# health / ping / protocol_info / close
# ---------------------------------------------------------------------------


def test_health_returns_job_result() -> None:
    """``health`` returns a typed :class:`JobResult` from the inner dict."""
    inner = FakeInner()
    router = CostAwareRouter(inner)
    result = asyncio.run(router.health())
    assert isinstance(result, JobResult)
    assert result.status == "ok"


def test_ping_forwards_to_inner_ping() -> None:
    """``ping`` returns whatever the inner adapter reports."""
    inner = FakeInner()
    router = CostAwareRouter(inner)
    result = asyncio.run(router.ping())
    assert result.status == "alive"
    assert result.message == "pong"


def test_ping_synthesizes_alive_when_inner_missing() -> None:
    """``ping`` returns a synthetic ``alive`` result when the inner has no ping."""
    class NoPing:
        """A bare inner router with no ``ping`` method (so the middleware synthesizes one)."""

        client: Any = None

        def dispatch(
            self, message: str, tier: str, payload: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            return {"ok": True, "tier": tier, "message": message}

        def dispatch_message(
            self,
            *,
            tier: str,
            message: str,
            payload: dict[str, Any] | None = None,
        ) -> JobResult:
            return JobResult(ok=True, tier=tier, message=message)

        def health(self) -> dict[str, Any]:
            return {"status": "ok"}

        def cancel(self, request_id: str) -> bool:
            return True

        def close(self) -> None:
            pass

        def protocol_info(self) -> ProtocolInfo:
            return ProtocolInfo(
                serverVersion="0.0.0+test",
                supportedVersions=["2025-03-26"],
                defaultVersion="2025-03-26",
                negotiatedVersion="2025-03-26",
                capabilities=ServerCapabilities(),
                serverInfo=ServerInfo(name="dispatch-mcp", version="0.0.0+test"),
            )

    inner = NoPing()
    router = CostAwareRouter(inner)
    result = asyncio.run(router.ping())
    assert result.status == "alive"
    assert result.message == "dispatch-mcp"


def test_ping_handles_async_inner() -> None:
    """``ping`` awaits an inner coroutine instead of treating it as a value."""
    class AsyncPingInner(FakeInner):
        def __init__(self) -> None:
            super().__init__()
        async def ping(self) -> JobResult:
            return JobResult(status="alive", message="async-pong")

    inner = AsyncPingInner()
    router = CostAwareRouter(inner)
    result = asyncio.run(router.ping())
    assert result.message == "async-pong"


def test_protocol_info_forwards_to_inner() -> None:
    """``protocol_info`` returns whatever the inner adapter reports."""
    info = ProtocolInfo(
        serverVersion="1.2.3",
        supportedVersions=["2025-03-26"],
        defaultVersion="2025-03-26",
        negotiatedVersion="2025-03-26",
        capabilities=ServerCapabilities(),
        serverInfo=ServerInfo(name="dispatch-mcp", version="1.2.3"),
    )
    inner = FakeInner(protocol_info=info)
    router = CostAwareRouter(inner)
    assert router.protocol_info() is info


def test_protocol_info_synthesizes_when_inner_missing() -> None:
    """``protocol_info`` returns a minimal default when the inner has none."""
    class NoProtocolInfo(FakeInner):
        def __init__(self) -> None:
            super().__init__()
        # Intentionally do NOT define protocol_info.

    inner = NoProtocolInfo()
    router = CostAwareRouter(inner)
    info = router.protocol_info()
    assert isinstance(info, ProtocolInfo)
    assert info.serverInfo is not None
    assert info.serverInfo.name == "dispatch-mcp"


def test_close_flushes_audit_log() -> None:
    """``close`` releases the inner adapter and flushes the audit log."""
    inner = FakeInner()
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "audit.jsonl"
        audit = AuditLog(jsonl_path=tmp)
        config = CostMiddlewareConfig(audit=audit)
        router = CostAwareRouter(inner, config=config)
        asyncio.run(router.dispatch_message(tier="haiku", message="hi"))
        router.close()
        # The file has the one allowed entry on disk after close.
        lines = tmp.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["decision"] == "allowed"
        assert payload["tier"] == "haiku"


def test_aclose_is_async_alias_for_close() -> None:
    """``aclose`` is the async counterpart of ``close``."""
    inner = FakeInner()
    router = CostAwareRouter(inner)
    asyncio.run(router.aclose())  # does not raise


# ---------------------------------------------------------------------------
# Properties / client proxy
# ---------------------------------------------------------------------------


def test_client_property_proxies_to_inner() -> None:
    """``client`` is a read-through proxy to the inner adapter's client."""
    inner = FakeInner()
    inner.client = "fake-client"
    router = CostAwareRouter(inner)
    assert router.client == "fake-client"


def test_client_property_returns_none_when_inner_has_no_client() -> None:
    """``client`` is ``None`` when the inner adapter does not expose one."""
    inner = FakeInner()
    # inner.client is already None by default.
    router = CostAwareRouter(inner)
    assert router.client is None


def test_calculator_property_exposes_calculator() -> None:
    """``calculator`` returns the bound :class:`CostCalculator`."""
    inner = FakeInner()
    registry = TierRegistry()
    config = CostMiddlewareConfig(registry=registry)
    router = CostAwareRouter(inner, config=config)
    assert isinstance(router.calculator, CostCalculator)
    assert router.calculator.registry is registry


def test_inner_property_exposes_wrapped_router() -> None:
    """``inner`` returns the wrapped inner router for inspection."""
    inner = FakeInner()
    router = CostAwareRouter(inner)
    assert router.inner is inner


# ---------------------------------------------------------------------------
# Custom ID factory / logger
# ---------------------------------------------------------------------------


def test_dispatch_message_uses_injected_id_factory() -> None:
    """A custom id factory supplies the request_id (e.g. for tracing)."""
    inner = FakeInner()
    router = CostAwareRouter(inner, id_factory=lambda: "trace-abc-123")
    result = asyncio.run(router.dispatch_message(tier="haiku", message="hi"))
    assert result.request_id == "trace-abc-123"
    entry = router.config.audit.entries()[0]
    assert entry.request_id == "trace-abc-123"
