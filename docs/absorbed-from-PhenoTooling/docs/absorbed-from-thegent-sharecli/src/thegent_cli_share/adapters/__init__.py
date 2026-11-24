"""Adapters - concrete implementations of ports."""

from .dedup import InMemoryLockAdapter
from .queue import InMemoryQueueAdapter

__all__ = [
    "InMemoryLockAdapter",
    "InMemoryQueueAdapter",
]
