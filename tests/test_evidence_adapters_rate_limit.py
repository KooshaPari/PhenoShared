"""Tests for rate_limit token bucket (5 req/s, burst 10)."""

from __future__ import annotations

from pheno.evidence.adapters.rate_limit import RateLimiter


def test_within_limit_passes() -> None:
    now = [0.0]

    def clock() -> float:
        return now[0]

    rl = RateLimiter(rate=5.0, burst=10, clock=clock, sleeper=lambda _: None)  # type: ignore[arg-type]
    # consume burst exactly — all should succeed without sleep
    for _ in range(10):
        assert rl.try_acquire() is True
    # next one fails (bucket empty, no time elapsed)
    assert rl.try_acquire() is False
    # advance 1s -> 5 tokens refill
    now[0] = 1.0
    assert rl.try_acquire() is True
    # 4 more should pass (5 refilled, 1 consumed)
    for _ in range(4):
        assert rl.try_acquire() is True
    assert rl.try_acquire() is False


def test_over_limit_throttles() -> None:
    now = [0.0]
    sleeps: list[float] = []

    def clock() -> float:
        return now[0]

    def sleeper(secs: float) -> None:
        sleeps.append(secs)
        now[0] += secs

    rl = RateLimiter(rate=5.0, burst=10, clock=clock, sleeper=sleeper)  # type: ignore[arg-type]
    # exhaust burst
    for _ in range(10):
        rl.try_acquire()
    # acquire should block ~0.2s for 1 token at 5/s
    rl.acquire(tokens=1)
    assert len(sleeps) == 1
    assert 0.19 < sleeps[0] < 0.21
    # after sleep, token consumed so next try fails until refill
    assert rl.try_acquire() is False
