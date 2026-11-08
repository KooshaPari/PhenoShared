"""thegent-cli-share - CLI share system with hexagonal architecture.

CLI Share System Architecture:
- Command deduplication (cmd_share)
- Task queue (Maildir-style)
- Smart merge (Mergiraf)
- Request coalescing (Singleflight)
- Coordination (HLC, OCC, leases)

xDD Methodologies Applied:
- TDD: Tests with pytest
- BDD: Behavior-driven with pytest-bdd
- DDD: Domain-driven design with bounded contexts
- SOLID: Single responsibility per module
- CQRS: Separate commands and queries
- EDA: Event-driven architecture
- Hexagonal: Ports and adapters pattern
"""

__version__ = "0.1.0"

from .domain.entities import (
    CommandLock,
    TaskQueueItem,
    MergeCandidate,
    CoordinationState,
    LockStatus,
    QueuePriority,
    MergeStrategy,
)
from .domain.value_objects import (
    CommandHash,
)
from .domain.events import (
    CliShareEvent,
    TaskEvent,
    MergeEvent,
    CoordinationEvent,
)
from .application.commands import (
    AcquireLockCommand,
    ReleaseLockCommand,
    EnqueueTaskCommand,
    MergeCommand,
)
from .application.queries import (
    GetLockQuery,
    ListLocksQuery,
    GetQueueDepthQuery,
    GetMergeCandidatesQuery,
)
from .ports.driven import (
    LockPort,
    QueuePort,
    MergePort,
    CoordinationPort,
)

__all__ = [
    # Domain
    "CommandLock",
    "TaskQueueItem",
    "MergeCandidate",
    "CoordinationState",
    "CommandHash",
    "LockStatus",
    "QueuePriority",
    "MergeStrategy",
    "CliShareEvent",
    "TaskEvent",
    "MergeEvent",
    "CoordinationEvent",
    # Application
    "AcquireLockCommand",
    "ReleaseLockCommand",
    "EnqueueTaskCommand",
    "MergeCommand",
    "GetLockQuery",
    "ListLocksQuery",
    "GetQueueDepthQuery",
    "GetMergeCandidatesQuery",
    # Ports
    "LockPort",
    "QueuePort",
    "MergePort",
    "CoordinationPort",
]
