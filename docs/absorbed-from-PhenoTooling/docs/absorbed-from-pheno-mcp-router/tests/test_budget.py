"""Tests for the :mod:`pheno_mcp_router.budget` enforcement.

The budget enforcer is the policy gate that prevents runaway
spend. These tests pin the small public surface (``check``,
``record``, ``snapshot``, ``reset``) and the interactions between
the global cap, per-tier caps, and the unpriced-tier floor.
Concurrency is exercised with a small thread fan-out so the
tracker cannot regress to a data race.

Ported from dispatch-mcp W2-1 (test_core_budget.py @ 6aad7fa) per
L5-104.1 with import rewrite.
"""

from __future__ import annotations

import threading

import pytest

from pheno_mcp_router.budget import (
    BudgetExceeded,
    BudgetPolicy,
    BudgetSnapshot,
    BudgetTracker,
)


# ---------------------------------------------------------------------------
# BudgetPolicy
# ---------------------------------------------------------------------------


def test_policy_defaults_are_unlimited() -> None:
    """Default policy is unlimited (no caps applied)."""
    policy = BudgetPolicy()
    assert policy.global_limit_usd == float("inf")
    assert policy.per_tier_limits_usd == {}


def test_policy_limit_for_returns_min_of_global_and_per_tier() -> None:
    """The effective limit is the tighter of global vs. per-tier."""
    policy = BudgetPolicy(
        global_limit_usd=100.0,
        per_tier_limits_usd={"haiku": 5.0, "opus": 50.0},
    )
    # haiku is per-tier 5 < global 100 → 5.
    assert policy.limit_for("haiku") == 5.0
    # opus is per-tier 50 < global 100 → 50.
    assert policy.limit_for("opus") == 50.0
    # worker has no per-tier entry → global 100.
    assert policy.limit_for("worker") == 100.0


def test_policy_from_dict_with_valid_data() -> None:
    """A plain dict coerces cleanly into a policy."""
    policy = BudgetPolicy.from_dict(
        {
            "global_limit_usd": 10.0,
            "per_tier_limits_usd": {"haiku": 1.0, "opus": 2.0},
        }
    )
    assert policy.global_limit_usd == 10.0
    assert policy.per_tier_limits_usd == {"haiku": 1.0, "opus": 2.0}


def test_policy_from_dict_normalizes_keys_to_lowercase() -> None:
    """Tier names are lowercased to match the canonical casing."""
    policy = BudgetPolicy.from_dict(
        {"per_tier_limits_usd": {"Haiku": 1.0, "OPUS": 2.0}}
    )
    assert "haiku" in policy.per_tier_limits_usd
    assert "opus" in policy.per_tier_limits_usd


def test_policy_from_dict_with_empty_input_yields_unlimited() -> None:
    """``None`` or empty dict produces the default unlimited policy."""
    assert BudgetPolicy.from_dict(None).global_limit_usd == float("inf")
    assert BudgetPolicy.from_dict({}).global_limit_usd == float("inf")


def test_policy_from_dict_invalid_values_fall_back_to_inf() -> None:
    """Non-numeric values are silently coerced to ``inf`` (no exception)."""
    policy = BudgetPolicy.from_dict(
        {"global_limit_usd": "not-a-number", "per_tier_limits_usd": {"haiku": "x"}}
    )
    assert policy.global_limit_usd == float("inf")
    assert policy.per_tier_limits_usd == {}


def test_policy_from_dict_partial_garbage_drops_only_bad_keys() -> None:
    """A mix of good and bad per-tier keys keeps the good ones."""
    policy = BudgetPolicy.from_dict(
        {"per_tier_limits_usd": {"haiku": 1.0, "opus": "bad"}}
    )
    assert "haiku" in policy.per_tier_limits_usd
    assert "opus" not in policy.per_tier_limits_usd


# ---------------------------------------------------------------------------
# BudgetSnapshot
# ---------------------------------------------------------------------------


def test_snapshot_remaining_usd_is_unlimited_when_inf() -> None:
    """An unlimited snapshot reports ``inf`` headroom (not a negative)."""
    snap = BudgetSnapshot(
        tier="haiku", spend_usd=5.0, limit_usd=float("inf"), request_count=3
    )
    assert snap.remaining_usd == float("inf")


def test_snapshot_remaining_usd_clamps_to_zero() -> None:
    """Over-budget snapshots report zero remaining (not negative)."""
    snap = BudgetSnapshot(
        tier="haiku", spend_usd=10.0, limit_usd=5.0, request_count=2
    )
    assert snap.remaining_usd == 0.0


def test_snapshot_utilization_caps_at_one() -> None:
    """``utilization`` is always in [0, 1] (clamped, not raw ratio)."""
    snap = BudgetSnapshot(
        tier="haiku", spend_usd=20.0, limit_usd=5.0, request_count=10
    )
    assert snap.utilization == 1.0


def test_snapshot_utilization_zero_for_unlimited() -> None:
    """An unlimited or zero-limit snapshot reports zero utilization."""
    snap_unlimited = BudgetSnapshot(
        tier="haiku", spend_usd=5.0, limit_usd=float("inf"), request_count=1
    )
    snap_zero = BudgetSnapshot(
        tier="haiku", spend_usd=0.0, limit_usd=0.0, request_count=0
    )
    assert snap_unlimited.utilization == 0.0
    assert snap_zero.utilization == 0.0


def test_snapshot_to_dict_shape() -> None:
    """The serialized shape is stable and includes request count."""
    snap = BudgetSnapshot(
        tier="haiku", spend_usd=0.5, limit_usd=1.0, request_count=2
    )
    payload = snap.to_dict()
    assert payload["tier"] == "haiku"
    assert payload["spend_usd"] == pytest.approx(0.5)
    assert payload["limit_usd"] == pytest.approx(1.0)
    assert payload["remaining_usd"] == pytest.approx(0.5)
    assert payload["utilization"] == pytest.approx(0.5)
    assert payload["request_count"] == 2


def test_snapshot_to_dict_uses_string_inf_for_unlimited() -> None:
    """``inf`` limits serialize as the string ``"inf"`` for JSON compatibility."""
    snap = BudgetSnapshot(
        tier=None, spend_usd=0.0, limit_usd=float("inf"), request_count=0
    )
    payload = snap.to_dict()
    assert payload["limit_usd"] == "inf"
    assert payload["remaining_usd"] == "inf"
    assert payload["tier"] == "global"


# ---------------------------------------------------------------------------
# BudgetTracker.check / record
# ---------------------------------------------------------------------------


def test_tracker_default_policy_is_unlimited() -> None:
    """A tracker with no policy accepts any cost without raising."""
    tracker = BudgetTracker()
    # 1 trillion USD is a fictional spend that would breach any cap —
    # yet the unlimited policy accepts it.
    tracker.check("haiku", 1_000_000_000_000.0)
    tracker.record("haiku", 1_000_000_000_000.0)
    assert tracker.snapshot().spend_usd == pytest.approx(1_000_000_000_000.0)


def test_tracker_global_cap_refuses_breach() -> None:
    """A single call that would exceed the global cap raises ``BudgetExceeded``."""
    tracker = BudgetTracker(
        policy=BudgetPolicy(global_limit_usd=1.0)
    )
    with pytest.raises(BudgetExceeded) as excinfo:
        tracker.check("haiku", 5.0)
    assert "haiku" in str(excinfo.value)
    # Detail payload is suitable for inclusion in audit entries.
    detail = excinfo.value.detail
    assert detail["tier"] == "haiku"
    assert detail["limiting_scope"] == "global"
    assert detail["global_limit_usd"] == 1.0
    assert detail["projected_global_usd"] == pytest.approx(5.0)


def test_tracker_per_tier_cap_refuses_breach() -> None:
    """A per-tier cap kicks in even when the global cap is roomier."""
    tracker = BudgetTracker(
        policy=BudgetPolicy(
            global_limit_usd=100.0, per_tier_limits_usd={"haiku": 2.0}
        )
    )
    with pytest.raises(BudgetExceeded) as excinfo:
        tracker.check("haiku", 5.0)
    assert excinfo.value.detail["limiting_scope"] == "tier"
    assert excinfo.value.detail["per_tier_limit_usd"] == 2.0


def test_tracker_allows_within_budget() -> None:
    """A check within the limit is a no-op (no exception, no state change)."""
    tracker = BudgetTracker(
        policy=BudgetPolicy(global_limit_usd=10.0, per_tier_limits_usd={"haiku": 1.0})
    )
    tracker.check("haiku", 0.5)  # within the per-tier cap
    # Spend was NOT yet recorded — check is a read-only gate.
    assert tracker.snapshot().spend_usd == 0.0
    assert tracker.snapshot("haiku").spend_usd == 0.0


def test_tracker_record_accumulates_global_and_per_tier() -> None:
    """``record`` advances both global and per-tier spend atomically."""
    tracker = BudgetTracker(
        policy=BudgetPolicy(global_limit_usd=10.0)
    )
    tracker.record("haiku", 1.0)
    tracker.record("haiku", 0.5)
    tracker.record("opus", 2.0)
    assert tracker.snapshot().spend_usd == pytest.approx(3.5)
    assert tracker.snapshot("haiku").spend_usd == pytest.approx(1.5)
    assert tracker.snapshot("opus").spend_usd == pytest.approx(2.0)
    assert tracker.snapshot("haiku").request_count == 2
    assert tracker.snapshot("opus").request_count == 1


def test_tracker_record_zero_or_negative_is_noop() -> None:
    """Free-tier dispatches do not move the counter."""
    tracker = BudgetTracker(policy=BudgetPolicy(global_limit_usd=10.0))
    tracker.record("freetier", 0.0)
    tracker.record("freetier", -5.0)
    assert tracker.snapshot().spend_usd == 0.0
    assert tracker.snapshot("freetier").request_count == 2


def test_tracker_unpriced_floor_prevents_bypass() -> None:
    """An unpriced tier cannot slip through with cost_usd=0."""
    tracker = BudgetTracker(
        policy=BudgetPolicy(
            global_limit_usd=0.5, per_tier_limits_usd={"mystery": 0.5}
        )
    )
    # Caller reports $0.00 for an unpriced tier — but the enforcer
    # applies the conservative floor to prevent the bypass.
    with pytest.raises(BudgetExceeded):
        tracker.check("mystery", 0.0)


def test_tracker_check_after_record_detects_overflow() -> None:
    """Recording + a follow-up check that would exceed the cap raises."""
    tracker = BudgetTracker(
        policy=BudgetPolicy(global_limit_usd=1.0, per_tier_limits_usd={"haiku": 1.0})
    )
    tracker.record("haiku", 0.8)
    # Subsequent 0.5 → 0.8 + 0.5 = 1.3 > 1.0 → reject.
    with pytest.raises(BudgetExceeded):
        tracker.check("haiku", 0.5)


def test_tracker_check_after_record_within_cap() -> None:
    """Recording + a follow-up check within the cap is silent."""
    tracker = BudgetTracker(
        policy=BudgetPolicy(global_limit_usd=1.0, per_tier_limits_usd={"haiku": 1.0})
    )
    tracker.record("haiku", 0.4)
    tracker.check("haiku", 0.3)  # 0.7 < 1.0
    tracker.record("haiku", 0.3)
    assert tracker.snapshot("haiku").spend_usd == pytest.approx(0.7)


def test_tracker_snapshot_unknown_tier_is_zero() -> None:
    """A tier that has never been recorded reports zero spend."""
    tracker = BudgetTracker(policy=BudgetPolicy(global_limit_usd=10.0))
    snap = tracker.snapshot("never-called")
    assert snap.spend_usd == 0.0
    assert snap.request_count == 0
    # limit_for still reports the per-tier or global cap.
    assert snap.limit_usd == 10.0


def test_tracker_reset_zeroes_all_state() -> None:
    """``reset`` is the test/admin escape hatch that clears all counters."""
    tracker = BudgetTracker(policy=BudgetPolicy(global_limit_usd=10.0))
    tracker.record("haiku", 1.0)
    tracker.record("opus", 2.0)
    tracker.reset()
    assert tracker.snapshot().spend_usd == 0.0
    assert tracker.snapshot("haiku").spend_usd == 0.0
    assert tracker.snapshot("opus").spend_usd == 0.0
    assert tracker.snapshot().request_count == 0


def test_tracker_policy_property_exposes_policy() -> None:
    """The ``policy`` property is the read-only handle operators inspect."""
    policy = BudgetPolicy(global_limit_usd=10.0)
    tracker = BudgetTracker(policy=policy)
    assert tracker.policy is policy


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_tracker_is_thread_safe_under_concurrent_record() -> None:
    """A burst of concurrent ``record`` calls must not lose updates."""
    tracker = BudgetTracker(
        policy=BudgetPolicy(global_limit_usd=1_000_000.0)
    )
    threads = []
    per_thread = 200
    for _ in range(10):
        t = threading.Thread(
            target=lambda: [tracker.record("haiku", 0.001) for _ in range(per_thread)]
        )
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    # 10 threads * 200 records * $0.001 = $2.0.
    expected = 10 * per_thread * 0.001
    assert tracker.snapshot().spend_usd == pytest.approx(expected)
    assert tracker.snapshot("haiku").request_count == 10 * per_thread


def test_tracker_concurrent_check_within_budget_never_raises() -> None:
    """Concurrent checks that all stay under the cap never raise."""
    tracker = BudgetTracker(
        policy=BudgetPolicy(global_limit_usd=100.0, per_tier_limits_usd={"haiku": 100.0})
    )
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            for _ in range(100):
                tracker.check("haiku", 0.1)  # 100 * 0.1 = 10 << 100
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
