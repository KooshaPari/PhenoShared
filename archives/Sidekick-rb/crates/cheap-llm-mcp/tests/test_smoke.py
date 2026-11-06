"""Smoke test for basic functionality."""

import pytest


@pytest.mark.requirement("FR-LLM-080")
def test_smoke():
    """Basic sanity check."""
    assert 2 + 2 == 4
