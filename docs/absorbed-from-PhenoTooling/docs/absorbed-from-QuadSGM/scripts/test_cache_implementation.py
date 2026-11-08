import asyncio
import os
import sys
import shutil
from unittest.mock import MagicMock, AsyncMock

# Add the backend path to sys.path
backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../4sgm/backend")
)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from repositories.cache import CachedRepositoryWrapper  # noqa: E402 -- sys.path setup required
import pytest  # noqa: E402 -- sys.path setup required


@pytest.mark.asyncio
async def test_multi_level_cache():
    # Setup
    namespace = "test_products"
    cache_dir = ".cache/test_repositories"

    # Clean up previous tests
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)

    # Mock repository
    mock_repo = MagicMock()
    mock_repo.get = AsyncMock(return_value={"id": "1", "name": "Product 1"})

    # Wrap with cache
    cached_repo = CachedRepositoryWrapper(
        mock_repo, namespace, disk_dir=cache_dir, memory_ttl=10, disk_ttl=60
    )

    print("--- Level 3: Fetching from Network (Mock) ---")
    # First call - should hit mock_repo.get
    res1 = await cached_repo.get("1")
    print(f"Result 1: {res1}")
    assert res1 == {"id": "1", "name": "Product 1"}
    assert mock_repo.get.call_count == 1

    print("\n--- Level 1: Fetching from Memory ---")
    # Second call - should hit memory cache
    res2 = await cached_repo.get("1")
    print(f"Result 2: {res2}")
    assert res2 == {"id": "1", "name": "Product 1"}
    assert mock_repo.get.call_count == 1  # No new call to mock_repo

    print("\n--- Level 2: Fetching from Disk ---")
    # Simulate memory cache expiration by clearing it
    cached_repo._cache.memory_cache.clear()

    # Third call - should hit disk cache
    res3 = await cached_repo.get("1")
    print(f"Result 3: {res3}")
    assert res3 == {"id": "1", "name": "Product 1"}
    assert mock_repo.get.call_count == 1  # No new call to mock_repo

    print("\n--- Invalidation: Update should clear cache ---")
    # Call update - should invalidate cache
    mock_repo.update = AsyncMock(return_value={"id": "1", "name": "Product 1 Updated"})
    await cached_repo.update("1", {"name": "Product 1 Updated"})

    # Fourth call - should hit mock_repo again after invalidation
    res4 = await cached_repo.get("1")
    print(f"Result 4: {res4}")
    assert mock_repo.get.call_count == 2

    print("\nTest passed successfully!")


if __name__ == "__main__":
    asyncio.run(test_multi_level_cache())
