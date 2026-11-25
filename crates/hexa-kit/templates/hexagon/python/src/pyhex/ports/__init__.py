"""
Ports Layer - Interface definitions
"""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, Protocol, TypeVar, runtime_checkable

from ..domain import DomainEvent

T = TypeVar("T")
TId = TypeVar("TId")
E = TypeVar("E", bound=DomainEvent)


# Markers
class InputPort(ABC):
    """Marker for input (driving) ports"""

    pass


class OutputPort(ABC):
    """Marker for output (driven) ports"""

    pass


# Repository
class Repository(Protocol[T, TId]):
    """Repository interface for entity persistence"""

    async def save(self, entity: T) -> T:
        """Save an entity"""
        ...

    async def find_by_id(self, id: TId) -> T | None:
        """Find an entity by ID"""
        ...

    async def delete(self, id: TId) -> None:
        """Delete an entity"""
        ...

    async def find_all(self) -> list[T]:
        """Find all entities"""
        ...


class QueryRepository(Protocol[T]):
    """Query repository for read operations"""

    async def find_by_filter(self, filter: "Filter") -> list[T]: ...

    async def count(self, filter: "Filter") -> int: ...


# Event Store
class EventStore(ABC, Generic[E]):
    """Event store interface for event sourcing"""

    @abstractmethod
    async def append(
        self,
        aggregate_id: str,
        events: list[E],
        expected_version: int,
    ) -> None: ...

    @abstractmethod
    async def get_events(self, aggregate_id: str) -> list[E]: ...


# Message Bus
class MessageBus(ABC):
    """Message bus interface for publishing events"""

    @abstractmethod
    async def publish(self, topic: str, event: DomainEvent) -> None: ...

    @abstractmethod
    def subscribe(
        self,
        topic: str,
        handler: "EventHandler",
    ) -> None: ...


class EventHandler(ABC):
    """Event handler interface"""

    @abstractmethod
    async def handle(self, event: DomainEvent) -> None: ...


# Filter
class Filter:
    """Query filter"""

    def __init__(
        self,
        conditions: list["Condition"] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ):
        self.conditions = conditions or []
        self.limit = limit
        self.offset = offset

    def add_condition(
        self,
        field: str,
        operator: "FilterOperator",
        value: object,
    ) -> "Filter":
        self.conditions.append(Condition(field, operator, value))
        return self


class Condition:
    """Filter condition"""

    def __init__(self, field: str, operator: "FilterOperator", value: object):
        self.field = field
        self.operator = operator
        self.value = value


class FilterOperator:
    """Filter operators"""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    CONTAINS = "contains"
    STARTS_WITH = "startsWith"
    IN = "in"


# Use Case
class UseCase(ABC, Generic[T, TId]):
    """Use case interface"""

    @abstractmethod
    async def execute(self, input: T) -> TId: ...
