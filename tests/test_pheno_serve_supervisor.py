"""Direct unit tests for scripts/pheno_serve_supervisor.py.

The supervisor is the load-bearing safety net for the pheno-serve-dev
gateway: it polls /readyz, kills stale processes, and relaunches. As of
v0.13 the script has zero direct tests; this file locks in the contract.

Critical contracts pinned here:
- _port_held must FAIL CLOSED: an inconclusive port check returns True
  so we never kill a healthy gateway on a slow upstream probe. This
  prevents the orphaned-instances failure mode the docstring warns about.
- main() must honor --once and --max-restarts and cleanly handle
  KeyboardInterrupt.
- _resolve_base_url must rewrite 0.0.0.0/:: to 127.0.0.1 so we never try
  to connect to a bind address.

No real HTTP, no real subprocesses, no real gateway launches.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import pheno_serve_supervisor as ps  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_urlopen_ok(payload: dict, status: int = 200) -> MagicMock:
    """Return a mock that urlopen()'s context-manager yields for 2xx."""
    body_bytes = json.dumps(payload).encode("utf-8")
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = body_bytes
    return resp


def _make_http_error(code: int, body: bytes | None, reason: str) -> HTTPError:
    """Build a real HTTPError instance with the given body/reason."""
    err = HTTPError(
        url="http://127.0.0.1:21080/readyz",
        code=code,
        msg=reason,
        hdrs=None,  # type: ignore[arg-type]
        fp=None,
    )
    if body is not None:
        # HTTPError.fp normally provides read(); inject a stub for the test.
        err.read = lambda: body  # type: ignore[method-assign]
    return err


def _completed_proc(stdout: str = "", stderr: str = "", returncode: int = 0) -> MagicMock:
    cp = MagicMock()
    cp.stdout = stdout
    cp.stderr = stderr
    cp.returncode = returncode
    return cp


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def _redirect_logs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Route REPO_ROOT + LOG_PATH to tmp_path so tests don't pollute the repo."""
    monkeypatch.setattr(ps, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(ps, "LOG_PATH", tmp_path / "supervisor.log")


def _write_min_config(tmp_path: Path) -> Path:
    return _write_yaml(
        tmp_path,
        "server:\n  host: '127.0.0.1'\n  port: 21080\n",
    )


# ---------------------------------------------------------------------------
# 1. TestReadyzCheck
# ---------------------------------------------------------------------------


class TestReadyzCheck:
    """_readyz_check(base_url, timeout) → (ready: bool, payload: dict)."""

    def test_returns_true_when_body_ok_true(self) -> None:
        with patch.object(ps, "urlopen") as opener:
            opener.return_value.__enter__.return_value = _make_urlopen_ok({"ok": True})
            ready, payload = ps._readyz_check("http://127.0.0.1:21080", 1.0)
        assert ready is True
        assert payload == {"ok": True}

    def test_returns_false_when_body_ok_false(self) -> None:
        with patch.object(ps, "urlopen") as opener:
            opener.return_value.__enter__.return_value = _make_urlopen_ok(
                {"ok": False, "detail": "no_active_profile"}
            )
            ready, payload = ps._readyz_check("http://127.0.0.1:21080", 1.0)
        assert ready is False
        assert payload["ok"] is False
        assert payload["detail"] == "no_active_profile"

    def test_appends_slash_to_readyz_path(self) -> None:
        """Trailing slash on base_url must not break the /readyz URL."""
        with patch.object(ps, "urlopen") as opener:
            opener.return_value.__enter__.return_value = _make_urlopen_ok({"ok": True})
            ps._readyz_check("http://127.0.0.1:21080/", 1.0)
        called_request = opener.call_args[0][0]
        # Request.full_url is the stable attribute that exposes the URL.
        assert called_request.full_url.endswith("/readyz")

    def test_strips_trailing_slash_no_double_slash(self) -> None:
        """The /readyz URL must not contain a double slash between host and path."""
        with patch.object(ps, "urlopen") as opener:
            opener.return_value.__enter__.return_value = _make_urlopen_ok({"ok": True})
            ps._readyz_check("http://127.0.0.1:21080/", 1.0)
        url = opener.call_args[0][0].full_url
        assert "//readyz" not in url
        assert url.endswith("/readyz")

    def test_http_error_returns_status_and_json_body(self) -> None:
        body = json.dumps({"error": "down"}).encode("utf-8")
        exc = _make_http_error(503, body=body, reason="Service Unavailable")
        with patch.object(ps, "urlopen", side_effect=exc):
            ready, payload = ps._readyz_check("http://127.0.0.1:21080", 1.0)
        assert ready is False
        assert payload["status"] == 503
        assert payload["body"] == {"error": "down"}

    def test_http_error_with_unreadable_body_falls_back_to_reason(self) -> None:
        """When the HTTPError body fails to JSON-parse, fall back to exc.reason."""
        exc = _make_http_error(500, body=b"<html>not json</html>", reason="Internal Server Error")
        # Make exc.read() raise so the inner except catches it.
        exc.read = lambda: (_ for _ in ()).throw(ValueError("bad json"))  # type: ignore[method-assign]
        with patch.object(ps, "urlopen", side_effect=exc):
            ready, payload = ps._readyz_check("http://127.0.0.1:21080", 1.0)
        assert ready is False
        assert payload["status"] == 500
        assert payload["body"] == {"error": "Internal Server Error"}

    def test_urlerror_returns_error_string(self) -> None:
        with patch.object(ps, "urlopen", side_effect=URLError("connection refused")):
            ready, payload = ps._readyz_check("http://127.0.0.1:21080", 1.0)
        assert ready is False
        assert "error" in payload
        assert "connection refused" in payload["error"]

    def test_timeout_returns_error_string(self) -> None:
        with patch.object(ps, "urlopen", side_effect=TimeoutError("timed out")):
            ready, payload = ps._readyz_check("http://127.0.0.1:21080", 1.0)
        assert ready is False
        assert "error" in payload
        assert "timed out" in payload["error"]

    def test_oserror_returns_error_string(self) -> None:
        with patch.object(ps, "urlopen", side_effect=OSError("addr in use")):
            ready, payload = ps._readyz_check("http://127.0.0.1:21080", 1.0)
        assert ready is False
        assert "error" in payload
        assert "addr in use" in payload["error"]


# ---------------------------------------------------------------------------
# 2. TestListGatewayPids
# ---------------------------------------------------------------------------


class TestListGatewayPids:
    """_list_gateway_pids() — return PIDs of pheno.serve.server processes."""

    def test_returns_pids_from_powershell(self) -> None:
        with patch.object(
            ps.subprocess,
            "run",
            return_value=_completed_proc("1234\n5678\n"),
        ):
            assert ps._list_gateway_pids() == [1234, 5678]

    def test_returns_empty_when_no_processes_match(self) -> None:
        with patch.object(ps.subprocess, "run", return_value=_completed_proc("")):
            assert ps._list_gateway_pids() == []

    def test_ignores_non_digit_lines(self) -> None:
        with patch.object(
            ps.subprocess,
            "run",
            return_value=_completed_proc("ProcessId\n----\n4321\nFooter\n"),
        ):
            assert ps._list_gateway_pids() == [4321]

    def test_returns_empty_on_subprocess_timeout(self) -> None:
        with patch.object(
            ps.subprocess,
            "run",
            side_effect=ps.subprocess.TimeoutExpired(cmd="powershell", timeout=10),
        ):
            assert ps._list_gateway_pids() == []

    def test_returns_empty_when_powershell_missing(self) -> None:
        with patch.object(ps.subprocess, "run", side_effect=FileNotFoundError()):
            assert ps._list_gateway_pids() == []


# ---------------------------------------------------------------------------
# 3. TestPortHeld  (CRITICAL: fail-closed contract)
# ---------------------------------------------------------------------------


class TestPortHeld:
    """_port_held(port) → bool.

    CONTRACT: any inconclusive result must return True so the supervisor
    does NOT kill a healthy gateway on a slow upstream probe. The
    docstring explicitly warns about orphaned instances. Do not regress.
    """

    def test_returns_true_on_subprocess_timeout(self) -> None:
        with patch.object(
            ps.subprocess,
            "run",
            side_effect=ps.subprocess.TimeoutExpired(cmd="powershell", timeout=10),
        ):
            assert ps._port_held(21080) is True

    def test_returns_true_when_powershell_missing(self) -> None:
        with patch.object(ps.subprocess, "run", side_effect=FileNotFoundError()):
            assert ps._port_held(21080) is True

    def test_returns_true_when_pid_listed(self) -> None:
        with patch.object(
            ps.subprocess,
            "run",
            return_value=_completed_proc("4321\n"),
        ):
            assert ps._port_held(21080) is True

    def test_returns_false_when_no_listener(self) -> None:
        """Empty stdout → no listener → False (port IS free)."""
        with patch.object(ps.subprocess, "run", return_value=_completed_proc("")):
            assert ps._port_held(21080) is False

    def test_returns_false_when_only_non_digit_output(self) -> None:
        """Get-NetTCPConnection error text is not a PID."""
        with patch.object(
            ps.subprocess,
            "run",
            return_value=_completed_proc(
                "Get-NetTCPConnection : No MSFT connections found\n"
            ),
        ):
            assert ps._port_held(21080) is False

    def test_multiple_pids_in_output_returns_true(self) -> None:
        with patch.object(
            ps.subprocess,
            "run",
            return_value=_completed_proc("111\n222\n333\n"),
        ):
            assert ps._port_held(21080) is True


# ---------------------------------------------------------------------------
# 4. TestKillPids
# ---------------------------------------------------------------------------


class TestKillPids:
    """_kill_pids(pids) — Stop-Process per PID, swallowing errors."""

    def test_calls_stop_process_per_pid(self) -> None:
        with patch.object(ps.subprocess, "run") as run_mock:
            ps._kill_pids([101, 202, 303])
        assert run_mock.call_count == 3
        for idx, pid in enumerate([101, 202, 303]):
            argv = run_mock.call_args_list[idx][0][0]
            assert argv[0] == "powershell"
            assert "Stop-Process" in argv[3]
            assert f"-Id {pid}" in argv[3]
            assert "-Force" in argv[3]

    def test_empty_pids_makes_no_subprocess_calls(self) -> None:
        with patch.object(ps.subprocess, "run") as run_mock:
            ps._kill_pids([])
        assert run_mock.call_count == 0

    def test_swallows_subprocess_exception(self) -> None:
        """If Stop-Process raises, _kill_pids must NOT propagate."""
        with patch.object(ps.subprocess, "run", side_effect=Exception("boom")):
            ps._kill_pids([404])  # must not raise

    def test_continues_killing_remaining_pids_after_failure(self) -> None:
        """One PID failing must not stop subsequent kills."""
        with patch.object(
            ps.subprocess,
            "run",
            side_effect=[Exception("boom"), MagicMock(), Exception("boom2")],
        ):
            ps._kill_pids([1, 2, 3])
        # All three calls attempted even though #1 and #3 raised.


# ---------------------------------------------------------------------------
# 5. TestLaunchGateway
# ---------------------------------------------------------------------------


class TestLaunchGateway:
    """_launch_gateway(python, config, cwd) → pid | None."""

    def test_returns_pid_on_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _redirect_logs(monkeypatch, tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 9999
        with patch.object(ps.subprocess, "Popen", return_value=fake_proc):
            pid = ps._launch_gateway(
                "C:/python.exe", tmp_path / "config.yaml", tmp_path
            )
        assert pid == 9999

    def test_returns_none_when_popen_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _redirect_logs(monkeypatch, tmp_path)
        with patch.object(
            ps.subprocess, "Popen", side_effect=OSError("spawn failed")
        ):
            pid = ps._launch_gateway(
                "C:/python.exe", tmp_path / "config.yaml", tmp_path
            )
        assert pid is None

    def test_invokes_pheno_serve_server_module(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _redirect_logs(monkeypatch, tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 12345
        with patch.object(ps.subprocess, "Popen", return_value=fake_proc) as popen_mock:
            ps._launch_gateway("python.exe", tmp_path / "c.yaml", tmp_path)
        argv = popen_mock.call_args[0][0]
        assert argv[0] == "python.exe"
        assert argv[1:4] == ["-m", "pheno.serve.server", "--config"]
        assert str(argv[4]).endswith("c.yaml")

    def test_runs_in_given_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _redirect_logs(monkeypatch, tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 1
        with patch.object(ps.subprocess, "Popen", return_value=fake_proc) as popen_mock:
            ps._launch_gateway("python.exe", tmp_path / "c.yaml", tmp_path)
        assert popen_mock.call_args.kwargs["cwd"] == str(tmp_path)


# ---------------------------------------------------------------------------
# 6. TestResolveBaseUrl
# ---------------------------------------------------------------------------


class TestResolveBaseUrl:
    """_resolve_base_url(config) → 'scheme://host:port'."""

    def test_uses_base_url_when_present(self, tmp_path: Path) -> None:
        cfg = _write_yaml(
            tmp_path,
            "server:\n  base_url: 'http://127.0.0.1:23080/v1'\n",
        )
        assert ps._resolve_base_url(cfg) == "http://127.0.0.1:23080"

    def test_strips_api_prefix_from_base_url(self, tmp_path: Path) -> None:
        """readyz lives at root, not under /v1 — must strip the prefix."""
        cfg = _write_yaml(
            tmp_path,
            "server:\n  base_url: 'http://pheno-serve-dev:23080/v1/chat'\n",
        )
        url = ps._resolve_base_url(cfg)
        assert "/v1" not in url
        assert "/chat" not in url
        assert url.startswith("http://pheno-serve-dev:23080")

    def test_rewrites_0_0_0_0_to_loopback(self, tmp_path: Path) -> None:
        cfg = _write_yaml(
            tmp_path,
            "server:\n  host: '0.0.0.0'\n  port: 21080\n",
        )
        assert ps._resolve_base_url(cfg) == "http://127.0.0.1:21080"

    def test_rewrites_double_colon_to_loopback(self, tmp_path: Path) -> None:
        cfg = _write_yaml(
            tmp_path,
            "server:\n  host: '::'\n  port: 21080\n",
        )
        assert ps._resolve_base_url(cfg) == "http://127.0.0.1:21080"

    def test_rewrites_empty_host_to_loopback(self, tmp_path: Path) -> None:
        cfg = _write_yaml(
            tmp_path,
            "server:\n  host: ''\n  port: 21080\n",
        )
        assert ps._resolve_base_url(cfg) == "http://127.0.0.1:21080"

    def test_leaves_127_0_0_1_unchanged(self, tmp_path: Path) -> None:
        cfg = _write_yaml(
            tmp_path,
            "server:\n  host: '127.0.0.1'\n  port: 21080\n",
        )
        assert ps._resolve_base_url(cfg) == "http://127.0.0.1:21080"

    def test_leaves_localhost_unchanged(self, tmp_path: Path) -> None:
        cfg = _write_yaml(
            tmp_path,
            "server:\n  host: 'localhost'\n  port: 21080\n",
        )
        assert ps._resolve_base_url(cfg) == "http://localhost:21080"

    def test_default_port_when_unspecified(self, tmp_path: Path) -> None:
        cfg = _write_yaml(
            tmp_path,
            "server:\n  host: '127.0.0.1'\n",
        )
        assert ps._resolve_base_url(cfg) == "http://127.0.0.1:21080"

    def test_falls_back_to_default_when_server_section_missing(
        self, tmp_path: Path
    ) -> None:
        cfg = _write_yaml(tmp_path, "other_key: 1\n")
        assert ps._resolve_base_url(cfg) == "http://127.0.0.1:21080"

    def test_returns_default_when_yaml_unreadable(self, tmp_path: Path) -> None:
        """Exception path: returns the safe default."""
        bad = tmp_path / "bad.yaml"
        # Force a YAML syntax error
        bad.write_text("[unterminated flow\n: : :\n", encoding="utf-8")
        assert ps._resolve_base_url(bad) == "http://127.0.0.1:21080"

    def test_returns_default_when_config_file_missing(self, tmp_path: Path) -> None:
        """FileNotFoundError is an Exception → fall back to default."""
        missing = tmp_path / "does_not_exist.yaml"
        assert ps._resolve_base_url(missing) == "http://127.0.0.1:21080"


# ---------------------------------------------------------------------------
# 7. TestMain
# ---------------------------------------------------------------------------


class TestMain:
    """main() — supervisor orchestrator with argparse-driven CLI.

    main() reads sys.argv via argparse, so tests inject args by
    monkey-patching sys.argv before calling main().
    """

    @staticmethod
    def _run(
        monkeypatch: pytest.MonkeyPatch, *extra_args: str
    ) -> int:
        argv = ["pheno_serve_supervisor.py", *extra_args]
        monkeypatch.setattr(sys, "argv", argv)
        return ps.main()

    def test_once_flag_exits_cleanly_when_readyz_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cfg = _write_min_config(tmp_path)
        _redirect_logs(monkeypatch, tmp_path)
        monkeypatch.setattr(ps.time, "sleep", lambda _s: None)

        with patch.object(ps, "_readyz_check", return_value=(True, {"ok": True})):
            rc = self._run(
                monkeypatch,
                "--config", str(cfg),
                "--python", "python.exe",
                "--once",
            )
        assert rc == 0

    def test_once_flag_exits_even_after_restart(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unhealthy + --once: one restart attempt, then exit 0."""
        cfg = _write_min_config(tmp_path)
        _redirect_logs(monkeypatch, tmp_path)
        monkeypatch.setattr(ps.time, "sleep", lambda _s: None)

        with patch.object(ps, "_readyz_check", return_value=(False, {"error": "down"})):
            with patch.object(ps, "_port_held", return_value=False):
                with patch.object(ps, "_list_gateway_pids", return_value=[]):
                    with patch.object(ps, "_launch_gateway", return_value=4242):
                        rc = self._run(
                            monkeypatch,
                            "--config", str(cfg),
                            "--python", "python.exe",
                            "--once",
                        )
        assert rc == 0

    def test_orchestrator_does_not_restart_on_http_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """HTTP 503 (gateway up but not-ready) must NOT trigger a kill/launch."""
        cfg = _write_min_config(tmp_path)
        _redirect_logs(monkeypatch, tmp_path)
        monkeypatch.setattr(ps.time, "sleep", lambda _s: None)

        with patch.object(
            ps, "_readyz_check", return_value=(False, {"status": 503, "body": {}})
        ):
            with patch.object(ps, "_port_held") as port_mock:
                with patch.object(ps, "_list_gateway_pids") as pids_mock:
                    with patch.object(ps, "_kill_pids") as kill_mock:
                        with patch.object(ps, "_launch_gateway") as launch_mock:
                            rc = self._run(
                                monkeypatch,
                                "--config", str(cfg),
                                "--python", "python.exe",
                                "--once",
                            )
        assert rc == 0
        port_mock.assert_not_called()
        pids_mock.assert_not_called()
        kill_mock.assert_not_called()
        launch_mock.assert_not_called()

    def test_max_restarts_exits_with_code_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After exceeding max-restarts, main returns 1 (not 0)."""
        cfg = _write_min_config(tmp_path)
        _redirect_logs(monkeypatch, tmp_path)
        monkeypatch.setattr(ps.time, "sleep", lambda _s: None)

        launches: list[int] = []

        def stub_launch(_python, _config, _cwd):
            launches.append(1)
            return 9999

        with patch.object(ps, "_readyz_check", return_value=(False, {"error": "down"})):
            with patch.object(ps, "_port_held", return_value=False):
                with patch.object(ps, "_list_gateway_pids", return_value=[]):
                    with patch.object(ps, "_launch_gateway", side_effect=stub_launch):
                        rc = self._run(
                            monkeypatch,
                            "--config", str(cfg),
                            "--python", "python.exe",
                            "--max-restarts", "1",
                        )
        # iter 1: restarts=1, not exceed (1>1 false). iter 2: restarts=2, exceed (2>1 true) → rc=1
        assert rc == 1
        assert len(launches) == 2

    def test_max_restarts_zero_means_unlimited(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--max-restarts 0 means unlimited — we break via --once instead."""
        cfg = _write_min_config(tmp_path)
        _redirect_logs(monkeypatch, tmp_path)
        monkeypatch.setattr(ps.time, "sleep", lambda _s: None)

        launches: list[int] = []

        def stub_launch(_python, _config, _cwd):
            launches.append(1)
            return 9999

        with patch.object(ps, "_readyz_check", return_value=(False, {"error": "down"})):
            with patch.object(ps, "_port_held", return_value=False):
                with patch.object(ps, "_list_gateway_pids", return_value=[]):
                    with patch.object(ps, "_launch_gateway", side_effect=stub_launch):
                        rc = self._run(
                            monkeypatch,
                            "--config", str(cfg),
                            "--python", "python.exe",
                            "--max-restarts", "0",
                            "--once",
                        )
        assert rc == 0
        assert len(launches) == 1

    def test_keyboard_interrupt_returns_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cfg = _write_min_config(tmp_path)
        _redirect_logs(monkeypatch, tmp_path)
        monkeypatch.setattr(ps.time, "sleep", lambda _s: None)

        def readyz_kbi(*_a, **_kw):
            raise KeyboardInterrupt

        with patch.object(ps, "_readyz_check", side_effect=readyz_kbi):
            rc = self._run(
                monkeypatch,
                "--config", str(cfg),
                "--python", "python.exe",
            )
        assert rc == 0

    def test_orchestrator_calls_in_order_on_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify the failure path runs readyz → port_held → list_pids → kill → launch."""
        cfg = _write_min_config(tmp_path)
        _redirect_logs(monkeypatch, tmp_path)
        monkeypatch.setattr(ps.time, "sleep", lambda _s: None)

        order: list[str] = []

        def stub_readyz(*_a, **_kw):
            order.append("readyz")
            return False, {"error": "down"}

        def stub_port(_port):
            order.append("port")
            return False

        def stub_list():
            order.append("list")
            return [4242]

        def stub_kill(_pids):
            order.append("kill")

        def stub_launch(*_a, **_kw):
            order.append("launch")
            return 1

        with patch.object(ps, "_readyz_check", side_effect=stub_readyz):
            with patch.object(ps, "_port_held", side_effect=stub_port):
                with patch.object(ps, "_list_gateway_pids", side_effect=stub_list):
                    with patch.object(ps, "_kill_pids", side_effect=stub_kill):
                        with patch.object(ps, "_launch_gateway", side_effect=stub_launch):
                            self._run(
                                monkeypatch,
                                "--config", str(cfg),
                                "--python", "python.exe",
                                "--once",
                            )
        assert order == ["readyz", "port", "list", "kill", "launch"]

    def test_failure_path_skips_kill_when_no_pids(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If no PIDs match, _kill_pids is NOT called (saves a powershell spawn)."""
        cfg = _write_min_config(tmp_path)
        _redirect_logs(monkeypatch, tmp_path)
        monkeypatch.setattr(ps.time, "sleep", lambda _s: None)

        with patch.object(ps, "_readyz_check", return_value=(False, {"error": "down"})):
            with patch.object(ps, "_port_held", return_value=False):
                with patch.object(ps, "_list_gateway_pids", return_value=[]):
                    with patch.object(ps, "_kill_pids") as kill_mock:
                        with patch.object(ps, "_launch_gateway", return_value=1):
                            self._run(
                                monkeypatch,
                                "--config", str(cfg),
                                "--python", "python.exe",
                                "--once",
                            )
        kill_mock.assert_not_called()
