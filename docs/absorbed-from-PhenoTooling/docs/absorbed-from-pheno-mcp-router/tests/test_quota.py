"""Tests for the :mod:`pheno_mcp_router.quota` rolling-window system.

The quota system caps tokens/request-count over a sliding window.
The tests use an injected monotonic clock so the rolling-window
pruning can be exercised deterministically without ``time.sleep``.
A small thread fan-out covers the concurrent record/check race.

Ported from dispatch-mcp W2-1 (test_core_quota.py @ 6aad7fa) per
L5-104.1 with import rewrite.
"""

from __future__ import annotations

import threading
from collections import deque

import pytest

from pheno_mcp_router.quota import (
    QuotaExceeded,
    QuotaPolicy,
    QuotaSnapshot,
    QuotaTracker,
    _Event,
)


# ---------------------------------------------------------------------------
# QuotaPolicy
# ---------------------------------------------------------------------------


def test_policy_default_window_is_60s() -> None:
    """The default window length is one minute."""
    policy = QuotaPolicy()
    assert policy.window_seconds == 60.0


def test_policy_default_limits_are_unlimited() -> None:
    """Default policy applies no token or request caps."""
    policy = QuotaPolicy()
    assert policy.max_tokens_per_window is None
    assert policy.max_requests_per_window is None
    assert policy.per_tier_max_tokens == {}
    assert policy.per_tier_max_requests == {}


def test_policy_rejects_window_below_floor() -> None:
    """A 0-second (or negative) window would defeat the quota system."""
    with pytest.raises(ValueError, match="window_seconds must be >= 1"):
        QuotaPolicy(window_seconds=0.0)
    with pytest.raises(ValueError, match="window_seconds must be >= 1"):
        QuotaPolicy(window_seconds=0.5)


def test_policy_rejects_negative_token_limit() -> None:
    """A negative token cap is a misconfiguration that must fail loud."""
    with pytest.raises(ValueError, match="max_tokens_per_window must be >= 0"):
        QuotaPolicy(max_tokens_per_window=-1)


def test_policy_rejects_negative_request_limit() -> None:
    """A negative request cap is a misconfiguration that must fail loud."""
    with pytest.raises(ValueError, match="max_requests_per_window must be >= 0"):
        QuotaPolicy(max_requests_per_window=-1)


def test_policy_from_dict_with_valid_data() -> None:
    """A plain dict coerces cleanly into a policy."""
    policy = QuotaPolicy.from_dict(
        {
            "window_seconds": 30.0,
            "max_tokens_per_window": 1000,
            "max_requests_per_window": 10,
            "per_tier_max_tokens": {"haiku": 500, "opus": 200},
            "per_tier_max_requests": {"haiku": 5},
        }
    )
    assert policy.window_seconds == 30.0
    assert policy.max_tokens_per_window == 1000
    assert policy.max_requests_per_window == 10
    assert policy.per_tier_max_tokens == {"haiku": 500, "opus": 200}
    assert policy.per_tier_max_requests == {"haiku": 5}


def test_policy_from_dict_normalizes_keys_to_lowercase() -> None:
    """Tier names are lowercased to match the canonical casing."""
    policy = QuotaPolicy.from_dict(
        {"per_tier_max_tokens": {"Haiku": 100, "OPUS": 50}}
    )
    assert "haiku" in policy.per_tier_max_tokens
    assert "opus" in policy.per_tier_max_tokens


def test_policy_from_dict_empty_input_yields_defaults() -> None:
    """``None`` or empty dict produces a default policy."""
    assert QuotaPolicy.from_dict(None).window_seconds == 60.0
    assert QuotaPolicy.from_dict({}).max_tokens_per_window is None


def test_policy_from_dict_invalid_values_are_skipped() -> None:
    """A bad value in a per-tier dict is dropped (not crashing)."""
    policy = QuotaPolicy.from_dict(
        {"per_tier_max_tokens": {"haiku": 100, "opus": "garbage"}}
    )
    assert policy.per_tier_max_tokens == {"haiku": 100}


# ---------------------------------------------------------------------------
# QuotaSnapshot
# ---------------------------------------------------------------------------


def test_snapshot_remaining_unlimited_is_none() -> None:
    """An unlimited snapshot reports ``None`` remaining (not ``inf``)."""
    snap = QuotaSnapshot(
        tier="haiku",
        window_seconds=60.0,
        tokens_used=10,
        requests_used=1,
        token_limit=None,
        request_limit=None,
    )
    assert snap.tokens_remaining is None
    assert snap.requests_remaining is None


def test_snapshot_remaining_clamps_to_zero() -> None:
    """Over-limit snapshots report zero remaining (not negative)."""
    snap = QuotaSnapshot(
        tier="haiku",
        window_seconds=60.0,
        tokens_used=200,
        requests_used=20,
        token_limit=100,
        request_limit=10,
    )
    assert snap.tokens_remaining == 0
    assert snap.requests_remaining == 0


def test_snapshot_to_dict_shape() -> None:
    """The serialized shape is stable and includes remaining headroom."""
    snap = QuotaSnapshot(
        tier="haiku",
        window_seconds=30.0,
        tokens_used=50,
        requests_used=2,
        token_limit=100,
        request_limit=10,
    )
    payload = snap.to_dict()
    assert payload["tier"] == "haiku"
    assert payload["window_seconds"] == 30.0
    assert payload["tokens_used"] == 50
    assert payload["requests_used"] == 2
    assert payload["token_limit"] == 100
    assert payload["request_limit"] == 10
    assert payload["tokens_remaining"] == 50
    assert payload["requests_remaining"] == 8


def test_snapshot_to_dict_global_tier_label() -> None:
    """The global (tier=None) snapshot serializes as ``"global"``."""
    snap = QuotaSnapshot(
        tier=None,
        window_seconds=60.0,
        tokens_used=0,
        requests_used=0,
        token_limit=1000,
        request_limit=100,
    )
    payload = snap.to_dict()
    assert payload["tier"] == "global"


# ---------------------------------------------------------------------------
# QuotaTracker: check, record, snapshot
# ---------------------------------------------------------------------------


class _Clock:
    """A monotonic clock stub controllable by the test."""

    def __init__(self, start: float = 1000.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def test_tracker_default_policy_accepts_anything() -> None:
    """A tracker with the default policy never raises."""
    tracker = QuotaTracker(clock=_Clock())
    for _ in range(100):
        tracker.check("haiku", tokens=10_000)


def test_tracker_check_rejects_over_token_limit() -> None:
    """A token cap fires when the projected sum exceeds the limit."""
    clock = _Clock()
    tracker = QuotaTracker(
        policy=QuotaPolicy(max_tokens_per_window=100), clock=clock
    )
    tracker.record("haiku", tokens=80)
    with pytest.raises(QuotaExceeded) as excinfo:
        tracker.check("haiku", tokens=30)  # 80 + 30 > 100
    assert excinfo.value.detail["limiting_dimension"] == "tokens"
    assert excinfo.value.detail["token_limit"] == 100
    assert excinfo.value.detail["tokens_used"] == 80
    assert excinfo.value.detail["tokens_requested"] == 30


def test_tracker_check_rejects_over_request_limit() -> None:
    """A request cap fires when the next request would exceed the limit."""
    clock = _Clock()
    tracker = QuotaTracker(
        policy=QuotaPolicy(max_requests_per_window=3), clock=clock
    )
    tracker.record("haiku", tokens=10)
    tracker.record("haiku", tokens=10)
    tracker.record("haiku", tokens=10)
    # Fourth request → 3 + 1 > 3.
    with pytest.raises(QuotaExceeded) as excinfo:
        tracker.check("haiku", tokens=10)
    assert excinfo.value.detail["limiting_dimension"] == "requests"
    assert excinfo.value.detail["request_limit"] == 3


def test_tracker_check_enforces_per_tier_independent_of_global() -> None:
    """A per-tier cap can fire even when the global cap has headroom."""
    clock = _Clock()
    tracker = QuotaTracker(
        policy=QuotaPolicy(
            max_tokens_per_window=10_000, per_tier_max_tokens={"haiku": 50}
        ),
        clock=clock,
    )
    tracker.record("haiku", tokens=40)
    with pytest.raises(QuotaExceeded) as excinfo:
        tracker.check("haiku", tokens=20)  # 40 + 20 = 60 > 50
    assert excinfo.value.detail["scope"] == "tier"
    assert excinfo.value.detail["tier"] == "haiku"


def test_tracker_check_rejects_negative_tokens() -> None:
    """Negative token counts in ``check`` raise ``ValueError`` (not silent)."""
    tracker = QuotaTracker(clock=_Clock())
    with pytest.raises(ValueError, match="tokens must be >= 0"):
        tracker.check("haiku", tokens=-1)


def test_tracker_record_clamps_negative_tokens_to_zero() -> None:
    """``record`` clamps to zero so a probe dispatch is safe."""
    clock = _Clock()
    tracker = QuotaTracker(clock=clock)
    tracker.record("haiku", tokens=-50)
    snap = tracker.snapshot("haiku")
    assert snap.tokens_used == 0
    assert snap.requests_used == 1


def test_tracker_window_prunes_old_events() -> None:
    """Events outside the rolling window are dropped from the count."""
    clock = _Clock()
    tracker = QuotaTracker(
        policy=QuotaPolicy(window_seconds=10, max_tokens_per_window=100),
        clock=clock,
    )
    tracker.record("haiku", tokens=50)
    # Advance past the window — the 50 should drop out.
    clock.advance(11)
    # A fresh 30-token dispatch should pass the gate and be recorded.
    tracker.check("haiku", tokens=30)  # gate passes (window is empty)
    tracker.record("haiku", tokens=30)  # advance the counter
    snap = tracker.snapshot("haiku")
    assert snap.tokens_used == 30


def test_tracker_snapshot_at_specific_now() -> None:
    """``snapshot(now=...)`` prunes against the explicit time, not the clock."""
    clock = _Clock(start=100.0)
    tracker = QuotaTracker(
        policy=QuotaPolicy(window_seconds=10), clock=clock
    )
    tracker.record("haiku", tokens=20)  # timestamp=100
    clock.advance(5)
    tracker.record("haiku", tokens=30)  # timestamp=105
    # Snapshot from t=110 → cutoff=100, t=100 is NOT pruned (< not <=),
    # t=105 is in window. Both events survive.
    snap = tracker.snapshot("haiku", now=110.0)
    assert snap.tokens_used == 50
    assert snap.requests_used == 2
    # Snapshot from t=120 → cutoff=110, t=100 and t=105 both pruned.
    snap_pruned = tracker.snapshot("haiku", now=120.0)
    assert snap_pruned.tokens_used == 0
    assert snap_pruned.requests_used == 0


def test_tracker_snapshot_global_aggregates_all_tiers() -> None:
    """A ``None`` snapshot aggregates across every tier in the window."""
    clock = _Clock()
    tracker = QuotaTracker(clock=clock)
    tracker.record("haiku", tokens=10)
    tracker.record("opus", tokens=20)
    tracker.record("worker", tokens=5)
    snap = tracker.snapshot()
    assert snap.tier is None
    assert snap.tokens_used == 35
    assert snap.requests_used == 3


def test_tracker_reset_clears_state() -> None:
    """``reset`` is the test/admin escape hatch that clears all events."""
    clock = _Clock()
    tracker = QuotaTracker(clock=clock)
    tracker.record("haiku", tokens=50)
    tracker.record("opus", tokens=30)
    tracker.reset()
    assert tracker.snapshot("haiku").tokens_used == 0
    assert tracker.snapshot("opus").tokens_used == 0
    assert tracker.snapshot().tokens_used == 0


def test_tracker_check_then_record_within_window() -> None:
    """A successful ``check`` followed by ``record`` is the hot-path pattern."""
    clock = _Clock()
    tracker = QuotaTracker(
        policy=QuotaPolicy(max_tokens_per_window=80), clock=clock
    )
    tracker.check("haiku", tokens=30)  # gate passes
    tracker.record("haiku", tokens=30)
    tracker.check("haiku", tokens=30)  # gate passes (30+30=60)
    tracker.record("haiku", tokens=30)
    # Next check: 60 + 30 = 90 > 80 → reject.
    with pytest.raises(QuotaExceeded):
        tracker.check("haiku", tokens=30)


def test_tracker_event_creation() -> None:
    """``_Event`` is a simple mutable holder used by the internal deque."""
    event = _Event(timestamp=1.0, tokens=42)
    assert event.timestamp == 1.0
    assert event.tokens == 42


def test_tracker_prune_drops_left_oldest_first() -> None:
    """``_prune`` drops events from the left of the deque (FIFO, strict <)."""
    clock = _Clock()
    tracker = QuotaTracker(clock=clock)
    # Inject a known deque with three events.
    dq: deque[_Event] = deque(
        [
            _Event(timestamp=10.0, tokens=1),
            _Event(timestamp=20.0, tokens=2),
            _Event(timestamp=30.0, tokens=3),
        ]
    )
    # Prune with cutoff=20 → the boundary is strict (<, not <=),
    # so t=10 is dropped, t=20 and t=30 stay.
    tracker._prune(dq, cutoff=20.0)  # type: ignore[attr-defined]
    assert [e.timestamp for e in dq] == [20.0, 30.0]
    assert [e.tokens for e in dq] == [2, 3]


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_tracker_concurrent_record_is_thread_safe() -> None:
    """A burst of concurrent ``record`` calls must not lose events."""
    clock = _Clock()
    tracker = QuotaTracker(
        policy=QuotaPolicy(max_tokens_per_window=1_000_000_000),
        clock=clock,
    )
    per_thread = 100
    threads = []
    for _ in range(5):
        t = threading.Thread(
            target=lambda: [tracker.record("haiku", tokens=10) for _ in range(per_thread)]
        )
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    assert tracker.snapshot("haiku").tokens_used == 5 * per_thread * 10
    assert tracker.snapshot("haiku").requests_used == 5 * per_thread


def test_tracker_concurrent_check_then_record_respects_caps() -> None:
    """Concurrent workers that always pass the cap must not crash."""
    clock = _Clock()
    tracker = QuotaTracker(
        policy=QuotaPolicy(max_tokens_per_window=1_000_000, max_requests_per_window=1_000_000),
        clock=clock,
    )
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            for _ in range(50):
                tracker.check("haiku", tokens=10)
                tracker.record("haiku", tokens=10)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
