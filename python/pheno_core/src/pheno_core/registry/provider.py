"""
Provider registry specializations.
"""

from __future__ import annotations

import logging
from enum import Enum
from threading import Lock
from typing import TYPE_CHECKING, Generic, TypeVar

from .base import Registry

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

T = TypeVar("T")
K = TypeVar("K", bound=Enum)


class ProviderRegistry(Registry[T], Generic[T, K]):
    """
    Specialized registry for providers with priority-based resolution.
    """

    def __init__(self, name: str, *, separator: str = ":"):
        super().__init__(name, separator=separator)
        self._instances: dict[str, T] = {}
        self._instance_lock = Lock()

    def register_provider(
        self,
        provider_type: K,
        provider_class: type[T],
        *,
        replace: bool = False,
        metadata: Mapping[str, object] | None = None,
        priority: int = 0,
    ) -> None:
        key = (
            f"{provider_type.name.lower()}"
            if hasattr(provider_type, "name")
            else str(provider_type)
        )
        self.register(key, provider_class, replace=replace, metadata=metadata, priority=priority)

    def get_provider(self, provider_type: K) -> T:
        key = (
            f"{provider_type.name.lower()}"
            if hasattr(provider_type, "name")
            else str(provider_type)
        )

        with self._instance_lock:
            if key in self._instances:
                return self._instances[key]

        provider_class = self.get(key)
        instance = self._create_provider_instance(provider_class, provider_type)

        with self._instance_lock:
            self._instances[key] = instance

        return instance

    def _create_provider_instance(self, provider_class: type[T], provider_type: K) -> T:
        return provider_class()

    def get_providers_by_priority(self) -> list[tuple[str, T, int]]:
        with self._lock:
            items = list(self._items.items())
            items.sort(key=lambda pair: pair[1].priority, reverse=True)
            return [(key, item.value, item.priority) for key, item in items]

    def clear_instances(self) -> None:
        with self._instance_lock:
            self._instances.clear()
            logger.debug("Cleared cached instances for %s registry", self._name)


__all__ = ["ProviderRegistry"]
