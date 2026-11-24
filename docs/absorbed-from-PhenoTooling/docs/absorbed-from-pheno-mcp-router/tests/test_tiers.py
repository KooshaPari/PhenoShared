"""Tests for the :mod:`pheno_mcp_router.tiers` registry and pricing tables.

The tier registry is the single source of truth for cost calculations
across the whole package. These tests pin the default pricing and
exhaustively cover the small surface area of the registry
(register, unregister, get, has, names, contains, len, iter) so a
regression in pricing math or registry mutation does not silently
affect downstream cost/budget/quota modules.

Ported from dispatch-mcp W2-1 (test_core_tiers.py @ 6aad7fa) per
L5-104.1 with import rewrite.
"""

from __future__ import annotations

import pytest

from pheno_mcp_router.tiers import (
    DEFAULT_REGISTRY,
    UNKNOWN_PRICING,
    TierPricing,
    TierRegistry,
)


# ---------------------------------------------------------------------------
# TierPricing.cost
# ---------------------------------------------------------------------------


def test_tier_pricing_cost_basic() -> None:
    """A pricing row produces the expected input + output cost in USD."""
    pricing = TierPricing(
        name="t",
        provider="p",
        model="m",
        input_per_1m=1.0,
        output_per_1m=3.0,
    )
    # 1M input tokens at $1/M = $1.00; 1M output at $3/M = $3.00.
    assert pricing.cost(1_000_000, 1_000_000) == pytest.approx(4.0)


def test_tier_pricing_cost_handles_zero() -> None:
    """Zero tokens (a probe dispatch) costs zero."""
    pricing = TierPricing(
        name="t", provider="p", model="m", input_per_1m=99.0, output_per_1m=99.0
    )
    assert pricing.cost(0, 0) == 0.0


def test_tier_pricing_cost_clamps_negative_tokens() -> None:
    """Defensive callers cannot produce negative invoices."""
    pricing = TierPricing(
        name="t", provider="p", model="m", input_per_1m=10.0, output_per_1m=10.0
    )
    # -1_000_000 input + 1_000_000 output: input is clamped to 0,
    # output is $10/M. Total must be non-negative.
    cost = pricing.cost(-1_000_000, 1_000_000)
    assert cost == pytest.approx(10.0)


def test_tier_pricing_cost_component_split() -> None:
    """input and output are summed independently."""
    pricing = TierPricing(
        name="t", provider="p", model="m", input_per_1m=2.0, output_per_1m=5.0
    )
    cost = pricing.cost(500_000, 200_000)
    # 500k * $2/M = $1.00; 200k * $5/M = $1.00.
    assert cost == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# UNKNOWN_PRICING
# ---------------------------------------------------------------------------


def test_unknown_pricing_is_free() -> None:
    """The unknown sentinel is intentionally free (zero rate)."""
    assert UNKNOWN_PRICING.cost(1_000_000, 1_000_000) == 0.0
    assert UNKNOWN_PRICING.input_per_1m == 0.0
    assert UNKNOWN_PRICING.output_per_1m == 0.0
    assert UNKNOWN_PRICING.provider == "unknown"


# ---------------------------------------------------------------------------
# Default registry coverage
# ---------------------------------------------------------------------------


def test_default_registry_contains_all_supported_tiers() -> None:
    """Every server-allowlisted tier must be in the default registry.

    The substrate's tier set is the canonical fleet tier set per
    ADR-013 — every pheno-mcp-* server should be able to look up
    any tier by name.
    """
    expected = {
        "worker",
        "main",
        "codeman",
        "freetier",
        "kimi",
        "kimi_thinking",
        "minimax",
        "opus",
        "haiku",
        "gemini",
    }
    assert set(DEFAULT_REGISTRY.names()) == expected


def test_default_registry_provider_attribution() -> None:
    """Provider metadata is populated for every tier (for audit grouping)."""
    for name in DEFAULT_REGISTRY.names():
        pricing = DEFAULT_REGISTRY.get(name)
        assert pricing.provider, f"tier {name!r} has no provider"
        assert pricing.model, f"tier {name!r} has no model"


def test_default_registry_opus_is_most_expensive() -> None:
    """The premium tier should have the highest per-million rates."""
    opus = DEFAULT_REGISTRY.get("opus")
    for other in DEFAULT_REGISTRY.names():
        if other == "opus":
            continue
        other_pricing = DEFAULT_REGISTRY.get(other)
        assert opus.input_per_1m >= other_pricing.input_per_1m
        assert opus.output_per_1m >= other_pricing.output_per_1m


def test_default_registry_freetier_is_zero_cost() -> None:
    """The free tier is metered in quota but not invoiced."""
    freetier = DEFAULT_REGISTRY.get("freetier")
    assert freetier.input_per_1m == 0.0
    assert freetier.output_per_1m == 0.0
    assert freetier.cost(999_999_999, 999_999_999) == 0.0


# ---------------------------------------------------------------------------
# TierRegistry: get, has, contains, len, iter
# ---------------------------------------------------------------------------


def test_registry_get_returns_unknown_for_unknown_tier() -> None:
    """Unknown tiers yield the ``UNKNOWN_PRICING`` sentinel (no None)."""
    registry = TierRegistry()
    pricing = registry.get("does-not-exist")
    assert pricing is UNKNOWN_PRICING


def test_registry_has_reports_membership() -> None:
    """``has`` distinguishes registered from unregistered tiers."""
    registry = TierRegistry()
    assert registry.has("haiku")
    assert not registry.has("totally-made-up")


def test_registry_contains_protocol() -> None:
    """``in registry`` works for strings and rejects other types safely."""
    registry = TierRegistry()
    assert "haiku" in registry
    assert "no-such-tier" not in registry
    # Non-strings must not raise — Protocol-side isinstance checks
    # would otherwise blow up.
    assert (42 in registry) is False


def test_registry_len_and_iter() -> None:
    """``len`` and ``iter`` are stable shapes used by the cost report."""
    registry = TierRegistry()
    assert len(registry) == len(registry.names())
    listed = list(iter(registry))
    assert sorted(listed) == sorted(registry.names())


# ---------------------------------------------------------------------------
# TierRegistry: register / unregister / seed isolation
# ---------------------------------------------------------------------------


def test_registry_register_overrides_existing_tier() -> None:
    """``register`` replaces an existing tier in place."""
    registry = TierRegistry()
    original = registry.get("haiku")
    custom = TierPricing(
        name="haiku",
        provider="anthropic",
        model="claude-3-5-haiku-negotiated",
        input_per_1m=0.4,
        output_per_1m=2.0,
    )
    registry.register(custom)
    assert registry.get("haiku") is custom
    assert registry.get("haiku") is not original


def test_registry_register_adds_new_tier() -> None:
    """``register`` adds a new tier."""
    registry = TierRegistry()
    new_tier = TierPricing(
        name="custom-tier",
        provider="acme",
        model="acme-1",
        input_per_1m=0.5,
        output_per_1m=1.5,
    )
    registry.register(new_tier)
    assert registry.has("custom-tier")
    assert registry.get("custom-tier") is new_tier


def test_registry_unregister_removes_tier() -> None:
    """``unregister`` removes a tier so subsequent lookups yield ``UNKNOWN``."""
    registry = TierRegistry()
    assert registry.has("haiku")
    registry.unregister("haiku")
    assert not registry.has("haiku")
    assert registry.get("haiku") is UNKNOWN_PRICING


def test_registry_unregister_unknown_is_noop() -> None:
    """``unregister`` is idempotent for missing tiers (no KeyError)."""
    registry = TierRegistry()
    registry.unregister("never-existed")
    # Still works after the no-op:
    assert registry.unregister("never-existed") is None


def test_registry_seed_dict_is_defensively_copied() -> None:
    """A caller mutating the seed dict after construction must not affect us."""
    seed = {
        "haiku": TierPricing(
            name="haiku", provider="anthropic", model="x",
            input_per_1m=0.8, output_per_1m=4.0,
        )
    }
    registry = TierRegistry(tiers=seed)
    # Mutate the original dict — the registry must not see the change.
    seed["haiku"] = TierPricing(
        name="haiku", provider="anthropic", model="x",
        input_per_1m=99.0, output_per_1m=99.0,
    )
    assert registry.get("haiku").input_per_1m == 0.8


def test_registry_seed_missing_yields_unknown_safely() -> None:
    """An empty seed dict is allowed and produces only UNKNOWN lookups."""
    registry = TierRegistry(tiers={})
    assert not registry.has("anything")
    assert registry.get("anything") is UNKNOWN_PRICING
    assert len(registry) == 0


def test_registry_names_returns_sorted_tuple() -> None:
    """``names()`` is deterministically ordered for stable report output."""
    registry = TierRegistry()
    names = registry.names()
    assert isinstance(names, tuple)
    assert names == tuple(sorted(names))
