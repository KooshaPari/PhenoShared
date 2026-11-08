"""
Product fixture factory for testing.

Provides factories for creating test product data with sensible defaults
and flexible customization.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4


@dataclass
class ProductFactory:
    """Factory for creating test product instances."""

    sku: str = field(default_factory=lambda: f"SKU-{uuid4().hex[:8].upper()}")
    name: str = "Test Product"
    description: str = "A test product for unit testing"
    price: float = 99.99
    quantity: int = 100
    category: str = "Test Category"
    tags: list[str] = field(default_factory=lambda: ["test", "fixture"])
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    image_url: Optional[str] = None
    weight: Optional[float] = 1.5
    dimensions: Optional[str] = "10x10x10"

    @classmethod
    def create(cls, **kwargs) -> dict:
        """
        Create a product instance with optional field overrides.

        Args:
            **kwargs: Field overrides

        Returns:
            dict: Product data as dictionary
        """
        factory = cls(**kwargs)
        return {
            "sku": factory.sku,
            "name": factory.name,
            "description": factory.description,
            "price": factory.price,
            "quantity": factory.quantity,
            "category": factory.category,
            "tags": factory.tags,
            "is_active": factory.is_active,
            "created_at": factory.created_at.isoformat(),
            "updated_at": factory.updated_at.isoformat(),
            "image_url": factory.image_url,
            "weight": factory.weight,
            "dimensions": factory.dimensions,
        }

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[dict]:
        """
        Create multiple product instances.

        Args:
            count: Number of products to create
            **kwargs: Common field overrides

        Returns:
            list[dict]: List of product data
        """
        products = []
        for i in range(count):
            product_kwargs = kwargs.copy()
            product_kwargs.setdefault("sku", f"SKU-{uuid4().hex[:8].upper()}")
            product_kwargs.setdefault("name", f"Test Product {i + 1}")
            products.append(cls.create(**product_kwargs))
        return products


def create_test_product(
    sku: str = None,
    name: str = "Test Product",
    price: float = 99.99,
    quantity: int = 100,
    **kwargs,
) -> dict:
    """
    Create a test product with sensible defaults.

    Args:
        sku: Product SKU (auto-generated if not provided)
        name: Product name
        price: Product price
        quantity: Available quantity
        **kwargs: Additional field overrides

    Returns:
        dict: Product data
    """
    return ProductFactory.create(
        sku=sku or f"SKU-{uuid4().hex[:8].upper()}",
        name=name,
        price=price,
        quantity=quantity,
        **kwargs,
    )


def create_digital_product(**kwargs) -> dict:
    """
    Create a test digital product (no weight/dimensions).

    Args:
        **kwargs: Field overrides

    Returns:
        dict: Digital product data
    """
    defaults = {
        "name": "Digital Product",
        "weight": None,
        "dimensions": None,
        "category": "Digital",
    }
    defaults.update(kwargs)
    return create_test_product(**defaults)


def create_physical_product(**kwargs) -> dict:
    """
    Create a test physical product (with weight/dimensions).

    Args:
        **kwargs: Field overrides

    Returns:
        dict: Physical product data
    """
    defaults = {
        "name": "Physical Product",
        "weight": 2.5,
        "dimensions": "15x15x15",
        "category": "Physical",
    }
    defaults.update(kwargs)
    return create_test_product(**defaults)
