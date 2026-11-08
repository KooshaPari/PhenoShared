"""Order repository interface."""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List
from .base import BaseRepository


@dataclass
class OrderItem:
    """Order item data model."""

    product_id: str
    sku: str
    name: str
    quantity: int
    unit_price: float
    subtotal: float


@dataclass
class Order:
    """Order data model."""

    id: str
    customer_id: str
    status: str = "pending"
    items: List[OrderItem] = field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    shipping: float = 0.0
    total: float = 0.0
    shipping_address: Optional[dict] = None
    billing_address: Optional[dict] = None
    payment_method: Optional[str] = None
    tracking_number: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class OrderRepository(BaseRepository):
    """Repository for order operations."""

    @abstractmethod
    async def get(self, order_id: str) -> Optional[Order]:
        """Get an order by ID."""
        pass

    @abstractmethod
    async def create(
        self,
        cart_id: str,
        customer_id: str,
        shipping_address: dict,
        billing_address: Optional[dict] = None,
        **data,
    ) -> Order:
        """Create a new order from a cart."""
        pass

    @abstractmethod
    async def update_status(self, order_id: str, status: str) -> Order:
        """Update order status."""
        pass

    @abstractmethod
    async def cancel(self, order_id: str, reason: str = "") -> bool:
        """Cancel an order."""
        pass

    @abstractmethod
    async def list(
        self, customer_id: Optional[str] = None, status: Optional[str] = None, **filters
    ) -> List[Order]:
        """List orders with optional filters."""
        pass

    @abstractmethod
    async def get_by_customer(self, customer_id: str, limit: int = 10) -> List[Order]:
        """Get orders for a customer."""
        pass

    @abstractmethod
    async def create_order(
        self,
        cart_id: str,
        customer_id: str,
        shipping_address: dict,
        billing_address: Optional[dict] = None,
    ) -> Order:
        """Create a new order from a cart."""
        pass
