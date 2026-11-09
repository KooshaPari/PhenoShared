"""Product repository interface."""

from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from .base import BaseRepository


@dataclass
class Product:
    """Product data model."""

    id: str
    sku: str
    name: str
    description: str
    price: float
    category: str
    brand: str
    in_stock: bool = True
    weight: float = 0.0
    dimensions: Optional[dict] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    quantity_on_hand: int = 50
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProductRepository(BaseRepository):
    """Repository for product operations."""

    @abstractmethod
    async def get(self, id: str) -> Optional[Product]:
        """Get a product by ID."""
        pass

    @abstractmethod
    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get a product by SKU."""
        pass

    @abstractmethod
    async def search(
        self, query: str, limit: int = 10, category: Optional[str] = None
    ) -> List[Product]:
        """Search products by query string."""
        pass

    @abstractmethod
    async def list(self, category: Optional[str] = None, **filters) -> List[Product]:
        """List products with optional filters."""
        pass

    @abstractmethod
    async def get_pricing(self, product_id: str) -> dict:
        """Get pricing details for a product."""
        pass

    @abstractmethod
    async def apply_discount(self, product_id: str, discount_code: str) -> dict:
        """Apply a discount to a product."""
        pass
