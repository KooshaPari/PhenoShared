"""Tier registry and pricing for pheno-mcp-router.

This module is the single source of truth for tier metadata used by
the cost calculator, budget enforcer, and audit trail. Tiers are
identified by their short name (``"haiku"``, ``"opus"``, etc.) and
map to a :class:`TierPricing` record that captures the upstream
model, the provider, and per-million-token rates for input and
output.

Pricing is intentionally hard-coded with public list prices for
each model as of the cost-tracking rollout date. Operators can
override rates at runtime by calling :func:`register_tier` (e.g.
from a configuration adapter) — the registry is mutable to
accommodate discount programs and negotiated enterprise rates.

Ported from dispatch-mcp W2-1 (commit ``6aad7fa``) per L5-104.1
as substrate-level tier metadata per ADR-013. Module imports
were rewritten from ``dispatch_mcp.core.X`` to ``pheno_mcp_router.X``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Iterator

# Pricing is stored as USD per 1,000,000 tokens. Float is acceptable
# here because the values are short, fixed-rate constants and the
# arithmetic is exact for the small magnitudes we sum.
_USD_PER_1M: Final[float] = 1.0
_TOKEN_UNIT: Final[int] = 1_000_000


@dataclass(slots=True, frozen=True)
class TierPricing:
    """Per-tier pricing and metadata for cost tracking.

    ``input_per_1m`` and ``output_per_1m`` are USD per 1,000,000
    tokens. ``provider`` is the upstream vendor (``"anthropic"``,
    ``"moonshot"``, etc.) and is used for grouping in audit output
    and cost reports. ``model`` is the canonical upstream model
    identifier (e.g. ``"claude-3-5-haiku-20241022"``).
    """

    name: str
    provider: str
    model: str
    input_per_1m: float
    output_per_1m: float
    description: str = ""

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        """Return the USD cost for a given token count.

        Negative token counts are clamped to zero so a defensive
        caller cannot produce a negative invoice.
        """
        in_tokens = max(0, int(input_tokens))
        out_tokens = max(0, int(output_tokens))
        return (
            in_tokens * self.input_per_1m / _TOKEN_UNIT
            + out_tokens * self.output_per_1m / _TOKEN_UNIT
        )


# Sentinel used to represent tiers that are valid for dispatch but
# have no published pricing. The cost calculator reports zero cost
# and the budget/quota systems use a conservative default rate so
# unknown tiers cannot bypass policy by accident.
@dataclass(slots=True, frozen=True)
class _UnknownPricing(TierPricing):
    input_per_1m: float = field(default=0.0)
    output_per_1m: float = field(default=0.0)
    description: str = "Unregistered tier — cost is unpriced."


UNKNOWN_PRICING: Final[TierPricing] = _UnknownPricing(
    name="unknown",
    provider="unknown",
    model="unknown",
)


_DEFAULT_REGISTRY: Final[dict[str, TierPricing]] = {
    "worker": TierPricing(
        name="worker",
        provider="internal",
        model="dispatch-worker",
        input_per_1m=0.20,
        output_per_1m=0.60,
        description="Cheap general-purpose worker tier.",
    ),
    "main": TierPricing(
        name="main",
        provider="internal",
        model="dispatch-main",
        input_per_1m=1.25,
        output_per_1m=5.00,
        description="Default mid-tier model for primary dispatch.",
    ),
    "codeman": TierPricing(
        name="codeman",
        provider="internal",
        model="dispatch-codeman",
        input_per_1m=0.80,
        output_per_1m=3.20,
        description="Code-focused mid-tier model.",
    ),
    "freetier": TierPricing(
        name="freetier",
        provider="internal",
        model="dispatch-freetier",
        input_per_1m=0.0,
        output_per_1m=0.0,
        description="Zero-cost free tier; counted in quotas but not invoiced.",
    ),
    "kimi": TierPricing(
        name="kimi",
        provider="moonshot",
        model="moonshot-v1-128k",
        input_per_1m=0.15,
        output_per_1m=0.60,
        description="Moonshot Kimi base model.",
    ),
    "kimi_thinking": TierPricing(
        name="kimi_thinking",
        provider="moonshot",
        model="moonshot-v1-thinking",
        input_per_1m=0.30,
        output_per_1m=1.20,
        description="Moonshot Kimi with extended reasoning.",
    ),
    "minimax": TierPricing(
        name="minimax",
        provider="minimax",
        model="minimax-M3",
        input_per_1m=0.20,
        output_per_1m=0.80,
        description="minimax general-purpose model.",
    ),
    "opus": TierPricing(
        name="opus",
        provider="anthropic",
        model="claude-opus-4",
        input_per_1m=15.00,
        output_per_1m=75.00,
        description="Anthropic Claude Opus 4 — premium tier.",
    ),
    "haiku": TierPricing(
        name="haiku",
        provider="anthropic",
        model="claude-3-5-haiku-20241022",
        input_per_1m=0.80,
        output_per_1m=4.00,
        description="Anthropic Claude 3.5 Haiku — budget tier.",
    ),
    "gemini": TierPricing(
        name="gemini",
        provider="google",
        model="gemini-2.5-pro",
        input_per_1m=1.25,
        output_per_1m=5.00,
        description="Google Gemini 2.5 Pro.",
    ),
}


class TierRegistry:
    """Mutable registry of tier pricing.

    The default registry is loaded at construction time. Operators
    can call :meth:`register` to override rates (e.g. for negotiated
    enterprise pricing) or :meth:`unregister` to disable a tier.
    Lookups via :meth:`get` always return a :class:`TierPricing` —
    unknown tiers yield :data:`UNKNOWN_PRICING` so callers do not
    need to handle ``None`` returns.

    The registry is intentionally NOT thread-safe; mutation is
    expected at startup, and reads dominate at runtime. The
    cost-tracking middleware holds a reference and calls
    :meth:`get` on the hot path.
    """

    __slots__ = ("_tiers",)

    def __init__(self, tiers: dict[str, TierPricing] | None = None) -> None:
        # Distinguish "no arg" (use defaults) from "explicit empty
        # dict" (use the empty dict). An empty dict is falsy, so
        # we check for ``None`` explicitly.
        if tiers is None:
            self._tiers: dict[str, TierPricing] = dict(_DEFAULT_REGISTRY)
        else:
            # Defensive copy: callers cannot mutate our internal
            # state by holding a reference to the seed dict.
            self._tiers = dict(tiers)

    def get(self, tier: str) -> TierPricing:
        """Return pricing for ``tier`` or :data:`UNKNOWN_PRICING`."""
        return self._tiers.get(tier, UNKNOWN_PRICING)

    def has(self, tier: str) -> bool:
        """Return ``True`` if ``tier`` is registered."""
        return tier in self._tiers

    def names(self) -> tuple[str, ...]:
        """Return a sorted tuple of registered tier names."""
        return tuple(sorted(self._tiers))

    def register(self, pricing: TierPricing) -> None:
        """Insert or replace a tier's pricing record."""
        self._tiers[pricing.name] = pricing

    def unregister(self, tier: str) -> None:
        """Remove a tier from the registry. Unknown tiers are ignored."""
        self._tiers.pop(tier, None)

    def __contains__(self, tier: object) -> bool:
        return isinstance(tier, str) and tier in self._tiers

    def __len__(self) -> int:
        return len(self._tiers)

    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        # Return a real iterator so callers that wrap us with
        # ``iter()`` get a proper iterator object (a tuple, while
        # iterable, is itself not an iterator under Python's
        # iterator protocol).
        return iter(self._tiers)


# Module-level default registry used by the cost calculator and
# budget enforcer when no explicit registry is injected. The
# server composition layer constructs the calculator with this
# default and may swap in a configured instance at startup.
DEFAULT_REGISTRY: Final[TierRegistry] = TierRegistry()


__all__ = [
    "DEFAULT_REGISTRY",
    "TierPricing",
    "TierRegistry",
    "UNKNOWN_PRICING",
]
