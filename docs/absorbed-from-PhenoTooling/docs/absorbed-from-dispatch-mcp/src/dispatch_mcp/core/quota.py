"""Usage quota system for dispatch_mcp.

The quota system gates dispatches on rolling-window token and
request counts. It is intentionally distinct from the budget
enforcer: budgets cap cumulative spend (USD), quotas cap
cumulative usage (tokens, request count) over a fixed time
window. Both layers cooperate — a dispatch must pass the quota
gate before it can spend, and a successful dispatch accrues
spend on the budget tracker.

A sliding window is implemented with a per-(tier, window) list
of recorded events. This is exact (no bucket-refresh edge
cases) and trivially testable. For a high-throughput deployment
the implementation can be swapped for a token-bucket variant
without changing the public API.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Final, overload

# Minimum window length. Anything shorter is a misconfiguration
# that would let callers reset the window by retrying; we clamp
# to this floor so the quota system cannot be silently disabled.
_MIN_WINDOW_SECONDS: Final[float] = 1.0


class QuotaExceeded(RuntimeError):
    """Raised when a dispatch would exceed a configured quota limit.

    The ``detail`` attribute carries a structured payload suitable
    for inclusion in MCP tool error responses and audit entries.
    """

    def __init__(self, message: str, detail: dict[str, Any]) -> None:
        super().__init__(message)
        self.detail = detail


@dataclass(slots=True, frozen=True)
class QuotaPolicy:
    """Per-tier and global rolling-window limits.

    ``window_seconds`` is the rolling window applied to both
    request counts and token counts. ``max_tokens_per_window``
    is the cap on the sum of input + output tokens in the
    window. ``max_requests_per_window`` is the cap on the number
    of dispatches. Either cap can be set to ``None`` (or
    omitted) to disable that particular check.
    """

    window_seconds: float = 60.0
    max_tokens_per_window: int | None = None
    max_requests_per_window: int | None = None
    per_tier_max_tokens: dict[str, int] = field(default_factory=dict)
    per_tier_max_requests: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.window_seconds < _MIN_WINDOW_SECONDS:
            raise ValueError(
                f"window_seconds must be >= {_MIN_WINDOW_SECONDS}; "
                f"got {self.window_seconds}"
            )
        if self.max_tokens_per_window is not None and self.max_tokens_per_window < 0:
            raise ValueError("max_tokens_per_window must be >= 0")
        if self.max_requests_per_window is not None and self.max_requests_per_window < 0:
            raise ValueError("max_requests_per_window must be >= 0")

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> QuotaPolicy:
        """Build a policy from a plain dict (e.g. JSON config).

        Missing or invalid values are coerced to permissive
        defaults (no limit). ``per_tier`` keys are lowercased.
        """
        if not data:
            return cls()
        try:
            window = float(data.get("window_seconds", 60.0))
        except (TypeError, ValueError):
            window = 60.0
        max_tokens = data.get("max_tokens_per_window")
        max_requests = data.get("max_requests_per_window")
        per_tier_tokens_raw = data.get("per_tier_max_tokens") or {}
        per_tier_requests_raw = data.get("per_tier_max_requests") or {}
        per_tier_tokens: dict[str, int] = {}
        per_tier_requests: dict[str, int] = {}
        if isinstance(per_tier_tokens_raw, dict):
            for key, value in per_tier_tokens_raw.items():
                try:
                    per_tier_tokens[str(key).lower()] = int(value)
                except (TypeError, ValueError):
                    continue
        if isinstance(per_tier_requests_raw, dict):
            for key, value in per_tier_requests_raw.items():
                try:
                    per_tier_requests[str(key).lower()] = int(value)
                except (TypeError, ValueError):
                    continue
        return cls(
            window_seconds=window,
            max_tokens_per_window=int(max_tokens) if max_tokens is not None else None,
            max_requests_per_window=int(max_requests) if max_requests is not None else None,
            per_tier_max_tokens=per_tier_tokens,
            per_tier_max_requests=per_tier_requests,
        )


@dataclass(slots=True, frozen=True)
class QuotaSnapshot:
    """Read-only view of in-window usage for a tier or the whole process."""

    tier: str | None
    window_seconds: float
    tokens_used: int
    requests_used: int
    token_limit: int | None
    request_limit: int | None

    @property
    def tokens_remaining(self) -> int | None:
        """Return the headroom in tokens, or ``None`` if unlimited."""
        if self.token_limit is None:
            return None
        return max(0, self.token_limit - self.tokens_used)

    @property
    def requests_remaining(self) -> int | None:
        """Return the headroom in requests, or ``None`` if unlimited."""
        if self.request_limit is None:
            return None
        return max(0, self.request_limit - self.requests_used)

    def to_dict(self) -> dict[str, str | int | float | None]:
        """Serialize for inclusion in tool responses and audit entries."""
        return {
            "tier": self.tier or "global",
            "window_seconds": self.window_seconds,
            "tokens_used": self.tokens_used,
            "requests_used": self.requests_used,
            "token_limit": self.token_limit,
            "request_limit": self.request_limit,
            "tokens_remaining": self.tokens_remaining,
            "requests_remaining": self.requests_remaining,
        }


@dataclass(slots=True)
class _Event:
    """Single dispatch event in the sliding window.

    Mutable so the deques can hold one record per dispatch and the
    tracker can advance ``now`` consistently for every check /
    record pair under the same lock.
    """

    timestamp: float
    tokens: int


class QuotaTracker:
    """Thread-safe rolling-window quota tracker.

    Internally the tracker keeps a per-tier deque of events
    (timestamp, tokens). On every :meth:`check` call it first
    prunes events older than the window, then enforces the
    applicable limits. The deque is append-only during normal
    operation; entries are dropped from the left as time moves
    forward.
    """

    __slots__ = ("_policy", "_lock", "_clock", "_global_events", "_per_tier_events")

    def __init__(
        self,
        policy: QuotaPolicy | None = None,
        *,
        clock: Any = None,
    ) -> None:
        self._policy: QuotaPolicy = policy or QuotaPolicy()
        self._lock = threading.Lock()
        # ``clock`` is injectable for tests; defaults to ``time.monotonic``.
        self._clock = clock if clock is not None else time.monotonic
        self._global_events: deque[_Event] = deque()
        self._per_tier_events: dict[str, deque[_Event]] = {}

    @property
    def policy(self) -> QuotaPolicy:
        """Return the active policy (read-only access)."""
        return self._policy

    def _prune(self, events: deque[_Event], cutoff: float) -> None:
        """Drop events strictly older than ``cutoff`` from the left of ``events``.

        The boundary is strict (``<``) so an event recorded at
        the exact moment of the cutoff is still in the window.
        This is the conventional sliding-window semantics: the
        window is ``[now - window_seconds, now]``.
        """
        while events and events[0].timestamp < cutoff:
            events.popleft()

    def _tokens_in_window(self, events: deque[_Event]) -> int:
        """Return the sum of tokens across events in ``events``."""
        return sum(event.tokens for event in events)

    def _requests_in_window(self, events: deque[_Event]) -> int:
        """Return the number of events in ``events``."""
        return len(events)

    def _enforce(
        self,
        *,
        scope: str,
        tier: str | None,
        tokens: int,
        token_limit: int | None,
        request_limit: int | None,
        tokens_in_window: int,
        requests_in_window: int,
    ) -> None:
        """Raise :class:`QuotaExceeded` if adding ``tokens`` would exceed a limit.

        ``scope`` is ``"global"`` or ``"tier"``; ``tier`` is the
        tier name when scope is tier. The two limits (tokens vs
        requests) are independent; whichever is exceeded first
        becomes the violation cause.
        """
        if token_limit is not None and tokens_in_window + tokens > token_limit:
            detail = {
                "scope": scope,
                "tier": tier,
                "window_seconds": self._policy.window_seconds,
                "tokens_used": tokens_in_window,
                "tokens_requested": tokens,
                "token_limit": token_limit,
                "limiting_dimension": "tokens",
            }
            raise QuotaExceeded(
                f"Quota exceeded ({scope}, tokens): "
                f"{tokens_in_window} + {tokens} > {token_limit}",
                detail,
            )
        if request_limit is not None and requests_in_window + 1 > request_limit:
            detail = {
                "scope": scope,
                "tier": tier,
                "window_seconds": self._policy.window_seconds,
                "requests_used": requests_in_window,
                "request_limit": request_limit,
                "limiting_dimension": "requests",
            }
            raise QuotaExceeded(
                f"Quota exceeded ({scope}, requests): "
                f"{requests_in_window + 1} > {request_limit}",
                detail,
            )

    def check(self, tier: str, tokens: int = 0) -> None:
        """Raise :class:`QuotaExceeded` if ``tier`` cannot accept a dispatch of ``tokens``.

        The check is read-only: a successful :meth:`check` does
        not advance any counter. Callers must invoke
        :meth:`record` after a successful dispatch so the
        counters reflect what actually happened.
        """
        if tokens < 0:
            raise ValueError("tokens must be >= 0")
        window = self._policy.window_seconds
        with self._lock:
            now = float(self._clock())
            cutoff = now - window
            self._prune(self._global_events, cutoff)
            tier_events = self._per_tier_events.get(tier)
            if tier_events is not None:
                self._prune(tier_events, cutoff)
            else:
                tier_events = deque()
                self._per_tier_events[tier] = tier_events

            global_tokens = self._tokens_in_window(self._global_events)
            global_requests = self._requests_in_window(self._global_events)
            tier_tokens = self._tokens_in_window(tier_events)
            tier_requests = self._requests_in_window(tier_events)

            self._enforce(
                scope="tier",
                tier=tier,
                tokens=tokens,
                token_limit=self._policy.per_tier_max_tokens.get(tier),
                request_limit=self._policy.per_tier_max_requests.get(tier),
                tokens_in_window=tier_tokens,
                requests_in_window=tier_requests,
            )
            self._enforce(
                scope="global",
                tier=None,
                tokens=tokens,
                token_limit=self._policy.max_tokens_per_window,
                request_limit=self._policy.max_requests_per_window,
                tokens_in_window=global_tokens,
                requests_in_window=global_requests,
            )

    def record(self, tier: str, tokens: int = 0) -> None:
        """Record a successful dispatch of ``tokens`` to ``tier``.

        Negative token counts are clamped to zero so a caller
        that records a probe dispatch (zero tokens) does not
        throw.
        """
        if tokens < 0:
            tokens = 0
        event = _Event(timestamp=float(self._clock()), tokens=int(tokens))
        with self._lock:
            self._global_events.append(event)
            tier_events = self._per_tier_events.get(tier)
            if tier_events is None:
                tier_events = deque()
                self._per_tier_events[tier] = tier_events
            tier_events.append(event)

    @overload
    def snapshot(self, tier: str | None = ...) -> QuotaSnapshot: ...

    @overload
    def snapshot(self, tier: str | None, *, now: float | None = ...) -> QuotaSnapshot: ...

    def snapshot(self, tier: str | None = None, *, now: float | None = None) -> QuotaSnapshot:
        """Return a :class:`QuotaSnapshot` for ``tier`` (or the global window).

        ``now`` is exposed for tests; in production the tracker
        reads the injected clock. The snapshot is captured under
        the lock so concurrent dispatches cannot tear the
        counts.
        """
        with self._lock:
            snapshot_now = float(now) if now is not None else float(self._clock())
            cutoff = snapshot_now - self._policy.window_seconds
            self._prune(self._global_events, cutoff)
            if tier is None:
                return QuotaSnapshot(
                    tier=None,
                    window_seconds=self._policy.window_seconds,
                    tokens_used=self._tokens_in_window(self._global_events),
                    requests_used=self._requests_in_window(self._global_events),
                    token_limit=self._policy.max_tokens_per_window,
                    request_limit=self._policy.max_requests_per_window,
                )
            tier_events = self._per_tier_events.get(tier)
            if tier_events is None:
                tier_events = deque()
            self._prune(tier_events, cutoff)
            return QuotaSnapshot(
                tier=tier,
                window_seconds=self._policy.window_seconds,
                tokens_used=self._tokens_in_window(tier_events),
                requests_used=self._requests_in_window(tier_events),
                token_limit=self._policy.per_tier_max_tokens.get(tier),
                request_limit=self._policy.per_tier_max_requests.get(tier),
            )

    def reset(self) -> None:
        """Drop all recorded events. Intended for tests and admin tools."""
        with self._lock:
            self._global_events.clear()
            self._per_tier_events.clear()
