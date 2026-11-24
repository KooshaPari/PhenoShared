"""Multi-level caching wrapper for repositories.

Implements memory -> disk -> network (underlying repo) caching pattern.
Uses cachetools for memory TTL cache and diskcache for persistent disk cache.
"""

import functools
import json
import logging
import os
from typing import Any, Callable, Coroutine, Generic, Optional, TypeVar

try:
    from cachetools import TTLCache
except ImportError:
    # Fallback if not installed (though it should be in venv)
    TTLCache = None

try:
    from diskcache import Cache as DiskCache
except ImportError:
    # Fallback if not installed
    DiskCache = None

logger = logging.getLogger(__name__)

T = TypeVar("T")


class MultiLevelCache(Generic[T]):
    """Multi-level cache implementation: Memory -> Disk -> Network."""

    def __init__(
        self,
        namespace: str,
        memory_ttl: Optional[int] = None,
        memory_maxsize: int = 100,
        disk_ttl: Optional[int] = None,
        disk_dir: Optional[str] = None,
    ):
        """Initialize cache levels."""
        self.namespace = namespace

        # Load from environment or use defaults
        memory_ttl = int(memory_ttl or os.getenv("CACHE_MEMORY_TTL", 300))
        disk_ttl = int(disk_ttl or os.getenv("CACHE_DISK_TTL", 3600))
        disk_dir = disk_dir or os.getenv("CACHE_DISK_DIR", ".cache/repositories")
        if TTLCache:
            self.memory_cache = TTLCache(maxsize=memory_maxsize, ttl=memory_ttl)
        else:
            self.memory_cache = None
            logger.warning("cachetools not installed, memory caching disabled")

        # Disk Cache (Level 2)
        if DiskCache:
            os.makedirs(disk_dir, exist_ok=True)
            self.disk_cache = DiskCache(os.path.join(disk_dir, namespace))
            self.disk_ttl = disk_ttl
        else:
            self.disk_cache = None
            logger.warning("diskcache not installed, disk caching disabled")

    async def get_or_fetch(
        self, key: str, fetch_func: Callable[[], Coroutine[Any, Any, Optional[T]]]
    ) -> Optional[T]:
        """Get from cache or fetch and store.

        Logic:
        1. Check memory cache (L1)
        2. Check disk cache (L2)
        3. Fetch from underlying source (L3/Network)
        4. Store in disk cache
        5. Store in memory cache
        """
        # 1. Memory Check
        if self.memory_cache is not None:
            val = self.memory_cache.get(key)
            if val is not None:
                logger.debug(f"Cache hit (memory): {self.namespace}:{key}")
                return val

        # 2. Disk Check
        if self.disk_cache is not None:
            val = self.disk_cache.get(key)
            if val is not None:
                logger.debug(f"Cache hit (disk): {self.namespace}:{key}")
                # Backfill memory cache
                if self.memory_cache is not None:
                    self.memory_cache[key] = val
                return val

        # 3. Fetch from source
        logger.debug(f"Cache miss: {self.namespace}:{key}. Fetching...")
        val = await fetch_func()

        if val is not None:
            # 4. Store in disk
            if self.disk_cache is not None:
                self.disk_cache.set(key, val, expire=self.disk_ttl)

            # 5. Store in memory
            if self.memory_cache is not None:
                self.memory_cache[key] = val

        return val

    def invalidate(self, key: str):
        """Invalidate a specific key in both cache levels."""
        if self.memory_cache is not None:
            self.memory_cache.pop(key, None)
        if self.disk_cache is not None:
            self.disk_cache.delete(key)
        logger.debug(f"Cache invalidated: {self.namespace}:{key}")

    def clear(self):
        """Clear all cache entries in this namespace."""
        if self.memory_cache is not None:
            self.memory_cache.clear()
        if self.disk_cache is not None:
            self.disk_cache.clear()
        logger.debug(f"Cache cleared: {self.namespace}")


class CachedRepositoryWrapper:
    """Wrapper that adds caching to any repository implementation."""

    def __init__(self, repo: Any, namespace: str, **cache_kwargs):
        self._repo = repo
        self._cache = MultiLevelCache(namespace, **cache_kwargs)

        # Proxied methods that should be cached
        self._cached_methods = {
            "get",
            "get_by_sku",
            "get_by_email",
            "get_by_customer",
            "list",
            "get_all",
            "search",
            "list_by_category",
        }

        # Methods that should invalidate cache
        self._invalidating_methods = {
            "update",
            "delete",
            "create",
            "update_inventory",
            "add_item",
            "remove_item",
            "update_item",
            "clear",
        }

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the underlying repository."""
        attr = getattr(self._repo, name)

        if not callable(attr):
            return attr

        if name in self._cached_methods:
            return self._wrap_cached(name, attr)

        if name in self._invalidating_methods:
            return self._wrap_invalidating(name, attr)

        return attr

    def _wrap_cached(self, name: str, func: Callable) -> Callable:
        """Wrap a method with caching logic."""

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a unique key for the call
            # We skip 'self' which is args[0] for the underlying repo call
            # but we need to handle it carefully since 'wrapper' is called on 'self' (the proxy)
            # The 'func' we are wrapping is already bound or expects its own 'self'

            # Simplified key: function name + stringified args/kwargs
            # In a real app, you'd want a more robust key generation
            cache_key = (
                f"{name}:{json.dumps(args, sort_keys=True, default=str)}:"
                f"{json.dumps(kwargs, sort_keys=True, default=str)}"
            )

            return await self._cache.get_or_fetch(cache_key, lambda: func(*args, **kwargs))

        return wrapper

    def _wrap_invalidating(self, name: str, func: Callable) -> Callable:
        """Wrap a method that should invalidate cache."""

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Simple invalidation: clear everything in this namespace
            # For more efficiency, you could map specific IDs to keys
            self._cache.clear()

            return result

        return wrapper
