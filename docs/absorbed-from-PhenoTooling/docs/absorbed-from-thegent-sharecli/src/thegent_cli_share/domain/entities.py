"""Domain entities - core business objects with identity.

DDD (Domain-Driven Design) Principles:
- Entities have unique identity
- Value objects are immutable
- Domain events are immutable facts
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from thegent_cli_share.config import LOCK_TIMEOUT_SECONDS


class LockStatus(str, Enum):
    """Lock status for command deduplication."""
    UNLOCKED = "unlocked"
    LOCKED = "locked"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"


class QueuePriority(str, Enum):
    """Task queue priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MergeStrategy(str, Enum):
    """Merge strategies for smart merge."""
    AUTO = "auto"
    THEIRS = "theirs"
    OURS = "ours"
    MANUAL = "manual"


class CommandLock(BaseModel):
    """Command lock entity for deduplication.

    Implements the cmd_share functionality - ensures only one
    instance of a command runs at a time.
    """
    cmd_hash: str = Field(description="Unique command hash")
    pid: int = Field(default=0, description="Process ID holding lock")
    status: LockStatus = Field(default=LockStatus.UNLOCKED)
    output_path: Optional[str] = Field(default=None)
    start_time: Optional[datetime] = Field(default=None)
    timeout_seconds: int = Field(default=LOCK_TIMEOUT_SECONDS)

    def is_locked(self) -> bool:
        """Check if the lock is held by a process."""
        return self.pid != 0 and self.status == LockStatus.LOCKED

    def acquire(self, pid: int, output_path: Optional[str] = None) -> None:
        """Acquire the lock for a process."""
        if self.is_locked() and self.pid != pid:
            raise ValueError(f"Lock held by PID {self.pid}")
        self.pid = pid
        self.status = LockStatus.LOCKED
        self.output_path = output_path
        self.start_time = datetime.now()

    def release(self, pid: int) -> None:
        """Release the lock."""
        if self.pid != pid:
            raise ValueError(f"Lock held by PID {self.pid}, cannot release")
        self.pid = 0
        self.status = LockStatus.UNLOCKED
        self.start_time = None

    def complete(self, pid: int) -> None:
        """Mark the command as completed."""
        if self.pid != pid:
            raise ValueError("Cannot complete - not lock owner")
        self.status = LockStatus.COMPLETED


class TaskQueueItem(BaseModel):
    """Task queue item for Maildir-style queue."""
    id: UUID = Field(default_factory=uuid4)
    command: str = Field(description="Command to execute")
    priority: QueuePriority = Field(default=QueuePriority.NORMAL)
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = Field(default="pending")
    cwd: Optional[str] = None
    env: dict[str, str] = Field(default_factory=dict)
    result: Optional[dict] = None

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    @property
    def is_running(self) -> bool:
        return self.status == "running"

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    def start(self) -> None:
        """Mark task as started."""
        self.status = "running"
        self.started_at = datetime.now()

    def complete(self, result: dict) -> None:
        """Mark task as completed."""
        self.status = "completed"
        self.completed_at = datetime.now()
        self.result = result


class MergeCandidate(BaseModel):
    """Merge candidate for smart merge."""
    id: UUID = Field(default_factory=uuid4)
    base_commit: str = Field(description="Base commit SHA")
    theirs_commit: str = Field(description="Their branch commit")
    ours_commit: str = Field(description="Our branch commit")
    strategy: MergeStrategy = Field(default=MergeStrategy.AUTO)
    conflict_count: int = Field(default=0)
    auto_mergeable: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)


class CoordinationState(BaseModel):
    """Coordination state for distributed locking."""
    resource_id: str = Field(description="Resource being coordinated")
    owner_id: Optional[str] = Field(default=None)
    lease_expires_at: Optional[datetime] = None
    version: int = Field(default=0)
    hlc_timestamp: int = Field(default=0)

    @property
    def is_owned(self) -> bool:
        return self.owner_id is not None

    def acquire_lease(self, owner_id: str, duration_seconds: int) -> None:
        """Acquire a lease on the resource."""
        from datetime import timedelta
        self.owner_id = owner_id
        self.lease_expires_at = datetime.now() + timedelta(seconds=duration_seconds)
        self.version += 1

    def release_lease(self, owner_id: str) -> None:
        """Release the lease."""
        if self.owner_id != owner_id:
            raise ValueError("Not the lease owner")
        self.owner_id = None
        self.lease_expires_at = None
        self.version += 1


class EditIntent(BaseModel):
    """Edit intent for file coordination between agents."""
    id: UUID = Field(default_factory=uuid4)
    agent_id: str = Field(description="Agent creating the intent")
    file_path: str = Field(description="File being edited")
    start_line: int = Field(description="Start line of edit")
    end_line: int = Field(description="End line of edit")
    created_at: datetime = Field(default_factory=datetime.now)

    def conflicts_with(self, other: "EditIntent") -> bool:
        """Check if this intent conflicts with another."""
        if self.file_path != other.file_path:
            return False
        # Check if ranges overlap
        return not (
            self.end_line < other.start_line or
            other.end_line < self.start_line
        )
