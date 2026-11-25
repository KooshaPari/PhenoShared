"""Per-adapter token-bucket rate limiting for evidence adapters."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class RateLimiter:
    """Token-bucket limiter (default 5 req/s, burst 10).

    Thread-safe via ``threading.Lock`` and ``time.monotonic``. No external
    dependencies. Use per-adapter instances via :func:`get_rate_limiter`.
    """

    def __init__(
        self,
        rate: float = 5.0,
        burst: int = 10,
        *,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        """Initialize token bucket with rate, burst, and optional clock/sleeper."""

        if rate <= 0 or burst < 1:
            raise ValueError("rate must be >0 and burst >=1")
        self.rate: float = float(rate)
        self.burst: int = int(burst)
        self._tokens: float = float(burst)
        self._lock: threading.Lock = threading.Lock()
        # Allow injection for tests without changing production path.
        self._clock: Callable[[], float] | None = clock
        self._sleeper: Callable[[float], None] | None = sleeper
        self._last: float = self._now()

    def _now(self) -> float:
        if self._clock is not None:
            return float(self._clock())
        return time.monotonic()

    def _sleep(self, secs: float) -> None:
        if self._sleeper is not None:
            self._sleeper(secs)
            return
        time.sleep(secs)

    def _refill(self) -> None:
        now = self._now()
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(float(self.burst), self._tokens + elapsed * self.rate)
            self._last = now

    def try_acquire(self, tokens: int = 1) -> bool:
        """Attempt to consume *tokens* without blocking. Return True on success."""
        if tokens < 1:
            raise ValueError("tokens must be >=1")
        with self._lock:
            self._refill()
            if self._tokens >= float(tokens):
                self._tokens -= float(tokens)
                return True
            return False

    def acquire(self, tokens: int = 1) -> None:
        """Block until *tokens* are available, then consume them."""
        if tokens < 1:
            raise ValueError("tokens must be >=1")
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= float(tokens):
                    self._tokens -= float(tokens)
                    return
                # tokens needed
                needed = float(tokens) - self._tokens
                wait = needed / self.rate
            # sleep outside lock
            # bound wait to avoid infinite sleep on clock skew
            if wait < 0:
                wait = 0
            self._sleep(wait)

    @property
    def available_tokens(self) -> float:
        """Current available tokens (refilled, thread-safe snapshot)."""
        with self._lock:
            self._refill()
            return float(self._tokens)


# Per-adapter singleton registry.
_REGISTRY: dict[str, RateLimiter] = {}
_REGISTRY_LOCK: threading.Lock = threading.Lock()

DEFAULT_RATE: float = 5.0
DEFAULT_BURST: int = 10

# Canonical 9 adapters for v0.12 (6 + openalex/scholar/wikipedia).
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


def get_rate_limiter(
    adapter: str,
    *,
    rate: float = DEFAULT_RATE,
    burst: int = DEFAULT_BURST,
) -> RateLimiter:
    """Return the shared :class:`RateLimiter` for *adapter* (create on demand)."""
    key = adapter.lower()
    with _REGISTRY_LOCK:
        if key not in _REGISTRY:
            _REGISTRY[key] = RateLimiter(rate=rate, burst=burst)
        return _REGISTRY[key]


def _reset_registry() -> None:
    """Clear registry (test helper)."""
    with _REGISTRY_LOCK:
        _REGISTRY.clear()


__all__ = [
    "ADAPTER_NAMES",
    "DEFAULT_BURST",
    "DEFAULT_RATE",
    "RateLimiter",
    "get_rate_limiter",
]
