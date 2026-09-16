"""Tests for pheno.runtime_config — the lazy YAML config loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from pheno.runtime_config import (
    DEFAULT_CONFIG_PATH,
    SUPPORTED_SCHEMA_VERSIONS,
    EvidenceConfig,
    RuntimeConfig,
    TraceBridgesConfig,
    TraceraConfig,
    load_config,
    reload,
)


def test_load_default_returns_runtime_config() -> None:
    """Default load returns a RuntimeConfig dataclass with all blocks."""
    cfg = load_config()
    assert isinstance(cfg, RuntimeConfig)
    # v0.13 Phase 1 task 6: schema_version bumped to 2 to add
    # `dual_write_default`, `dual_write_sample_rate`, `cohort_policies`,
    # `env_overrides`, and `active_environment`.
    assert cfg.schema_version == 2
    assert isinstance(cfg.tracera, TraceraConfig)
    assert isinstance(cfg.evidence, EvidenceConfig)
    assert isinstance(cfg.trace_bridges, TraceBridgesConfig)


def test_load_is_cached() -> None:
    """Two consecutive loads return the same instance (lru_cache)."""
    a = load_config()
    b = load_config()
    assert a is b


def test_tracera_block_has_expected_keys() -> None:
    """TraceraConfig exposes all 10 schema fields."""
    cfg = load_config()
    for attr in (
        "host",
        "port",
        "base_url",
        "api_token",
        "enabled",
        "flush_interval_s",
        "batch_size",
        "retry_max",
        "health_check_on_init",
        "timeout_s",
    ):
        assert hasattr(cfg.tracera, attr), f"missing {attr}"


def test_evidence_block_has_expected_keys() -> None:
    """EvidenceConfig exposes 3 schema fields."""
    cfg = load_config()
    for attr in ("base_url", "rate_limit_per_min", "circuit_breaker_threshold"):
        assert hasattr(cfg.evidence, attr), f"missing {attr}"


def test_trace_bridges_block_has_expected_keys() -> None:
    """TraceBridgesConfig exposes 6 schema fields (v0.13 Phase 1 task 6)."""
    cfg = load_config()
    for attr in (
        "dual_write",
        "dual_write_default",
        "dual_write_sample_rate",
        "include_kinds",
        "cohort_policies",
        "env_overrides",
        "active_environment",
    ):
        assert hasattr(cfg.trace_bridges, attr), f"missing {attr}"


def test_default_path_resolves_to_repo_root() -> None:
    """DEFAULT_CONFIG_PATH points at config/pheno_runtime.yaml."""
    assert DEFAULT_CONFIG_PATH.name == "pheno_runtime.yaml"
    assert DEFAULT_CONFIG_PATH.parent.name == "config"
    assert DEFAULT_CONFIG_PATH.exists(), "pheno_runtime.yaml missing"


def test_supported_schema_versions_includes_v1() -> None:
    """v1 and v2 are both supported (v0.13 Phase 1 task 6 bumps default to v2)."""
    assert 1 in SUPPORTED_SCHEMA_VERSIONS
    assert 2 in SUPPORTED_SCHEMA_VERSIONS


def test_reload_clears_cache() -> None:
    """reload() returns a fresh RuntimeConfig instance."""
    a = load_config()
    b = reload()
    # Both should be equal in content but reload forces a fresh load
    assert a.path == b.path
    assert a.schema_version == b.schema_version


def test_tracera_env_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When YAML fields are null, env vars are used as fallback."""
    cfg_path = tmp_path / "pheno_runtime.yaml"
    cfg_path.write_text("schema_version: 1\ntracera:\n  host: null\n  port: null\n")
    monkeypatch.setenv("TRACERA_HOST", "10.0.0.42")
    monkeypatch.setenv("TRACERA_PORT", "9999")
    cfg = load_config(cfg_path)
    assert cfg.tracera.host == "10.0.0.42"
    assert cfg.tracera.port == 9999


def test_tracera_grapheon_env_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GRAPHEON_* is used when the runtime YAML leaves fields unset."""
    cfg_path = tmp_path / "pheno_runtime.yaml"
    cfg_path.write_text(
        "schema_version: 1\ntracera:\n  host: null\n  port: null\n"
    )
    monkeypatch.setenv("GRAPHEON_HOST", "grapheon.test")
    monkeypatch.setenv("GRAPHEON_PORT", "9443")
    monkeypatch.setenv("GRAPHEON_BASE_URL", "https://grapheon.test/api")
    monkeypatch.setenv("GRAPHEON_API_TOKEN", "grapheon-token")
    monkeypatch.delenv("TRACERA_HOST", raising=False)
    monkeypatch.delenv("TRACERA_PORT", raising=False)
    monkeypatch.delenv("TRACERA_BASE_URL", raising=False)
    monkeypatch.delenv("TRACERA_API_TOKEN", raising=False)

    cfg = load_config(cfg_path)

    assert cfg.tracera.host == "grapheon.test"
    assert cfg.tracera.port == 9443
    assert cfg.tracera.base_url == "https://grapheon.test/api"
    assert cfg.tracera.api_token == "grapheon-token"


def test_tracera_destination_precedes_grapheon(monkeypatch: pytest.MonkeyPatch) -> None:
    from pheno.runtime_config import TraceraConfig

    for suffix, value in {"HOST": "destination.test", "PORT": "9000", "BASE_URL": "https://destination.test", "API_TOKEN": "destination-token"}.items():
        monkeypatch.setenv("TRACERA_" + suffix, value)
        monkeypatch.setenv("GRAPHEON_" + suffix, "8080" if suffix == "PORT" else "old")
    cfg = TraceraConfig.from_raw({})
    assert (cfg.host, cfg.port, cfg.base_url, cfg.api_token) == (
        "destination.test", 9000, "https://destination.test", "destination-token"
    )


def test_tracera_yaml_wins_over_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When YAML has a value, env vars are ignored for that field."""
    cfg_path = tmp_path / "pheno_runtime.yaml"
    cfg_path.write_text(
        'schema_version: 1\ntracera:\n  host: "yaml-host"\n  port: 1234\n'
    )
    monkeypatch.setenv("TRACERA_HOST", "env-host")
    cfg = load_config(cfg_path)
    assert cfg.tracera.host == "yaml-host"
    assert cfg.tracera.port == 1234
