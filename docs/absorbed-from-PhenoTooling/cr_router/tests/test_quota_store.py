"""Tests for cr_router.quota_store."""
from __future__ import annotations

import json
from datetime import date

import pytest

from cr_router.quota_store import QuotaExhaustedError, QuotaStore


def test_quota_store_module_imports():
    """The QuotaStore module must import cleanly."""
    assert QuotaStore is not None
    assert QuotaExhaustedError is not None


def test_initial_state_is_zero(tmp_state_root):
    """A fresh QuotaStore reports zero usage for any provider."""
    store = QuotaStore(state_root=tmp_state_root)
    assert store.usage("coderabbit") == 0
    assert store.remaining("coderabbit", limit=10) == 10


def test_record_increments_counter(tmp_state_root):
    """record() bumps usage by 1 for the current day."""
    store = QuotaStore(state_root=tmp_state_root)
    store.record("coderabbit")
    store.record("coderabbit")
    assert store.usage("coderabbit") == 2


def test_usage_isolated_per_provider(tmp_state_root):
    """Recording on one provider must not affect another's counter."""
    store = QuotaStore(state_root=tmp_state_root)
    store.record("coderabbit")
    store.record("coderabbit")
    store.record("pr-agent")
    assert store.usage("coderabbit") == 2
    assert store.usage("pr-agent") == 1
    assert store.usage("greptile") == 0


def test_record_writes_file(tmp_state_root):
    """record() must persist the counter to disk so it survives across calls."""
    store = QuotaStore(state_root=tmp_state_root)
    store.record("coderabbit")
    path = tmp_state_root / f"quota-coderabbit.{date.today().isoformat()}.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert data == {"provider": "coderabbit", "date": date.today().isoformat(), "used": 1}


def test_remaining_subtracts_usage(tmp_state_root):
    """remaining(provider, limit) returns limit - usage for today."""
    store = QuotaStore(state_root=tmp_state_root)
    store.record("coderabbit")
    store.record("coderabbit")
    assert store.remaining("coderabbit", limit=10) == 8


def test_consume_raises_when_exhausted(tmp_state_root):
    """consume(provider, limit) raises QuotaExhaustedError when remaining == 0."""
    store = QuotaStore(state_root=tmp_state_root)
    for _ in range(2):
        store.record("coderabbit")
    with pytest.raises(QuotaExhaustedError):
        store.consume("coderabbit", limit=2)


def test_consume_returns_when_under_limit(tmp_state_root):
    """consume(provider, limit) records one use and returns None when under limit."""
    store = QuotaStore(state_root=tmp_state_root)
    assert store.consume("coderabbit", limit=10) is None
    assert store.usage("coderabbit") == 1


def test_remaining_treats_null_quota_as_unlimited(tmp_state_root):
    """When a provider has no daily quota (e.g. self-hosted), remaining is +inf."""
    store = QuotaStore(state_root=tmp_state_root)
    for _ in range(5):
        store.record("pr-agent")
    assert store.remaining("pr-agent", limit=None) == float("inf")
