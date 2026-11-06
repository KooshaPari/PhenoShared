from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str
    default_model: str
    variants: dict[str, str] = field(default_factory=dict)
    max_tokens: int = 4096
    timeout_s: float = 120.0

    @property
    def api_key(self) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(f"Provider {self.name!r}: env var {self.api_key_env} is not set")
        return key


@dataclass
class Config:
    providers: dict[str, ProviderConfig]
    default_provider: str = "minimax"
    default_variant: str = "highspeed"
    monthly_cost_cap_usd: float | None = None
    cache_ttl_seconds: float = 0.0  # 0 = disabled; cache only applies at temp=0


DEFAULT_CONFIG_PATHS = [
    Path.home() / ".cheap-llm" / "config.toml",
    Path.cwd() / "cheap-llm.toml",
]


def load(path: Path | None = None) -> Config:
    if path is None:
        for p in DEFAULT_CONFIG_PATHS:
            if p.exists():
                path = p
                break
    if path is None or not path.exists():
        return _defaults()
    data = tomllib.loads(path.read_text())
    providers_raw = data.get("providers", {})
    if not isinstance(providers_raw, dict):
        raise ValueError(f"{path}: [providers] must be a table")
    providers = {}
    for name, cfg in providers_raw.items():
        if not isinstance(cfg, dict):
            raise ValueError(f"{path}: [providers.{name}] must be a table")
        required = {"base_url", "api_key_env", "default_model"}
        missing = required - cfg.keys()
        if missing:
            raise ValueError(f"{path}: [providers.{name}] missing required keys: {sorted(missing)}")
        try:
            providers[name] = ProviderConfig(name=name, **cfg)
        except TypeError as e:
            raise ValueError(f"{path}: [providers.{name}]: {e}") from e
    return Config(
        providers=providers or _defaults().providers,
        default_provider=data.get("default_provider", "minimax"),
        default_variant=data.get("default_variant", "highspeed"),
        monthly_cost_cap_usd=data.get("monthly_cost_cap_usd"),
        cache_ttl_seconds=data.get("cache_ttl_seconds", 0.0),
    )


def _defaults() -> Config:
    return Config(
        providers={
            "minimax": ProviderConfig(
                name="minimax",
                base_url="https://api.minimax.io/v1",
                api_key_env="MINIMAX_API_KEY",
                default_model="MiniMax-M2.7-highspeed",
                variants={
                    "base": "MiniMax-M2.7",
                    "highspeed": "MiniMax-M2.7-highspeed",
                    # No dedicated codex variant; M2.7 was trained with strong code skills.
                    "codex": "MiniMax-M2.7",
                },
            ),
            "kimi": ProviderConfig(
                name="kimi",
                base_url="https://api.moonshot.ai/v1",
                api_key_env="MOONSHOT_API_KEY",
                default_model="kimi-k2-turbo-preview",
                variants={
                    "turbo": "kimi-k2-turbo-preview",
                },
            ),
            "fireworks": ProviderConfig(
                name="fireworks",
                base_url="https://api.fireworks.ai/inference/v1",
                api_key_env="FIREWORKS_API_KEY",
                default_model="accounts/fireworks/models/minimax-m2p7",
                variants={
                    "minimax": "accounts/fireworks/models/minimax-m2p7",
                    "kimi": "accounts/fireworks/models/kimi-k2-instruct",
                },
            ),
        },
    )
