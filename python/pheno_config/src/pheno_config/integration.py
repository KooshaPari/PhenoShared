from __future__ import annotations

import logging
from typing import Literal

from pheno.config.core import Config


class MorphIntegrationSettings(Config):
    sandbox_enabled: bool = True
    allow_symlinks: bool = False
    use_sdk_analytics: bool = True
    analytics_radon_enabled: bool = False
    analytics_grimp_enabled: bool = False
    use_sdk_secret_scan: bool = True
    secret_scan_strict_mode: bool = True
    secret_scan_entropy_threshold: float = 4.5
    secret_scan_max_results: int = 1000
    use_sdk_logging: bool = True
    use_sdk_semantic_search: bool = True
    use_sdk_code_analysis: bool = True
    use_sdk_embeddings: bool = True
    cache_strategy: str = "lru"
    cache_max_entries: int = 1024
    cache_ttl_seconds: float | None = 3600
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_base_url: str | None = None
    embedding_cache_dir: str | None = None
    logging_format: str = "json"
    logging_level: str = "INFO"
    logging_enable_console: bool = True
    logging_enable_file: bool = False
    logging_file_path: str | None = None
    logging_max_file_size: int = 10 * 1024 * 1024
    logging_backup_count: int = 5
    logging_sinks: tuple[str, ...] = ("stdout",)
    workspace_dir: str | None = None
    network_timeout_seconds: float = 60.0
    retry_max_attempts: int = 3
    retry_backoff_factor: float = 1.5


class RouterIntegrationSettings(Config):
    sandbox_enabled: bool = False
    logging_format: str = "json"
    use_sdk_logging: bool = False
    logging_sinks: tuple[str, ...] = ("stdout",)
    logging_level: str = "INFO"
    analytics_radon_enabled: bool = False
    analytics_grimp_enabled: bool = False
    cache_strategy: str = "lru"
    vector_search_provider: str = "vertex"
    rate_limit_enabled: bool = True


def _load_legacy_morph_env() -> dict[str, object]:
    raw = MorphIntegrationSettings.from_env(prefix="MORPH_", _return_dict=True)  # type: ignore[arg-type]
    if not raw:
        return {}
    # Let Pydantic handle coercion
    parsed = MorphIntegrationSettings(**raw)
    logging.getLogger(__name__).warning(
        "Detected deprecated MORPH_* environment variables. Please migrate to PHENO_MORPH_* equivalents.",
    )
    return parsed.model_dump()


def get_morph_settings(*, env_prefix: str = "PHENO") -> MorphIntegrationSettings:
    base = MorphIntegrationSettings.load(env_prefix=f"{env_prefix}_MORPH_")
    legacy = _load_legacy_morph_env()
    if legacy:
        base = base.model_copy(update={k: legacy[k] for k in legacy})
    return base


def get_router_settings(*, env_prefix: str = "PHENO") -> RouterIntegrationSettings:
    return RouterIntegrationSettings.load(env_prefix=f"{env_prefix}_ROUTER_")


def get_integration_settings(service: Literal["morph", "router"], *, env_prefix: str = "PHENO"):
    if service == "morph":
        return get_morph_settings(env_prefix=env_prefix)
    if service == "router":
        return get_router_settings(env_prefix=env_prefix)
    raise ValueError(f"Unsupported integration service: {service}")
