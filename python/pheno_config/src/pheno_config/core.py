"""Consolidated Configuration Management.

Unified configuration system with features from:
- config-kit: Pydantic v2 models, multi-source loading
- pydevkit: Hierarchical merging, dot-notation access
    - pheno.tui.core.config: Hot-reload, profile-based config

Features:
- Pydantic v2 BaseModel foundation
- Hierarchical loading (env > files > defaults)
- Hot-reload support
- Schema validation
- Type safety
- Dot-notation access
- Profile-based configuration
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Self, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="Config")


class Config(BaseModel):
    """Base configuration class with Pydantic v2.

    All configuration classes should inherit from this to get:
    - Type validation
    - Environment variable loading
    - File loading (JSON, YAML, TOML)
    - Hierarchical merging

    Example:
        >>> class DatabaseConfig(Config):
        ...     host: str = "localhost"
        ...     port: int = 5432
        ...     name: str = "mydb"
        ...
        >>> # Load from environment
        >>> db_config = DatabaseConfig.from_env(prefix="DB_")
        ...
        >>> # Load from file
        >>> db_config = DatabaseConfig.from_file("config.yaml")
        ...
        >>> # Load with cascade (env > file > defaults)
        >>> db_config = DatabaseConfig.load(
        ...     env_prefix="DB_",
        ...     config_file="config.yaml"
        ... )
    """

    model_config = {"extra": "allow", "validate_assignment": True}

    @classmethod
    def from_env(cls, prefix: str = "", _return_dict: bool = False) -> Self | dict[str, Any]:
        """Load configuration from environment variables.

        Args:
            prefix: Prefix for environment variables (e.g., "APP_")
            _return_dict: Internal flag to return dict instead of instance

        Returns:
            Configuration instance or dict if _return_dict=True

        Example:
            >>> config = AppConfig.from_env(prefix="APP_")
        """
        data = {}
        prefix_upper = prefix.upper()

        # Get all fields from the model
        for field_name in cls.model_fields:
            env_key = f"{prefix_upper}{field_name.upper()}"
            if env_key in os.environ:
                data[field_name] = os.environ[env_key]

        if _return_dict:
            return data
        return cls(**data)

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        """Load configuration from file (JSON, YAML, or TOML).

        Args:
            path: Path to configuration file

        Returns:
            Configuration instance

        Example:
            >>> config = AppConfig.from_file("config.yaml")
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        # Determine format from extension
        suffix = path.suffix.lower()

        if suffix in [".yaml", ".yml"]:
            import yaml

            with open(path) as f:
                data = yaml.safe_load(f) or {}
        elif suffix == ".json":
            import json

            with open(path) as f:
                data = json.load(f)
        elif suffix == ".toml":
            try:
                import tomllib  # Python 3.11+
            except ImportError:
                import tomli as tomllib  # Fallback
            with open(path, "rb") as f:
                data = tomllib.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {suffix}")

        return cls(**data)

    @classmethod
    def load(
        cls,
        env_prefix: str = "",
        config_file: str | Path | None = None,
        defaults: dict[str, Any] | None = None,
    ) -> Self:
        """Load configuration with hierarchical merging.

        Priority: env > config_file > defaults

        Args:
            env_prefix: Prefix for environment variables
            config_file: Path to configuration file
            defaults: Default values

        Returns:
            Configuration instance with merged values

        Example:
            >>> config = AppConfig.load(
            ...     env_prefix="APP_",
            ...     config_file="config.yaml",
            ...     defaults={"debug": False}
            ... )
        """
        # Start with defaults
        data = defaults or {}

        # Merge file config
        if config_file:
            try:
                file_config = cls.from_file(config_file)
                data.update(file_config.model_dump())
            except FileNotFoundError:
                logger.warning(f"Config file not found: {config_file}, using defaults")

        # Merge environment variables (highest priority)
        # Only merge values that are actually set in environment
        if env_prefix:
            env_data = cls.from_env(prefix=env_prefix, _return_dict=True)
            data.update(env_data)

        return cls(**data)


class AppConfig(Config):
    """Canonical application configuration surface.

    Provides baseline fields for name, logging, and environment tagging while allowing
    teams to extend the model with additional settings as needed.
    """

    name: str = "pheno-app"
    debug: bool = False
    log_level: str = "INFO"
    environment: str = "development"


class MorphConfig(Config):
    """
    Morph-specific runtime options exposed via pheno.config.
    """

    enable_structlog: bool = Field(default=True, description="Enable structlog adapter by default")
    embedding_cache_dir: str = Field(
        default=".morph_cache/embeddings",
        description="Local embedding cache path",
    )
    security_profile: str = Field(default="strict", description="Secret scanning profile")
    enable_presidio: bool = Field(
        default=False,
        description="Toggle Presidio PII analyzer integration",
    )
    allow_remote_embeddings: bool = Field(
        default=True,
        description="Allow litellm-powered remote embeddings",
    )
    subsystem_timeouts: dict[str, float] = Field(
        default_factory=lambda: {"semantic_search": 30.0, "secret_scan": 60.0},
        description="Operation timeouts (seconds) per subsystem",
    )


class DatabaseConfig(Config):
    """Relational database connection parameters.

    The defaults target a local Postgres instance but align with production needs such
    as pooling and overflow thresholds.
    """

    host: str = "localhost"
    port: int = 5432
    name: str = "postgres"
    user: str = "postgres"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20


class RedisConfig(Config):
    """Redis connection details tuned for ``redis-py`` compatibility.

    Callers can forward ``RedisConfig.model_dump()`` directly to client
    constructors for ergonomic setup.
    """

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    max_connections: int = 50


class ConfigManager:
    """Configuration manager with dot-notation access and hierarchical merging.

    Features:
    - Dot-notation access (e.g., config.get("app.debug"))
    - Hierarchical merging (env > files > defaults)
    - Runtime overrides
    - Freeze/unfreeze support

    Example:
        >>> manager = ConfigManager()
        >>> manager.load_from_dict({"app": {"debug": True}})
        >>> debug = manager.get("app.debug")  # True
        >>> manager.set("app.log_level", "DEBUG")
    """

    def __init__(self):
        self._config: dict[str, Any] = {}
        self._frozen = False

    def load_from_dict(self, data: dict[str, Any]) -> None:
        """Overwrite the registry with values from ``data``.

        Args:
            data: Nested mapping representing the target configuration state.

        Raises:
            RuntimeError: If the manager has been frozen via :meth:`freeze`.
        """
        if self._frozen:
            raise RuntimeError("Configuration is frozen")
        self._config = data.copy()

    def load_from_env(self, prefix: str = "") -> None:
        """Populate the registry from environment variables honouring ``prefix``.

        Args:
            prefix: Upper-case prefix (e.g., ``PHENO_``) used to filter variables.

        Raises:
            RuntimeError: When invoked while the manager is frozen.
        """
        if self._frozen:
            raise RuntimeError("Configuration is frozen")

        prefix_upper = prefix.upper()
        for key, value in os.environ.items():
            if key.startswith(prefix_upper):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix_upper) :].lower()
                self._config[config_key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.

        Args:
            key: Dot-separated key (e.g., "app.debug")
            default: Default value if key not found

        Returns:
            Configuration value

        Example:
            >>> value = manager.get("database.host", "localhost")
        """
        parts = key.split(".")
        current = self._config

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default

        return current

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation.

        Args:
            key: Dot-separated key (e.g., "app.debug")
            value: Value to set

        Example:
            >>> manager.set("app.debug", True)
        """
        if self._frozen:
            raise RuntimeError("Configuration is frozen")

        parts = key.split(".")
        current = self._config

        # Navigate to the parent of the target key
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the value
        current[parts[-1]] = value

    def freeze(self) -> None:
        """Prevent further mutations to the registry.

        Ideal once application bootstrap completes to guard against accidental runtime
        writes.
        """
        self._frozen = True

    def unfreeze(self) -> None:
        """Re-enable mutations following a :meth:`freeze` call.

        Primarily intended for administrative utilities or tests that require temporary
        write access.
        """
        self._frozen = False

    def to_dict(self) -> dict[str, Any]:
        """Produce a shallow copy of the current configuration state.

        Returns:
            Dictionary snapshot suitable for inspection or serialization.
        """
        return self._config.copy()


# Global config manager instance
_config_manager = ConfigManager()


def config_manager() -> ConfigManager:
    """Retrieve the process-wide configuration manager singleton.

    Returns:
        Shared :class:`ConfigManager` instance used across the SDK.
    """
    return _config_manager


def parse_dotenv(path: str | Path = ".env") -> dict[str, str]:
    """Parse .env file into dictionary.

    Args:
        path: Path to .env file

    Returns:
        Dictionary of environment variables

    Example:
        >>> env_vars = parse_dotenv(".env.local")
    """
    path = Path(path)
    if not path.exists():
        return {}

    env_vars = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")

    return env_vars


def load_env_cascade(
    root_dirs: list[Path] | None = None,
    env_files: list[Path] | None = None,
) -> dict[str, str]:
    """Load environment variables with cascading priority.

    Priority: env_files > .env.local > .env

    Args:
        root_dirs: Directories to search for .env files
        env_files: Specific .env files to load

    Returns:
        Merged environment variables

    Example:
        >>> env = load_env_cascade(
        ...     root_dirs=[Path(".")],
        ...     env_files=[Path(".env.production")]
        ... )
    """
    env_vars = {}

    # Load from root directories
    if root_dirs:
        for root_dir in root_dirs:
            # Load .env
            env_file = root_dir / ".env"
            if env_file.exists():
                env_vars.update(parse_dotenv(env_file))

            # Load .env.local (higher priority)
            env_local = root_dir / ".env.local"
            if env_local.exists():
                env_vars.update(parse_dotenv(env_local))

    # Load specific env files (highest priority)
    if env_files:
        for env_file in env_files:
            if env_file.exists():
                env_vars.update(parse_dotenv(env_file))

    return env_vars


__all__ = [
    "AppConfig",
    "Config",
    "ConfigManager",
    "DatabaseConfig",
    "RedisConfig",
    "config_manager",
    "load_env_cascade",
    "parse_dotenv",
]
