from __future__ import annotations

import time

import pytest

from cheap_llm_mcp.cache import TTLCache


@pytest.mark.requirement("FR-LLM-020")
def test_cache_hit_before_ttl():
    c = TTLCache(ttl_seconds=10)
    c.set("k", "v")
    assert c.get("k") == "v"


@pytest.mark.requirement("FR-LLM-021")
def test_cache_miss_after_ttl():
    c = TTLCache(ttl_seconds=0.01)
    c.set("k", "v")
    time.sleep(0.02)
    assert c.get("k") is None


@pytest.mark.requirement("FR-LLM-022")
def test_cache_eviction_at_max():
    c = TTLCache(ttl_seconds=60, max_entries=2)
    c.set("a", 1)
    time.sleep(0.001)
    c.set("b", 2)
    time.sleep(0.001)
    c.set("c", 3)
    # oldest ("a") should be evicted
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


@pytest.mark.requirement("FR-LLM-023")
def test_cache_key_stable():
    k1 = TTLCache.key("hello", {"a": 1}, 42)
    k2 = TTLCache.key("hello", {"a": 1}, 42)
    assert k1 == k2


@pytest.mark.requirement("FR-LLM-024")
def test_cache_key_differs_on_args():
    k1 = TTLCache.key("hello")
    k2 = TTLCache.key("hello", "world")
    assert k1 != k2
