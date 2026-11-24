"""In-memory queue adapter for task queue operations."""

from typing import Optional
from ..domain.entities import TaskQueueItem, QueuePriority
from thegent_cli_share.config import (
    QUEUE_PRIORITY_SORT_CRITICAL,
    QUEUE_PRIORITY_SORT_HIGH,
    QUEUE_PRIORITY_SORT_LOW,
    QUEUE_PRIORITY_SORT_NORMAL,
)


class InMemoryQueueAdapter:
    """In-memory implementation of QueuePort for testing and local use."""

    def __init__(self) -> None:
        self._queue: list[TaskQueueItem] = []

    def enqueue(self, item: TaskQueueItem) -> TaskQueueItem:
        """Add item to queue."""
        self._queue.append(item)
        # Sort by priority
        self._queue.sort(key=lambda x: (
            QUEUE_PRIORITY_SORT_CRITICAL if x.priority == QueuePriority.CRITICAL else
            QUEUE_PRIORITY_SORT_HIGH if x.priority == QueuePriority.HIGH else
            QUEUE_PRIORITY_SORT_NORMAL if x.priority == QueuePriority.NORMAL else
            QUEUE_PRIORITY_SORT_LOW
        ))
        return item

    def dequeue(self) -> Optional[TaskQueueItem]:
        """Remove and return next item."""
        if not self._queue:
            return None
        item = self._queue.pop(0)
        item.status = "dequeued"
        return item

    def peek(self) -> Optional[TaskQueueItem]:
        """View next item without removing."""
        if not self._queue:
            return None
        return self._queue[0]

    def length(self) -> int:
        """Get queue length."""
        return len(self._queue)

    def clear(self) -> None:
        """Clear the queue."""
        self._queue.clear()

    def list_all(self) -> list[TaskQueueItem]:
        """List all queued items."""
        return list(self._queue)


__all__ = ["InMemoryQueueAdapter"]
