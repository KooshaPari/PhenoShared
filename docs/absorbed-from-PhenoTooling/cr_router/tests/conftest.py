"""Shared pytest fixtures for cr_router tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_state_root(tmp_path: Path) -> Path:
    """A throwaway directory for QuotaStore file backing.

    Tests pass this to QuotaStore(state_root=...) so the daily-counter JSON
    files never touch the real var/ tree.
    """
    p = tmp_path / "cr_router_state"
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture
def provider_ids() -> list[str]:
    """Hardcoded mirror of cr_roster/providers.yaml (D3 queue).

    We deliberately do NOT import load_providers() inside the unit tests —
    that would couple router logic to roster I/O. Instead, tests that need a
    fixed provider list pass this fixture. The single integration test that
    DOES exercise load_providers() lives in test_provider_queue.py.
    """
    return ["coderabbit", "pr-agent", "gemini-code", "sourcery", "greptile", "bito"]
