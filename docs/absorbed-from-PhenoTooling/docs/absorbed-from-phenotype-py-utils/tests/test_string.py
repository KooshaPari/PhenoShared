"""Tests for :mod:`phenotype_py_utils.string`."""

from __future__ import annotations

import pytest

from phenotype_py_utils.string import slugify, truncate


def test_truncate_no_truncation_needed() -> None:
    assert truncate("hi", max_len=10) == "hi"


def test_truncate_exact_length() -> None:
    s = "0123456789"
    assert truncate(s, max_len=10) == s


def test_truncate_shorter_max_len() -> None:
    assert truncate("hello world", max_len=8) == "hello..."


def test_truncate_empty_string() -> None:
    assert truncate("", max_len=10) == ""


def test_truncate_max_len_less_than_suffix_raises() -> None:
    with pytest.raises(ValueError, match="must be >="):
        truncate("hello", max_len=2, suffix="...")


def test_truncate_custom_suffix() -> None:
    assert truncate("abcdef", max_len=5, suffix="…") == "abcd…"


def test_truncate_unicode_aware() -> None:
    """Truncation is character-based, not byte-based."""
    s = "héllo wörld"  # 11 chars
    assert len(s) == 11
    result = truncate(s, max_len=8)
    assert len(result) == 8
    assert result.endswith("...")


def test_slugify_basic() -> None:
    assert slugify("Hello World") == "hello-world"


def test_slugify_special_chars() -> None:
    assert slugify("  !!Phenotype  v2  ") == "phenotype-v2"


def test_slugify_already_lowercase() -> None:
    assert slugify("foo-bar") == "foo-bar"


def test_slugify_empty_returns_untitled() -> None:
    assert slugify("") == "untitled"


def test_slugify_only_special_chars() -> None:
    assert slugify("!!!") == "untitled"


def test_slugify_numbers_preserved() -> None:
    assert slugify("Plan 9 from Outer Space") == "plan-9-from-outer-space"


def test_slugify_underscores_collapsed() -> None:
    assert slugify("foo___bar") == "foo-bar"
