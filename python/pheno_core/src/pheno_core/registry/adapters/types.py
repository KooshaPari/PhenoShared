"""
Type aliases for adapter plugins.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .enums import AdapterType

if TYPE_CHECKING:
    from .registry import AdapterRegistry

PluginHook = Callable[["AdapterRegistry", Any], None]

__all__ = ["AdapterType", "PluginHook"]
