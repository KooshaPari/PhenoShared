"""Shipping repository interface."""

from abc import abstractmethod
from .base import BaseRepository
from typing import List


class ShippingRepository(BaseRepository):
    """Repository for shipping operations."""

    @abstractmethod
    async def calculate_shipping(
        self, origin: str, destination: str, weight_lbs: float
    ) -> dict:
        """Calculate shipping costs and options."""
        pass

    @abstractmethod
    async def get_shipping_methods(self) -> List[dict]:
        """Get available shipping methods."""
        pass

    @abstractmethod
    async def track_shipment(self, tracking_number: str) -> dict:
        """Track a shipment."""
        pass

    @abstractmethod
    async def estimate_delivery(self, destination: str, shipping_method: str) -> dict:
        """Estimate delivery date."""
        pass

    @abstractmethod
    async def validate_address(self, address: str) -> bool:
        """Validate a shipping address."""
        pass
