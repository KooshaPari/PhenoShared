"""Config file loader: YAML / TOML / JSON with env-var override.

Detects file format from extension. Raises ``ConfigError`` on parse failure
or missing path. When ``env_override`` is enabled (the default), any env var
named ``<PREFIX><KEY>__<SUBKEY>`` (double underscore for nesting) is applied
to the loaded config as a string. For example,
``PHENOTYPE_LOG__LEVEL=DEBUG`` overrides ``log.level``.

Config file discovery
---------------------
Use :func:`find_config` to search well-known locations automatically::

    cfg = load_config(find_config())
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

ENV_PREFIX = "PHENOTYPE_"

# ---------------------------------------------------------------------------
# Default search paths (XDG-compatible)
# ---------------------------------------------------------------------------
_CONFIG_ENV_VAR = "PHENOTYPE_CONFIG"  # env var pointing to a config file
_CONFIG_FILENAMES = ["config.yaml", "config.yml", "config.json", "config.toml"]


class ConfigError(Exception):
    """Raised when config loading fails (missing file, parse error, etc.)."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_config(
    *,
    search_cwd: bool = True,
    search_xdg: bool = True,
    search_config_dir: bool = True,
) -> Path | None:
    """Locate a config file from well-known paths.

    Search order (first match wins):

    1. ``$PHENOTYPE_CONFIG`` — explicit env-var override.
    2. ``./<filename>`` for each known filename — current working directory.
    3. ``./config/<filename>`` — ``config/`` subdirectory of CWD.
    4. ``$XDG_CONFIG_HOME/phenotype/<filename>`` (defaulting to
       ``~/.config/phenotype/``).
    5. Each ``$XDG_CONFIG_DIRS/phenotype/<filename>`` (defaulting to
       ``/etc/xdg/phenotype/``).

    Args:
        search_cwd: Search the current working directory and its
            ``config/`` subdirectory.
        search_xdg: Search XDG config paths.
        search_config_dir: Search ``./config/`` subdirectory.

    Returns:
        The first config file found, or ``None`` if no file exists.
    """
    # 1. Explicit env-var override
    env_path = os.environ.get(_CONFIG_ENV_VAR)
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    candidates: list[Path] = []

    if search_cwd:
        for name in _CONFIG_FILENAMES:
            candidates.append(Path.cwd() / name)

    if search_config_dir:
        for name in _CONFIG_FILENAMES:
            candidates.append(Path.cwd() / "config" / name)

    if search_xdg:
        xdg_config_home = Path(
            os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        )
        for name in _CONFIG_FILENAMES:
            candidates.append(xdg_config_home / "phenotype" / name)

        xdg_config_dirs = os.environ.get("XDG_CONFIG_DIRS", "/etc/xdg").split(":")
        for d in xdg_config_dirs:
            for name in _CONFIG_FILENAMES:
                candidates.append(Path(d) / "phenotype" / name)

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def load_config(
    path: str | Path,
    *,
    env_override: bool = True,
    env_prefix: str = ENV_PREFIX,
) -> dict[str, Any]:
    """Load a config file (YAML/TOML/JSON), optionally overridden by env vars.

    Args:
        path: Path to the config file. Must have a .yaml/.yml/.toml/.json
            extension.
        env_override: If True, merge env vars into the config.
        env_prefix: Prefix for env-var override keys.

    Returns:
        The merged config dict.

    Raises:
        ConfigError: If the file doesn't exist, can't be parsed, or the
            root value is not a mapping.
    """
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file not found: {p}")

    suffix = p.suffix.lower()
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigError(f"Could not read {p}: {e}") from e

    try:
        if suffix in (".yaml", ".yml"):
            data: Any = yaml.safe_load(text) or {}
        elif suffix == ".json":
            data = json.loads(text)
        elif suffix == ".toml":
            data = _load_toml(text)
        else:
            raise ConfigError(f"Unsupported config format: {suffix}")
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise ConfigError(f"Could not parse {p}: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError(f"Config root must be a mapping, got {type(data).__name__}")

    if env_override:
        _apply_env_overrides(data, env_prefix)

    return data


def merge_configs(
    paths: list[str | Path],
    *,
    env_override: bool = True,
    env_prefix: str = ENV_PREFIX,
) -> dict[str, Any]:
    """Load and deep-merge multiple config files (later files win).

    Each file is loaded via :func:`load_config` and merged left-to-right,
    so keys in later files override those in earlier files.

    Args:
        paths: Ordered list of config file paths.
        env_override: Passed through to each :func:`load_config` call.
            Env-var overrides are applied to the **final merged result**,
            not per-file.
        env_prefix: Prefix for env-var override keys.

    Returns:
        The merged config dict.

    Raises:
        ConfigError: If any file cannot be loaded.
    """
    merged: dict[str, Any] = {}
    for path in paths:
        cfg = load_config(path, env_override=False)
        _deep_merge(merged, cfg)
    if env_override:
        _apply_env_overrides(merged, env_prefix)
    return merged


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_toml(text: str) -> Any:
    """Load TOML text using stdlib tomllib (3.11+) or the tomli fallback."""
    if sys.version_info >= (3, 11):
        import tomllib

        return tomllib.loads(text)
    try:
        import tomli  # type: ignore[import-not-found]
    except ImportError as e:
        raise ConfigError(
            "toml support requires Python 3.11+ or the 'tomli' package "
            "(install phenotype-py-utils[toml])"
        ) from e
    return tomli.loads(text)


def _apply_env_overrides(data: dict[str, Any], prefix: str) -> None:
    """Walk ``os.environ`` and apply ``PREFIX*__*`` keys into ``data`` in place.

    Keys are matched case-insensitively: ``PHENOTYPE_LOG__LEVEL`` will
    override ``log.level``. This matches typical 12-factor usage (env vars
    are uppercase) while still letting YAML/JSON configs use the
    conventional lowercase nesting.
    """
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        rest = key[len(prefix) :].lower()
        parts = rest.split("__")
        cur: Any = data
        for part in parts[:-1]:
            existing = cur.get(part)
            if not isinstance(existing, dict):
                cur[part] = {}
            cur = cur[part]
        cur[parts[-1]] = value


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> None:
    """Recursively merge ``overlay`` into ``base`` in place."""
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


__all__ = [
    "ConfigError",
    "find_config",
    "load_config",
    "merge_configs",
]
