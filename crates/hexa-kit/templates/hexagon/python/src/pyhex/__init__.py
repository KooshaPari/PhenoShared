"""
Phenotype Python Hexagonal Architecture Kit

A comprehensive implementation of Hexagonal Architecture (Ports & Adapters)
with Clean Architecture principles, SOLID compliance, and domain-driven design.
"""

from .application import (
    DTO,
    ApplicationError,
    Command,
    Query,
)
from .domain import (
    AggregateRoot,
    DomainError,
    DomainEvent,
    DomainService,
    Entity,
    EntityId,
    ValueObject,
)
from .ports import (
    InputPort,
    OutputPort,
    Repository,
    UseCase,
)

__version__ = "1.0.0"
__all__ = [
    # Domain
    "Entity",
    "ValueObject",
    "AggregateRoot",
    "DomainEvent",
    "DomainService",
    "DomainError",
    "EntityId",
    # Ports
    "InputPort",
    "OutputPort",
    "Repository",
    "UseCase",
    # Application
    "DTO",
    "Command",
    "Query",
    "ApplicationError",
]
