"""Tests for cr_router.router — the composition of ProviderQueue + QuotaStore."""
from __future__ import annotations

import pytest

from cr_router.quota_store import QuotaExhaustedError, QuotaStore
from cr_router.router import Router, RouterError


def _make_providers(ids: list[str]) -> list[dict]:
    return [{"id": pid, "name": pid, "priority": i + 1, "quota_per_day": 2, "free_tier": "test"} for i, pid in enumerate(ids)]


def test_router_module_imports():
    """The Router module must import cleanly."""
    assert Router is not None
    assert RouterError is not None


def test_pick_returns_primary_when_under_quota(tmp_state_root, provider_ids):
    """First call returns the highest-priority provider."""
    r = Router(providers=_make_providers(provider_ids), quota_store=QuotaStore(state_root=tmp_state_root))
    chosen = r.pick()
    assert chosen is not None
    assert chosen["id"] == "coderabbit"


def test_pick_records_consumption(tmp_state_root, provider_ids):
    """pick() must record one usage against the chosen provider."""
    r = Router(providers=_make_providers(provider_ids), quota_store=QuotaStore(state_root=tmp_state_root))
    r.pick()
    assert r.quota_store.usage("coderabbit") == 1


def test_pick_rotates_when_primary_exhausted(tmp_state_root, provider_ids):
    """Once coderabbit's quota is full, pick() returns pr-agent."""
    r = Router(providers=_make_providers(provider_ids), quota_store=QuotaStore(state_root=tmp_state_root))
    r.pick()  # coderabbit: 1/2
    r.pick()  # coderabbit: 2/2
    chosen = r.pick()
    assert chosen is not None
    assert chosen["id"] == "pr-agent"


def test_pick_skips_null_quota_provider(tmp_state_root, provider_ids):
    """A provider with quota_per_day=None is treated as unlimited."""
    providers = _make_providers(provider_ids)
    for p in providers:
        if p["id"] == "pr-agent":
            p["quota_per_day"] = None
    r = Router(providers=providers, quota_store=QuotaStore(state_root=tmp_state_root))
    # Exhaust coderabbit (2 uses)
    r.pick()
    r.pick()
    chosen = r.pick()
    assert chosen is not None
    assert chosen["id"] == "pr-agent"  # unlimited → always picked over rate-limited


def test_pick_returns_none_when_everyone_exhausted(tmp_state_root, provider_ids):
    """When all rate-limited providers hit their quota, pick() returns None."""
    providers = _make_providers(provider_ids)
    # Make the only unlimited one (pr-agent) artificially limited.
    for p in providers:
        p["quota_per_day"] = 1
    r = Router(providers=providers, quota_store=QuotaStore(state_root=tmp_state_root))
    for _ in providers:
        chosen = r.pick()
        assert chosen is not None
    # Now everyone should be at 1/1.
    chosen = r.pick()
    assert chosen is None


def test_pick_is_pure_dry_run_when_dry_run_true(tmp_state_root, provider_ids):
    """With dry_run=True, pick() returns the next provider WITHOUT recording consumption."""
    r = Router(providers=_make_providers(provider_ids), quota_store=QuotaStore(state_root=tmp_state_root), dry_run=True)
    chosen = r.pick()
    assert chosen is not None
    assert chosen["id"] == "coderabbit"
    # No counter was written.
    assert r.quota_store.usage("coderabbit") == 0


def test_status_reports_current_state(tmp_state_root, provider_ids):
    """status() returns a summary dict with per-provider used/limit/remaining."""
    r = Router(providers=_make_providers(provider_ids), quota_store=QuotaStore(state_root=tmp_state_root))
    r.pick()
    s = r.status()
    assert "providers" in s
    coderabbit = next(p for p in s["providers"] if p["id"] == "coderabbit")
    assert coderabbit["used"] == 1
    assert coderabbit["limit"] == 2
    assert coderabbit["remaining"] == 1


def test_status_lists_exhausted_providers(tmp_state_root, provider_ids):
    """status() flags providers at 0 remaining."""
    r = Router(providers=_make_providers(provider_ids), quota_store=QuotaStore(state_root=tmp_state_root))
    r.pick()
    r.pick()
    s = r.status()
    coderabbit = next(p for p in s["providers"] if p["id"] == "coderabbit")
    assert coderabbit["exhausted"] is True
