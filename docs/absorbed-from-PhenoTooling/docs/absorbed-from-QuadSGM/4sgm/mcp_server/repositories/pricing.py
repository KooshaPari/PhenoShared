"""Pricing repository interface."""

from abc import abstractmethod
from .base import BaseRepository
from typing import Optional, List


class PricingRepository(BaseRepository):
    """Repository for pricing operations."""

    @abstractmethod
    async def get_bulk_pricing(self, product_id: str, quantity: int) -> dict:
        """Get bulk pricing for a product."""
        pass

    @abstractmethod
    async def apply_coupon(
        self, coupon_code: str, cart_total: float, customer_id: Optional[str] = None
    ) -> dict:
        """Apply a coupon to an order."""
        pass

    @abstractmethod
    async def get_promotions(self) -> List[dict]:
        """Get active promotions."""
        pass

    @abstractmethod
    async def calculate_savings(
        self, original_price: float, discount_rate: float
    ) -> dict:
        """Calculate potential savings."""
        pass

    @abstractmethod
    async def validate_coupon(self, coupon_code: str) -> bool:
        """Check if a coupon code is valid."""
        pass

    @abstractmethod
    async def get_pricing(self, product_id: str, quantity: int = 1) -> dict:
        """Get pricing for a product."""
        pass

    @abstractmethod
    async def validate_discount_code(self, code: str) -> float:
        """Validate a discount code and return discount rate."""
        pass
