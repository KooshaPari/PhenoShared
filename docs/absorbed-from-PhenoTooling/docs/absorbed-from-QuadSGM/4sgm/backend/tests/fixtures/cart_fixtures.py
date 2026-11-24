"""
Cart fixture factory for testing.

Provides factories for creating test cart data with sensible defaults
and flexible customization.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


@dataclass
class CartItemData:
    """Data class for a cart item."""

    sku: str
    quantity: int = 1
    price: float = 99.99
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "sku": self.sku,
            "quantity": self.quantity,
            "price": self.price,
            "added_at": self.added_at.isoformat(),
        }


@dataclass
class CartFactory:
    """Factory for creating test cart instances."""

    user_id: str = field(default_factory=lambda: f"user-{uuid4().hex[:8]}")
    status: str = "active"
    items: list[CartItemData] = field(default_factory=list)
    total_items: int = 0
    total_price: float = 0.0
    currency: str = "USD"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None

    def add_item(self, sku: str, quantity: int = 1, price: float = 99.99):
        """
        Add an item to the cart.

        Args:
            sku: Product SKU
            quantity: Item quantity
            price: Item price
        """
        item = CartItemData(sku=sku, quantity=quantity, price=price)
        self.items.append(item)
        self.total_items += quantity
        self.total_price += price * quantity
        self.updated_at = datetime.now(timezone.utc)

    @classmethod
    def create(cls, **kwargs) -> dict:
        """
        Create a cart instance with optional field overrides.

        Args:
            **kwargs: Field overrides

        Returns:
            dict: Cart data as dictionary
        """
        factory = cls(**kwargs)
        return {
            "user_id": factory.user_id,
            "status": factory.status,
            "items": [item.to_dict() for item in factory.items],
            "total_items": factory.total_items,
            "total_price": factory.total_price,
            "currency": factory.currency,
            "created_at": factory.created_at.isoformat(),
            "updated_at": factory.updated_at.isoformat(),
            "expires_at": factory.expires_at.isoformat() if factory.expires_at else None,
            "notes": factory.notes,
        }

    @classmethod
    def create_with_items(cls, items: list[tuple[str, int, float]] = None, **kwargs) -> dict:
        """
        Create a cart with items.

        Args:
            items: List of (sku, quantity, price) tuples
            **kwargs: Field overrides

        Returns:
            dict: Cart data with items
        """
        factory = cls(**kwargs)

        if items:
            for sku, quantity, price in items:
                factory.add_item(sku, quantity, price)

        return factory.create()


def create_test_cart(
    user_id: str = None,
    status: str = "active",
    items: list[tuple[str, int, float]] = None,
    **kwargs,
) -> dict:
    """
    Create a test cart with sensible defaults.

    Args:
        user_id: User ID (auto-generated if not provided)
        status: Cart status
        items: List of (sku, quantity, price) tuples
        **kwargs: Additional field overrides

    Returns:
        dict: Cart data
    """
    return CartFactory.create_with_items(
        user_id=user_id or f"user-{uuid4().hex[:8]}",
        status=status,
        items=items,
        **kwargs,
    )


def create_abandoned_cart(**kwargs) -> dict:
    """
    Create a test abandoned cart.

    Args:
        **kwargs: Field overrides

    Returns:
        dict: Abandoned cart data
    """
    defaults = {
        "status": "abandoned",
        "items": [("SKU-001", 2, 49.99)],
    }
    defaults.update(kwargs)
    return create_test_cart(**defaults)


def create_checkout_cart(**kwargs) -> dict:
    """
    Create a test cart in checkout status.

    Args:
        **kwargs: Field overrides

    Returns:
        dict: Checkout cart data
    """
    defaults = {
        "status": "checkout",
        "items": [("SKU-001", 1, 99.99), ("SKU-002", 2, 49.99)],
    }
    defaults.update(kwargs)
    return create_test_cart(**defaults)


def create_completed_cart(**kwargs) -> dict:
    """
    Create a test completed cart.

    Args:
        **kwargs: Field overrides

    Returns:
        dict: Completed cart data
    """
    defaults = {
        "status": "completed",
        "items": [("SKU-001", 1, 99.99)],
    }
    defaults.update(kwargs)
    return create_test_cart(**defaults)
