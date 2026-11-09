"""Smoke tests for the ``phenotype-py-utils`` runtime dependency.

The package itself (and its submodules) is the optional surface that
downstream repos opt into. This test verifies the import works and that
each of the five advertised utility functions is callable.
"""

from __future__ import annotations

from phenotype_py_utils import (
    from_unix,
    iso_now,
    load_config,
    parse_args,
    setup_logging,
    truncate,
)


def test_load_config_importable() -> None:
    assert callable(load_config)


def test_setup_logging_importable() -> None:
    assert callable(setup_logging)


def test_parse_args_importable() -> None:
    assert callable(parse_args)


def test_iso_now_importable() -> None:
    assert callable(iso_now)


def test_truncate_importable() -> None:
    assert callable(truncate)
    # "phenotype-py-utils" is 18 chars. max_len=12, suffix="..." (3) → 9 + "..." = "phenotype..."
    assert truncate("phenotype-py-utils", max_len=12) == "phenotype..."
    assert truncate("hi", max_len=10) == "hi"


def test_iso_now_returns_z_suffix() -> None:
    s = iso_now()
    assert isinstance(s, str)
    assert s.endswith("Z")


def test_from_unix_returns_z_suffix() -> None:
    s = from_unix(1_700_000_000.0)
    assert isinstance(s, str)
    assert s.endswith("Z")
