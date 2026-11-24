"""
Plugin utilities for adapter registry.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .enums import AdapterType
    from .registry import AdapterRegistry

PluginHook = Callable[["AdapterRegistry", Any], None]


class PluginRegistry:
    """
    Stores plugin hooks keyed by adapter type/name.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, list[PluginHook]] = {}

    def register(self, adapter_type: AdapterType, name: str, plugin: PluginHook) -> None:
        key = f"{adapter_type.value}:{name}"
        self._plugins.setdefault(key, []).append(plugin)

    def get(self, adapter_type: AdapterType, name: str) -> list[PluginHook]:
        key = f"{adapter_type.value}:{name}"
        return list(self._plugins.get(key, []))

    def clear(self) -> None:
        self._plugins.clear()


__all__ = ["PluginHook", "PluginRegistry"]
