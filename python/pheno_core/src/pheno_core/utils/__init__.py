"""
Utility modules for pheno-sdk.
"""

from __future__ import annotations

try:
    from .env import env_override_enabled, get_env, get_env_bool, reload_env
except ImportError:
    # Fallback basic implementations
    import os

    def get_env(key: str, default: str | None = None) -> str | None:
        return os.environ.get(key, default)

    def get_env_bool(key: str, default: bool = False) -> bool:
        raw_default = "true" if default else "false"
        raw_value = get_env(key, raw_default)
        return (raw_value or raw_default).strip().lower() == "true"

    def env_override_enabled() -> bool:
        return get_env("ZEN_MCP_FORCE_ENV_OVERRIDE", "false").strip().lower() == "true"

    def reload_env():
        pass


__all__ = [
    "env_override_enabled",
    "get_env",
    "get_env_bool",
    "reload_env",
]
