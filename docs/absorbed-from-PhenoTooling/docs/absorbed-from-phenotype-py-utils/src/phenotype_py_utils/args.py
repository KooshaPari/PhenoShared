"""Typed CLI argument parser.

Wraps :mod:`argparse` with a typed dataclass return value. Each dataclass
field becomes a ``--field-name`` CLI option, using the field's type for
``type=`` (or ``BooleanOptionalAction`` for ``bool`` fields), its default
for ``default=``, and a ``required=True`` when the field has no default.

Note: with ``from __future__ import annotations`` enabled, dataclass
``f.type`` is a string. We resolve those strings via
:func:`typing.get_type_hints` so the underlying :class:`argparse.ArgumentParser`
gets the real class (e.g. ``str`` instead of ``"str"``).
"""

from __future__ import annotations

import argparse
import dataclasses
import types
import typing
from collections.abc import Sequence
from dataclasses import MISSING, fields
from typing import Any, TypeVar, get_args, get_origin, get_type_hints

T = TypeVar("T")
_NONE_TYPE = type(None)


class ArgError(Exception):
    """Raised when argument parsing or validation fails."""


def _resolve_type(cls: type[Any], name: str, declared: Any) -> Any:
    """Resolve a dataclass field's type, handling PEP 563 stringified hints."""
    if not isinstance(declared, str):
        return declared
    try:
        return get_type_hints(cls).get(name, declared)
    except Exception:
        return declared


def _unwrap_optional(type_: Any) -> Any:
    """If ``type_`` is ``Optional[T]`` / ``Union[T, None]`` / ``T | None``,
    return ``T``; otherwise return ``type_`` unchanged.
    """
    if type_ is None or type_ is type(None):
        return None
    origin = get_origin(type_)
    if origin in (typing.Union, types.UnionType):
        args = tuple(a for a in get_args(type_) if a is not _NONE_TYPE)
        if len(args) == 1:
            return args[0]
    return type_


def _add_dataclass_argument(parser: argparse.ArgumentParser, cls: type[Any], f: Any) -> None:
    """Translate a single dataclass ``field`` into an ``add_argument`` call."""
    name = f.name.replace("_", "-")
    type_ = _unwrap_optional(_resolve_type(cls, f.name, f.type))
    has_default = f.default is not MISSING
    help_text = f.metadata.get("help", "") if f.metadata else ""

    if type_ is bool:
        parser.add_argument(
            f"--{name}",
            action=argparse.BooleanOptionalAction,
            default=f.default if has_default else None,
            help=help_text,
        )
        return

    parser.add_argument(
        f"--{name}",
        type=type_ if type_ is not None else str,
        default=f.default if has_default else None,
        required=not has_default,
        help=help_text,
    )


def parse_args(cls: type[T], argv: Sequence[str] | None = None) -> T:
    """Parse CLI args into a dataclass instance.

    Args:
        cls: A dataclass with primitive-type fields.
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        An instance of ``cls`` populated from the parsed args.

    Raises:
        ArgError: If ``cls`` is not a dataclass. Note that
            :mod:`argparse` itself raises ``SystemExit`` on parse
            errors; this function does not swallow those.
    """
    if not dataclasses.is_dataclass(cls):
        raise ArgError(f"{cls.__name__} is not a dataclass")

    parser = argparse.ArgumentParser(
        prog=cls.__name__,
        description=cls.__doc__ or "",
    )
    for f in fields(cls):
        _add_dataclass_argument(parser, cls, f)

    ns = parser.parse_args(argv)
    kwargs: dict[str, Any] = {f.name: getattr(ns, f.name) for f in fields(cls)}
    return cls(**kwargs)
