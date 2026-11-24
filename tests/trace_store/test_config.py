# Tests for trace_store.config — Tracera runtime-config loader.
#
# v0.12 WBS-PERT-100 task 12 (Phase 1 — Tracera adapter config) ac_v1.

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from pheno.trace_store.config import load_config, resolve_token


@pytest.fixture
def tmp_yaml(tmp_path: Path) -> Path:
    return tmp_path / "tracera.yaml"


class TestLoadConfig:
    def test_default_when_file_missing(self, tmp_path: Path) -> None:
        # No file written; load should return the default config.
        config = load_config(tmp_path / "missing.yaml")
        assert config["host"] == "127.0.0.1"
        assert config["port"] == 8080
        assert config["base_url"] is None
        assert config["api_token_env"] == "TRACERA_API_TOKEN"
        assert config["timeout"] == 5.0
        assert config["batch_size"] == 32
        assert config["enabled"] is False
        assert config["session_id"] is None

    def test_file_load(self, tmp_yaml: Path) -> None:
        tmp_yaml.write_text(
            "host: tracera.test\n"
            "port: 9090\n"
            "enabled: true\n"
            "session_id: default-session\n"
        )
        config = load_config(tmp_yaml)
        assert config["host"] == "tracera.test"
        assert config["port"] == 9090
        assert config["enabled"] is True
        assert config["session_id"] == "default-session"
        # Defaults still apply for omitted keys.
        assert config["api_token_env"] == "TRACERA_API_TOKEN"
        assert config["batch_size"] == 32

    def test_partial_config_merges_with_defaults(self, tmp_yaml: Path) -> None:
        tmp_yaml.write_text("port: 9999\n")
        config = load_config(tmp_yaml)
        assert config["port"] == 9999
        # All other keys still come from defaults.
        assert config["host"] == "127.0.0.1"
        assert config["enabled"] is False
        assert config["api_token_env"] == "TRACERA_API_TOKEN"

    def test_empty_yaml_returns_defaults(self, tmp_yaml: Path) -> None:
        tmp_yaml.write_text("")
        config = load_config(tmp_yaml)
        # Empty yaml → safe_load returns None → defaults used.
        assert config == {
            "host": "127.0.0.1",
            "port": 8080,
            "base_url": None,
            "api_token_env": "TRACERA_API_TOKEN",
            "timeout": 5.0,
            "batch_size": 32,
            "enabled": False,
            "session_id": None,
        }

    def test_non_dict_yaml_returns_defaults(self, tmp_yaml: Path) -> None:
        # Non-dict top-level yaml should NOT crash; fall back to defaults.
        tmp_yaml.write_text("- item1\n- item2\n")
        config = load_config(tmp_yaml)
        assert config["host"] == "127.0.0.1"
        assert config["port"] == 8080


class TestResolveToken:
    def test_tracera_token_precedes_grapheon_fallback(self) -> None:
        """The successor token wins when both deployments are configured."""
        config = {"api_token_env": "TRACERA_API_TOKEN"}
        with patch.dict(
            os.environ,
            {"GRAPHEON_API_TOKEN": "canonical", "TRACERA_API_TOKEN": "legacy"},
        ):
            assert resolve_token(config) == "legacy"

    def test_resolves_from_named_env_var(self) -> None:
        config = {"api_token_env": "MY_CUSTOM_TOKEN_VAR"}
        with patch.dict(os.environ, {"MY_CUSTOM_TOKEN_VAR": "secret-xyz"}):
            assert resolve_token(config) == "secret-xyz"

    def test_returns_none_when_env_var_unset(self) -> None:
        config = {"api_token_env": "MY_UNSET_VAR"}
        env = {k: v for k, v in os.environ.items() if k != "MY_UNSET_VAR"}
        with patch.dict(os.environ, env, clear=True):
            assert resolve_token(config) is None

    def test_defaults_to_tracera_api_token_when_key_missing(self) -> None:
        # No api_token_env in config → fall back to default env var name.
        config: dict = {}
        with patch.dict(os.environ, {"TRACERA_API_TOKEN": "default-token"}):
            assert resolve_token(config) == "default-token"

    def test_default_env_var_unset_returns_none(self) -> None:
        config: dict = {}
        env = {k: v for k, v in os.environ.items() if k != "TRACERA_API_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            assert resolve_token(config) is None
