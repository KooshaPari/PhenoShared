"""
Adapter registry implementation.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
import time
from threading import Lock
from typing import TYPE_CHECKING, Any

from ..base import RegistryItem
from .enums import AdapterType
from .plugins import PluginHook, PluginRegistry

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """
    Unified adapter registry that consolidates adapter management functionality.
    """

    def __init__(self) -> None:
        self._adapters: dict[AdapterType, dict[str, RegistryItem[Any]]] = {
            adapter_type: {} for adapter_type in AdapterType
        }
        self._instances: dict[str, Any] = {}
        self._metrics: dict[str, dict[str, float]] = {}
        self._callbacks: dict[str, list[Callable[..., None]]] = {}
        self._lock = Lock()
        self._plugins = PluginRegistry()

    def register_adapter(
        self,
        adapter_type: AdapterType,
        name: str,
        adapter_class: type,
        *,
        replace: bool = False,
        metadata: Mapping[str, Any] | None = None,
        priority: int = 0,
        factory: Callable[..., Any] | None = None,
        singleton: bool = True,
        health_check: Callable[[Any], Any] | None = None,
        plugins: Iterable[PluginHook] | None = None,
    ) -> None:
        with self._lock:
            if not replace and name in self._adapters[adapter_type]:
                raise ValueError(
                    f"Adapter '{name}' already registered for type '{adapter_type.value}'",
                )

            adapter_metadata: dict[str, Any] = dict(metadata or {})
            adapter_metadata.setdefault("singleton", singleton)
            if factory is not None:
                adapter_metadata["factory"] = factory
            if health_check is not None:
                adapter_metadata["health_check"] = health_check

            self._adapters[adapter_type][name] = RegistryItem(
                key=name,
                value=adapter_class,
                metadata=adapter_metadata,
                priority=priority,
            )

            instance_key = self._instance_key(adapter_type, name)
            self._instances.pop(instance_key, None)
            self._metrics.pop(instance_key, None)

            if plugins:
                for hook in plugins:
                    self._plugins.register(adapter_type, name, hook)

            logger.info("Registered %s adapter: %s", adapter_type.value, name)

    def register_plugin(self, adapter_type: AdapterType, name: str, plugin: PluginHook) -> None:
        self._plugins.register(adapter_type, name, plugin)

    def get_adapter_class(self, adapter_type: AdapterType, name: str) -> type:
        with self._lock:
            if name not in self._adapters[adapter_type]:
                available = list(self._adapters[adapter_type].keys())
                raise KeyError(
                    f"No {adapter_type.value} adapter registered with name '{name}'. Available: {available}",
                )
            return self._adapters[adapter_type][name].value

    def create_adapter_instance(
        self,
        adapter_type: AdapterType,
        name: str,
        *,
        cache: bool = True,
        **kwargs: Any,
    ) -> Any:
        instance_key = self._instance_key(adapter_type, name)
        if cache and instance_key in self._instances:
            return self._instances[instance_key]

        with self._lock:
            entry = self._adapters[adapter_type].get(name)
            if entry is None:
                available = list(self._adapters[adapter_type].keys())
                raise KeyError(
                    f"No {adapter_type.value} adapter registered with name '{name}'. Available: {available}",
                )

        metadata = dict(entry.metadata)
        singleton = metadata.get("singleton", True)
        factory = metadata.get("factory")

        start = time.perf_counter()
        instance = factory(**kwargs) if factory else entry.value(**kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if cache and singleton:
            with self._lock:
                self._instances[instance_key] = instance

        with self._lock:
            self._metrics[instance_key] = {
                "last_create_ms": elapsed_ms,
                "singleton": float(bool(singleton)),
            }
            plugins = self._plugins.get(adapter_type, name)

        for plugin in plugins:
            try:
                plugin(self, instance)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Adapter plugin %s failed for %s (%s): %s",
                    getattr(plugin, "__name__", plugin),
                    name,
                    adapter_type.value,
                    exc,
                )

        return instance

    def resolve_adapter(self, adapter_type: AdapterType, name: str, **kwargs: Any) -> Any:
        return self.create_adapter_instance(adapter_type, name, **kwargs)

    def resolve_many(self, adapter_type: AdapterType, names: Iterable[str]) -> dict[str, Any]:
        return {name: self.create_adapter_instance(adapter_type, name) for name in names}

    def list_adapters(self, adapter_type: AdapterType) -> list[str]:
        with self._lock:
            return list(self._adapters[adapter_type].keys())

    def get_adapter_types(self) -> list[AdapterType]:
        with self._lock:
            return [t for t in AdapterType if self._adapters[t]]

    def get_adapters_by_priority(self, adapter_type: AdapterType) -> list[tuple[str, type, int]]:
        with self._lock:
            items = list(self._adapters[adapter_type].items())
            items.sort(key=lambda pair: pair[1].priority, reverse=True)
            return [(name, item.value, item.priority) for name, item in items]

    async def run_health_checks(self) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        for adapter_type in AdapterType:
            for name, entry in list(self._adapters[adapter_type].items()):
                health_check = entry.metadata.get("health_check")
                if health_check is None:
                    continue
                try:
                    instance = self.create_adapter_instance(adapter_type, name)
                    result = health_check(instance)
                    results[f"{adapter_type.value}:{name}"] = {
                        "status": "ok",
                        "result": result,
                    }
                except Exception as exc:  # pragma: no cover - health check failure
                    logger.warning(
                        "Health check failed for %s (%s): %s",
                        name,
                        adapter_type.value,
                        exc,
                    )
                    results[f"{adapter_type.value}:{name}"] = {
                        "status": "error",
                        "error": str(exc),
                    }
        return results

    # ------------------------------------------------------------------
    # Callback helpers
    # ------------------------------------------------------------------
    def register_callback(self, key: str, callback: Callable[..., None]) -> None:
        self._callbacks.setdefault(key, []).append(callback)

    def trigger_callbacks(self, key: str, *args: Any, **kwargs: Any) -> None:
        for callback in list(self._callbacks.get(key, [])):
            try:
                callback(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Adapter callback %s failed: %s",
                    getattr(callback, "__name__", callback),
                    exc,
                )

    # ------------------------------------------------------------------
    # Auto-discovery
    # ------------------------------------------------------------------
    def autodiscover(self, package: str, *, adapter_type: AdapterType | None = None) -> int:
        module = importlib.import_module(package)
        discovered = 0
        for _finder, name, ispkg in pkgutil.walk_packages(module.__path__, module.__name__ + "."):
            if ispkg:
                continue
            try:
                imported = importlib.import_module(name)
            except Exception as exc:  # pragma: no cover - discovery failure
                logger.debug("Failed to import %s during autodiscovery: %s", name, exc)
                continue

            for attr in dir(imported):
                obj = getattr(imported, attr)
                if isinstance(obj, type) and issubclass(obj, RegistryItem):
                    discovered += 1
                    if adapter_type is None:
                        raise NotImplementedError("Auto-detecting adapter type is not implemented")
                    self.register_adapter(adapter_type, obj.__name__.lower(), obj)
        return discovered

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    def get_metrics(self, adapter_type: AdapterType, name: str) -> dict[str, float]:
        key = self._instance_key(adapter_type, name)
        return dict(self._metrics.get(key, {}))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _instance_key(self, adapter_type: AdapterType, name: str) -> str:
        return f"{adapter_type.value}:{name}"


_adapter_registry: AdapterRegistry | None = None


def get_adapter_registry() -> AdapterRegistry:
    global _adapter_registry
    if _adapter_registry is None:
        _adapter_registry = AdapterRegistry()
    return _adapter_registry


__all__ = ["AdapterRegistry", "get_adapter_registry"]
