"""Smoke tests for the public API surface."""

from __future__ import annotations

import phenotype_py_utils


def test_version_is_string() -> None:
    assert isinstance(phenotype_py_utils.__version__, str)
    assert phenotype_py_utils.__version__ == "0.1.0"


def test_all_public_api_importable() -> None:
    from phenotype_py_utils import (  # noqa: F401
        ArgError,
        ConfigError,
        JsonFormatter,
        from_unix,
        iso_now,
        load_config,
        parse_args,
        setup_logging,
        slugify,
        truncate,
    )


def test_all_list_matches_imports() -> None:
    expected = {
        "ArgError",
        "ConfigError",
        "JsonFormatter",
        "from_unix",
        "iso_now",
        "load_config",
        "parse_args",
        "setup_logging",
        "slugify",
        "truncate",
    }
    assert set(phenotype_py_utils.__all__) == expected
