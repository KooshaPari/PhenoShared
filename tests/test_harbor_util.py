"""Comprehensive unit tests for pheno.harbor_util.

Covers: harbor_exe, _load_forge_creds, litellm_model, omniroute_env,
fireworks_env, local_env, route_env.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from pheno.harbor_util import (
    _load_forge_creds,
    fireworks_env,
    harbor_exe,
    litellm_model,
    local_env,
    omniroute_env,
    route_env,
)

# ---------------------------------------------------------------------------
# harbor_exe tests
# ---------------------------------------------------------------------------


class TestHarborExe:
    def test_fallback_when_appdata_missing(self) -> None:
        """When APPDATA doesn't exist, returns 'harbor'."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("APPDATA", None)
            result = harbor_exe()
            assert result == "harbor"

    def test_fallback_when_appdata_path_not_exists(self) -> None:
        """When APPDATA exists but harbor.exe is not there, returns 'harbor'."""
        with patch.dict(os.environ, {"APPDATA": "/nonexistent/path"}):
            result = harbor_exe()
            assert result == "harbor"

    def test_returns_appdata_path_when_exists(self, tmp_path: Path) -> None:
        """When the harbor.exe exists under APPDATA, returns that path."""
        harbor_dir = tmp_path / "Python" / "Python314" / "Scripts"
        harbor_dir.mkdir(parents=True)
        harbor_exe_path = harbor_dir / "harbor.exe"
        harbor_exe_path.write_text("", encoding="utf-8")
        with patch.dict(os.environ, {"APPDATA": str(tmp_path)}):
            result = harbor_exe()
            assert str(harbor_exe_path) in result


# ---------------------------------------------------------------------------
# _load_forge_creds tests
# ---------------------------------------------------------------------------


class TestLoadForgeCreds:
    def test_no_creds_file(self) -> None:
        with patch("pheno.harbor_util.Path.home") as mock_home:
            mock_home.return_value = Path("/nonexistent/home")
            result = _load_forge_creds()
            assert result == []

    def test_creds_file_exists(self, tmp_path: Path) -> None:
        creds = [{"id": "openai", "auth_details": {"api_key": "sk-test"}}]
        forge_dir = tmp_path / "forge"
        forge_dir.mkdir()
        creds_file = forge_dir / ".credentials.json"
        creds_file.write_text(json.dumps(creds), encoding="utf-8")
        with patch("pheno.harbor_util.Path.home", return_value=tmp_path):
            result = _load_forge_creds()
        assert result == creds
        assert result[0]["id"] == "openai"

    def test_creds_file_invalid_json(self, tmp_path: Path) -> None:
        forge_dir = tmp_path / "forge"
        forge_dir.mkdir()
        creds_file = forge_dir / ".credentials.json"
        creds_file.write_text("not json {{{", encoding="utf-8")
        with patch("pheno.harbor_util.Path.home", return_value=tmp_path):
            with pytest.raises(json.JSONDecodeError):
                _load_forge_creds()


# ---------------------------------------------------------------------------
# litellm_model tests
# ---------------------------------------------------------------------------


class TestLitellmModel:
    def test_direct_with_fireworks_accounts(self) -> None:
        result = litellm_model(
            "accounts/123/models/mymodel", direct=True
        )
        assert result == "fireworks_ai/accounts/123/models/mymodel"

    def test_direct_with_custom_model(self) -> None:
        result = litellm_model("gpt-4", direct=True, direct_model="custom/model")
        assert result == "custom/model"

    def test_direct_without_accounts_prefix(self) -> None:
        result = litellm_model("gpt-4", direct=True)
        assert result == "gpt-4"

    def test_non_direct_with_slash(self) -> None:
        result = litellm_model("provider/model")
        assert result == "openai/provider/model"

    def test_non_direct_without_slash(self) -> None:
        result = litellm_model("gpt-4")
        assert result == "openai/gpt-4"


# ---------------------------------------------------------------------------
# omniroute_env tests
# ---------------------------------------------------------------------------


class TestOmnirouteEnv:
    def test_sets_default_env_vars(self) -> None:
        with patch.dict(os.environ, {"HOME": "/tmp"}, clear=False):
            env = omniroute_env()
        assert env["OPENAI_BASE_URL"] == "http://127.0.0.1:20128/v1"
        assert env["PYTHONIOENCODING"] == "utf-8"
        assert env["PYTHONUTF8"] == "1"

    def test_preserves_existing_openai_key(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "existing-key"}, clear=False):
            env = omniroute_env()
        assert env["OPENAI_API_KEY"] == "existing-key"

    def test_preserves_existing_base_url(self) -> None:
        with patch.dict(
            os.environ,
            {"OPENAI_BASE_URL": "http://custom:9999/v1"},
            clear=False,
        ):
            env = omniroute_env()
        assert env["OPENAI_BASE_URL"] == "http://custom:9999/v1"

    def test_loads_key_from_forge_creds(self, tmp_path: Path) -> None:
        creds = [
            {
                "id": "openai_compatible",
                "auth_details": {"api_key": "from-creds"},
            }
        ]
        forge_dir = tmp_path / "forge"
        forge_dir.mkdir()
        creds_file = forge_dir / ".credentials.json"
        creds_file.write_text(json.dumps(creds), encoding="utf-8")
        with (
            patch.dict(os.environ, {}, clear=False),
            patch("pheno.harbor_util.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("OPENAI_API_KEY", None)
            env = omniroute_env()
        assert env["OPENAI_API_KEY"] == "from-creds"

    def test_loads_key_from_responses_compatible(self, tmp_path: Path) -> None:
        creds = [
            {
                "id": "openai_responses_compatible",
                "auth_details": {"api_key": "resp-key"},
            }
        ]
        forge_dir = tmp_path / "forge"
        forge_dir.mkdir()
        creds_file = forge_dir / ".credentials.json"
        creds_file.write_text(json.dumps(creds), encoding="utf-8")
        with (
            patch.dict(os.environ, {}, clear=False),
            patch("pheno.harbor_util.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("OPENAI_API_KEY", None)
            env = omniroute_env()
        assert env["OPENAI_API_KEY"] == "resp-key"

    def test_no_creds_no_key(self, tmp_path: Path) -> None:
        with (
            patch.dict(os.environ, {}, clear=False),
            patch("pheno.harbor_util.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("OPENAI_API_KEY", None)
            env = omniroute_env()
        assert "OPENAI_API_KEY" not in env

    def test_creds_without_matching_id(self, tmp_path: Path) -> None:
        creds = [{"id": "unrelated", "auth_details": {"api_key": "nope"}}]
        forge_dir = tmp_path / "forge"
        forge_dir.mkdir()
        creds_file = forge_dir / ".credentials.json"
        creds_file.write_text(json.dumps(creds), encoding="utf-8")
        with (
            patch.dict(os.environ, {}, clear=False),
            patch("pheno.harbor_util.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("OPENAI_API_KEY", None)
            env = omniroute_env()
        assert "OPENAI_API_KEY" not in env

    def test_creds_with_no_auth_details(self, tmp_path: Path) -> None:
        creds = [{"id": "openai_compatible"}]
        forge_dir = tmp_path / "forge"
        forge_dir.mkdir()
        creds_file = forge_dir / ".credentials.json"
        creds_file.write_text(json.dumps(creds), encoding="utf-8")
        with (
            patch.dict(os.environ, {}, clear=False),
            patch("pheno.harbor_util.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("OPENAI_API_KEY", None)
            env = omniroute_env()
        assert "OPENAI_API_KEY" not in env


# ---------------------------------------------------------------------------
# fireworks_env tests
# ---------------------------------------------------------------------------


class TestFireworksEnv:
    def test_sets_fireworks_base_url(self) -> None:
        env = fireworks_env()
        assert env["OPENAI_BASE_URL"] == "https://api.fireworks.ai/inference/v1"

    def test_uses_existing_fireworks_key(self) -> None:
        with patch.dict(
            os.environ, {"FIREWORKS_AI_API_KEY": "fw-key"}, clear=False
        ):
            env = fireworks_env()
        assert env["FIREWORKS_AI_API_KEY"] == "fw-key"
        assert env["OPENAI_API_KEY"] == "fw-key"

    def test_uses_existing_openai_key_fallback(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "oai-key"}, clear=False):
            os.environ.pop("FIREWORKS_AI_API_KEY", None)
            env = fireworks_env()
        assert env["OPENAI_API_KEY"] == "oai-key"
        assert env["FIREWORKS_AI_API_KEY"] == "oai-key"

    def test_loads_key_from_forge_creds(self, tmp_path: Path) -> None:
        creds = [
            {
                "id": "fireworks-ai-firepass",
                "auth_details": {"api_key": "fw-cred-key"},
            }
        ]
        forge_dir = tmp_path / "forge"
        forge_dir.mkdir()
        creds_file = forge_dir / ".credentials.json"
        creds_file.write_text(json.dumps(creds), encoding="utf-8")
        with (
            patch.dict(os.environ, {}, clear=False),
            patch("pheno.harbor_util.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("FIREWORKS_AI_API_KEY", None)
            os.environ.pop("OPENAI_API_KEY", None)
            env = fireworks_env()
        assert env["OPENAI_API_KEY"] == "fw-cred-key"
        assert env["FIREWORKS_AI_API_KEY"] == "fw-cred-key"

    def test_custom_credential_id(self, tmp_path: Path) -> None:
        creds = [
            {
                "id": "my-custom-id",
                "auth_details": {"api_key": "custom-key"},
            }
        ]
        forge_dir = tmp_path / "forge"
        forge_dir.mkdir()
        creds_file = forge_dir / ".credentials.json"
        creds_file.write_text(json.dumps(creds), encoding="utf-8")
        with (
            patch.dict(os.environ, {}, clear=False),
            patch("pheno.harbor_util.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("FIREWORKS_AI_API_KEY", None)
            os.environ.pop("OPENAI_API_KEY", None)
            env = fireworks_env(credential_id="my-custom-id")
        assert env["OPENAI_API_KEY"] == "custom-key"

    def test_no_creds_no_key(self, tmp_path: Path) -> None:
        with (
            patch.dict(os.environ, {}, clear=False),
            patch("pheno.harbor_util.Path.home", return_value=tmp_path),
        ):
            os.environ.pop("FIREWORKS_AI_API_KEY", None)
            os.environ.pop("OPENAI_API_KEY", None)
            env = fireworks_env()
        assert "OPENAI_API_KEY" not in env
        assert "FIREWORKS_AI_API_KEY" not in env

    def test_sets_encoding_defaults(self) -> None:
        env = fireworks_env()
        assert env["PYTHONIOENCODING"] == "utf-8"
        assert env["PYTHONUTF8"] == "1"

    def test_preserves_existing_encoding(self) -> None:
        with patch.dict(
            os.environ,
            {"PYTHONIOENCODING": "latin-1"},
            clear=False,
        ):
            env = fireworks_env()
        assert env["PYTHONIOENCODING"] == "latin-1"


# ---------------------------------------------------------------------------
# local_env tests
# ---------------------------------------------------------------------------


class TestLocalEnv:
    def test_sets_base_url_and_key(self) -> None:
        env = local_env("http://localhost:8080/v1")
        assert env["OPENAI_BASE_URL"] == "http://localhost:8080/v1"
        assert env["OPENAI_API_KEY"] == "local-no-key"

    def test_custom_api_key(self) -> None:
        env = local_env("http://localhost:8080/v1", api_key="my-key")
        assert env["OPENAI_API_KEY"] == "my-key"

    def test_strips_trailing_slash(self) -> None:
        env = local_env("http://localhost:8080/v1/")
        assert env["OPENAI_BASE_URL"] == "http://localhost:8080/v1"

    def test_encoding_defaults(self) -> None:
        env = local_env("http://localhost:8080/v1")
        assert env["PYTHONIOENCODING"] == "utf-8"
        assert env["PYTHONUTF8"] == "1"


# ---------------------------------------------------------------------------
# route_env tests
# ---------------------------------------------------------------------------


class TestRouteEnv:
    def test_local_direct_route(self) -> None:
        entry = {
            "route_kind": "local_direct",
            "label": "my-model",
            "base_url": "http://127.0.0.1:8080/v1",
        }
        kind, model, env = route_env(entry)
        assert kind == "local_direct"
        assert model == "openai/my-model"
        assert env["OPENAI_BASE_URL"] == "http://127.0.0.1:8080/v1"

    def test_local_direct_default_base_url(self) -> None:
        entry = {"route_kind": "local_direct", "label": "m"}
        kind, model, env = route_env(entry)
        assert env["OPENAI_BASE_URL"] == "http://127.0.0.1:8080/v1"

    def test_pheno_serve_route(self) -> None:
        entry = {"route_kind": "pheno_serve", "label": "pheno-m"}
        kind, model, env = route_env(entry)
        assert kind == "pheno_serve"
        assert model == "openai/pheno-m"
        assert env["OPENAI_BASE_URL"] == "http://127.0.0.1:21080/v1"

    def test_pheno_serve_custom_base_url(self) -> None:
        entry = {
            "route_kind": "pheno_serve",
            "label": "m",
            "base_url": "http://custom:3000/v1",
        }
        kind, model, env = route_env(entry)
        assert env["OPENAI_BASE_URL"] == "http://custom:3000/v1"

    def test_local_direct_with_api_model(self) -> None:
        entry = {
            "route_kind": "local_direct",
            "api_model": "real-model-name",
            "label": "fallback",
        }
        kind, model, env = route_env(entry)
        assert model == "openai/real-model-name"

    def test_local_direct_with_cfg_local_api_key(self) -> None:
        entry = {"route_kind": "local_direct", "label": "m"}
        cfg = {"provider": {"local_api_key": "secret-key"}}
        kind, model, env = route_env(entry, cfg)
        assert env["OPENAI_API_KEY"] == "secret-key"

    def test_local_direct_cfg_none_uses_default_key(self) -> None:
        entry = {"route_kind": "local_direct", "label": "m"}
        kind, model, env = route_env(entry, None)
        assert env["OPENAI_API_KEY"] == "local-no-key"

    def test_omniroute_cloud_combo(self) -> None:
        entry = {"route_kind": "omniroute_cloud", "combo": True}
        kind, model, env = route_env(entry)
        assert kind == "omniroute_cloud"
        assert model == "openai/Main"

    def test_omniroute_cloud_with_id(self) -> None:
        entry = {
            "route_kind": "omniroute_cloud",
            "id": "some-model",
        }
        kind, model, env = route_env(entry)
        assert kind == "omniroute_cloud"
        assert model == "openai/some-model"

    def test_default_route_kind(self) -> None:
        """When route_kind is not specified, defaults to omniroute_cloud."""
        entry = {"id": "gpt-4"}
        kind, model, env = route_env(entry)
        assert kind == "omniroute_cloud"
        assert model == "openai/gpt-4"

    def test_omniroute_env_returned_for_cloud_routes(self) -> None:
        entry = {"route_kind": "omniroute_cloud", "id": "gpt-4"}
        kind, model, env = route_env(entry)
        assert env["OPENAI_BASE_URL"] == "http://127.0.0.1:20128/v1"

    def test_local_direct_with_custom_provider_key(self) -> None:
        entry = {"route_kind": "local_direct", "label": "m"}
        cfg = {"provider": {"local_api_key": "prov-key"}}
        kind, model, env = route_env(entry, cfg)
        assert env["OPENAI_API_KEY"] == "prov-key"

    def test_omniroute_cloud_without_combo_or_id(self) -> None:
        """Non-combo omniroute_cloud with id uses litellm_model."""
        entry = {"route_kind": "omniroute_cloud", "id": "claude-3"}
        kind, model, env = route_env(entry)
        assert model == "openai/claude-3"

    def test_route_env_entry_without_id_field(self) -> None:
        """Entry missing 'id' and no combo — should raise KeyError."""
        entry = {"route_kind": "omniroute_cloud"}
        with pytest.raises(KeyError):
            route_env(entry)

    def test_pheno_serve_no_label_uses_local(self) -> None:
        """pheno_serve route with no label defaults to 'local'."""
        entry = {"route_kind": "pheno_serve"}
        kind, model, env = route_env(entry)
        assert model == "openai/local"
