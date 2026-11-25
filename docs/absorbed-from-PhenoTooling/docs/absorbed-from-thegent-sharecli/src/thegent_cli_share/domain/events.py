"""Domain events - immutable facts representing state changes.

Event Sourcing Principles:
- Events are immutable
- Append-only log
- Reconstruct state by replaying events
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from dataclasses import dataclass


class EventType(str, Enum):
    """Event type enumeration."""
    LOCK_ACQUIRED = "lock_acquired"
    LOCK_RELEASED = "lock_released"
    LOCK_COMPLETED = "lock_completed"
    LOCK_TIMEOUT = "lock_timeout"
    TASK_ENQUEUED = "task_enqueued"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    MERGE_STARTED = "merge_started"
    MERGE_COMPLETED = "merge_completed"
    MERGE_CONFLICT = "merge_conflict"
    COORD_LEASE_ACQUIRED = "coord_lease_acquired"
    COORD_LEASE_RELEASED = "coord_lease_released"


@dataclass(frozen=True)
class CliShareEvent:
    """Base event for CLI share operations."""
    event_type: EventType
    timestamp: datetime
    cmd_hash: str
    pid: Optional[int] = None
    metadata: Optional[dict] = None


@dataclass(frozen=True)
class TaskEvent:
    """Event for task queue operations."""
    event_type: EventType
    timestamp: datetime
    task_id: str
    metadata: Optional[dict] = None


@dataclass(frozen=True)
class MergeEvent:
    """Event for merge operations."""
    event_type: EventType
    timestamp: datetime
    base_commit: str
    branch_name: str
    conflict_count: int = 0
    metadata: Optional[dict] = None


@dataclass(frozen=True)
class CoordinationEvent:
    """Event for coordination operations."""
    event_type: EventType
    timestamp: datetime
    resource_id: str
    owner_id: str
    metadata: Optional[dict] = None
