"""Repository adapters for different backends.

This package provides concrete implementations of repository protocols.
Currently supported adapters:
- Supabase: PostgreSQL-based backend
- Mock: In-memory backend for testing

Example:
    ```python
    from repositories.adapters.supabase import SupabaseProductRepository
    from repositories.adapters.mock import MockProductRepository

    # Use Supabase adapter in production
    repo = SupabaseProductRepository(supabase_client)

    # Use mock adapter in tests
    repo = MockProductRepository()
    ```
"""

from .mock import (
    MockCartRepository,
    MockCustomerRepository,
    MockInventoryRepository,
    MockOrderRepository,
    MockPricingRepository,
    MockProductRepository,
    MockRFQRepository,
    MockShippingRepository,
)
from .supabase import (
    SupabaseCartRepository,
    SupabaseCustomerRepository,
    SupabaseOrderRepository,
    SupabaseProductRepository,
    SupabaseRFQRepository,
    SupabaseShippingRepository,
)

__all__ = [
    # Supabase adapters
    "SupabaseProductRepository",
    "SupabaseCartRepository",
    "SupabaseOrderRepository",
    "SupabaseCustomerRepository",
    "SupabaseShippingRepository",
    "SupabaseRFQRepository",
    # Mock adapters
    "MockProductRepository",
    "MockCartRepository",
    "MockOrderRepository",
    "MockCustomerRepository",
    "MockShippingRepository",
    "MockRFQRepository",
    "MockInventoryRepository",
    "MockPricingRepository",
]
