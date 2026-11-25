"""Lazy re-exports for the ``cli`` extras group.

Install with: ``pip install phenotype-py-extras[cli]``

Re-exports:
    click, rich, typer, pydantic
"""

from __future__ import annotations

from typing import Any

__all__ = ["click", "rich", "typer", "pydantic"]

_LAZY_ATTRS = {
    "click": "click",
    "rich": "rich",
    "typer": "typer",
    "pydantic": "pydantic",
}


def __getattr__(name: str) -> Any:
    """Lazily import an extras library on first attribute access (PEP 562).

    The lazy mapping keys are the public attribute names; values are the
    importable module names. When a name does not match a lazy entry we raise
    ``AttributeError`` so ``hasattr(...)`` and tab-completion behave correctly.
    """
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module 'phenotype_py_extras.cli' has no attribute {name!r}")
    import importlib

    value = importlib.import_module(target)
    globals()[name] = value  # cache for subsequent lookups
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_ATTRS))
