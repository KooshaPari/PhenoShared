# Tests for beads.agileplus_adapter.config — AgilePlus runtime-config loader.
#
# v0.12 WBS-PERT-100 task 27 (Phase 2 — AgilePlus config schema) ac_v1.

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from beads.agileplus_adapter.config import (
    is_enabled,
    load_config,
    resolve_token,
)


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    return tmp_path / "config.json"


class TestLoadConfig:
    def test_default_when_file_missing(self, tmp_path: Path) -> None:
        config = load_config(tmp_path / "missing.json")
        assert config["schema_version"] == 1
        assert config["host"] == "127.0.0.1"
        assert config["port"] == 8080
        assert config["base_url"] is None
        assert config["api_token_env"] == "AGILEPLUS_API_TOKEN"
        assert config["timeout"] == 5.0
        assert config["work_package_id"] == 1
        assert config["enabled"] is False
        assert config["session_id"] is None

    def test_file_load(self, tmp_config: Path) -> None:
        tmp_config.write_text(
            '{"host": "agileplus.test", "port": 9090, '
            '"enabled": true, "session_id": "default-session"}'
        )
        config = load_config(tmp_config)
        assert config["host"] == "agileplus.test"
        assert config["port"] == 9090
        assert config["enabled"] is True
        assert config["session_id"] == "default-session"
        # Defaults still apply for omitted keys.
        assert config["api_token_env"] == "AGILEPLUS_API_TOKEN"
        assert config["work_package_id"] == 1

    def test_partial_config_merges_with_defaults(self, tmp_config: Path) -> None:
        tmp_config.write_text('{"port": 9999}')
        config = load_config(tmp_config)
        assert config["port"] == 9999
        # All other keys still come from defaults.
        assert config["host"] == "127.0.0.1"
        assert config["enabled"] is False

    def test_empty_file_returns_defaults(self, tmp_config: Path) -> None:
        tmp_config.write_text("")
        config = load_config(tmp_config)
        # Empty file = treat as missing → defaults (consistent with
        # pheno.trace_store.config.load_config which treats empty YAML
        # the same way).
        assert config["host"] == "127.0.0.1"
        assert config["enabled"] is False

    def test_non_dict_returns_defaults(self, tmp_config: Path) -> None:
        tmp_config.write_text("[1, 2, 3]")
        config = load_config(tmp_config)
        # Non-dict → ignore contents, keep defaults.
        assert config == {
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

    def test_invalid_json_raises(self, tmp_config: Path) -> None:
        tmp_config.write_text("{ not valid json")
        with pytest.raises(ValueError, match="not valid JSON"):
            load_config(tmp_config)

    def test_unsupported_schema_version_raises(self, tmp_config: Path) -> None:
        tmp_config.write_text('{"schema_version": 99}')
        with pytest.raises(ValueError, match="schema_version=99 not in"):
            load_config(tmp_config)

    def test_default_path_is_dot_agileplus(self, tmp_path: Path) -> None:
        from beads.agileplus_adapter.agileplus_adapter import DEFAULT_CONFIG_PATH

        assert Path.home() / ".agileplus" / "config.json" == DEFAULT_CONFIG_PATH


class TestResolveToken:
    def test_resolves_from_named_env_var(self) -> None:
        config = {"api_token_env": "MY_CUSTOM_AGILEPLUS_VAR"}
        with patch.dict(os.environ, {"MY_CUSTOM_AGILEPLUS_VAR": "secret-xyz"}):
            assert resolve_token(config) == "secret-xyz"

    def test_returns_none_when_env_var_unset(self) -> None:
        config = {"api_token_env": "MY_UNSET_VAR"}
        env = {k: v for k, v in os.environ.items() if k != "MY_UNSET_VAR"}
        with patch.dict(os.environ, env, clear=True):
            assert resolve_token(config) is None

    def test_defaults_to_agileplus_api_token_when_key_missing(self) -> None:
        config: dict = {}
        with patch.dict(os.environ, {"AGILEPLUS_API_TOKEN": "default-token"}):
            assert resolve_token(config) == "default-token"


class TestIsEnabled:
    def test_enabled_true(self) -> None:
        assert is_enabled({"enabled": True}) is True

    def test_enabled_false(self) -> None:
        assert is_enabled({"enabled": False}) is False

    def test_missing_key_defaults_false(self) -> None:
        assert is_enabled({}) is False
