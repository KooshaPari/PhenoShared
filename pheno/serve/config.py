"""Configuration loading for pheno-serve-dev."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pheno.paths import CONFIG_DIR, PHENO_ROOT


@dataclass(frozen=True)
class ServeConfig:
    """Lazy view over ``pheno_serve.yaml`` with typed property accessors."""

    path: Path
    raw: dict[str, Any]

    @property
    def server(self) -> dict[str, Any]:
        """Server block (host/port/etc.) from the raw config."""
        return self.raw.get("server", {}) or {}

    @property
    def profiles(self) -> dict[str, dict[str, Any]]:
        """Profile mapping (alias -> raw profile dict)."""
        return self.raw.get("profiles", {}) or {}

    @property
    def capture_headers(self) -> list[str]:
        """List of header names to capture from incoming requests."""
        return list((self.raw.get("headers", {}) or {}).get("capture", []) or [])

    @property
    def events_path(self) -> Path:
        """Resolved path for the JSONL event log."""
        path = self.server.get("events_path", "logs/pheno_serve/events.jsonl")
        return _resolve_path(path)

    @property
    def state_path(self) -> Path:
        """Resolved path for the persisted state JSON file."""
        path = self.server.get("state_path", "state/pheno_serve.json")
        return _resolve_path(path)


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PHENO_ROOT / path


def load_config(path: str | Path | None = None) -> ServeConfig:
    """Load a ``pheno_serve.yaml`` config; defaults to ``CONFIG_DIR/pheno_serve.yaml``."""
    cfg_path = Path(path) if path else CONFIG_DIR / "pheno_serve.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return ServeConfig(path=cfg_path, raw=raw)
