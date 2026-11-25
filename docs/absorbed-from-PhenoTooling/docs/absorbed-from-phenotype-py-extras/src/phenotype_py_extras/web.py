"""Lazy re-exports for the ``web`` extras group.

Install with: ``pip install phenotype-py-extras[web]``

Re-exports:
    fastapi, uvicorn, pydantic, pydantic_settings
"""

from __future__ import annotations

from typing import Any

__all__ = ["fastapi", "uvicorn", "pydantic", "pydantic_settings"]

_LAZY_ATTRS = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pydantic": "pydantic",
    "pydantic_settings": "pydantic_settings",
}


def __getattr__(name: str) -> Any:
    """Lazily import an extras library on first attribute access (PEP 562)."""
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module 'phenotype_py_extras.web' has no attribute {name!r}")
    import importlib

    value = importlib.import_module(target)
    globals()[name] = value  # cache for subsequent lookups
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_ATTRS))
