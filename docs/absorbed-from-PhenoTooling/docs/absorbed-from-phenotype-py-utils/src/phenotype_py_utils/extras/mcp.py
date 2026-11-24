"""Lazy re-exports for the ``mcp`` extras group.

Install with: ``pip install phenotype-py-utils[mcp]``

Re-exports:
    fastmcp, pydantic, pydantic_settings, httpx
"""

from __future__ import annotations

from typing import Any

__all__ = ["fastmcp", "pydantic", "pydantic_settings", "httpx"]

_LAZY_ATTRS = {
    "fastmcp": "fastmcp",
    "pydantic": "pydantic",
    "pydantic_settings": "pydantic_settings",
    "httpx": "httpx",
}


def __getattr__(name: str) -> Any:
    """Lazily import an extras library on first attribute access (PEP 562)."""
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module 'phenotype_py_utils.extras.mcp' has no attribute {name!r}")
    import importlib

    value = importlib.import_module(target)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_ATTRS))
