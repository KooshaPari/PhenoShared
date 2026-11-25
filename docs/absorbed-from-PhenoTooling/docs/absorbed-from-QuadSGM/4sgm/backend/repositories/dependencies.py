"""Dependency injection for repositories.

This module provides FastAPI dependency functions that create and inject
repository instances into route handlers. The adapter is selected based
on the REPOSITORY_ADAPTER environment variable, allowing easy swapping
between Supabase, mock, and future backends.

Pattern:
    - Uses FastAPI's Depends() for dependency injection
    - Caches client instances (e.g., Supabase) at module level
    - Factory functions return repository instances
    - Environment-driven adapter selection

Example:
    ```python
    from fastapi import FastAPI, Depends
    from repositories.dependencies import get_product_repo

    app = FastAPI()

    @app.get("/products/{product_id}")
    async def get_product(
        product_id: str,
        product_repo = Depends(get_product_repo)
    ):
        product = await product_repo.get(product_id)
        return product
    ```

Environment Variables:
    - REPOSITORY_ADAPTER: "supabase" (default) or "mock"
    - SUPABASE_URL: Project URL (required if using supabase)
    - SUPABASE_KEY: API key (required if using supabase)
"""

import logging
import os
from typing import Any, Optional

from .cache import CachedRepositoryWrapper

logger = logging.getLogger(__name__)

# Adapter selection
ADAPTER = os.getenv("REPOSITORY_ADAPTER", "supabase").lower()
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"

# Cached clients
_supabase_client: Optional[object] = None


def wrap_with_cache(repo: Any, namespace: str) -> Any:
    """Wrap repository with multi-level cache if enabled."""
    if not CACHE_ENABLED:
        return repo

    logger.info(f"Enabling cache for {namespace} repository")
    return CachedRepositoryWrapper(repo, namespace)


def get_supabase_client():
    """Get or create Supabase client.

    Uses lazy initialization to avoid connection overhead in tests.
    Only called when REPOSITORY_ADAPTER is "supabase".

    Returns:
        Supabase client instance

    Raises:
        ImportError: If supabase library not installed
        ValueError: If SUPABASE_URL or SUPABASE_KEY not set
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    try:
        import supabase
    except ImportError:
        raise ImportError("supabase library not installed. Install with: pip install supabase")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables required")

    _supabase_client = supabase.create_client(url, key)
    logger.info("Supabase client initialized")
    return _supabase_client


# Product Repository
async def get_product_repo():
    """Get ProductRepository instance."""
    if ADAPTER == "mock":
        from repositories.adapters.mock import MockProductRepository

        repo = MockProductRepository()
    else:
        from repositories.adapters.supabase import SupabaseProductRepository

        client = get_supabase_client()
        repo = SupabaseProductRepository(client)

    return wrap_with_cache(repo, "products")


# Cart Repository
async def get_cart_repo():
    """Get CartRepository instance."""
    if ADAPTER == "mock":
        from repositories.adapters.mock import MockCartRepository

        repo = MockCartRepository()
    else:
        from repositories.adapters.supabase import SupabaseCartRepository

        client = get_supabase_client()
        repo = SupabaseCartRepository(client)

    return wrap_with_cache(repo, "carts")


# Order Repository
async def get_order_repo():
    """Get OrderRepository instance."""
    if ADAPTER == "mock":
        from repositories.adapters.mock import MockOrderRepository

        repo = MockOrderRepository()
    else:
        from repositories.adapters.supabase import SupabaseOrderRepository

        client = get_supabase_client()
        repo = SupabaseOrderRepository(client)

    return wrap_with_cache(repo, "orders")


# Customer Repository
async def get_customer_repo():
    """Get CustomerRepository instance."""
    if ADAPTER == "mock":
        from repositories.adapters.mock import MockCustomerRepository

        repo = MockCustomerRepository()
    else:
        from repositories.adapters.supabase import SupabaseCustomerRepository

        client = get_supabase_client()
        repo = SupabaseCustomerRepository(client)

    return wrap_with_cache(repo, "customers")


# Shipping Repository
async def get_shipping_repo():
    """Get ShippingRepository instance."""
    if ADAPTER == "mock":
        from repositories.adapters.mock import MockShippingRepository

        repo = MockShippingRepository()
    else:
        from repositories.adapters.supabase import SupabaseShippingRepository

        client = get_supabase_client()
        repo = SupabaseShippingRepository(client)

    return wrap_with_cache(repo, "shipping")


# RFQ Repository
async def get_rfq_repo():
    """Get RFQRepository instance."""
    if ADAPTER == "mock":
        from repositories.adapters.mock import MockRFQRepository

        repo = MockRFQRepository()
    else:
        from repositories.adapters.supabase import SupabaseRFQRepository

        client = get_supabase_client()
        repo = SupabaseRFQRepository(client)

    return wrap_with_cache(repo, "rfqs")


# Collection of all dependency functions
DEPENDENCIES = {
    "product": get_product_repo,
    "cart": get_cart_repo,
    "order": get_order_repo,
    "customer": get_customer_repo,
    "shipping": get_shipping_repo,
    "rfq": get_rfq_repo,
}

__all__ = [
    "get_product_repo",
    "get_cart_repo",
    "get_order_repo",
    "get_customer_repo",
    "get_shipping_repo",
    "get_rfq_repo",
    "DEPENDENCIES",
    "ADAPTER",
]
