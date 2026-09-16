"""Model alias registry for pheno-serve-dev."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pheno.serve.config import ServeConfig


@dataclass(frozen=True)
class ServingProfile:
    """A backend model profile: alias, engine, upstream URL, and operational status."""

    alias: str
    engine: str
    base_url: str | None
    status: str
    raw: dict[str, Any]

    @property
    def backend_mode(self) -> str:
        """Backend mode hint from the raw config (default ``"auto"``)."""
        return str(self.raw.get("backend_mode", "auto"))

    @property
    def active(self) -> bool:
        """True when status is ``"active"`` or ``"ready"``."""
        return self.status in ("active", "ready")

    @property
    def upstream_chat_url(self) -> str:
        """Return the upstream OpenAI-compat ``/chat/completions`` URL."""
        if not self.base_url:
            raise ValueError(f"profile {self.alias} has no base_url")
        return self.base_url.rstrip("/") + "/chat/completions"

    @property
    def upstream_models_url(self) -> str:
        """Return the upstream ``/models`` URL."""
        if not self.base_url:
            raise ValueError(f"profile {self.alias} has no base_url")
        return self.base_url.rstrip("/") + "/models"


class ProfileRegistry:
    """In-memory index of ServingProfile entries keyed by alias."""

    def __init__(self, config: ServeConfig):
        self.config = config
        self._profiles = {
            alias: ServingProfile(
                alias=alias,
                engine=str(profile.get("engine", "unknown")),
                base_url=profile.get("base_url"),
                status=str(profile.get("status", "active")),
                raw=profile,
            )
            for alias, profile in config.profiles.items()
        }

    def list(self) -> list[ServingProfile]:
        """Return all configured profiles."""
        return list(self._profiles.values())

    def get(self, alias: str) -> ServingProfile:
        """Look up a profile by alias; falls back to the default profile."""
        if alias in self._profiles:
            return self._profiles[alias]
        for profile in self._profiles.values():
            if profile.raw.get("default"):
                return profile
        raise KeyError(f"unknown model alias: {alias}")

    def openai_models(self) -> dict[str, Any]:
        """Emit the OpenAI ``/v1/models`` envelope (filtered by active flag)."""
        expose_planned = bool(
            self.config.raw.get("server", {}).get("expose_planned_models", False)
        )
        return {
            "object": "list",
            "data": [
                {
                    "id": profile.alias,
                    "object": "model",
                    "owned_by": "pheno-serve-dev",
                    "engine": profile.engine,
                    "status": profile.status,
                }
                for profile in self.list()
                if profile.active or expose_planned
            ],
        }
