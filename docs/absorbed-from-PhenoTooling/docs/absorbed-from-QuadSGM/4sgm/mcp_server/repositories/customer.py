"""Customer repository interface."""

from abc import abstractmethod
from .base import BaseRepository
from typing import Dict


class CustomerRepository(BaseRepository):
    """Repository for customer operations."""

    @abstractmethod
    async def get_customer_history(self, user_id: str, limit: int = 10) -> dict:
        """Get customer order history."""
        pass

    @abstractmethod
    async def get_customer_preferences(self, user_id: str) -> dict:
        """Get customer preferences."""
        pass

    @abstractmethod
    async def save_customer_preferences(
        self, user_id: str, preferences: Dict[str, any]
    ) -> dict:
        """Save customer preferences."""
        pass

    @abstractmethod
    async def customer_exists(self, user_id: str) -> bool:
        """Check if a customer exists."""
        pass

    @abstractmethod
    async def get_customer_value(self, user_id: str) -> float:
        """Get total customer lifetime value."""
        pass
