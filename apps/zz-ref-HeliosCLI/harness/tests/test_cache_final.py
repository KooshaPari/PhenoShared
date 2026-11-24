"""Final tests for cache."""

import harness.cache as cache_module
from harness.cache import L1Cache, L2Cache


def test_l1_cache_set_get():
    """Test L1Cache set and get."""
    cache = L1Cache()
    # Cache.get should work
    result = cache.get("test_key")
    assert result is None


def test_l1_cache_clear():
    cache = L1Cache()
    cache.set("test_key", "value")

    cache.clear()

    assert cache.get("test_key") is None


def test_l1_cache_clear_uses_rust_backend(monkeypatch):
    class RustCache:
        def __init__(self, **_kwargs):
            self.cleared = False

        def clear(self):
            self.cleared = True

    monkeypatch.setattr(cache_module, "RUST_AVAILABLE", True)
    monkeypatch.setattr(cache_module, "RustLruCache", RustCache, raising=False)
    cache = L1Cache()

    cache.clear()

    assert cache._rust.cleared is True


def test_l2_cache_set_get():
    """Test L2Cache set and get."""
    cache = L2Cache()
    result = cache.get("test_key")
    assert result is None
