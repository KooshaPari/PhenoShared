"""Tests for circuit_breaker (5 failures -> open, half-open after 30s)."""

from __future__ import annotations

from pheno.evidence.adapters.circuit_breaker import CircuitBreaker


def test_open_after_threshold() -> None:
    now = [0.0]

    def clock() -> float:
        return now[0]

    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0, clock=clock)  # type: ignore[arg-type]
    assert cb.state == "closed"
    assert cb.can_execute() is True
    for _ in range(4):
        cb.record_failure()
        assert cb.state == "closed"
        assert cb.can_execute() is True
    cb.record_failure()  # 5th
    assert cb.state == "open"
    assert cb.can_execute() is False
    # still open before timeout
    now[0] = 29.0
    assert cb.can_execute() is False
    assert cb.state == "open"


def test_half_open_recovery() -> None:
    now = [0.0]

    def clock() -> float:
        return now[0]

    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0, clock=clock)  # type: ignore[arg-type]
    for _ in range(5):
        cb.record_failure()
    assert cb.state == "open"
    # advance past timeout -> half-open
    now[0] = 30.0
    assert cb.can_execute() is True
    assert cb.state == "half_open"
    # success closes it
    cb.record_success()
    assert cb.state == "closed"
    assert cb.can_execute() is True
    assert cb.failure_count == 0
    # reopen then half-open failure re-opens
    for _ in range(5):
        cb.record_failure()
    now[0] = 60.0
    assert cb.can_execute() is True  # half-open again
    assert cb.state == "half_open"
    cb.record_failure()
    assert cb.state == "open"
    assert cb.can_execute() is False
