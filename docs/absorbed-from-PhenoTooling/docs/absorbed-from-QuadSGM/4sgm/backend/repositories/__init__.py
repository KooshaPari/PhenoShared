"""Repository pattern implementation for 4SGM.

This package implements the repository pattern to decouple business logic
from data access. All repositories follow protocol-based contracts,
allowing for flexible adapter swapping without changing consumer code.

Architecture:
    - base.py: Protocol definitions (contracts)
    - product.py, cart.py, etc.: Repository re-exports
    - adapters/supabase.py: Supabase implementations
    - adapters/mock.py: In-memory implementations for testing
    - dependencies.py: Dependency injection and factory functions

Key Principles:
    1. Protocol-based contracts: Repositories are Python Protocols,
       allowing any class implementing the methods to be used.

    2. Pluggable adapters: Implementations can be swapped by
       environment configuration without changing application code.

    3. Clean separation: Business logic (routes, services) uses
       repository protocols, not concrete implementations.

    4. Testing: Mock adapters provide in-memory implementations
       without external dependencies.

Example Usage:
    ```python
    from fastapi import FastAPI, Depends
    from repositories.dependencies import get_product_repo

    app = FastAPI()

    @app.get("/products/{product_id}")
    async def get_product(
        product_id: str,
        repo = Depends(get_product_repo)
    ):
        product = await repo.get(product_id)
        return product
    ```

Environment Variables:
    - REPOSITORY_ADAPTER: "supabase" (default) or "mock"
    - SUPABASE_URL: Supabase project URL
    - SUPABASE_KEY: Supabase API key
"""

from .base import (
    BaseRepository,
    CartRepository,
    CustomerRepository,
    OrderRepository,
    ProductRepository,
    RFQRepository,
    ShippingRepository,
)

__all__ = [
    "BaseRepository",
    "ProductRepository",
    "CartRepository",
    "OrderRepository",
    "CustomerRepository",
    "ShippingRepository",
    "RFQRepository",
]
