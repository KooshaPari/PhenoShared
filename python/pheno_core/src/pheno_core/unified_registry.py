"""Unified Registry System.

This module provides a comprehensive unified registry system that consolidates all
registry patterns used throughout the Pheno-SDK codebase.

This is the CANONICAL registry implementation that replaces all other registry
implementations across the codebase.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
)

try:  # Python 3.10+
    from importlib.metadata import entry_points
except Exception:  # pragma: no cover
    entry_points = None  # type: ignore

from .registry.adapters import AdapterRegistry
from .registry.base import Registry
from .registry.provider import ProviderRegistry

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

T = TypeVar("T")
K = TypeVar("K", bound=Enum)


class RegistryType(Enum):
    """
    Types of registries supported by the unified system.
    """

    GENERIC = "generic"
    PROVIDER = "provider"
    ADAPTER = "adapter"
    TOOL = "tool"
    PLUGIN = "plugin"
    RESOURCE = "resource"
    COMPONENT = "component"


@dataclass
class RegistryConfig:
    """
    Configuration for a registry instance.
    """

    name: str
    registry_type: RegistryType
    separator: str = ":"
    thread_safe: bool = True
    auto_discovery: bool = False
    entry_point_group: str | None = None
    cache_instances: bool = False
    priority_resolution: bool = False
    metadata_required: bool = False


class UnifiedRegistryManager:
    """Central manager for all registries in the system.

    Provides a single point of access for all registry operations and ensures
    consistency across the codebase.
    """

    def __init__(self):
        """
        Initialize the unified registry manager.
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._registries: dict[str, Registry[Any]] = {}
        self._configs: dict[str, RegistryConfig] = {}
        self._lock = Lock()

        # Initialize default registries
        self._initialize_default_registries()

    def _initialize_default_registries(self) -> None:
        """
        Initialize default registries.
        """
        # Tool registry
        self.create_registry(
            "tools",
            RegistryType.GENERIC,
            config=RegistryConfig(
                name="tools",
                registry_type=RegistryType.GENERIC,
                auto_discovery=True,
                entry_point_group="pheno.tools",
            ),
        )

        # Provider registry
        self.create_registry(
            "providers",
            RegistryType.PROVIDER,
            config=RegistryConfig(
                name="providers",
                registry_type=RegistryType.PROVIDER,
                priority_resolution=True,
                cache_instances=True,
            ),
        )

        # Adapter registry
        self.create_registry(
            "adapters",
            RegistryType.ADAPTER,
            config=RegistryConfig(
                name="adapters",
                registry_type=RegistryType.ADAPTER,
                auto_discovery=True,
                cache_instances=True,
            ),
        )

        # Plugin registry
        self.create_registry(
            "plugins",
            RegistryType.PLUGIN,
            config=RegistryConfig(
                name="plugins",
                registry_type=RegistryType.PLUGIN,
                auto_discovery=True,
                entry_point_group="pheno.plugins",
            ),
        )

        # Resource registry
        self.create_registry(
            "resources",
            RegistryType.RESOURCE,
            config=RegistryConfig(
                name="resources",
                registry_type=RegistryType.RESOURCE,
                metadata_required=True,
            ),
        )

        # Component registry
        self.create_registry(
            "components",
            RegistryType.COMPONENT,
            config=RegistryConfig(
                name="components",
                registry_type=RegistryType.COMPONENT,
                auto_discovery=True,
            ),
        )

    def create_registry(
        self,
        name: str,
        registry_type: RegistryType,
        *,
        config: RegistryConfig | None = None,
    ) -> Registry[Any]:
        """Create a new registry.

        Args:
            name: Name of the registry
            registry_type: Type of registry to create
            config: Optional configuration for the registry

        Returns:
            The created registry instance
        """
        with self._lock:
            if name in self._registries:
                raise ValueError(f"Registry '{name}' already exists")

            # Create registry based on type
            if registry_type == RegistryType.PROVIDER:
                registry = ProviderRegistry(name)
            elif registry_type == RegistryType.ADAPTER:
                registry = AdapterRegistry()
            else:
                registry = Registry(name)

            # Store registry and config
            self._registries[name] = registry
            if config:
                self._configs[name] = config
            else:
                self._configs[name] = RegistryConfig(name=name, registry_type=registry_type)

            self.logger.info(f"Created {registry_type.value} registry: {name}")
            return registry

    def get_registry(self, name: str) -> Registry[Any]:
        """Get a registry by name.

        Args:
            name: Name of the registry

        Returns:
            The registry instance

        Raises:
            KeyError: If registry not found
        """
        with self._lock:
            if name not in self._registries:
                available = list(self._registries.keys())
                raise KeyError(f"Registry '{name}' not found. Available: {available}")
            return self._registries[name]

    def list_registries(self) -> list[str]:
        """
        List all registry names.
        """
        with self._lock:
            return list(self._registries.keys())

    def get_registry_config(self, name: str) -> RegistryConfig:
        """
        Get configuration for a registry.
        """
        with self._lock:
            if name not in self._configs:
                raise KeyError(f"Registry config '{name}' not found")
            return self._configs[name]

    def register_item(
        self,
        registry_name: str,
        key: str,
        item: Any,
        *,
        replace: bool = False,
        metadata: Mapping[str, Any] | None = None,
        priority: int = 0,
    ) -> None:
        """Register an item in a specific registry.

        Args:
            registry_name: Name of the registry
            key: Key for the item
            item: Item to register
            replace: Whether to replace existing item
            metadata: Optional metadata
            priority: Priority for the item
        """
        registry = self.get_registry(registry_name)
        registry.register(key, item, replace=replace, metadata=metadata, priority=priority)

    def get_item(self, registry_name: str, key: str) -> Any:
        """
        Get an item from a registry.
        """
        registry = self.get_registry(registry_name)
        return registry.get(key)

    def list_items(self, registry_name: str, prefix: str | None = None) -> dict[str, Any]:
        """
        List items in a registry.
        """
        registry = self.get_registry(registry_name)
        return registry.list(prefix)

    def unregister_item(self, registry_name: str, key: str) -> None:
        """
        Unregister an item from a registry.
        """
        registry = self.get_registry(registry_name)
        registry.unregister(key)

    def clear_registry(self, registry_name: str) -> None:
        """
        Clear all items from a registry.
        """
        registry = self.get_registry(registry_name)
        registry.clear()

    def auto_discover(self, registry_name: str) -> None:
        """
        Auto-discover items for a registry.
        """
        config = self.get_registry_config(registry_name)
        registry = self.get_registry(registry_name)

        if not config.auto_discovery:
            self.logger.warning(f"Auto-discovery not enabled for registry '{registry_name}'")
            return

        # Load from entry points if configured
        if config.entry_point_group:
            registry.load_entry_points(config.entry_point_group)

        # Auto-discover from package if it's an adapter registry
        if isinstance(registry, AdapterRegistry):
            registry.auto_discover_adapters()

    def get_registry_summary(self) -> dict[str, Any]:
        """
        Get a summary of all registries.
        """
        summary = {"total_registries": len(self._registries), "registries": {}}

        for name, registry in self._registries.items():
            config = self._configs.get(name)
            summary["registries"][name] = {
                "type": config.registry_type.value if config else "unknown",
                "item_count": len(registry),
                "thread_safe": config.thread_safe if config else True,
                "auto_discovery": config.auto_discovery if config else False,
                "entry_point_group": config.entry_point_group if config else None,
            }

        return summary


# Global registry manager instance
_registry_manager: UnifiedRegistryManager | None = None


def get_registry_manager() -> UnifiedRegistryManager:
    """
    Get the global registry manager instance.
    """
    global _registry_manager
    if _registry_manager is None:
        _registry_manager = UnifiedRegistryManager()
    return _registry_manager


# Convenience functions for backward compatibility
def get_tool_registry() -> Registry[Any]:
    """
    Get the tool registry.
    """
    return get_registry_manager().get_registry("tools")


def get_provider_registry() -> Registry[Any]:
    """
    Get the provider registry.
    """
    return get_registry_manager().get_registry("providers")


def get_adapter_registry() -> AdapterRegistry:
    """
    Get the adapter registry.
    """
    return get_registry_manager().get_registry("adapters")


def get_plugin_registry() -> Registry[Any]:
    """
    Get the plugin registry.
    """
    return get_registry_manager().get_registry("plugins")


def get_resource_registry() -> Registry[Any]:
    """
    Get the resource registry.
    """
    return get_registry_manager().get_registry("resources")


def get_component_registry() -> Registry[Any]:
    """
    Get the component registry.
    """
    return get_registry_manager().get_registry("components")


# Migration utilities
class RegistryMigrator:
    """
    Utility class for migrating from old registry implementations.
    """

    def __init__(self, target_registry: str):
        """Initialize migrator for a target registry.

        Args:
            target_registry: Name of the target registry
        """
        self.target_registry = target_registry
        self.manager = get_registry_manager()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def migrate_from_dict(self, items: dict[str, Any], **kwargs) -> None:
        """
        Migrate items from a dictionary.
        """
        registry = self.manager.get_registry(self.target_registry)

        for key, item in items.items():
            try:
                registry.register(key, item, **kwargs)
                self.logger.debug(f"Migrated item '{key}' to {self.target_registry}")
            except Exception as e:
                self.logger.exception(f"Failed to migrate item '{key}': {e}")

    def migrate_from_old_registry(self, old_registry: Any, **kwargs) -> None:
        """
        Migrate items from an old registry implementation.
        """
        registry = self.manager.get_registry(self.target_registry)

        # Try to get items from old registry
        if hasattr(old_registry, "list"):
            items = old_registry.list()
        elif hasattr(old_registry, "_items"):
            items = old_registry._items
        elif hasattr(old_registry, "items"):
            items = old_registry.items
        else:
            self.logger.warning(f"Cannot migrate from {type(old_registry)} - no known interface")
            return

        for key, item in items.items():
            try:
                # Handle different item formats
                if hasattr(item, "value"):
                    # RegistryItem format
                    registry.register(
                        key,
                        item.value,
                        metadata=item.metadata,
                        priority=item.priority,
                    )
                else:
                    # Direct item
                    registry.register(key, item, **kwargs)

                self.logger.debug(f"Migrated item '{key}' to {self.target_registry}")
            except Exception as e:
                self.logger.exception(f"Failed to migrate item '{key}': {e}")


# Export all public classes and functions
__all__ = [
    "RegistryConfig",
    "RegistryMigrator",
    "RegistryType",
    # Core classes
    "UnifiedRegistryManager",
    "get_adapter_registry",
    "get_component_registry",
    "get_plugin_registry",
    "get_provider_registry",
    # Global manager accessor
    "get_registry_manager",
    "get_resource_registry",
    # Convenience functions
    "get_tool_registry",
]
