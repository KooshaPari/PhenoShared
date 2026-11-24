"""
Process-wide registry singletons and helper functions.
"""

from __future__ import annotations

from typing import Any

from .base import Registry

_tool_registry = Registry("tools")
_provider_registry = Registry("providers")
_plugin_registry = Registry("plugins")


def get_tool_registry() -> Registry[Any]:
    return _tool_registry


def get_provider_registry() -> Registry[Any]:
    return _provider_registry


def get_plugin_registry() -> Registry[Any]:
    return _plugin_registry


def register_tool(name: str, tool: Any, **kwargs) -> None:
    _tool_registry.register(name, tool, **kwargs)


def get_tool(name: str) -> Any:
    return _tool_registry.get(name)


def list_tools(prefix: str | None = None) -> dict[str, Any]:
    return _tool_registry.list(prefix)


__all__ = [
    "get_plugin_registry",
    "get_provider_registry",
    "get_tool",
    "get_tool_registry",
    "list_tools",
    "register_tool",
]
