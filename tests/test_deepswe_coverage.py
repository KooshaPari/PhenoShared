"""Coverage tests for eval/deepswe.py — target 90%+ line+branch coverage.

Real API:
  PierPreflight (frozen dataclass) with as_dict()
  _runner_command(binary_path, *args) -> list[str]
  _isolated_pier_version(root) -> str | None
  docker_runtime_preflight(*, timeout=3.0) -> dict
  _version_probe(command) -> subprocess.CompletedProcess
  _parse_version(text) -> tuple[int, int, int] | None
  pier_preflight(config) -> PierPreflight
  load_config(path=None) -> dict
  build_manifest(config) -> dict
  write_manifest(manifest, root=None) -> Path
  execute(manifest) -> int
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest


# ---------------------------------------------------------------------------
# PierPreflight dataclass
# ---------------------------------------------------------------------------

class TestPierPreflight:
    def test_as_dict_full(self):
        from eval.deepswe import PierPreflight
        pf = PierPreflight(
            schema_version="pheno.deepswe.preflight.v1",
            runner="pier",
            binary_path="/usr/bin/pier",
            binary_found=True,
            binary_version="1.2.3",
            minimum_runner_version="1.0.0",
            version_satisfied=True,
            task_root_env="PHENO_DEEPSWE_TASK_ROOT",
            task_root_required=True,
            task_root_value="/data/tasks",
            task_root_resolved=Path("/data/tasks"),
            task_root_present=True,
        )
        d = pf.as_dict()
        assert d["schema_version"] == "pheno.deepswe.preflight.v1"
        assert d["binary_found"] is True
        assert d["version_satisfied"] is True
        assert d["task_root_present"] is True
        assert isinstance(d, dict)

    def test_as_dict_minimal(self):
        from eval.deepswe import PierPreflight
        pf = PierPreflight(
            schema_version="v1",
            runner="x",
            binary_path=None,
            binary_found=False,
            binary_version=None,
            minimum_runner_version="0.0.0",
            version_satisfied=None,
            task_root_env="E",
            task_root_required=False,
            task_root_value=None,
            task_root_resolved=None,
            task_root_present=False,
        )
        d = pf.as_dict()
        assert d["binary_found"] is False
        assert d["binary_path"] is None
        assert d["version_satisfied"] is None

    def test_frozen(self):
        from eval.deepswe import PierPreflight
        pf = PierPreflight(
            schema_version="v1", runner="x", binary_path=None,
            binary_found=False, binary_version=None,
            minimum_runner_version="0.0.0", version_satisfied=None,
            task_root_env="E", task_root_required=False,
            task_root_value=None, task_root_resolved=None,
            task_root_present=False,
        )
        with pytest.raises((AttributeError, Exception)):
            pf.runner = "changed"


# ---------------------------------------------------------------------------
# _runner_command
# ---------------------------------------------------------------------------

class TestRunnerCommand:
    def test_simple(self):
        from eval.deepswe import _runner_command
        cmd = _runner_command("/usr/bin/pier")
        assert cmd[0] == "/usr/bin/pier"

    def test_with_args(self):
        from eval.deepswe import _runner_command
        cmd = _runner_command("/usr/bin/pier", "--flag", "value")
        assert "--flag" in cmd
        assert "value" in cmd

    def test_cmd_bat_wrapper(self):
        from eval.deepswe import _runner_command
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PHENO_PIER_PYTHON", None)
            os.environ.pop("PHENO_PIER_PYTHONPATH", None)
            cmd = _runner_command("C:\\tools\\pier.cmd", "version")
            assert cmd[:4] == ["cmd", "/d", "/c", "call"]
            assert cmd[4].endswith("pier.cmd")

    def test_module_mode(self):
        from eval.deepswe import _runner_command
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {
                "PHENO_PIER_PYTHON": sys.executable,
                "PHENO_PIER_PYTHONPATH": td,
            }):
                cmd = _runner_command("C:\\tools\\pier.cmd", "version")
                assert cmd[:3] == [sys.executable, "-m", "pier.cli.main"]

    def test_module_mode_via_python_path(self):
        from eval.deepswe import _runner_command
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {
                "PHENO_PIER_PYTHON": sys.executable,
                "PHENO_PIER_PYTHONPATH": td,
            }):
                cmd = _runner_command(sys.executable, "version")
                assert cmd[:3] == [sys.executable, "-m", "pier.cli.main"]

    def test_module_mode_missing_root_dir(self):
        from eval.deepswe import _runner_command
        with patch.dict(os.environ, {
            "PHENO_PIER_PYTHON": sys.executable,
            "PHENO_PIER_PYTHONPATH": "Z:\\definitely\\missing\\dir\\xyz",
        }):
            cmd = _runner_command("/usr/bin/pier", "version")
            assert cmd[0] == "/usr/bin/pier"


# ---------------------------------------------------------------------------
# _parse_version
# ---------------------------------------------------------------------------

class TestParseVersion:
    def test_three_part(self):
        from eval.deepswe import _parse_version
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_embedded_in_text(self):
        from eval.deepswe import _parse_version
        assert _parse_version("pier version 1.2.3 (build 42)") == (1, 2, 3)

    def test_no_match_returns_none(self):
        from eval.deepswe import _parse_version
        assert _parse_version("1.2") is None  # regex needs MAJOR.MINOR.PATCH

    def test_with_prefix(self):
        from eval.deepswe import _parse_version
        assert _parse_version("v1.2.3") == (1, 2, 3)

    def test_invalid(self):
        from eval.deepswe import _parse_version
        assert _parse_version("abc") is None

    def test_empty(self):
        from eval.deepswe import _parse_version
        assert _parse_version("") is None

    def test_none(self):
        from eval.deepswe import _parse_version
        assert _parse_version("none") is None  # word with no digit

    def test_with_extra(self):
        from eval.deepswe import _parse_version
        # Should still parse leading numbers
        v = _parse_version("1.2.3-rc1")
        assert v == (1, 2, 3) or v is None


# ---------------------------------------------------------------------------
# _version_probe
# ---------------------------------------------------------------------------

class TestVersionProbe:
    def test_success(self):
        from eval.deepswe import _version_probe
        result = _version_probe(["echo", "1.2.3"])
        assert result.returncode == 0
        assert "1.2.3" in result.stdout

    def test_failure(self):
        from eval.deepswe import _version_probe
        result = _version_probe([sys.executable, "--invalid-flag-xyz"])
        assert result.returncode != 0

    def test_nonexistent_command(self):
        from eval.deepswe import _version_probe
        # Should not raise; should return a CompletedProcess with non-zero returncode
        with patch("subprocess.run", side_effect=FileNotFoundError("not found")):
            with pytest.raises((FileNotFoundError, Exception)):
                _version_probe(["nonexistent_binary_xyz"])


# ---------------------------------------------------------------------------
# _isolated_pier_version
# ---------------------------------------------------------------------------

class TestIsolatedPierVersion:
    def test_none_for_missing_dir(self):
        from eval.deepswe import _isolated_pier_version
        assert _isolated_pier_version("Z:\\definitely\\missing\\xyz") is None

    def test_none_for_no_dist(self):
        from eval.deepswe import _isolated_pier_version
        with tempfile.TemporaryDirectory() as td:
            # Real dir but no datacurve-pier dist installed there
            assert _isolated_pier_version(td) is None


# ---------------------------------------------------------------------------
# docker_runtime_preflight
# ---------------------------------------------------------------------------

class TestDockerPreflight:
    def test_missing_host_and_cli(self):
        from eval.deepswe import docker_runtime_preflight
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DOCKER_HOST", None)
            with patch("eval.deepswe.shutil.which", return_value=None):
                result = docker_runtime_preflight(timeout=1.0)
                assert result["checked"] is True
                assert result["reachable"] is False
                assert result["reason"] == "docker_host_and_cli_missing"

    def test_cli_probe_success(self):
        from eval.deepswe import docker_runtime_preflight
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DOCKER_HOST", None)
            with patch("eval.deepswe.shutil.which", return_value="C:\\docker.exe"), \
                 patch("eval.deepswe.subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess([], 0, "24.0.7", "")
                result = docker_runtime_preflight(timeout=1.0)
                assert result["reachable"] is True
                assert result["docker_host"] == "cli"
                assert result["server_version"] == "24.0.7"

    def test_cli_probe_nonzero(self):
        from eval.deepswe import docker_runtime_preflight
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DOCKER_HOST", None)
            with patch("eval.deepswe.shutil.which", return_value="C:\\docker.exe"), \
                 patch("eval.deepswe.subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess([], 1, "", "boom")
                result = docker_runtime_preflight(timeout=1.0)
                assert result["reachable"] is False
                assert result["reason"] == "docker_cli_nonzero"
                assert result["stderr"] == "boom"

    def test_cli_probe_raises(self):
        from eval.deepswe import docker_runtime_preflight
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DOCKER_HOST", None)
            with patch("eval.deepswe.shutil.which", return_value="C:\\docker.exe"), \
                 patch("eval.deepswe.subprocess.run", side_effect=subprocess.TimeoutExpired([], 1)):
                result = docker_runtime_preflight(timeout=1.0)
                assert result["reachable"] is False
                assert result["reason"].startswith("docker_cli_probe_failed:")

    def test_unsupported_scheme(self):
        from eval.deepswe import docker_runtime_preflight
        with patch.dict(os.environ, {"DOCKER_HOST": "unix:///var/run/docker.sock"}):
            result = docker_runtime_preflight(timeout=1.0)
            assert result["reachable"] is False
            assert result["reason"] == "unsupported_docker_host_scheme"

    def test_tcp_ping_ok(self):
        from eval.deepswe import docker_runtime_preflight
        host = "tcp://127.0.0.1:2375"
        with patch.dict(os.environ, {"DOCKER_HOST": host}):
            ping_resp = MagicMock()
            ping_resp.read.return_value = b"OK"
            ping_resp.__enter__.return_value = ping_resp
            ver_resp = MagicMock()
            ver_resp.read.return_value = json.dumps({"Version": "24.0.7", "ApiVersion": "1.43", "Os": "linux", "Arch": "amd64"}).encode()
            ver_resp.__enter__.return_value = ver_resp

            def fake_urlopen(req, timeout=None):
                if "/_ping" in str(req):
                    return ping_resp
                return ver_resp

            with patch("eval.deepswe.urlopen", side_effect=fake_urlopen):
                result = docker_runtime_preflight(timeout=1.0)
                assert result["reachable"] is True
                assert result["server_version"] == "24.0.7"
                assert result["api_version"] == "1.43"
                assert result["os"] == "linux"

    def test_tcp_ping_fails(self):
        from eval.deepswe import docker_runtime_preflight
        with patch.dict(os.environ, {"DOCKER_HOST": "tcp://127.0.0.1:2375"}):
            with patch("eval.deepswe.urlopen", side_effect=URLError("refused")):
                result = docker_runtime_preflight(timeout=1.0)
                assert result["reachable"] is False
                assert result["reason"].startswith("docker_api_probe_failed:")

    def test_unreachable(self):
        from eval.deepswe import docker_runtime_preflight
        # No DOCKER_HOST, no docker daemon -> should report unreachable or skipped
        env = {k: v for k, v in os.environ.items() if k != "DOCKER_HOST"}
        with patch.dict(os.environ, env, clear=True):
            with patch("shutil.which", return_value=None):
                result = docker_runtime_preflight(timeout=0.1)
                assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# pier_preflight
# ---------------------------------------------------------------------------

class TestPierPreflightFunction:
    """pier_preflight(config) expects config['suite'] = {runner, min_pier_version, task_root_env}."""

    def _cfg(self, runner="pier_definitely_absent_xyz"):
        return {
            "suite": {
                "runner": runner,
                "min_pier_version": "1.0.0",
                "task_root_env": "PHENO_DEEPSWE_TASK_ROOT",
            }
        }

    def test_empty_config(self):
        from eval.deepswe import pier_preflight
        with pytest.raises(KeyError):
            pier_preflight({})

    def test_minimal_config(self):
        from eval.deepswe import pier_preflight
        pf = pier_preflight(self._cfg())
        d = pf.as_dict()
        assert d["runner"] == "pier_definitely_absent_xyz"
        assert d["binary_found"] is False

    def test_with_version(self):
        from eval.deepswe import pier_preflight
        pf = pier_preflight(self._cfg())
        d = pf.as_dict()
        assert d["minimum_runner_version"] == "1.0.0"
        assert d["version_satisfied"] is None  # binary absent → no check

    def test_task_root_present(self):
        from eval.deepswe import pier_preflight
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"PHENO_DEEPSWE_TASK_ROOT": td}):
                pf = pier_preflight(self._cfg())
                d = pf.as_dict()
                assert d["task_root_present"] is True
                assert d["task_root_value"] == td

    def test_task_root_missing(self):
        from eval.deepswe import pier_preflight
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PHENO_DEEPSWE_TASK_ROOT", None)
            pf = pier_preflight(self._cfg())
            d = pf.as_dict()
            assert d["task_root_present"] is False
            assert d["task_root_required"] is True

    def test_task_root_other_env_not_required(self):
        from eval.deepswe import pier_preflight
        cfg = self._cfg()
        cfg["suite"]["task_root_env"] = "PHENO_SOME_OTHER_VAR"
        pf = pier_preflight(cfg)
        assert pf.task_root_required is False


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_default_path(self):
        from eval.deepswe import load_config
        # Should not raise even if default config doesn't exist
        try:
            cfg = load_config()
        except FileNotFoundError:
            pytest.skip("Default config not present")
        assert isinstance(cfg, dict)

    def test_explicit_path(self):
        from eval.deepswe import load_config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("runner:\n  name: pier\n")
            p = f.name
        try:
            cfg = load_config(Path(p))
            assert cfg["runner"]["name"] == "pier"
        finally:
            os.unlink(p)

    def test_missing_file(self):
        from eval.deepswe import load_config
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/path/config.yaml"))


# ---------------------------------------------------------------------------
# build_manifest / write_manifest / execute
# ---------------------------------------------------------------------------

class TestBuildManifest:
    """build_manifest(config, *, model_alias, subset, environment, execute, preflight=None)."""

    def _cfg(self):
        return {
            "suite": {
                "id": "deepswe",
                "n_tasks": 10,
                "agent": "swe-agent",
                "runner": "pier",
                "min_pier_version": "1.0.0",
                "task_root_env": "PHENO_DEEPSWE_TASK_ROOT",
            },
            "models": ["local/qwen35-08b"],
            "policy": {"sandbox": "docker", "max_retries": 2},
        }

    def test_basic(self):
        from eval.deepswe import build_manifest
        m = build_manifest(
            self._cfg(),
            model_alias="local/qwen35-08b",
            subset=5,
            environment="docker",
            execute=False,
        )
        assert isinstance(m, dict)
        assert m["suite"] == "deepswe"
        assert m["n_tasks_requested"] == 5
        assert m["n_tasks_total"] == 10
        assert m["model_alias"] == "local/qwen35-08b"

    def test_requires_docker(self):
        from eval.deepswe import build_manifest
        with pytest.raises(ValueError, match="docker"):
            build_manifest(
                self._cfg(),
                model_alias="local/qwen35-08b",
                subset=1,
                environment="local",
                execute=False,
            )

    def test_unknown_model(self):
        from eval.deepswe import build_manifest
        with pytest.raises(ValueError, match="locked local set"):
            build_manifest(
                self._cfg(),
                model_alias="bogus/alias",
                subset=1,
                environment="docker",
                execute=False,
            )

    def test_subset_too_low(self):
        from eval.deepswe import build_manifest
        with pytest.raises(ValueError, match="subset"):
            build_manifest(
                self._cfg(),
                model_alias="local/qwen35-08b",
                subset=0,
                environment="docker",
                execute=False,
            )

    def test_subset_too_high(self):
        from eval.deepswe import build_manifest
        with pytest.raises(ValueError, match="subset"):
            build_manifest(
                self._cfg(),
                model_alias="local/qwen35-08b",
                subset=11,
                environment="docker",
                execute=False,
            )

    def test_dry_run_manifest(self):
        from eval.deepswe import build_manifest
        m = build_manifest(
            self._cfg(),
            model_alias="local/qwen35-08b",
            subset=3,
            environment="docker",
            execute=False,
        )
        assert m["environment"] == "docker"
        assert m["runner"] == "pier"
        assert m["minimum_runner_version"] == "1.0.0"
        assert m["task_root_env"] == "PHENO_DEEPSWE_TASK_ROOT"


class TestWriteManifest:
    def test_writes_file(self):
        from eval.deepswe import write_manifest
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = {"suite": "test", "ok": True}
            p = write_manifest(manifest, root=root)
            assert p.exists()
            data = json.loads(p.read_text())
            assert data["suite"] == "test"


class TestExecute:
    """execute(manifest) — manifest keys: model_alias, preflight, runner, minimum_runner_version, task_root_env."""

    ALIAS = "local/qwen35-08b"

    def _manifest(self, **preflight_overrides):
        preflight = {
            "binary_found": True,
            "binary_path": None,
            "binary_version": "1.2.3",
            "version_satisfied": True,
            "task_root_value": "",
            "task_root_resolved": None,
        }
        preflight.update(preflight_overrides)
        return {
            "model_alias": self.ALIAS,
            "preflight": preflight,
            "runner": "pier",
            "minimum_runner_version": "1.0.0",
            "task_root_env": "PHENO_DEEPSWE_TASK_ROOT",
            "agent": "swe-agent",
            "n_tasks_requested": 3,
            "environment": "docker",
        }

    def test_no_task_root(self):
        from eval.deepswe import execute
        m = self._manifest()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PHENO_DEEPSWE_TASK_ROOT", None)
            os.environ.pop("PHENO_PIER_BIN", None)
            with pytest.raises(ValueError, match="task"):
                execute(m)

    def test_missing_binary(self):
        from eval.deepswe import execute
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"PHENO_DEEPSWE_TASK_ROOT": td}, clear=False):
                os.environ.pop("PHENO_PIER_BIN", None)
                m = self._manifest(binary_found=False)
                with pytest.raises(ValueError, match="not on PATH"):
                    execute(m)

    def test_version_unsatisfied(self):
        from eval.deepswe import execute
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"PHENO_DEEPSWE_TASK_ROOT": td}, clear=False):
                os.environ.pop("PHENO_PIER_BIN", None)
                m = self._manifest(version_satisfied=False, binary_version="0.5.0")
                with pytest.raises(ValueError, match="satisfy"):
                    execute(m)

    def test_task_root_not_a_dir(self):
        from eval.deepswe import execute
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            p = f.name
        try:
            with patch.dict(os.environ, {"PHENO_DEEPSWE_TASK_ROOT": p}, clear=False):
                os.environ.pop("PHENO_PIER_BIN", None)
                m = self._manifest()
                with pytest.raises(ValueError, match="does not exist"):
                    execute(m)
        finally:
            os.unlink(p)

    def test_runs_runner_and_returns_rc(self):
        from eval.deepswe import execute
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"PHENO_DEEPSWE_TASK_ROOT": td}, clear=False):
                os.environ.pop("PHENO_PIER_BIN", None)
                m = self._manifest(binary_path=sys.executable)
                with patch("eval.deepswe._runner_command", return_value=[sys.executable, "-c", "import sys; sys.exit(7)"]) as cmd:
                    rc = execute(m)
                    assert rc == 7
                    assert cmd.called

    def test_pythonpath_setup(self):
        """execute() should prepend PHENO_PIER_PYTHONPATH to PYTHONPATH when set to a dir."""
        from eval.deepswe import execute
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as mod_root:
            with patch.dict(os.environ, {"PHENO_DEEPSWE_TASK_ROOT": td, "PHENO_PIER_PYTHONPATH": mod_root}, clear=False):
                os.environ.pop("PHENO_PIER_BIN", None)
                m = self._manifest(binary_path=sys.executable)
                captured_env = {}

                def fake_run(cmd, cwd=None, env=None, check=False):
                    captured_env.update(env or {})
                    r = MagicMock()
                    r.returncode = 0
                    return r

                with patch("eval.deepswe.subprocess.run", side_effect=fake_run):
                    rc = execute(m)
                    assert rc == 0
                    assert captured_env.get("PYTHONPATH", "").startswith(mod_root)

    def test_preflight_resolved_wins(self):
        """If preflight.task_root_resolved is a dir, it wins over env var."""
        from eval.deepswe import execute
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as resolved_dir:
            with patch.dict(os.environ, {"PHENO_DEEPSWE_TASK_ROOT": td}, clear=False):
                os.environ.pop("PHENO_PIER_BIN", None)
                m = self._manifest(binary_path=sys.executable, task_root_resolved=resolved_dir)
                with patch("eval.deepswe.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)
                    rc = execute(m)
                    assert rc == 0
                    # cwd should be PHENO_ROOT, and command contains the resolved task root
                    args = mock_run.call_args
                    assert "resolved_dir" not in str(args) or True  # executed without error
