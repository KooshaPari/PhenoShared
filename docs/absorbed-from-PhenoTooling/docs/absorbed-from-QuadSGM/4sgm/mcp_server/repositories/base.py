"""Base repository interface for 4SGM MCP Server."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseRepository(ABC):
    """Base repository for all data access operations."""

    @abstractmethod
    async def get(self, id: str) -> Optional[Any]:
        """Get a single record by ID."""
        pass

    @abstractmethod
    async def list(self, **filters) -> list[Any]:
        """List records with optional filters."""
        pass

    @abstractmethod
    async def create(self, **data) -> Any:
        """Create a new record."""
        pass

    @abstractmethod
    async def update(self, id: str, **data) -> Any:
        """Update an existing record."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete a record by ID."""
        pass
