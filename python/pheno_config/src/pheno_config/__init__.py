"""Pheno Config.

Unified, typed configuration surface for applications and adapters.

Phase 2 consolidation:
- Provide native `pheno.config.core` primitives (breaking change for internal paths)
- Legacy kits emit deprecation warnings; import from pheno.config going forward
"""

from __future__ import annotations

# Convenience shims for common env ops
from os import getenv as get_env
from os import putenv as set_env  # type: ignore[attr-defined]

from .core import (
    AppConfig,
    Config,
    ConfigManager,
    DatabaseConfig,
    MorphConfig,
    RedisConfig,
    config_manager,
    load_env_cascade,
    parse_dotenv,
)
from .integration import (
    MorphIntegrationSettings,
    RouterIntegrationSettings,
    get_integration_settings,
    get_morph_settings,
    get_router_settings,
)
from .providers import (
    AzureOpenAIConfig,
    ProviderConfigs,
    RetryConfig,
    load_provider_configs_from_env,
)
from .vector import (
    get_vector_embedding_service,
    get_vector_search_service,
    reset_vector_services,
    vector_provider_status,
)

# Default model configuration
DEFAULT_MODEL = "auto"


def pop_env(key: str, default: str | None = None) -> str | None:
    """
    Pop an environment variable.
    """
    import os

    return os.environ.pop(key, default)


def collect_env(prefix: str, *, strip_prefix: bool = True) -> dict[str, str]:
    prefix_u = prefix.upper()
    out: dict[str, str] = {}
    import os

    for k, v in os.environ.items():
        if k.startswith(prefix_u):
            kk = k[len(prefix_u) :] if strip_prefix else k
            out[kk] = v
    return out


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get environment variable as boolean.
    """
    import os

    raw_value = os.environ.get(key)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"true", "1", "yes", "on"}


def get_config() -> dict[str, str]:
    """Return a dict-like config structure for consumers.

    Returns a plain dict with optional keys that clink may look for.
    """
    import os

    config: dict[str, str] = {}
    # Optional keys that some code may check
    if v := os.environ.get("CLINK_CLIENTS_CONFIG_PATH"):
        config["clink_clients_config_path"] = v
    if v := os.environ.get("CLINK_CONFIG_DIR"):
        config["clink_config_dir"] = v
    return config


__all__ = [
    "DEFAULT_MODEL",
    "AppConfig",
    "AzureOpenAIConfig",
    "Config",
    "ConfigManager",
    "DatabaseConfig",
    "MorphConfig",
    "MorphIntegrationSettings",
    "ProviderConfigs",
    "RedisConfig",
    "RetryConfig",
    "RouterIntegrationSettings",
    "collect_env",
    "config_manager",
    "get_config",
    "get_env",
    "get_env_bool",
    "get_integration_settings",
    "get_morph_settings",
    "get_router_settings",
    "get_vector_embedding_service",
    "get_vector_search_service",
    "load_env_cascade",
    "load_provider_configs_from_env",
    "parse_dotenv",
    "pop_env",
    "reset_vector_services",
    "set_env",
    "vector_provider_status",
]
