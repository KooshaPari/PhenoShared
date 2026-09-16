"""config — Tracera runtime-config loader.

Loads `config/tracera.yaml` and applies defaults for any missing keys.
Backwards-compatible: missing file → returns the default config dict
(so callers can construct TraceraAdapter without requiring the yaml).

v0.12 WBS-PERT-100 task 12 (Phase 1 — Tracera adapter config).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Default config — matches config/tracera.yaml shipped values.
_DEFAULT_CONFIG: dict[str, Any] = {
    "host": "127.0.0.1",
    "port": 8080,
    "base_url": None,
    "api_token_env": "TRACERA_API_TOKEN",  # nosec B105
    "timeout": 5.0,
    "batch_size": 32,
    "enabled": False,
    "session_id": None,
}


def load_config(path: str | Path = "config/tracera.yaml") -> dict[str, Any]:
    """Load tracera config from YAML file; apply defaults for missing keys.

    If the file does not exist, returns the default config dict.
    Keys present in the file override the defaults; missing keys are
    filled in from defaults (so a partial yaml is safe to commit).
    """
    path = Path(path)
    config = dict(_DEFAULT_CONFIG)
    if path.is_file():
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if isinstance(loaded, dict):
            config.update(loaded)
    return config


def resolve_token(config: dict[str, Any]) -> str | None:
    """Resolve the API token from the env var named in `api_token_env`.

    Returns None when the env var is unset OR when api_token_env is
    missing from the config (defensive default).
    """
    import os

    env_var = config.get("api_token_env") or "TRACERA_API_TOKEN"
    if env_var == "TRACERA_API_TOKEN":
        # Prefer the successor destination while preserving older deployments.
        return os.environ.get(env_var) or os.environ.get("GRAPHEON_API_TOKEN")
    return os.environ.get(env_var)
