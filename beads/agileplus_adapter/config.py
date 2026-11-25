"""agileplus_adapter.config — runtime-config loader for the bead store.

v0.12 WBS-PERT-100 task 27 (Phase 2 — AgilePlus config schema) ac_v1.

Reads `~/.agileplus/config.json` and returns a typed config dict
with defaults applied for missing keys. Mirrors the layered design
of `pheno.trace_store.config` (load_config + resolve_token).

Schema:

    {
      "schema_version": 1,
      "host": "127.0.0.1",
      "port": 8080,
      "base_url": null,
      "api_token_env": "AGILEPLUS_API_TOKEN",
      "timeout": 5.0,
      "work_package_id": 1,
      "enabled": false,
      "session_id": null
    }

Field reference:

| Field | Default | Notes |
|-------|---------|-------|
| schema_version | 1 | bumped on breaking schema changes |
| host | 127.0.0.1 | AgilePlus hostname |
| port | 8080 | AgilePlus port |
| base_url | null | if set, overrides host:port |
| api_token_env | AGILEPLUS_API_TOKEN | env var name to look up at runtime |
| timeout | 5.0 | per-request HTTP timeout in seconds |
| work_package_id | 1 | single WP used for bead routing |
| enabled | false | master switch for dual-write (task 28) |
| session_id | null | optional default session id |

The loader is intentionally tolerant: missing file → defaults;
partial file → defaults merged with the partial config; non-dict
file → defaults. Callers should always get a usable config dict.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from beads.agileplus_adapter.agileplus_adapter import DEFAULT_CONFIG_PATH

# Supported schema versions (bump on breaking changes).
SUPPORTED_SCHEMA_VERSIONS = (1,)


# Default config — matches ~/.agileplus/config.json shipped values.
_DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "host": "127.0.0.1",
    "port": 8080,
    "base_url": None,
    "api_token_env": "AGILEPLUS_API_TOKEN",
    "timeout": 5.0,
    "work_package_id": 1,
    "enabled": False,
    "session_id": None,
}


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load the AgilePlus config from JSON; apply defaults for missing keys.

    If the file does not exist, returns the default config dict.
    Keys present in the file override the defaults; missing keys are
    filled in from defaults (so a partial config is safe to commit).

    Args:
        path: explicit config path; defaults to
            `~/.agileplus/config.json`.

    Raises:
        ValueError: when the schema_version is not in
            SUPPORTED_SCHEMA_VERSIONS.
    """
    target = Path(path) if path else DEFAULT_CONFIG_PATH
    config = dict(_DEFAULT_CONFIG)
    if target.is_file():
        raw = target.read_text(encoding="utf-8").strip()
        # Empty file = treat as missing → defaults.
        if not raw:
            return config
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"agileplus config {target} is not valid JSON: {exc}"
            ) from exc
        if not isinstance(loaded, dict):
            # Non-dict top-level → ignore contents, keep defaults.
            return config
        version = loaded.get("schema_version", 1)
        if version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(
                f"agileplus config schema_version={version} not in "
                f"supported set {SUPPORTED_SCHEMA_VERSIONS}. "
                f"Update SUPPORTED_SCHEMA_VERSIONS."
            )
        config.update(loaded)
    return config


def resolve_token(config: dict[str, Any]) -> str | None:
    """Resolve the API token from the env var named in `api_token_env`.

    Returns None when the env var is unset OR when `api_token_env`
    is missing from the config (defensive default).
    """
    env_var = config.get("api_token_env") or "AGILEPLUS_API_TOKEN"
    return os.environ.get(env_var)


def is_enabled(config: dict[str, Any]) -> bool:
    """Return True iff the dual-write master switch is on.

    Convenience accessor — callers don't have to read the `enabled`
    field directly. Returns False when the key is missing (defensive).
    """
    return bool(config.get("enabled", False))
