"""Application commands - CQRS command handlers."""

from dataclasses import dataclass
from typing import Optional

from ..domain.entities import QueuePriority, MergeStrategy
from thegent_cli_share.config import LOCK_TIMEOUT_SECONDS, QUEUE_TIMEOUT_SECONDS


@dataclass
class AcquireLockCommand:
    """Command to acquire a lock on a command."""
    cmd_hash: str
    pid: int
    output_path: Optional[str] = None
    timeout_seconds: int = LOCK_TIMEOUT_SECONDS


@dataclass
class ReleaseLockCommand:
    """Command to release a lock."""
    cmd_hash: str
    pid: int


@dataclass
class EnqueueTaskCommand:
    """Command to enqueue a task."""
    command: str
    priority: QueuePriority = QueuePriority.NORMAL
    cwd: Optional[str] = None
    env: Optional[dict[str, str]] = None
    timeout_seconds: int = QUEUE_TIMEOUT_SECONDS


@dataclass
class MergeCommand:
    """Command to perform a merge operation."""
    base_commit: str
    theirs_commit: str
    ours_commit: str
    strategy: MergeStrategy = MergeStrategy.AUTO
