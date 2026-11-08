"""Driven ports - interfaces for infrastructure adapters.

Hexagonal Architecture: Ports define how the domain interacts with external systems.
"""

from typing import Protocol, Optional
from ..domain.entities import CommandLock, TaskQueueItem, MergeCandidate, CoordinationState
from ..domain.value_objects import CommandHash


class LockPort(Protocol):
    """Port for command lock operations."""
    
    def acquire(self, cmd_hash: CommandHash, pid: int, output_path: Optional[str] = None) -> CommandLock:
        """Acquire a command lock."""
        ...
    
    def release(self, cmd_hash: CommandHash, pid: int) -> None:
        """Release a command lock."""
        ...
    
    def get(self, cmd_hash: CommandHash) -> Optional[CommandLock]:
        """Get lock status."""
        ...
    
    def list_all(self) -> list[CommandLock]:
        """List all locks."""
        ...


class QueuePort(Protocol):
    """Port for task queue operations."""
    
    def enqueue(self, item: TaskQueueItem) -> TaskQueueItem:
        """Add item to queue."""
        ...
    
    def dequeue(self) -> Optional[TaskQueueItem]:
        """Remove and return next item."""
        ...
    
    def peek(self) -> Optional[TaskQueueItem]:
        """View next item without removing."""
        ...
    
    def length(self) -> int:
        """Get queue length."""
        ...
    
    def clear(self) -> None:
        """Clear the queue."""
        ...


class MergePort(Protocol):
    """Port for merge operations."""
    
    def find_conflicts(self, base: str, theirs: str, ours: str) -> list[MergeCandidate]:
        """Find merge conflicts between branches."""
        ...
    
    def merge(self, base: str, theirs: str, strategy: str = "auto") -> dict:
        """Perform merge with given strategy."""
        ...
    
    def apply_resolution(self, candidate_id: str, resolution: dict) -> None:
        """Apply conflict resolution."""
        ...


class CoordinationPort(Protocol):
    """Port for distributed coordination."""
    
    def acquire_lease(self, resource_id: str, owner_id: str, duration_seconds: int) -> CoordinationState:
        """Acquire a lease on a resource."""
        ...
    
    def release_lease(self, resource_id: str, owner_id: str) -> None:
        """Release a lease."""
        ...
    
    def check_lease(self, resource_id: str) -> Optional[CoordinationState]:
        """Check lease status."""
        ...
