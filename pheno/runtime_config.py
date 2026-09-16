"""pheno.runtime_config — lazy loader for ``config/pheno_runtime.yaml``.

The pheno-harness runtime has several adapters (Tracera, evidence,
trace bridges) that benefit from a single config source-of-truth. This
module exposes a typed accessor that:

  - resolves the config path (default: ``config/pheno_runtime.yaml``)
  - parses the YAML once per process (cached)
  - validates ``schema_version`` against the supported range
  - exposes ``.tracera``, ``.evidence``, ``.trace_bridges`` accessors
  - falls back to env vars when YAML values are null

Env vars always win over YAML if BOTH are set, so the deployment
override path stays simple.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from pheno.paths import CONFIG_DIR

SUPPORTED_SCHEMA_VERSIONS = (1, 2)
DEFAULT_CONFIG_PATH = CONFIG_DIR / "pheno_runtime.yaml"

# Environment names recognized by `pheno.runtime_config.active_environment`.
# The active environment is selected by the `PHENO_ENV` env var; when unset
# the loader falls back to "dev". Used by `trace_bridges.env_overrides`
# and `trace_bridges.cohort_policies`.
KNOWN_ENVIRONMENTS = ("dev", "staging", "prod")
DEFAULT_ENVIRONMENT = "dev"


def _env_value(canonical: str, legacy: str, default: str) -> str:
    """Resolve Tracera destination config before the Grapheon fallback."""
    return os.environ.get(canonical) or os.environ.get(legacy) or default


@dataclass(frozen=True)
class TraceraConfig:
    """Typed view of the ``tracera:`` block."""

    host: str
    port: int
    base_url: str | None
    api_token: str | None
    enabled: bool
    flush_interval_s: int
    batch_size: int
    retry_max: int
    health_check_on_init: bool
    timeout_s: int

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> TraceraConfig:
        return cls(
            host=str(raw.get("host") or _env_value("TRACERA_HOST", "GRAPHEON_HOST", "127.0.0.1")),
            port=int(raw.get("port") or _env_value("TRACERA_PORT", "GRAPHEON_PORT", "8080")),
            base_url=raw.get("base_url") or os.environ.get("TRACERA_BASE_URL") or os.environ.get("GRAPHEON_BASE_URL"),
            api_token=raw.get("api_token") or os.environ.get("TRACERA_API_TOKEN") or os.environ.get("GRAPHEON_API_TOKEN"),
            enabled=bool(raw.get("enabled", False)),
            flush_interval_s=int(raw.get("flush_interval_s", 30)),
            batch_size=int(raw.get("batch_size", 100)),
            retry_max=int(raw.get("retry_max", 3)),
            health_check_on_init=bool(raw.get("health_check_on_init", True)),
            timeout_s=int(raw.get("timeout_s", 10)),
        )


@dataclass(frozen=True)
class EvidenceConfig:
    """Typed view of the ``evidence:`` block."""

    base_url: str | None
    rate_limit_per_min: int
    circuit_breaker_threshold: int

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> EvidenceConfig:
        return cls(
            base_url=raw.get("base_url") or os.environ.get("EVIDENCE_BASE_URL"),
            rate_limit_per_min=int(raw.get("rate_limit_per_min", 60)),
            circuit_breaker_threshold=int(raw.get("circuit_breaker_threshold", 5)),
        )


@dataclass(frozen=True)
class TraceBridgesConfig:
    """Typed view of the ``trace_bridges:`` block."""

    dual_write: bool
    dual_write_default: bool
    dual_write_sample_rate: float
    include_kinds: list[str]
    cohort_policies: dict[str, str]
    env_overrides: dict[str, str]
    active_environment: str

    @classmethod
    def from_raw(
        cls, raw: dict[str, Any], *, active_environment: str | None = None
    ) -> TraceBridgesConfig:
        explicit_dual_write = raw.get("dual_write")
        # Resolve dual_write_default with backward-compatible env vars.
        # `TRACERA_DUAL_WRITE` was the legacy name (no _DEFAULT suffix);
        # we honor both for callers that haven't migrated.
        env_default = (
            os.environ.get("TRACERA_DUAL_WRITE_DEFAULT", "")
            or os.environ.get("TRACERA_DUAL_WRITE", "")
        ).lower() in ("1", "true", "yes", "on")
        default_dual_write = bool(raw.get("dual_write_default", False) or env_default)
        sample_rate_raw = raw.get(
            "dual_write_sample_rate",
            os.environ.get("TRACERA_DUAL_WRITE_SAMPLE_RATE", "1.0"),
        )
        try:
            sample_rate = float(sample_rate_raw)
        except (TypeError, ValueError):
            sample_rate = 1.0
        # Clamp to valid range.
        sample_rate = max(0.0, min(1.0, sample_rate))
        cohort = dict(raw.get("cohort_policies", {}) or {})
        # Fill in canonical keys so consumers can rely on their presence.
        for env_name in KNOWN_ENVIRONMENTS:
            cohort.setdefault(env_name, "off")
        env_overrides = dict(raw.get("env_overrides", {}) or {})
        return cls(
            dual_write=bool(explicit_dual_write)
            if explicit_dual_write is not None
            else default_dual_write,
            dual_write_default=default_dual_write,
            dual_write_sample_rate=sample_rate,
            include_kinds=list(raw.get("include_kinds", [])),
            cohort_policies=cohort,
            env_overrides=env_overrides,
            active_environment=active_environment
            or os.environ.get("PHENO_ENV", DEFAULT_ENVIRONMENT),
        )


@dataclass(frozen=True)
class RuntimeConfig:
    """Top-level config view."""

    path: Path
    schema_version: int
    tracera: TraceraConfig
    evidence: EvidenceConfig
    trace_bridges: TraceBridgesConfig


def active_environment() -> str:
    """Return the active PHENO_ENV (defaults to "dev").

    Recognized environments: "dev", "staging", "prod". When the env var
    is unset or unknown, returns the default ("dev").
    """
    env = os.environ.get("PHENO_ENV", DEFAULT_ENVIRONMENT)
    return env if env in KNOWN_ENVIRONMENTS else DEFAULT_ENVIRONMENT


@lru_cache(maxsize=1)
def _load(path_str: str) -> RuntimeConfig:
    """Parse the config once per process (cached on the path string)."""
    path = Path(path_str)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    version = int(raw.get("schema_version", 1))
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"pheno_runtime.yaml schema_version={version} not in "
            f"supported set {SUPPORTED_SCHEMA_VERSIONS}. "
            f"Update pheno.runtime_config.SUPPORTED_SCHEMA_VERSIONS."
        )
    env_name = active_environment()
    return RuntimeConfig(
        path=path,
        schema_version=version,
        tracera=TraceraConfig.from_raw(raw.get("tracera", {})),
        evidence=EvidenceConfig.from_raw(raw.get("evidence", {})),
        trace_bridges=TraceBridgesConfig.from_raw(
            raw.get("trace_bridges", {}),
            active_environment=env_name,
        ),
    )


def load_config(path: str | Path | None = None) -> RuntimeConfig:
    """Load (and cache) the runtime config.

    Args:
        path: explicit config path; defaults to
            ``config/pheno_runtime.yaml`` at the repo root.
    """
    target = str(path) if path else str(DEFAULT_CONFIG_PATH)
    return _load(target)


def reload() -> RuntimeConfig:
    """Force a fresh load (e.g. after editing the config file)."""
    _load.cache_clear()
    return load_config()
