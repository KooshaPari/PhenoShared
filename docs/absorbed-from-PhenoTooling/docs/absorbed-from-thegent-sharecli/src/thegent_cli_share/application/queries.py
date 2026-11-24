"""Application queries - CQRS query handlers."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GetLockQuery:
    """Query to get a specific lock."""
    cmd_hash: str


@dataclass
class ListLocksQuery:
    """Query to list all locks."""
    include_expired: bool = False


@dataclass
class GetQueueDepthQuery:
    """Query to get the queue depth."""
    priority: Optional[str] = None


@dataclass
class GetMergeCandidatesQuery:
    """Query to get merge candidates."""
    base_branch: Optional[str] = None
    min_conflicts: int = 0
