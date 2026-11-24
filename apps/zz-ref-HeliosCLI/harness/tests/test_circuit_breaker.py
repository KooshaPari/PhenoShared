"""State-machine coverage for the public CircuitBreaker API."""

from harness import CircuitBreaker


def _open_breaker() -> CircuitBreaker:
    breaker = CircuitBreaker(failure_threshold=1, timeout_seconds=0, success_threshold=3)
    breaker.record_failure()
    assert breaker._state == "open"
    assert breaker.can_execute()
    assert breaker._state == "half_open"
    return breaker


def test_open_breaker_enters_half_open_after_timeout():
    breaker = _open_breaker()

    assert breaker.can_execute()
    assert breaker._state == "half_open"


def test_half_open_requires_multiple_consecutive_successes_to_close():
    breaker = _open_breaker()

    breaker.record_success()
    assert breaker._state == "half_open"
    breaker.record_success()
    assert breaker._state == "half_open"
    breaker.record_success()

    assert breaker._state == "closed"
    assert breaker._failures == 0
    assert breaker._successes == 0


def test_half_open_failure_reopens_and_resets_recovery_credit():
    breaker = _open_breaker()
    breaker.record_success()
    assert breaker._successes == 1

    breaker.record_failure()
    assert breaker._state == "open"
    assert breaker._successes == 0

    assert breaker.can_execute()
    breaker.record_success()
    assert breaker._state == "half_open"
    assert breaker._successes == 1


def test_closed_successes_do_not_count_toward_half_open_recovery():
    breaker = CircuitBreaker(failure_threshold=1, timeout_seconds=0, success_threshold=3)
    breaker.record_success()
    breaker.record_success()

    breaker.record_failure()
    assert breaker.can_execute()
    breaker.record_success()

    assert breaker._state == "half_open"
    assert breaker._successes == 1
