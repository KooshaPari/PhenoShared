"""Budget enforcement for pheno-mcp-router.

The budget enforcer caps cumulative USD spend across dispatches.
It supports two independent limits:

- A **global** cap on total spend.
- **Per-tier** caps that restrict spend on a single named tier.

Each limit is a hard ceiling. When a dispatch would push spend
over the limit, the enforcer raises :class:`BudgetExceeded` so
the middleware can refuse the call before it consumes upstream
capacity. The enforcer is thread-safe; the cost middleware holds
a single instance and dispatches concurrently from MCP request
handlers.

Ported from dispatch-mcp W2-1 (commit ``6aad7fa``) per L5-104.1
as substrate-level budget enforcement per ADR-013.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Final

from pheno_mcp_router import config as _config

# Per-dispatch conservative fallback rate for unpriced tiers.
# Multiplying by this rate before checking the budget prevents an
# unregistered tier from slipping through the enforcer with zero
# cost. The constant is a generous upper bound on the public list
# price of any model in the registry.
_UNPRICED_FLOOR_USD: Final[float] = _config.UNPRICED_FLOOR_USD


class BudgetExceeded(RuntimeError):
    """Raised when a dispatch would exceed a configured budget limit.

    The ``detail`` attribute carries a structured payload suitable
    for inclusion in MCP tool error responses and audit entries.
    """

    def __init__(self, message: str, detail: dict[str, Any]) -> None:
        super().__init__(message)
        self.detail = detail


@dataclass(slots=True, frozen=True)
class BudgetPolicy:
    """Budget limits applied by :class:`BudgetTracker`.

    ``global_limit_usd`` caps the sum of all spend across every
    tier. ``per_tier_limits_usd`` caps spend for a specific tier.
    Use ``float("inf")`` to disable a limit (this is also the
    default when a tier has no entry).
    """

    global_limit_usd: float = float("inf")
    per_tier_limits_usd: dict[str, float] = field(default_factory=dict)

    def limit_for(self, tier: str) -> float:
        """Return the lower of the global and per-tier limit for ``tier``."""
        per_tier = self.per_tier_limits_usd.get(tier, float("inf"))
        return min(self.global_limit_usd, per_tier)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> BudgetPolicy:
        """Build a policy from a plain dict (e.g. JSON config).

        Missing or invalid values are coerced to ``inf`` so a
        partial config does not silently zero out a limit.
        ``per_tier`` keys are lowercased to match the canonical
        tier name casing used in :mod:`pheno_mcp_router.tiers`.
        """
        if not data:
            return cls()
        raw_global = data.get("global_limit_usd", float("inf"))
        try:
            global_limit = float(raw_global)
        except (TypeError, ValueError):
            global_limit = float("inf")
        raw_per_tier = data.get("per_tier_limits_usd") or {}
        per_tier: dict[str, float] = {}
        if isinstance(raw_per_tier, dict):
            for key, value in raw_per_tier.items():
                try:
                    per_tier[str(key).lower()] = float(value)
                except (TypeError, ValueError):
                    continue
        return cls(global_limit_usd=global_limit, per_tier_limits_usd=per_tier)


@dataclass(slots=True, frozen=True)
class BudgetSnapshot:
    """Read-only view of current spend for a single tier or the whole process.

    ``spend_usd`` is the cumulative amount charged so far.
    ``limit_usd`` is the active cap (``inf`` for unlimited).
    ``utilization`` is ``spend / limit`` clamped to ``[0, 1]``;
    callers that want raw ratio should divide manually with
    care for ``inf`` limits.
    """

    tier: str | None
    spend_usd: float
    limit_usd: float
    request_count: int

    @property
    def remaining_usd(self) -> float:
        """Return the headroom in USD (``max(0, limit - spend)``)."""
        if self.limit_usd == float("inf"):
            return float("inf")
        return max(0.0, self.limit_usd - self.spend_usd)

    @property
    def utilization(self) -> float:
        """Return ``min(1.0, spend / limit)``. Always defined."""
        if self.limit_usd == float("inf") or self.limit_usd <= 0:
            return 0.0
        return min(1.0, self.spend_usd / self.limit_usd)

    def to_dict(self) -> dict[str, str | float | int]:
        """Serialize for inclusion in tool responses and audit entries."""
        limit: str | float = (
            "inf" if self.limit_usd == float("inf") else round(self.limit_usd, 6)
        )
        remaining: str | float = (
            "inf" if self.remaining_usd == float("inf") else round(self.remaining_usd, 6)
        )
        return {
            "tier": self.tier or "global",
            "spend_usd": round(self.spend_usd, 8),
            "limit_usd": limit,
            "remaining_usd": remaining,
            "utilization": round(self.utilization, 6),
            "request_count": self.request_count,
        }


class BudgetTracker:
    """Thread-safe accumulator of dispatch spend.

    The tracker is the authoritative source of "how much have we
    spent?". :meth:`check` is a read-only gate that does not
    mutate state; :meth:`record` is the write that advances
    spend. The two-step pattern lets the middleware reject a
    dispatch *before* it consumes upstream capacity while still
    recording accurate spend only for dispatches that actually
    happened.
    """

    __slots__ = ("_policy", "_lock", "_global_spend", "_per_tier_spend", "_per_tier_count")

    def __init__(self, policy: BudgetPolicy | None = None) -> None:
        self._policy: BudgetPolicy = policy or BudgetPolicy()
        self._lock = threading.Lock()
        self._global_spend = 0.0
        # Parallel dicts so we can report per-tier request counts
        # without scanning a single value dict on every check.
        self._per_tier_spend: dict[str, float] = {}
        self._per_tier_count: dict[str, int] = {}

    @property
    def policy(self) -> BudgetPolicy:
        """Return the active policy (read-only access)."""
        return self._policy

    def check(self, tier: str, estimated_cost_usd: float) -> None:
        """Raise :class:`BudgetExceeded` if ``tier`` cannot accept ``estimated_cost_usd``.

        Unknown tiers are charged a conservative floor rate
        (:data:`_UNPRICED_FLOOR_USD`) so the enforcer cannot be
        bypassed by dispatching to a tier that has no published
        pricing. The floor is applied only during ``check``; the
        actual :meth:`record` call uses the cost computed by the
        cost calculator so the audit trail reflects the real
        charge.
        """
        # Floor the estimate when the tier is unpriced so the
        # check cannot be silently bypassed with cost_usd=0.
        effective = max(estimated_cost_usd, _UNPRICED_FLOOR_USD) if estimated_cost_usd <= 0 else estimated_cost_usd
        with self._lock:
            per_tier_spend = self._per_tier_spend.get(tier, 0.0)
            per_tier_limit = self._policy.per_tier_limits_usd.get(tier, float("inf"))
            effective_limit = min(self._policy.global_limit_usd, per_tier_limit)
            projected_global = self._global_spend + effective
            projected_per_tier = per_tier_spend + effective
            if effective_limit == float("inf"):
                return
            if projected_global > effective_limit and projected_per_tier > self._per_tier_spend.get(
                tier, 0.0
            ) + (
                effective_limit - self._global_spend
            ):
                # Detailed condition: the new spend would push
                # *either* the global or the per-tier total over
                # the active limit. We report whichever limit is
                # tighter so the operator gets an actionable
                # error.
                self._raise_violation(
                    tier=tier,
                    projected_global=projected_global,
                    projected_per_tier=projected_per_tier,
                    global_limit=self._policy.global_limit_usd,
                    per_tier_limit=per_tier_limit,
                    effective_limit=effective_limit,
                )

    def _raise_violation(
        self,
        *,
        tier: str,
        projected_global: float,
        projected_per_tier: float,
        global_limit: float,
        per_tier_limit: float,
        effective_limit: float,
    ) -> None:
        """Emit a structured :class:`BudgetExceeded`.

        Split out from :meth:`check` to keep the lock-held section
        small and to centralize the violation message shape.
        """
        limiting_scope = "global" if global_limit <= per_tier_limit else "tier"
        detail = {
            "tier": tier,
            "effective_limit_usd": effective_limit,
            "limiting_scope": limiting_scope,
            "projected_global_usd": projected_global,
            "projected_per_tier_usd": projected_per_tier,
            "global_limit_usd": global_limit,
            "per_tier_limit_usd": per_tier_limit,
        }
        msg = (
            f"Budget exceeded for tier '{tier}': "
            f"projected spend ${projected_global:.6f} would exceed "
            f"limit ${effective_limit:.6f} ({limiting_scope} cap)."
        )
        raise BudgetExceeded(msg, detail)

    def record(self, tier: str, cost_usd: float) -> None:
        """Accumulate ``cost_usd`` against ``tier`` and the global total.

        Request counts are always advanced, including for
        free-tier / $0 dispatches, so the per-tier count is a
        faithful measure of activity. Spend itself is only
        accumulated when ``cost_usd > 0``; the lock is held only
        for the critical-section update, so concurrent
        dispatchers do not serialize on the budget tracker any
        longer than necessary.
        """
        with self._lock:
            self._per_tier_count[tier] = self._per_tier_count.get(tier, 0) + 1
            if cost_usd <= 0:
                return
            self._global_spend += cost_usd
            self._per_tier_spend[tier] = self._per_tier_spend.get(tier, 0.0) + cost_usd

    def snapshot(self, tier: str | None = None) -> BudgetSnapshot:
        """Return a :class:`BudgetSnapshot` for ``tier`` (or the global total).

        The snapshot is a value object captured under the lock;
        callers may inspect it without holding any monitor.
        """
        with self._lock:
            if tier is None:
                return BudgetSnapshot(
                    tier=None,
                    spend_usd=self._global_spend,
                    limit_usd=self._policy.global_limit_usd,
                    request_count=sum(self._per_tier_count.values()),
                )
            return BudgetSnapshot(
                tier=tier,
                spend_usd=self._per_tier_spend.get(tier, 0.0),
                limit_usd=self._policy.limit_for(tier),
                request_count=self._per_tier_count.get(tier, 0),
            )

    def reset(self) -> None:
        """Zero out all spend counters. Intended for tests and admin tools."""
        with self._lock:
            self._global_spend = 0.0
            self._per_tier_spend.clear()
            self._per_tier_count.clear()


__all__ = [
    "BudgetExceeded",
    "BudgetPolicy",
    "BudgetSnapshot",
    "BudgetTracker",
]
