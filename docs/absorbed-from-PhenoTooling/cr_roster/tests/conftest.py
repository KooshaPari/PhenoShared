"""Pytest fixtures for cr_roster tests."""
from __future__ import annotations

from pathlib import Path

import pytest

ROSTER_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def roster_root() -> Path:
    """Absolute path to the cr_roster/ directory."""
    return ROSTER_ROOT


@pytest.fixture(scope="session")
def providers_yaml_path(roster_root: Path) -> Path:
    """Absolute path to providers.yaml."""
    return roster_root / "providers.yaml"


@pytest.fixture(scope="session")
def schema_json_path(roster_root: Path) -> Path:
    """Absolute path to schema.json."""
    return roster_root / "schema.json"
