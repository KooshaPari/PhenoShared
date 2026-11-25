"""Single source of truth for the currently authorized local model aliases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .paths import CONFIG_DIR


def local_aliases(config_path: Path | None = None) -> set[str]:
    """Return the locked set of authorized local model aliases from the matrix YAML."""
    path = config_path or CONFIG_DIR / "local_model_bench_matrix.yaml"
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(item["alias"]) for item in (data.get("models") or {}).values()}


def require_local_alias(alias: str, config_path: Path | None = None) -> str:
    """Validate that ``alias`` is in the locked local set, else raise ValueError."""
    allowed = local_aliases(config_path)
    if alias not in allowed:
        raise ValueError(
            f"model alias is not in the locked local set: {alias}; allowed={sorted(allowed)}"
        )
    return alias


def runtime_admissible_aliases(config_path: Path | None = None) -> set[str]:
    """Return locked aliases whose exact artifact is not fail-closed."""
    path = config_path or CONFIG_DIR / "local_model_bench_matrix.yaml"
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    blocked_markers = ("blocked", "conversion_failed", "missing", "unresolved")
    allowed: set[str] = set()
    for item in (data.get("models") or {}).values():
        alias = str(item.get("alias", ""))
        status = str(item.get("exact_artifact_status", "")).lower()
        if alias and status and not any(marker in status for marker in blocked_markers):
            allowed.add(alias)
    return allowed


def require_runtime_alias(alias: str, config_path: Path | None = None) -> str:
    """Reject aliases whose current artifact admission is explicitly blocked."""
    require_local_alias(alias, config_path)
    allowed = runtime_admissible_aliases(config_path)
    if alias not in allowed:
        raise ValueError(
            f"model alias is not runtime-admissible: {alias}; allowed={sorted(allowed)}"
        )
    return alias


__all__ = [
    "local_aliases",
    "require_local_alias",
    "runtime_admissible_aliases",
    "require_runtime_alias",
]
