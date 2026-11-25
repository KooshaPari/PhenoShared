"""
Core registry primitives.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from threading import Lock
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Mapping

try:  # pragma: no cover - fallback for older Python
    from importlib.metadata import entry_points
except Exception:  # pragma: no cover
    entry_points = None  # type: ignore

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class RegistryItem(Generic[T]):
    """
    Immutable wrapper that stores a registered object and its metadata.
    """

    key: str
    value: T
    metadata: dict[str, Any] = field(default_factory=dict)
    priority: int = 0


class Registry(Generic[T]):
    """
    Generic threadsafe registry with namespaced keys.
    """

    def __init__(self, name: str, *, separator: str = ":"):
        self._name = name
        self._sep = separator
        self._items: dict[str, RegistryItem[T]] = {}
        self._lock = Lock()

    def register(
        self,
        key: str,
        item: T,
        *,
        replace: bool = False,
        metadata: Mapping[str, Any] | None = None,
        priority: int = 0,
    ) -> None:
        with self._lock:
            if key in self._items and not replace:
                raise KeyError(f"Key '{key}' already registered. Use replace=True to override.")

            self._items[key] = RegistryItem(
                key=key,
                value=item,
                metadata=metadata or {},
                priority=priority,
            )
            logger.debug("Registered %s in %s registry", key, self._name)

    def get(self, key: str) -> T:
        with self._lock:
            if key not in self._items:
                raise KeyError(f"Key '{key}' not found in {self._name} registry")
            return self._items[key].value

    def get_with_metadata(self, key: str) -> RegistryItem[T]:
        with self._lock:
            if key not in self._items:
                raise KeyError(f"Key '{key}' not found in {self._name} registry")
            return self._items[key]

    def list(self, prefix: str | None = None) -> dict[str, T]:
        with self._lock:
            if prefix is None:
                return {key: item.value for key, item in self._items.items()}
            prefix_key = f"{prefix}{self._sep}"
            return {
                key: item.value for key, item in self._items.items() if key.startswith(prefix_key)
            }

    def unregister(self, key: str) -> None:
        with self._lock:
            if key in self._items:
                del self._items[key]
                logger.debug("Unregistered %s from %s registry", key, self._name)
            else:
                raise KeyError(f"Key '{key}' not found in {self._name} registry")

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            logger.debug("Cleared %s registry", self._name)

    def load_entry_points(self, group: str) -> None:
        if entry_points is None:
            logger.warning("Entry points not available, skipping entry point loading")
            return

        try:
            eps = entry_points(group=group)
            for ep in eps:
                try:
                    item = ep.load()
                    key = ep.name
                    self.register(key, item, metadata={"entry_point": str(ep)})
                    logger.debug("Loaded %s from entry point %s", key, ep)
                except Exception as exc:  # pragma: no cover
                    logger.warning("Failed to load entry point %s: %s", ep, exc)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to load entry points for group %s: %s", group, exc)

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._items


__all__ = ["Registry", "RegistryItem"]
