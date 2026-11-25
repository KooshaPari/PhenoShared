"""
Application Layer - Use cases, DTOs, and application services
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

T = TypeVar("T")
TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


# DTO
@dataclass
class DTO(Generic[T]):
    """Data Transfer Object"""

    data: T
    meta: Optional["DtoMeta"] = None


@dataclass
class DtoMeta:
    """DTO metadata"""

    version: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    request_id: str | None = None


@dataclass
class PaginatedResult(Generic[T]):
    """Paginated result"""

    data: list[T]
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size


# Command
@dataclass
class Command:
    """Base command"""

    command_type: str
    payload: dict
    metadata: dict = field(default_factory=dict)


@dataclass
class Query:
    """Base query"""

    query_type: str
    filters: list["QueryFilter"] = field(default_factory=list)
    pagination: Optional["PaginationInput"] = None


@dataclass
class QueryFilter:
    """Query filter"""

    field: str
    operator: str
    value: Any


@dataclass
class PaginationInput:
    """Pagination input"""

    page: int = 1
    page_size: int = 20

    def __post_init__(self):
        if self.page < 1:
            self.page = 1
        if self.page_size < 1:
            self.page_size = 20
        if self.page_size > 100:
            self.page_size = 100


# Use Case
class UseCaseFunc(Generic[TInput, TOutput]):
    """Function adapter for use cases"""

    def __init__(
        self,
        fn: callable,
    ):
        self._fn = fn

    async def execute(self, input: TInput) -> TOutput:
        return await self._fn(input)


class CommandHandler(Generic[T, TOutput]):
    """Command handler"""

    def __init__(self, use_case: "UseCase[T, TOutput]"):
        self._use_case = use_case

    async def handle(self, command: T) -> TOutput:
        return await self._use_case.execute(command)


class QueryHandler(Generic[T, TOutput]):
    """Query handler"""

    def __init__(self, use_case: "UseCase[T, TOutput]"):
        self._use_case = use_case

    async def handle(self, query: T) -> TOutput:
        return await self._use_case.execute(query)


# Application Service
class ApplicationService(ABC):
    """Base application service"""

    pass


# Application Error
class ApplicationError(Exception):
    """Application-level error"""

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
        return f"ApplicationError(code={self.code!r}, message={self.message!r})"


class AppErrors:
    """Common application errors"""

    Validation = lambda msg: ApplicationError("VALIDATION_ERROR", msg)
    NotFound = lambda msg: ApplicationError("NOT_FOUND", msg)
    Conflict = lambda msg: ApplicationError("CONFLICT", msg)
    Unauthorized = lambda msg: ApplicationError("UNAUTHORIZED", msg)
