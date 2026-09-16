"""Per-adapter circuit breaker for evidence adapters."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class CircuitBreaker:
    """Closed -> open on 5 consecutive failures, half-open after 30s.

    Thread-safe via ``threading.Lock`` and ``time.monotonic``. No external deps.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if failure_threshold < 1 or recovery_timeout <= 0:
            raise ValueError("invalid circuit breaker bounds")
        self.failure_threshold: int = int(failure_threshold)
        self.recovery_timeout: float = float(recovery_timeout)
        self._lock: threading.Lock = threading.Lock()
        self._failures: int = 0
        self._state: str = "closed"  # closed | open | half_open
        self._opened_at: float | None = None
        self._clock: Callable[[], float] | None = clock

    def _now(self) -> float:
        if self._clock is not None:
            return float(self._clock())
        return time.monotonic()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failures

    def can_execute(self) -> bool:
        """Return True if caller should attempt the operation."""
        with self._lock:
            if self._state == "closed":
                return True
            if self._state == "half_open":
                return True
            # open
            assert self._state == "open"  # nosec B101
            if self._opened_at is None:
                return False
            elapsed = self._now() - self._opened_at
            if elapsed >= self.recovery_timeout:
                self._state = "half_open"
                return True
            return False

    def record_success(self) -> None:
        """Record a successful call; closes the breaker."""
        with self._lock:
            self._failures = 0
            self._state = "closed"
            self._opened_at = None

    def record_failure(self) -> None:
        """Record a failure; opens breaker if threshold reached."""
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = "open"
                self._opened_at = self._now()
            elif self._state == "half_open":
                # Any failure in half-open re-opens immediately
                self._state = "open"
                self._opened_at = self._now()

    def reset(self) -> None:
        """Force-closed (test helper)."""
        with self._lock:
            self._failures = 0
            self._state = "closed"
            self._opened_at = None


# Per-adapter singleton registry.
_REGISTRY: dict[str, CircuitBreaker] = {}
_REGISTRY_LOCK: threading.Lock = threading.Lock()

DEFAULT_FAILURE_THRESHOLD: int = 5
DEFAULT_RECOVERY_TIMEOUT: float = 30.0

ADAPTER_NAMES: tuple[str, ...] = (
    "arxiv",
    "github",
    "huggingface",
    "modelscope",
    "reddit",
    "local_corpus",
    "openalex",
    "semantic_scholar",
    "wikipedia",
)


def get_circuit_breaker(
    adapter: str,
    *,
    failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
    recovery_timeout: float = DEFAULT_RECOVERY_TIMEOUT,
) -> CircuitBreaker:
    """Return the shared :class:`CircuitBreaker` for *adapter*."""
    key = adapter.lower()
    with _REGISTRY_LOCK:
        if key not in _REGISTRY:
            _REGISTRY[key] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
            )
        return _REGISTRY[key]


def _reset_registry() -> None:
    """Clear registry (test helper)."""
    with _REGISTRY_LOCK:
        _REGISTRY.clear()


__all__ = [
    "ADAPTER_NAMES",
    "CircuitBreaker",
    "DEFAULT_FAILURE_THRESHOLD",
    "DEFAULT_RECOVERY_TIMEOUT",
    "get_circuit_breaker",
]
