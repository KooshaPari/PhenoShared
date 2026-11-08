"""Tests for the zero-dep context module."""

from __future__ import annotations

import asyncio

import pytest

from phenotype_request_id.context import (
    get_request_id,
    set_request_id,
    with_request_id,
)


def test_get_request_id_defaults_to_none() -> None:
    # No context set; we don't assert cleanup because each test is
    # its own contextvar copy under pytest-asyncio, but to be safe:
    assert get_request_id() is None


def test_with_request_id_sets_and_resets() -> None:
    assert get_request_id() is None
    with with_request_id("rid-1") as rid:
        assert rid == "rid-1"
        assert get_request_id() == "rid-1"
    assert get_request_id() is None


def test_with_request_id_restores_outer_value() -> None:
    with with_request_id("outer"):
        assert get_request_id() == "outer"
        with with_request_id("inner"):
            assert get_request_id() == "inner"
        assert get_request_id() == "outer"
    assert get_request_id() is None


def test_with_request_id_rejects_empty() -> None:
    with pytest.raises(ValueError):
        with with_request_id(""):
            pass


def test_set_request_id_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        set_request_id(123)  # type: ignore[arg-type]


async def test_async_isolation_concurrent_requests_have_distinct_ids() -> None:
    """Two coroutines setting different IDs must not see each other's value."""
    seen_a: list[str | None] = []
    seen_b: list[str | None] = []

    async def task(name: str, target: list[str | None]) -> None:
        with with_request_id(name):
            # Yield to the event loop several times so the two tasks
            # interleave. If contextvars were mis-implemented with
            # threading.local, the other task's value would leak here.
            for _ in range(20):
                await asyncio.sleep(0)
                target.append(get_request_id())

    await asyncio.gather(task("A", seen_a), task("B", seen_b))

    assert all(v == "A" for v in seen_a)
    assert all(v == "B" for v in seen_b)
    assert seen_a and seen_b
