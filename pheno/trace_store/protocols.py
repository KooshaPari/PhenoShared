"""Protocols — TraceStoreAdapter interface for pheno trace persistence.

Defines the contract that all `trace_store.*` adapters implement.
Adapters convert pheno `traces/` events into the wire format of the
target backend (Tracera, local SQLite, S3 archive, etc.).

Refs:
- docs/integrations/tracera-api.md (TraceraAdapter target).
- v0.12 WBS-PERT-100 task 8 (Phase 1 — Tracera adapter skeleton).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4


@dataclass(frozen=True)
class TraceEvent:
    """A single trace event to be persisted by a TraceStoreAdapter.

    Fields:
        id: unique event identifier (UUID v4).
        kind: event kind (claim | evidence | trace | sprint | story | ...).
        ts: event timestamp (timezone-aware, default = now UTC).
        actor: originating actor (agent id, daemon name, etc.).
        target: optional target reference (issue id, branch name, ...).
        session_id: optional session id for grouping related events.
        payload: arbitrary JSON-serializable event payload.

    Methods:
        to_dict: serialize to a dict suitable for JSON encoding.
        from_dict: construct from a dict (inverse of to_dict).
    """

    id: UUID
    kind: str
    ts: datetime
    actor: str
    target: str | None = None
    session_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def make(
        kind: str,
        actor: str,
        target: str | None = None,
        session_id: str | None = None,
        payload: dict[str, Any] | None = None,
        ts: datetime | None = None,
        id: UUID | None = None,
    ) -> TraceEvent:
        """Construct a TraceEvent with sensible defaults.

        Defaults: id = uuid4(), ts = now UTC, payload = {}.
        """
        return TraceEvent(
            id=id or uuid4(),
            kind=kind,
            ts=ts or datetime.now(UTC),
            actor=actor,
            target=target,
            session_id=session_id,
            payload=payload or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "id": str(self.id),
            "kind": self.kind,
            "ts": self.ts.isoformat(),
            "actor": self.actor,
            "target": self.target,
            "session_id": self.session_id,
            "payload": self.payload,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> TraceEvent:
        """Construct from a dict (inverse of to_dict)."""
        return TraceEvent(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            kind=data["kind"],
            ts=datetime.fromisoformat(data["ts"]),
            actor=data["actor"],
            target=data.get("target"),
            session_id=data.get("session_id"),
            payload=data.get("payload", {}),
        )


class TraceStoreError(Exception):
    """Base error for TraceStoreAdapter implementations."""

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


@runtime_checkable
class TraceStoreAdapter(Protocol):
    """Protocol that all trace_store adapters implement.

    Concrete adapters must implement these methods. The protocol is
    `runtime_checkable` for use with `isinstance(x, TraceStoreAdapter)`.
    """

    def append_event(self, event: TraceEvent) -> str:
        """Append a single event; returns the persisted event id.

        Raises:
            TraceStoreError: on transport / serialization failure.
        """
        ...

    def query(self, session_id: str) -> list[TraceEvent]:
        """Return all events for the given session id (ordered by ts ASC).

        Raises:
            TraceStoreError: on transport / serialization failure.
        """
        ...

    def flush(self) -> None:
        """Flush any buffered events to the backend.

        Adapters may buffer events for batched async writes; `flush()`
        forces synchronous persistence of all buffered events. Should be
        a no-op for adapters that write synchronously.
        """
        ...

    def health(self) -> dict[str, Any]:
        """Return backend health status (adapter-specific).

        Returns at least: {"status": "ok" | "degraded" | "down"}.
        """
        ...
