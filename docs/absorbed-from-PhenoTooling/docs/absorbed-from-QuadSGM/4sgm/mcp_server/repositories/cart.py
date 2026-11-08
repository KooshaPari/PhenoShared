"""Cart repository interface."""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List
from .base import BaseRepository


@dataclass
class CartItem:
    """Cart item data model."""

    product_id: str
    sku: str
    name: str
    quantity: int
    unit_price: float
    subtotal: float


@dataclass
class Cart:
    """Cart data model."""

    id: str
    customer_id: Optional[str] = None
    items: List[CartItem] = field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    shipping: float = 0.0
    total: float = 0.0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CartRepository(BaseRepository):
    """Repository for cart operations."""

    @abstractmethod
    async def get(self, cart_id: str) -> Optional[Cart]:
        """Get a cart by ID."""
        pass

    @abstractmethod
    async def create(self, customer_id: Optional[str] = None) -> Cart:
        """Create a new cart."""
        pass

    @abstractmethod
    async def add_item(
        self, cart_id: str, product_id: str, quantity: int, unit_price: float = 0.0
    ) -> Cart:
        """Add an item to the cart."""
        pass

    @abstractmethod
    async def remove_item(self, cart_id: str, product_id: str) -> Cart:
        """Remove an item from the cart."""
        pass

    @abstractmethod
    async def update_item_quantity(
        self, cart_id: str, product_id: str, quantity: int
    ) -> Cart:
        """Update the quantity of an item in the cart."""
        pass

    @abstractmethod
    async def clear(self, cart_id: str) -> bool:
        """Clear all items from the cart."""
        pass

    @abstractmethod
    async def calculate_total(self, cart_id: str) -> dict:
        """Calculate cart totals including tax and shipping."""
        pass

    @abstractmethod
    async def validate(self, cart_id: str) -> dict:
        """Validate cart for checkout (check inventory, pricing, etc.)."""
        pass

    @abstractmethod
    async def create_cart(self, user_id: str) -> dict:
        """Create a new cart for a user."""
        pass
