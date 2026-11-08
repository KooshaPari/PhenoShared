"""Inventory repository interface."""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, List
from .base import BaseRepository


@dataclass
class Inventory:
    """Inventory data model."""

    product_id: str
    sku: str
    quantity: int
    reserved: int = 0
    warehouse_location: str = ""
    reorder_point: int = 10
    last_updated: Optional[str] = None


class InventoryRepository(BaseRepository):
    """Repository for inventory operations."""

    @abstractmethod
    async def get(self, product_id: str) -> Optional[Inventory]:
        """Get inventory for a product."""
        pass

    @abstractmethod
    async def get_by_sku(self, sku: str) -> Optional[Inventory]:
        """Get inventory by SKU."""
        pass

    @abstractmethod
    async def update_quantity(
        self, product_id: str, quantity_change: int, reason: str = ""
    ) -> Inventory:
        """Update inventory quantity (positive or negative)."""
        pass

    @abstractmethod
    async def reserve(self, product_id: str, quantity: int) -> bool:
        """Reserve inventory for an order."""
        pass

    @abstractmethod
    async def release(self, product_id: str, quantity: int) -> bool:
        """Release reserved inventory."""
        pass

    @abstractmethod
    async def check_availability(self, product_id: str, quantity: int) -> bool:
        """Check if sufficient quantity is available."""
        pass

    @abstractmethod
    async def list(self, low_stock_only: bool = False, **filters) -> List[Inventory]:
        """List inventory with optional filters."""
        pass

    async def get_inventory(self, product_id: str) -> Optional[Any]:
        """Get inventory with flat interface fields (in_stock, available, warehouse_locations)."""
        return await self.get(product_id)

    async def update_inventory(
        self, product_id: str, quantity_change: int
    ) -> Optional[Any]:
        """Update inventory quantity."""
        return await self.update_quantity(product_id, quantity_change)
