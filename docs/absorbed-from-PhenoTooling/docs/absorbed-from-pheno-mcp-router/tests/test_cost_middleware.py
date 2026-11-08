"""Tests for the :mod:`pheno_mcp_router.cost_middleware` adapter.

The :class:`CostAwareLlmAdapter` is the substrate-level integration
point that composes the cost calculator, budget enforcer, quota
tracker, and audit trail around any inner :class:`LlmPort`. These
tests use a fake inner LlmPort so the middleware can be exercised
in isolation from any HTTP transport.

Unlike the dispatch-mcp original (which wrapped a Router protocol
with ``health``, ``ping``, ``protocol_info``, ``close``,
``aclose``, ``client``), the substrate version exposes the much
narrower ``LlmPort`` contract (``async chat(messages, model) -> str``)
plus the tier-aware :meth:`dispatch` and :meth:`dispatch_with_metadata`
helpers. These tests focus on the substrate surface.

The convention used here (sync ``def`` tests wrapping ``asyncio.run``)
matches :mod:`tests.test_ports` so the test suite does not depend
on ``pytest-asyncio``.

Ported from dispatch-mcp W2-1 (test_core_cost_middleware.py @
6aad7fa) per L5-104.1 with import rewrite + scope reduction to
the substrate's LlmPort Protocol.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from pheno_mcp_router.audit import AuditLog
from pheno_mcp_router.budget import BudgetExceeded, BudgetPolicy, BudgetTracker
from pheno_mcp_router.cost import CostCalculator
from pheno_mcp_router.cost_middleware import (
    CostAwareDispatchResult,
    CostAwareLlmAdapter,
    CostMiddlewareConfig,
    TierWorker,
)
from pheno_mcp_router.quota import (
    QuotaExceeded,
    QuotaPolicy,
    QuotaTracker,
)
from pheno_mcp_router.tiers import DEFAULT_REGISTRY, TierRegistry


# ---------------------------------------------------------------------------
# Fake inner LlmPort
# ---------------------------------------------------------------------------


class FakeInner:
    """A minimal :class:`LlmPort` stand-in.

    Mirrors the structural surface the middleware delegates to: an
    async :meth:`chat` returning the assistant text, plus optional
    tracking of every dispatch for assertions. No HTTP, no real
    upstream call.
    """

    def __init__(
        self,
        responder: Any | None = None,
        *,
        fail_with: BaseException | None = None,
    ) -> None:
        self._responder = responder or (lambda messages, model: f"echo:{messages[0]['content']}")
        self._fail_with = fail_with
        self.dispatched: list[dict[str, Any]] = []

    async def chat(self, messages: list[dict[str, Any]], model: str) -> str:
        """LlmPort.chat — return canned text or raise the configured error."""
        self.dispatched.append({"messages": messages, "model": model})
        if self._fail_with is not None:
            raise self._fail_with
        return self._responder(messages, model)


def _run(coro: Any) -> Any:
    """Drive a coroutine to completion with a fresh event loop."""
    return asyncio.run(coro)


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


def test_dispatch_returns_assistant_text() -> None:
    """A successful dispatch returns the inner adapter's text."""
    inner = FakeInner()
    adapter = CostAwareLlmAdapter(inner)
    text = _run(
        adapter.dispatch(
            [{"role": "user", "content": "hi"}],
            model="claude-3-5-haiku-20241022",
            tier="haiku",
        )
    )
    assert text == "echo:hi"


def test_dispatch_with_metadata_returns_full_cost_line_item() -> None:
    """A successful dispatch enriches the result with cost metadata."""
    inner = FakeInner()
    adapter = CostAwareLlmAdapter(inner)
    result = _run(
        adapter.dispatch_with_metadata(
            [{"role": "user", "content": "hi"}],
            model="claude-3-5-haiku-20241022",
            tier="haiku",
        )
    )
    assert isinstance(result, CostAwareDispatchResult)
    assert result.text == "echo:hi"
    assert result.tier == "haiku"
    assert result.decision == "allowed"
    assert result.reason == "ok"
    assert result.model == "claude-3-5-haiku-20241022"
    assert result.provider == "anthropic"
    assert result.is_priced is True
    assert result.request_id  # auto-generated UUID


def test_dispatch_charges_budget_and_quota() -> None:
    """A successful dispatch advances both budget and quota counters."""
    inner = FakeInner()
    adapter = CostAwareLlmAdapter(inner)
    _run(
        adapter.dispatch(
            [{"role": "user", "content": "hi"}], model="m", tier="haiku"
        )
    )
    # The budget tracker recorded a non-zero haiku spend.
    snap = adapter.config.budget.snapshot("haiku")
    assert snap.spend_usd > 0.0
    assert snap.request_count == 1
    # The quota tracker recorded a dispatch (with input tokens estimated).
    qsnap = adapter.config.quota.snapshot("haiku")
    assert qsnap.requests_used == 1
    assert qsnap.tokens_used >= 1


def test_dispatch_appends_audit_entry_allowed() -> None:
    """A successful dispatch records an ``allowed`` audit entry."""
    inner = FakeInner()
    audit = AuditLog()
    config = CostMiddlewareConfig(audit=audit)
    adapter = CostAwareLlmAdapter(inner, config=config)
    _run(
        adapter.dispatch(
            [{"role": "user", "content": "hi"}], model="m", tier="haiku"
        )
    )
    entries = audit.entries()
    assert len(entries) == 1
    e = entries[0]
    assert e.decision == "allowed"
    assert e.reason == "ok"
    assert e.tier == "haiku"
    assert e.model == "claude-3-5-haiku-20241022"
    assert e.is_priced is True


def test_dispatch_to_dict_shape_is_stable() -> None:
    """``CostAwareDispatchResult.to_dict`` exposes the documented fields."""
    inner = FakeInner()
    adapter = CostAwareLlmAdapter(inner)
    result = _run(
        adapter.dispatch_with_metadata(
            [{"role": "user", "content": "hi"}],
            model="m",
            tier="haiku",
        )
    )
    payload = result.to_dict()
    for key in (
        "text",
        "tier",
        "model",
        "provider",
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "is_priced",
        "request_id",
        "decision",
        "reason",
        "detail",
    ):
        assert key in payload


# ---------------------------------------------------------------------------
# LlmPort.chat surface (passthrough with tier="unknown")
# ---------------------------------------------------------------------------


def test_chat_dispatches_under_unknown_tier() -> None:
    """``chat`` is a substrate-LlmPort-compatible pass-through.

    The substrate callers that don't know which tier they're
    targeting still get cost tracking under the "unknown" tier —
    operators see the dispatch in the audit trail even though
    they didn't tag it.
    """
    inner = FakeInner()
    audit = AuditLog()
    config = CostMiddlewareConfig(audit=audit)
    adapter = CostAwareLlmAdapter(inner, config=config)
    text = _run(adapter.chat([{"role": "user", "content": "hi"}], model="m"))
    assert text == "echo:hi"
    # The audit log records the dispatch under the unknown tier.
    entries = audit.entries()
    assert len(entries) == 1
    assert entries[0].tier == "unknown"


def test_chat_passthrough_when_disabled() -> None:
    """``enabled=False`` skips policy entirely; chat returns inner text."""
    inner = FakeInner()
    config = CostMiddlewareConfig(enabled=False)
    adapter = CostAwareLlmAdapter(inner, config=config)
    text = _run(adapter.chat([{"role": "user", "content": "hi"}], model="m"))
    assert text == "echo:hi"


# ---------------------------------------------------------------------------
# Disabled middleware (pass-through)
# ---------------------------------------------------------------------------


def test_dispatch_passthrough_when_disabled_still_records_audit() -> None:
    """A disabled middleware still records audit (so disabling does not lose data)."""
    inner = FakeInner()
    config = CostMiddlewareConfig(enabled=False)
    adapter = CostAwareLlmAdapter(inner, config=config)
    text = _run(
        adapter.dispatch(
            [{"role": "user", "content": "hi"}], model="m", tier="haiku"
        )
    )
    assert text == "echo:hi"
    # Audit entry is still recorded (allowed).
    entries = adapter.config.audit.entries()
    assert len(entries) == 1
    assert entries[0].decision == "allowed"


# ---------------------------------------------------------------------------
# Quota gate
# ---------------------------------------------------------------------------


def test_quota_exceeded_blocks_dispatch() -> None:
    """A quota-refused dispatch raises ``QuotaExceeded`` and records a blocked audit."""
    inner = FakeInner()
    quota = QuotaTracker(
        policy=QuotaPolicy(max_requests_per_window=1)
    )
    audit = AuditLog()
    config = CostMiddlewareConfig(quota=quota, audit=audit)
    adapter = CostAwareLlmAdapter(inner, config=config)

    # First call consumes the single request slot.
    _run(
        adapter.dispatch(
            [{"role": "user", "content": "first"}], model="m", tier="haiku"
        )
    )

    # Second call hits the quota and is refused.
    with pytest.raises(QuotaExceeded):
        _run(
            adapter.dispatch(
                [{"role": "user", "content": "second"}], model="m", tier="haiku"
            )
        )

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


def test_budget_exceeded_blocks_dispatch() -> None:
    """A budget-refused dispatch raises ``BudgetExceeded`` and records a blocked audit."""
    inner = FakeInner()
    budget = BudgetTracker(
        policy=BudgetPolicy(global_limit_usd=0.0001)  # absurdly small cap
    )
    audit = AuditLog()
    config = CostMiddlewareConfig(budget=budget, audit=audit)
    adapter = CostAwareLlmAdapter(inner, config=config)

    with pytest.raises(BudgetExceeded):
        _run(
            adapter.dispatch(
                [{"role": "user", "content": "hi"}], model="m", tier="haiku"
            )
        )

    decisions = [e.decision for e in audit.entries()]
    assert decisions == ["blocked"]
    blocked = audit.entries()[0]
    assert blocked.reason == "budget"
    assert blocked.cost_usd == 0.0


def test_upstream_failure_does_not_charge_budget() -> None:
    """An upstream error records a blocked entry but does not charge spend."""
    inner = FakeInner(fail_with=RuntimeError("upstream down"))
    audit = AuditLog()
    config = CostMiddlewareConfig(audit=audit)
    adapter = CostAwareLlmAdapter(inner, config=config)

    with pytest.raises(RuntimeError, match="upstream down"):
        _run(
            adapter.dispatch(
                [{"role": "user", "content": "hi"}], model="m", tier="haiku"
            )
        )

    # Spend was NOT recorded — the dispatch never happened.
    assert adapter.config.budget.snapshot().spend_usd == 0.0
    # Quota usage was also NOT recorded.
    assert adapter.config.quota.snapshot().requests_used == 0
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


def test_unknown_tier_marks_unpriced() -> None:
    """An unregistered tier reports ``is_priced=False`` and zero cost."""
    inner = FakeInner()
    adapter = CostAwareLlmAdapter(inner)
    result = _run(
        adapter.dispatch_with_metadata(
            [{"role": "user", "content": "hi"}],
            model="m",
            tier="mystery-tier",
        )
    )
    assert result.text == "echo:hi"
    assert result.cost_usd == 0.0
    assert result.model == "unknown"
    # The audit entry is marked unpriced.
    entry = adapter.config.audit.entries()[0]
    assert entry.is_priced is False
    assert entry.cost_usd == 0.0


# ---------------------------------------------------------------------------
# Per-tier worker
# ---------------------------------------------------------------------------


def test_worker_returns_callable_bound_to_tier() -> None:
    """``worker(tier)`` returns a ``TierWorker`` that dispatches to that tier."""
    inner = FakeInner()
    adapter = CostAwareLlmAdapter(inner)
    w = adapter.worker("haiku")
    assert isinstance(w, TierWorker)
    assert repr(w) == "TierWorker(tier='haiku')"

    text = _run(w([{"role": "user", "content": "hi"}], model="m"))
    assert text == "echo:hi"
    # The inner adapter saw the dispatch with the right messages.
    assert inner.dispatched[0]["messages"] == [{"role": "user", "content": "hi"}]


# ---------------------------------------------------------------------------
# Properties / client proxy
# ---------------------------------------------------------------------------


def test_calculator_property_exposes_calculator() -> None:
    """``calculator`` returns the bound :class:`CostCalculator`."""
    inner = FakeInner()
    registry = TierRegistry()
    config = CostMiddlewareConfig(registry=registry)
    adapter = CostAwareLlmAdapter(inner, config=config)
    assert isinstance(adapter.calculator, CostCalculator)
    assert adapter.calculator.registry is registry


def test_inner_property_exposes_wrapped_adapter() -> None:
    """``inner`` returns the wrapped inner LlmPort for inspection."""
    inner = FakeInner()
    adapter = CostAwareLlmAdapter(inner)
    assert adapter.inner is inner


# ---------------------------------------------------------------------------
# Custom ID factory
# ---------------------------------------------------------------------------


def test_dispatch_uses_injected_id_factory() -> None:
    """A custom id factory supplies the request_id (e.g. for tracing)."""
    inner = FakeInner()
    adapter = CostAwareLlmAdapter(inner, id_factory=lambda: "trace-abc-123")
    result = _run(
        adapter.dispatch_with_metadata(
            [{"role": "user", "content": "hi"}], model="m", tier="haiku"
        )
    )
    assert result.request_id == "trace-abc-123"
    entry = adapter.config.audit.entries()[0]
    assert entry.request_id == "trace-abc-123"
