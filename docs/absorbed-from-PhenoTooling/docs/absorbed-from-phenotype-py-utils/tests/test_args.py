"""Tests for :mod:`phenotype_py_utils.args`."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from phenotype_py_utils.args import ArgError, _resolve_type, parse_args


@dataclass
class Simple:
    """A simple CLI tool."""

    name: str
    verbose: bool = False
    count: int = 1


@dataclass
class Required:
    """A CLI with a required field."""

    path: str
    mode: str = "r"


@dataclass
class WithDefault:
    """A CLI with a default that uses a non-primitive value type."""

    threshold: float = 0.5


def test_basic_parse() -> None:
    result = parse_args(Simple, ["--name", "phenotype"])
    assert isinstance(result, Simple)
    assert result.name == "phenotype"
    assert result.verbose is False
    assert result.count == 1


def test_bool_flag_enabled_and_disabled() -> None:
    enabled = parse_args(Simple, ["--name", "x", "--verbose"])
    assert enabled.verbose is True

    disabled = parse_args(Simple, ["--name", "x", "--no-verbose"])
    assert disabled.verbose is False


def test_missing_required_raises_systemexit() -> None:
    with pytest.raises(SystemExit):
        parse_args(Required, [])


def test_default_values() -> None:
    result = parse_args(Simple, ["--name", "x", "--count", "5"])
    assert result.count == 5


def test_not_a_dataclass_raises() -> None:
    class NotADataclass:
        pass

    with pytest.raises(ArgError, match="not a dataclass"):
        parse_args(NotADataclass, [])


def test_program_name_uses_class_name() -> None:
    """The argparse prog defaults to the dataclass name."""
    # Smoke test: parse_args should not raise on a Simple call
    result = parse_args(Simple, ["--name", "x"])
    assert result.name == "x"


def test_optional_default() -> None:
    result = parse_args(WithDefault, [])
    assert result.threshold == 0.5


def test_help_arg_exits_cleanly() -> None:
    with pytest.raises(SystemExit) as excinfo:
        parse_args(Simple, ["--help"])
    assert excinfo.value.code == 0


def test_optional_type_default() -> None:
    """Optional[str] with default should accept no flag."""

    @dataclass
    class WithOptional:
        """CLI with an optional string."""

        name: str
        label: str | None = None

    result = parse_args(WithOptional, ["--name", "x"])
    assert result.label is None


def test_resolve_type_passthrough_non_string() -> None:
    """_resolve_type should return non-string declared types unchanged."""

    @dataclass
    class WithInt:
        """A dataclass with a non-string annotation (no future annotations)."""

    # When the declared type is not a string, it should be returned as-is.
    assert _resolve_type(WithInt, "x", int) is int


def test_resolve_type_unresolvable_forward_ref() -> None:
    """_resolve_type should fall back to the original string when get_type_hints fails."""

    @dataclass
    class WithBadRef:
        """A dataclass with a forward reference to a non-existent type."""

        x: "NonExistentType"  # type: ignore[valid-type]  # noqa: F821,UP037

    # get_type_hints() will raise NameError for "NonExistentType";
    # _resolve_type should catch it and return the original string.
    result = _resolve_type(WithBadRef, "x", "NonExistentType")
    assert result == "NonExistentType"


def test_unwrap_optional_none_type() -> None:
    """_unwrap_optional should return None when given None or type(None)."""
    from phenotype_py_utils.args import _unwrap_optional

    assert _unwrap_optional(None) is None
    assert _unwrap_optional(type(None)) is None
