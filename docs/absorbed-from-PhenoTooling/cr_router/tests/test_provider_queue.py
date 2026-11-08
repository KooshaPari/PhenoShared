"""Tests for cr_router.provider_queue."""
from __future__ import annotations

import pytest

from cr_router.provider_queue import ProviderQueue


def test_provider_queue_module_imports():
    """The ProviderQueue module must import cleanly."""
    assert ProviderQueue is not None


def test_construction_from_explicit_list(provider_ids):
    """A queue built from an explicit list preserves order."""
    q = ProviderQueue(providers=[{"id": pid} for pid in provider_ids])
    assert [p["id"] for p in q.iter()] == provider_ids


def test_construction_from_cr_roster():
    """When no providers are passed, the queue falls back to cr_roster.load_providers()."""
    q = ProviderQueue()
    ids = [p["id"] for p in q.iter()]
    assert ids[0] == "coderabbit"  # D2 primary
    assert "pr-agent" in ids        # D3 fallback chain
    assert len(ids) == 6            # full D3 queue


def test_next_skips_exhausted(provider_ids):
    """next(exhausted={...}) returns the first provider NOT in the exhausted set."""
    q = ProviderQueue(providers=[{"id": pid} for pid in provider_ids])
    chosen = q.next(exhausted={"coderabbit", "pr-agent"})
    assert chosen is not None
    assert chosen["id"] == "gemini-code"


def test_next_returns_none_when_all_exhausted(provider_ids):
    """When every provider is exhausted, next() returns None."""
    q = ProviderQueue(providers=[{"id": pid} for pid in provider_ids])
    chosen = q.next(exhausted=set(provider_ids))
    assert chosen is None
