"""
Domain Layer - Pure business logic with no external dependencies
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, List, TypeVar
from uuid import UUID, uuid4

T = TypeVar("T")
TId = TypeVar("TId", bound="EntityId")


# Entity
class Entity(ABC, Generic[TId]):
    """Base class for all entities"""

    @property
    @abstractmethod
    def id(self) -> TId:
        """Returns the entity's unique identifier"""
        pass

    def equals(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __eq__(self, other: object) -> bool:
        return self.equals(other)

    def __hash__(self) -> int:
        return hash(self.id)


# Value Object
class ValueObject(ABC):
    """Base class for all value objects"""

    @abstractmethod
    def equals(self, other: object) -> bool:
        pass

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.equals(other)

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass(frozen=True)
class EntityId(ValueObject):
    """Entity ID value object"""

    value: str

    @classmethod
    def create(cls) -> "EntityId":
        return cls(value=str(uuid4()))

    def equals(self, other: object) -> bool:
        return isinstance(other, EntityId) and self.value == other.value

    def __str__(self) -> str:
        return self.value


# Aggregate Root
class AggregateRoot(Entity[TId], Generic[TId]):
    """Base class for aggregate roots"""

    def __init__(self, id: TId):
        self._id = id
        self._version: int = 1
        self._pending_events: list[DomainEvent] = []

    @property
    def id(self) -> TId:
        return self._id

    @property
    def version(self) -> int:
        return self._version

    @property
    def pending_events(self) -> list["DomainEvent"]:
        return list(self._pending_events)

    def add_event(self, event: "DomainEvent") -> None:
        self._pending_events.append(event)
        self._version += 1

    def pull_events(self) -> list["DomainEvent"]:
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    def clear_events(self) -> None:
        self._pending_events.clear()


# Domain Event
class DomainEvent(ABC):
    """Base class for domain events"""

    def __init__(
        self,
        event_type: str,
        aggregate_id: str,
        occurred_at: datetime | None = None,
    ):
        self._event_type = event_type
        self._aggregate_id = aggregate_id
        self._occurred_at = occurred_at or datetime.utcnow()

    @property
    def event_type(self) -> str:
        return self._event_type

    @property
    def aggregate_id(self) -> str:
        return self._aggregate_id

    @property
    def occurred_at(self) -> datetime:
        return self._occurred_at


# Domain Service
class DomainService(ABC):
    """Base class for domain services"""

    pass


# Domain Error
class DomainError(Exception):
    """Domain-level error"""

    def __init__(
        self,
        code: str,
        message: str,
        cause: Exception | None = None,
    ):
        self.code = code
        self.message = message
        self.cause = cause
        super().__init__(f"{code}: {message}")

    def __repr__(self) -> str:
        return f"DomainError(code={self.code!r}, message={self.message!r})"


class Errors:
    """Common domain errors"""

    NotFound = lambda msg="Entity not found": DomainError("NOT_FOUND", msg)
    InvalidInput = lambda msg="Invalid input": DomainError("INVALID_INPUT", msg)
    Conflict = lambda msg="Conflict": DomainError("CONFLICT", msg)
