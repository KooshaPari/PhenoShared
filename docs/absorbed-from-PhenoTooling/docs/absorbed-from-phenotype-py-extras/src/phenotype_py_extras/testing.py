"""Lazy re-exports for the ``testing`` extras group.

Install with: ``pip install phenotype-py-extras[testing]``

Re-exports:
    pytest, pytest_asyncio, pytest_cov
"""

from __future__ import annotations

from typing import Any

__all__ = ["pytest", "pytest_asyncio", "pytest_cov"]

_LAZY_ATTRS = {
    "pytest": "pytest",
    "pytest_asyncio": "pytest_asyncio",
    "pytest_cov": "pytest_cov",
}


def __getattr__(name: str) -> Any:
    """Lazily import an extras library on first attribute access (PEP 562)."""
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module 'phenotype_py_extras.testing' has no attribute {name!r}")
    import importlib

    value = importlib.import_module(target)
    globals()[name] = value  # cache for subsequent lookups
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_ATTRS))
