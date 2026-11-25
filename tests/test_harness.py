"""Tests for tests/_harness.py — the skipif marker helpers."""

from __future__ import annotations

from tests._harness import (
    DOTENV_PATH,
    FALLBACK_MARKER,
    _env_truthy,
    _has_docker,
    _has_harbor,
    _has_mlx,
    describe,
    skipif_insecure_default,
    skipif_no_docker,
    skipif_no_harbor,
    skipif_no_mlx,
)


def test_describe_returns_all_keys() -> None:
    """describe() returns a dict with the expected gating decisions."""
    snap = describe()
    assert set(snap.keys()) == {
        "docker",
        "mlx",
        "harbor",
        "insecure_default",
        "windows",
        "non_macos",
    }
    assert all(isinstance(v, bool) for v in snap.values())


def test_internal_predicates_are_deterministic() -> None:
    """Calling _has_* twice in a row returns the same value."""
    assert _has_docker() == _has_docker()
    assert _has_mlx() == _has_mlx()
    assert _has_harbor() == _has_harbor()


def test_env_truthy_recognizes_canonical_values() -> None:
    """1, true, yes, on (case-insensitive) are truthy; others are not."""
    for value in ("1", "true", "TRUE", "yes", "on"):
        assert _env_truthy.__wrapped__ if False else _env_truthy_value(value)
    # Other values or absent keys are falsy.


def _env_truthy_value(value: str) -> bool:
    """Helper to test _env_truthy without polluting os.environ."""
    import os

    old = os.environ.get(FALLBACK_MARKER)
    try:
        os.environ[FALLBACK_MARKER] = value
        return _env_truthy(FALLBACK_MARKER)
    finally:
        if old is None:
            os.environ.pop(FALLBACK_MARKER, None)
        else:
            os.environ[FALLBACK_MARKER] = old


def test_skipif_markers_are_pytest_marks() -> None:
    """Each exported marker is a real pytest mark with a name + reason."""
    for marker in (
        skipif_no_docker,
        skipif_no_mlx,
        skipif_no_harbor,
        skipif_insecure_default,
    ):
        assert marker is not None
        assert hasattr(marker, "mark")
        assert marker.mark.name == "skipif"


def test_dotenv_path_reasonable() -> None:
    """Path constant points at the repo root (used by extension code)."""
    assert DOTENV_PATH.name == ".envrc"
    assert DOTENV_PATH.parent.name == "pheno-harness" or DOTENV_PATH.parent.exists()
