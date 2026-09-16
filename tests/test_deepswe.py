"""Unit tests for eval.deepswe — manifest building, preflight, and execution.

Covers PierPreflight, _runner_command, _parse_version, docker_runtime_preflight,
_pier_preflight, build_manifest, write_manifest, execute, and load_config.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest import mock

import pytest
import yaml

from eval.deepswe import (
    PierPreflight,
    _isolated_pier_version,
    _parse_version,
    _runner_command,
    _version_probe,
    build_manifest,
    docker_runtime_preflight,
    execute,
    load_config,
    write_manifest,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def deepswe_config(tmp_path: Path) -> dict:
    """Minimal valid DeepSWE config dict."""
    return {
        "suite": {
            "id": "deep-swe",
            "n_tasks": 113,
            "task_root_env": "PHENO_DEEPSWE_TASK_ROOT",
            "runner": "pier",
            "agent": "mini-swe-agent",
            "min_pier_version": "0.3.0",
        },
        "policy": {
            "local_only": True,
            "cloud_evals_disabled": True,
        },
        "models": ["local/qwen35-08b", "local/lfm25-8b-a1b"],
    }


@pytest.fixture
def minimal_preflight() -> PierPreflight:
    """A minimal PierPreflight with binary found."""
    return PierPreflight(
        schema_version="pheno.deepswe.preflight.v1",
        runner="pier",
        binary_path="/usr/bin/pier",
        binary_found=True,
        binary_version="0.4.0",
        minimum_runner_version="0.3.0",
        version_satisfied=True,
        task_root_env="PHENO_DEEPSWE_TASK_ROOT",
        task_root_required=True,
        task_root_value="/tmp/tasks",
        task_root_resolved=Path("/tmp/tasks"),
        task_root_present=True,
    )


@pytest.fixture
def preflight_no_binary() -> PierPreflight:
    """PierPreflight with no binary found."""
    return PierPreflight(
        schema_version="pheno.deepswe.preflight.v1",
        runner="pier",
        binary_path=None,
        binary_found=False,
        binary_version=None,
        minimum_runner_version="0.3.0",
        version_satisfied=None,
        task_root_env="PHENO_DEEPSWE_TASK_ROOT",
        task_root_required=True,
        task_root_value=None,
        task_root_resolved=None,
        task_root_present=False,
    )


@pytest.fixture
def preflight_bad_version() -> PierPreflight:
    """PierPreflight with binary version too old."""
    return PierPreflight(
        schema_version="pheno.deepswe.preflight.v1",
        runner="pier",
        binary_path="/usr/bin/pier",
        binary_found=True,
        binary_version="0.2.0",
        minimum_runner_version="0.3.0",
        version_satisfied=False,
        task_root_env="PHENO_DEEPSWE_TASK_ROOT",
        task_root_required=True,
        task_root_value="/tmp/tasks",
        task_root_resolved=Path("/tmp/tasks"),
        task_root_present=True,
    )


# ---------------------------------------------------------------------------
# PierPreflight
# ---------------------------------------------------------------------------

class TestPierPreflight:
    def test_as_dict_with_resolved(self, minimal_preflight: PierPreflight) -> None:
        d = minimal_preflight.as_dict()
        assert d["binary_found"] is True
        assert d["binary_path"] == "/usr/bin/pier"
        # Path coerced to str via str(); format depends on OS
        assert str(Path("/tmp/tasks")) in (d["task_root_resolved"] or "")

    def test_as_dict_without_resolved(self, preflight_no_binary: PierPreflight) -> None:
        d = preflight_no_binary.as_dict()
        assert d["binary_found"] is False
        assert d["task_root_resolved"] is None

    def test_frozen(self, minimal_preflight: PierPreflight) -> None:
        with pytest.raises(AttributeError):
            minimal_preflight.binary_found = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# _parse_version
# ---------------------------------------------------------------------------

class TestParseVersion:
    def test_valid(self) -> None:
        assert _parse_version("0.3.0") == (0, 3, 0)

    def test_embedded(self) -> None:
        assert _parse_version("pier v1.2.3 (build 456)") == (1, 2, 3)

    def test_no_match(self) -> None:
        assert _parse_version("no version here") is None

    def test_two_part(self) -> None:
        assert _parse_version("1.2") is None

    def test_empty(self) -> None:
        assert _parse_version("") is None


# ---------------------------------------------------------------------------
# _runner_command
# ---------------------------------------------------------------------------

class TestRunnerCommand:
    def test_native_binary(self) -> None:
        result = _runner_command("pier", "run", "--help")
        assert result == ["pier", "run", "--help"]

    def test_cmd_wrapper(self) -> None:
        result = _runner_command("pier.cmd", "version")
        assert result == ["cmd", "/d", "/c", "call", "pier.cmd", "version"]

    def test_bat_wrapper(self) -> None:
        result = _runner_command("run.bat", "test")
        assert result == ["cmd", "/d", "/c", "call", "run.bat", "test"]

    def test_module_path_when_env_set(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        mod_python = str(tmp_path / "python.exe")
        mod_root = str(tmp_path / "src")
        os.makedirs(mod_root, exist_ok=True)
        monkeypatch.setenv("PHENO_PIER_PYTHON", mod_python)
        monkeypatch.setenv("PHENO_PIER_PYTHONPATH", mod_root)
        result = _runner_command("pier.cmd", "run")
        assert result == [mod_python, "-m", "pier.cli.main", "run"]

    def test_module_path_when_binary_is_python(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        mod_python = str(tmp_path / "python.exe")
        mod_root = str(tmp_path / "src")
        os.makedirs(mod_root, exist_ok=True)
        monkeypatch.setenv("PHENO_PIER_PYTHON", mod_python)
        monkeypatch.setenv("PHENO_PIER_PYTHONPATH", mod_root)
        result = _runner_command(mod_python, "--version")
        assert result == [mod_python, "-m", "pier.cli.main", "--version"]

    def test_module_root_not_dir_falls_through(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PHENO_PIER_PYTHON", "/some/python")
        monkeypatch.setenv("PHENO_PIER_PYTHONPATH", "/nonexistent_path_xyz")
        result = _runner_command("pier.cmd", "run")
        # Falls through to cmd wrapper
        assert result == ["cmd", "/d", "/c", "call", "pier.cmd", "run"]


# ---------------------------------------------------------------------------
# _isolated_pier_version
# ---------------------------------------------------------------------------

class TestIsolatedPierVersion:
    def test_returns_none_on_missing_dist(self, tmp_path: Path) -> None:
        assert _isolated_pier_version(str(tmp_path)) is None

    def test_returns_none_on_os_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_distributions(path=None):
            raise OSError("no such path")
        monkeypatch.setattr("eval.deepswe.distributions", fake_distributions)
        assert _isolated_pier_version("/nonexistent") is None

    def test_returns_none_on_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_distributions(path=None):
            raise ValueError("bad value")
        monkeypatch.setattr("eval.deepswe.distributions", fake_distributions)
        assert _isolated_pier_version("/nonexistent") is None


# ---------------------------------------------------------------------------
# docker_runtime_preflight
# ---------------------------------------------------------------------------

class TestDockerRuntimePreflight:
    def test_no_docker_host_no_cli(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        monkeypatch.setattr("eval.deepswe.shutil.which", lambda x: None)
        result = docker_runtime_preflight()
        assert result["reachable"] is False
        assert result["reason"] == "docker_host_and_cli_missing"

    def test_cli_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        monkeypatch.setattr("eval.deepswe.shutil.which", lambda x: "/usr/bin/docker")
        completed = subprocess.CompletedProcess(
            args=["docker", "version", "--format", "{{.Server.Version}}"],
            returncode=0,
            stdout="24.0.7\n",
            stderr="",
        )
        monkeypatch.setattr("eval.deepswe.subprocess.run", lambda *a, **kw: completed)
        result = docker_runtime_preflight()
        assert result["reachable"] is True
        assert result["server_version"] == "24.0.7"

    def test_cli_nonzero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        monkeypatch.setattr("eval.deepswe.shutil.which", lambda x: "/usr/bin/docker")
        completed = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Error: daemon not running"
        )
        monkeypatch.setattr("eval.deepswe.subprocess.run", lambda *a, **kw: completed)
        result = docker_runtime_preflight()
        assert result["reachable"] is False
        assert result["reason"] == "docker_cli_nonzero"
        assert "daemon not running" in result["stderr"]

    def test_cli_oserror(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        monkeypatch.setattr("eval.deepswe.shutil.which", lambda x: "/usr/bin/docker")
        def bad_run(*a, **kw):
            raise OSError("permission denied")
        monkeypatch.setattr("eval.deepswe.subprocess.run", bad_run)
        result = docker_runtime_preflight()
        assert result["reachable"] is False
        assert "docker_cli_probe_failed" in result["reason"]

    def test_cli_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        monkeypatch.setattr("eval.deepswe.shutil.which", lambda x: "/usr/bin/docker")
        def timeout_run(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="docker", timeout=3)
        monkeypatch.setattr("eval.deepswe.subprocess.run", timeout_run)
        result = docker_runtime_preflight()
        assert result["reachable"] is False
        assert "docker_cli_probe_failed" in result["reason"]

    def test_unsupported_scheme(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
        result = docker_runtime_preflight()
        assert result["reachable"] is False
        assert result["reason"] == "unsupported_docker_host_scheme"

    def test_tcp_probe_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DOCKER_HOST", "tcp://127.0.0.1:2375")
        ping_resp = mock.MagicMock()
        ping_resp.read.return_value = b"OK"
        ping_resp.__enter__ = mock.MagicMock(return_value=ping_resp)
        ping_resp.__exit__ = mock.MagicMock(return_value=False)

        version_resp = mock.MagicMock()
        version_resp.read.return_value = json.dumps(
            {"Version": "24.0.7", "ApiVersion": "1.43", "Os": "linux", "Arch": "amd64"}
        ).encode()
        version_resp.__enter__ = mock.MagicMock(return_value=version_resp)
        version_resp.__exit__ = mock.MagicMock(return_value=False)

        call_count = 0
        def mock_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ping_resp
            return version_resp

        monkeypatch.setattr("eval.deepswe.urlopen", mock_urlopen)
        result = docker_runtime_preflight()
        assert result["reachable"] is True
        assert result["server_version"] == "24.0.7"
        assert result["api_version"] == "1.43"

    def test_tcp_probe_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DOCKER_HOST", "tcp://127.0.0.1:2375")
        def bad_urlopen(req, timeout=None):
            raise OSError("connection refused")
        monkeypatch.setattr("eval.deepswe.urlopen", bad_urlopen)
        result = docker_runtime_preflight()
        assert result["reachable"] is False
        assert "docker_api_probe_failed" in result["reason"]

    def test_tcp_probe_json_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DOCKER_HOST", "tcp://127.0.0.1:2375")
        ping_resp = mock.MagicMock()
        ping_resp.read.return_value = b"OK"
        ping_resp.__enter__ = mock.MagicMock(return_value=ping_resp)
        ping_resp.__exit__ = mock.MagicMock(return_value=False)

        version_resp = mock.MagicMock()
        version_resp.read.return_value = b"not json"
        version_resp.__enter__ = mock.MagicMock(return_value=version_resp)
        version_resp.__exit__ = mock.MagicMock(return_value=False)

        call_count = 0
        def mock_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            return [ping_resp, version_resp][call_count - 1]

        monkeypatch.setattr("eval.deepswe.urlopen", mock_urlopen)
        result = docker_runtime_preflight()
        assert result["reachable"] is False
        assert "docker_api_probe_failed" in result["reason"]


# ---------------------------------------------------------------------------
# _version_probe
# ---------------------------------------------------------------------------

class TestVersionProbe:
    def test_normal_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        completed = subprocess.CompletedProcess(
            args=["pier", "--version"], returncode=0, stdout="pier 0.4.0", stderr=""
        )
        monkeypatch.setattr("eval.deepswe.subprocess.run", lambda *a, **kw: completed)
        result = _version_probe(["pier", "--version"])
        assert result.stdout == "pier 0.4.0"

    def test_cmd_wrapper_uses_tempfile(self, monkeypatch: pytest.MonkeyPatch) -> None:
        completed = subprocess.CompletedProcess(
            args=["cmd", "/d", "/c", "call", "pier.cmd", "--version"],
            returncode=0,
            stdout="",
            stderr="",
        )
        monkeypatch.setattr("eval.deepswe.subprocess.run", lambda *a, **kw: completed)
        result = _version_probe(["cmd", "/d", "/c", "call", "pier.cmd", "--version"])
        assert isinstance(result, subprocess.CompletedProcess)

    def test_module_invocation_sets_pythonpath(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PHENO_PIER_PYTHONPATH", "/some/root")
        monkeypatch.delenv("PATH", raising=False)
        completed = subprocess.CompletedProcess(
            args=["python", "-m", "pier.cli.main", "--version"],
            returncode=0,
            stdout="0.5.0",
            stderr="",
        )
        def capture_run(command, **kw):
            assert kw.get("env") is not None
            assert "PYTHONPATH" in kw["env"]
            return completed

        monkeypatch.setattr("eval.deepswe.subprocess.run", capture_run)
        result = _version_probe(["python", "-m", "pier.cli.main", "--version"])
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_loads_yaml(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "deepswe.yaml"
        cfg_path.write_text(yaml.dump({"suite": {"id": "test"}}), encoding="utf-8")
        result = load_config(cfg_path)
        assert result["suite"]["id"] == "test"

    def test_empty_file(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "deepswe.yaml"
        cfg_path.write_text("", encoding="utf-8")
        result = load_config(cfg_path)
        assert result == {}


# ---------------------------------------------------------------------------
# build_manifest
# ---------------------------------------------------------------------------

class TestBuildManifest:
    def test_valid_dry_run(
        self, deepswe_config: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        result = build_manifest(
            deepswe_config,
            model_alias="local/qwen35-08b",
            subset=10,
            environment="docker",
            execute=False,
        )
        assert result["schema_version"] == 1
        assert result["suite"] == "deep-swe"
        assert result["run_mode"] == "dry_run"
        assert result["scoreable"] is False
        assert result["review_required"] is True
        assert result["n_tasks_requested"] == 10
        assert result["integrity"]["no_training_on_eval_tasks"] is True

    def test_valid_execute_with_preflight(
        self, deepswe_config: dict, minimal_preflight: PierPreflight,
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        monkeypatch.setattr(
            "eval.deepswe.docker_runtime_preflight",
            lambda **kw: {
                "checked": True, "reachable": True,
                "docker_host": "cli", "server_version": "24.0",
            },
        )
        result = build_manifest(
            deepswe_config,
            model_alias="local/qwen35-08b",
            subset=1,
            environment="docker",
            execute=True,
            preflight=minimal_preflight,
        )
        assert result["run_mode"] == "execute"
        assert "runtime_preflight" in result
        assert result["runtime_preflight"]["reachable"] is True

    def test_bad_environment(self, deepswe_config: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        with pytest.raises(ValueError, match="cloud environments are disabled"):
            build_manifest(
                deepswe_config,
                model_alias="local/qwen35-08b",
                subset=1,
                environment="cloud",
                execute=False,
            )

    def test_model_not_enabled(self, deepswe_config: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        with pytest.raises(ValueError, match="model is not enabled"):
            build_manifest(
                deepswe_config,
                model_alias="local/nonexistent",
                subset=1,
                environment="docker",
                execute=False,
            )

    def test_subset_too_high(self, deepswe_config: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        with pytest.raises(ValueError, match="subset must be between"):
            build_manifest(
                deepswe_config,
                model_alias="local/qwen35-08b",
                subset=999,
                environment="docker",
                execute=False,
            )

    def test_subset_zero(self, deepswe_config: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        with pytest.raises(ValueError, match="subset must be between"):
            build_manifest(
                deepswe_config,
                model_alias="local/qwen35-08b",
                subset=0,
                environment="docker",
                execute=False,
            )

    def test_execute_without_binary_raises(
        self, deepswe_config: dict, preflight_no_binary: PierPreflight,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        with pytest.raises(ValueError, match="binary not on PATH"):
            build_manifest(
                deepswe_config,
                model_alias="local/qwen35-08b",
                subset=1,
                environment="docker",
                execute=True,
                preflight=preflight_no_binary,
            )

    def test_execute_with_bad_version_raises(
        self, deepswe_config: dict, preflight_bad_version: PierPreflight,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        with pytest.raises(ValueError, match="does not satisfy"):
            build_manifest(
                deepswe_config,
                model_alias="local/qwen35-08b",
                subset=1,
                environment="docker",
                execute=True,
                preflight=preflight_bad_version,
            )

    def test_execute_task_root_missing(
        self, deepswe_config: dict, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        pf = PierPreflight(
            schema_version="pheno.deepswe.preflight.v1",
            runner="pier",
            binary_path="/usr/bin/pier",
            binary_found=True,
            binary_version="0.4.0",
            minimum_runner_version="0.3.0",
            version_satisfied=True,
            task_root_env="PHENO_DEEPSWE_TASK_ROOT",
            task_root_required=True,
            task_root_value="/nonexistent/path",
            task_root_resolved=Path("/nonexistent/path"),
            task_root_present=False,
        )
        with pytest.raises(ValueError, match="existing DeepSWE tasks directory"):
            build_manifest(
                deepswe_config,
                model_alias="local/qwen35-08b",
                subset=1,
                environment="docker",
                execute=True,
                preflight=pf,
            )

    def test_execute_docker_not_reachable(
        self, deepswe_config: dict, minimal_preflight: PierPreflight,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        monkeypatch.setattr(
            "eval.deepswe.docker_runtime_preflight",
            lambda **kw: {"checked": True, "reachable": False, "reason": "no docker"},
        )
        with pytest.raises(ValueError, match="Docker-compatible runtime is not reachable"):
            build_manifest(
                deepswe_config,
                model_alias="local/qwen35-08b",
                subset=1,
                environment="docker",
                execute=True,
                preflight=minimal_preflight,
            )

    def test_preflight_embedded_in_manifest(
        self, deepswe_config: dict, minimal_preflight: PierPreflight,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        result = build_manifest(
            deepswe_config,
            model_alias="local/qwen35-08b",
            subset=5,
            environment="docker",
            execute=False,
            preflight=minimal_preflight,
        )
        assert result["preflight"]["binary_found"] is True

    def test_execute_mode_sets_run_mode(
        self, deepswe_config: dict, minimal_preflight: PierPreflight,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        monkeypatch.setattr(
            "eval.deepswe.docker_runtime_preflight",
            lambda **kw: {"checked": True, "reachable": True, "server_version": "24.0"},
        )
        result = build_manifest(
            deepswe_config,
            model_alias="local/qwen35-08b",
            subset=1,
            environment="docker",
            execute=True,
            preflight=minimal_preflight,
        )
        assert result["run_mode"] == "execute"

    def test_dry_run_with_preflight_task_root_optional(
        self, deepswe_config: dict, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Task root is required only when task_root_env == 'PHENO_DEEPSWE_TASK_ROOT'."""
        monkeypatch.setattr("eval.deepswe.require_local_alias", lambda *a, **kw: None)
        pf = PierPreflight(
            schema_version="pheno.deepswe.preflight.v1",
            runner="pier",
            binary_path="/usr/bin/pier",
            binary_found=True,
            binary_version="0.4.0",
            minimum_runner_version="0.3.0",
            version_satisfied=True,
            task_root_env="OTHER_ENV",
            task_root_required=False,
            task_root_value=None,
            task_root_resolved=None,
            task_root_present=False,
        )
        result = build_manifest(
            deepswe_config,
            model_alias="local/qwen35-08b",
            subset=1,
            environment="docker",
            execute=False,
            preflight=pf,
        )
        assert result["run_mode"] == "dry_run"


# ---------------------------------------------------------------------------
# write_manifest
# ---------------------------------------------------------------------------

class TestWriteManifest:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        manifest = {"schema_version": 1, "suite": "test"}
        path = write_manifest(manifest, root=tmp_path)
        assert path.exists()
        assert path.suffix == ".json"
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["schema_version"] == 1

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        manifest = {"test": True}
        path = write_manifest(manifest, root=tmp_path / "nested" / "dir")
        assert path.exists()


# ---------------------------------------------------------------------------
# execute
# ---------------------------------------------------------------------------

class TestExecute:
    def test_missing_preflight_binary(
        self, deepswe_config: dict, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_runtime_alias", lambda *a, **kw: None)
        manifest = {
            "runner": "pier",
            "model_alias": "test",
            "task_root_env": "PHENO_DEEPSWE_TASK_ROOT",
            "n_tasks_requested": 1,
            "agent": "mini-swe-agent",
            "minimum_runner_version": "0.3.0",
            "environment": "docker",
            "preflight": {"binary_found": False},
        }
        with pytest.raises(ValueError, match="binary not on PATH"):
            execute(manifest)

    def test_missing_preflight_version_unsatisfied(
        self, deepswe_config: dict, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_runtime_alias", lambda *a, **kw: None)
        manifest = {
            "runner": "pier",
            "model_alias": "test",
            "task_root_env": "PHENO_DEEPSWE_TASK_ROOT",
            "n_tasks_requested": 1,
            "agent": "mini-swe-agent",
            "minimum_runner_version": "0.3.0",
            "environment": "docker",
            "preflight": {"binary_found": True, "version_satisfied": False, "binary_version": "0.1.0"},
        }
        with pytest.raises(ValueError, match="does not satisfy"):
            execute(manifest)

    def test_no_task_root_raises(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_runtime_alias", lambda *a, **kw: None)
        manifest = {
            "runner": "pier",
            "model_alias": "test",
            "task_root_env": "PHENO_DEEPSWE_TASK_ROOT",
            "n_tasks_requested": 1,
            "agent": "mini-swe-agent",
            "minimum_runner_version": "0.3.0",
            "environment": "docker",
            "preflight": {"binary_found": True, "version_satisfied": True},
        }
        monkeypatch.delenv("PHENO_DEEPSWE_TASK_ROOT", raising=False)
        with pytest.raises(ValueError, match="set PHENO_DEEPSWE_TASK_ROOT"):
            execute(manifest)

    def test_task_root_not_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_runtime_alias", lambda *a, **kw: None)
        fake_file = tmp_path / "not_a_dir"
        fake_file.write_text("x")
        manifest = {
            "runner": "pier",
            "model_alias": "test",
            "task_root_env": "PHENO_DEEPSWE_TASK_ROOT",
            "n_tasks_requested": 1,
            "agent": "mini-swe-agent",
            "minimum_runner_version": "0.3.0",
            "environment": "docker",
            "preflight": {"binary_found": True, "version_satisfied": True},
        }
        monkeypatch.setenv("PHENO_DEEPSWE_TASK_ROOT", str(fake_file))
        with pytest.raises(ValueError, match="does not exist"):
            execute(manifest)

    def test_success_with_env_fallback(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_runtime_alias", lambda *a, **kw: None)
        task_dir = tmp_path / "tasks"
        task_dir.mkdir()
        manifest = {
            "runner": "pier",
            "model_alias": "test",
            "task_root_env": "PHENO_DEEPSWE_TASK_ROOT",
            "n_tasks_requested": 1,
            "agent": "mini-swe-agent",
            "minimum_runner_version": "0.3.0",
            "environment": "docker",
            "preflight": {"binary_found": True, "version_satisfied": True},
        }
        monkeypatch.setenv("PHENO_DEEPSWE_TASK_ROOT", str(task_dir))
        monkeypatch.setenv("PHENO_PIER_BIN", "pier")
        monkeypatch.delenv("PHENO_PIER_PYTHONPATH", raising=False)
        completed = subprocess.CompletedProcess(args=[], returncode=0)
        monkeypatch.setattr("eval.deepswe.subprocess.run", lambda *a, **kw: completed)
        monkeypatch.setattr("eval.deepswe.local_env", lambda *a, **kw: {})
        monkeypatch.setattr(
            "eval.deepswe.PHENO_ROOT", tmp_path,
        )
        result = execute(manifest)
        assert result == 0

    def test_uses_resolved_task_root_from_preflight(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_runtime_alias", lambda *a, **kw: None)
        task_dir = tmp_path / "resolved_tasks"
        task_dir.mkdir()
        manifest = {
            "runner": "pier",
            "model_alias": "test",
            "task_root_env": "PHENO_DEEPSWE_TASK_ROOT",
            "n_tasks_requested": 1,
            "agent": "mini-swe-agent",
            "minimum_runner_version": "0.3.0",
            "environment": "docker",
            "preflight": {
                "binary_found": True,
                "version_satisfied": True,
                "binary_path": "/usr/bin/pier",
                "task_root_resolved": str(task_dir),
                "task_root_value": str(task_dir),
            },
        }
        monkeypatch.delenv("PHENO_DEEPSWE_TASK_ROOT", raising=False)
        monkeypatch.delenv("PHENO_PIER_PYTHONPATH", raising=False)
        completed = subprocess.CompletedProcess(args=[], returncode=0)
        monkeypatch.setattr("eval.deepswe.subprocess.run", lambda *a, **kw: completed)
        monkeypatch.setattr("eval.deepswe.local_env", lambda *a, **kw: {})
        monkeypatch.setattr("eval.deepswe.PHENO_ROOT", tmp_path)
        result = execute(manifest)
        assert result == 0

    def test_pythonpath_set_when_module_root_exists(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        monkeypatch.setattr("eval.deepswe.require_runtime_alias", lambda *a, **kw: None)
        task_dir = tmp_path / "tasks"
        task_dir.mkdir()
        module_root = tmp_path / "src"
        module_root.mkdir()
        manifest = {
            "runner": "pier",
            "model_alias": "test",
            "task_root_env": "PHENO_DEEPSWE_TASK_ROOT",
            "n_tasks_requested": 1,
            "agent": "mini-swe-agent",
            "minimum_runner_version": "0.3.0",
            "environment": "docker",
            "preflight": {
                "binary_found": True,
                "version_satisfied": True,
                "task_root_resolved": str(task_dir),
                "task_root_value": str(task_dir),
            },
        }
        monkeypatch.delenv("PHENO_DEEPSWE_TASK_ROOT", raising=False)
        monkeypatch.setenv("PHENO_PIER_PYTHONPATH", str(module_root))
        completed = subprocess.CompletedProcess(args=[], returncode=0)
        monkeypatch.setattr("eval.deepswe.subprocess.run", lambda *a, **kw: completed)
        monkeypatch.setattr("eval.deepswe.local_env", lambda *a, **kw: {})
        monkeypatch.setattr("eval.deepswe.PHENO_ROOT", tmp_path)
        result = execute(manifest)
        assert result == 0
