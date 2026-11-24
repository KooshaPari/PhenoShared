"""Audit trail for dispatch model selections.

The audit trail records every dispatch decision — both the
successful ones and the ones the cost-tracking middleware
refused (quota or budget exceeded). The log is the canonical
record of which upstream model served which request and at
what cost; it is also the source of truth for post-hoc
analysis ("which tier consumed the most tokens yesterday?").

The default :class:`AuditLog` is an in-memory append-only
list. An optional JSONL sink can be wired in for durable
persistence; the log is otherwise stateless and never blocks
on I/O. Reads are O(N) over the recorded history, which is
acceptable for the request volumes dispatch-mcp handles.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, IO, Final, Literal

# Allowed decisions. "allowed" is the success path; "blocked"
# is recorded when a quota or budget gate refuses the dispatch.
# "dry_run" is a future-proofing value used by tooling that
# evaluates cost without actually dispatching.
Decision = Literal["allowed", "blocked", "dry_run"]
_DECISION_VALUES: Final[frozenset[str]] = frozenset({"allowed", "blocked", "dry_run"})


@dataclass(slots=True, frozen=True)
class AuditEntry:
    """A single row in the audit trail.

    ``decision`` distinguishes successful from refused
    dispatches. ``reason`` is a short machine-readable tag
    (``"ok"``, ``"quota"``, ``"budget"``) used by operators
    for filtering; ``detail`` is an optional structured
    payload with the underlying policy state. ``request_id``
    is a per-dispatch UUID so an entry can be correlated with
    upstream logs.
    """

    request_id: str
    timestamp: float
    tier: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    decision: str
    reason: str
    is_priced: bool
    detail: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.decision not in _DECISION_VALUES:
            raise ValueError(
                f"decision must be one of {sorted(_DECISION_VALUES)}; got {self.decision!r}"
            )
        if self.input_tokens < 0:
            raise ValueError("input_tokens must be >= 0")
        if self.output_tokens < 0:
            raise ValueError("output_tokens must be >= 0")
        if self.cost_usd < 0:
            raise ValueError("cost_usd must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict (used by JSONL persistence)."""
        result = asdict(self)
        result["timestamp_iso"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp)
        )
        return result


@dataclass(slots=True, frozen=True)
class AuditSummary:
    """Aggregate counters derived from a set of audit entries.

    Returned by :meth:`AuditLog.summarize`. ``total_spend_usd``
    is the sum of cost across allowed entries; blocked entries
    are reported by count but not by cost (they did not
    consume upstream capacity).
    """

    total_entries: int
    allowed_entries: int
    blocked_entries: int
    total_input_tokens: int
    total_output_tokens: int
    total_spend_usd: float
    spend_by_tier: dict[str, float]
    requests_by_tier: dict[str, int]
    spend_by_model: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        """Serialize for inclusion in tool responses and reports."""
        return {
            "total_entries": self.total_entries,
            "allowed_entries": self.allowed_entries,
            "blocked_entries": self.blocked_entries,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_spend_usd": round(self.total_spend_usd, 8),
            "spend_by_tier": {
                tier: round(amount, 8) for tier, amount in self.spend_by_tier.items()
            },
            "requests_by_tier": dict(self.requests_by_tier),
            "spend_by_model": {
                model: round(amount, 8) for model, amount in self.spend_by_model.items()
            },
        }


class AuditLog:
    """Thread-safe append-only audit log.

    Records are kept in memory and, optionally, mirrored to a
    JSONL file for durability. The in-memory list is the
    source of truth for queries; the JSONL file is a
    one-way tap that does not influence reads.

    The log does not enforce a maximum size by default. Set
    ``max_entries`` to bound memory use in long-running
    deployments; the oldest entries are dropped when the cap
    is reached (audit records are summarized elsewhere for
    long-term retention).
    """

    __slots__ = (
        "_lock",
        "_entries",
        "_clock",
        "_id_factory",
        "_sink",
        "_sink_lock",
        "_max_entries",
    )

    def __init__(
        self,
        *,
        max_entries: int | None = None,
        jsonl_path: str | os.PathLike[str] | None = None,
        clock: Any = None,
        id_factory: Any = None,
    ) -> None:
        if max_entries is not None and max_entries < 0:
            raise ValueError("max_entries must be >= 0")
        self._lock = threading.Lock()
        self._entries: list[AuditEntry] = []
        self._clock = clock if clock is not None else time.time
        self._id_factory = id_factory if id_factory is not None else uuid.uuid4
        self._sink: IO[str] | None = None
        self._sink_lock = threading.Lock()
        self._max_entries = max_entries
        if jsonl_path is not None:
            # Open the sink in append mode so a process restart
            # appends to the same file rather than overwriting.
            self._sink = Path(jsonl_path).open("a", encoding="utf-8")

    def close(self) -> None:
        """Flush and close the JSONL sink if one is configured.

        Safe to call multiple times; subsequent calls are
        no-ops. The in-memory entries are not affected.
        """
        with self._sink_lock:
            if self._sink is not None:
                self._sink.flush()
                self._sink.close()
                self._sink = None

    def record(
        self,
        *,
        tier: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        decision: Decision,
        reason: str = "ok",
        request_id: str | None = None,
        is_priced: bool = True,
        detail: dict[str, Any] | None = None,
        timestamp: float | None = None,
    ) -> AuditEntry:
        """Append an entry to the log and (optionally) the JSONL sink.

        ``decision`` and ``reason`` are stored as provided; the
        validation in :class:`AuditEntry` ensures only legal
        decision values are recorded. ``request_id`` defaults
        to a fresh UUID4 — pass an explicit ID when correlating
        with upstream request logs.
        """
        entry = AuditEntry(
            request_id=request_id or str(self._id_factory()),
            timestamp=float(timestamp) if timestamp is not None else float(self._clock()),
            tier=tier,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            decision=decision,
            reason=reason,
            is_priced=is_priced,
            detail=detail or {},
        )
        with self._lock:
            self._entries.append(entry)
            if self._max_entries is not None:
                # Drop the oldest entries first. The trim is
                # intentionally O(N) — it only runs when the
                # cap is reached, and is bounded by the cap.
                while len(self._entries) > self._max_entries:
                    self._entries.pop(0)
        # Sink write is outside the entry lock so a slow disk
        # does not block other recorders; the sink lock
        # serializes the sink access itself.
        if self._sink is not None:
            with self._sink_lock:
                self._sink.write(json.dumps(entry.to_dict(), sort_keys=True) + "\n")
                self._sink.flush()
        return entry

    def entries(self) -> tuple[AuditEntry, ...]:
        """Return an immutable snapshot of the recorded entries."""
        with self._lock:
            return tuple(self._entries)

    def filter(
        self,
        *,
        tier: str | None = None,
        decision: Decision | None = None,
        since: float | None = None,
        until: float | None = None,
    ) -> tuple[AuditEntry, ...]:
        """Return entries matching all of the provided filters.

        All filters are optional; an unfiltered call returns
        every entry. ``since`` and ``until`` are inclusive
        timestamps in the same epoch units used elsewhere in
        the audit trail.
        """
        with self._lock:
            results: list[AuditEntry] = []
            for entry in self._entries:
                if tier is not None and entry.tier != tier:
                    continue
                if decision is not None and entry.decision != decision:
                    continue
                if since is not None and entry.timestamp < since:
                    continue
                if until is not None and entry.timestamp > until:
                    continue
                results.append(entry)
            return tuple(results)

    def summarize(
        self,
        *,
        tier: str | None = None,
        decision: Decision | None = None,
        since: float | None = None,
        until: float | None = None,
    ) -> AuditSummary:
        """Aggregate counters for the filtered entries.

        Spend is summed only over ``allowed`` entries because
        blocked dispatches did not consume upstream capacity.
        Per-tier and per-model breakdowns are also restricted
        to allowed entries for the same reason.
        """
        allowed = 0
        blocked = 0
        total_input = 0
        total_output = 0
        total_spend = 0.0
        spend_by_tier: dict[str, float] = {}
        requests_by_tier: dict[str, int] = {}
        spend_by_model: dict[str, float] = {}
        with self._lock:
            for entry in self._entries:
                if tier is not None and entry.tier != tier:
                    continue
                if decision is not None and entry.decision != decision:
                    continue
                if since is not None and entry.timestamp < since:
                    continue
                if until is not None and entry.timestamp > until:
                    continue
                total_input += entry.input_tokens
                total_output += entry.output_tokens
                if entry.decision == "allowed":
                    allowed += 1
                    total_spend += entry.cost_usd
                    spend_by_tier[entry.tier] = spend_by_tier.get(entry.tier, 0.0) + entry.cost_usd
                    spend_by_model[entry.model] = (
                        spend_by_model.get(entry.model, 0.0) + entry.cost_usd
                    )
                    requests_by_tier[entry.tier] = requests_by_tier.get(entry.tier, 0) + 1
                elif entry.decision == "blocked":
                    blocked += 1
        return AuditSummary(
            total_entries=allowed + blocked,
            allowed_entries=allowed,
            blocked_entries=blocked,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_spend_usd=total_spend,
            spend_by_tier=spend_by_tier,
            requests_by_tier=requests_by_tier,
            spend_by_model=spend_by_model,
        )

    def clear(self) -> None:
        """Drop all in-memory entries. Does not affect the JSONL sink."""
        with self._lock:
            self._entries.clear()
