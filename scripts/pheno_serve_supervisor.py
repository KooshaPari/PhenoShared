#!/usr/bin/env python3
"""pheno-serve-dev supervisor — keeps the pheno-serve-dev gateway alive.

N03 deliverable. Runs as a scheduled task (PhenoHarness-PhenoServeSupervisor).
Polls the gateway's /readyz endpoint on a fixed interval; if the gateway is
unhealthy or absent, kills any stale pheno-serve processes and launches a
fresh one. Logs JSONL events to .runtime/pheno-serve-supervisor.log.

This is the load-bearing safety net for the dev box: the gateway is the
single point of entry for every eval, so a crash loop here silently breaks
all downstream evals. The supervisor trades a few extra restarts for
permanent liveness.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / ".runtime" / "pheno-serve-supervisor.log"


def _log(event: str, **fields: object) -> None:
    """Append a JSONL event to the supervisor log."""
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
        **fields,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _readyz_check(base_url: str, timeout: float) -> tuple[bool, dict]:
    """Return (ready, payload_or_error)."""
    url = base_url.rstrip("/") + "/readyz"
    req = Request(url, method="GET")
    try:
        with (
            urlopen(req, timeout=timeout) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            body = json.loads(resp.read().decode("utf-8"))
            return 200 <= resp.status < 300 and body.get("ok") is True, body
    except HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except Exception:
            body = {"error": exc.reason}
        return False, {"status": exc.code, "body": body}
    except (URLError, OSError, TimeoutError) as exc:
        return False, {"error": str(exc)}


def _list_gateway_pids() -> list[int]:
    """Return PIDs of running pheno.serve.server processes (Windows)."""
    try:
        ps = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'pheno\\.serve\\.server' } | Select-Object -ExpandProperty ProcessId",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        _log("list_pids_failed", error=str(exc))
        return []
    out = []
    for line in ps.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            out.append(int(line))
    return out


def _listen_port(base_url: str) -> int:
    """Extract the listen port from the gateway base URL."""
    try:
        from urllib.parse import urlsplit

        return urlsplit(base_url).port or 21080
    except Exception:
        return 21080


def _port_held(port: int) -> bool:
    """Return True if any process holds the given TCP listen port (Windows).

    The gateway can be alive-but-slow: its /readyz handler blocks up to
    upstream_timeout_s (60s) probing upstream, so a bounded readyz probe can
    time out while the gateway itself is perfectly healthy. Before treating
    a timeout as a dead gateway we must confirm the port is actually free;
    otherwise every slow-upstream moment kills and relaunches the gateway
    and the supervisor accumulates orphaned instances.
    """
    try:
        ps = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        _log("port_check_failed", error=str(exc))
        return True  # fail closed: never kill on an inconclusive check
    return any(line.strip().isdigit() for line in ps.stdout.splitlines())


def _kill_pids(pids: list[int]) -> None:
    for pid in pids:
        try:
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"Stop-Process -Id {pid} -Force",
                ],
                capture_output=True,
                timeout=10,
            )
            _log("kill_pid", pid=pid)
        except Exception as exc:
            _log("kill_pid_failed", pid=pid, error=str(exc))


def _launch_gateway(python: str, config: Path, cwd: Path) -> int | None:
    """Launch a fresh gateway as a detached process."""
    log_out = REPO_ROOT / ".runtime" / "pheno_serve_supervisor.out.log"
    log_err = REPO_ROOT / ".runtime" / "pheno_serve_supervisor.err.log"
    log_out.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.Popen(
            [python, "-m", "pheno.serve.server", "--config", str(config)],
            cwd=str(cwd),
            stdout=log_out.open("a", encoding="utf-8"),
            stderr=log_err.open("a", encoding="utf-8"),
            creationflags=subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
            if hasattr(subprocess, "DETACHED_PROCESS")
            else 0,
        )
        _log("launch_gateway", pid=proc.pid, config=str(config))
        return proc.pid
    except Exception as exc:
        _log("launch_failed", error=str(exc))
        return None


def _resolve_base_url(config: Path) -> str:
    """Resolve the gateway origin (scheme://host:port) for readyz probes.

    Prefers server.base_url, stripped to its origin. The gateway serves
    /readyz at the root (not under /v1), so the /v1 API prefix must be
    dropped. Falls back to server.host/server.port with a bind-host
    substitution: a listen address like 0.0.0.0 is not a valid connect
    destination on Windows (WinError 10049), so 0.0.0.0/:: -> 127.0.0.1.
    """
    try:
        from urllib.parse import urlparse

        import yaml  # local import — keep startup cheap

        cfg = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        server = cfg.get("server", {}) or {}
        base = (server.get("base_url") or "").strip()
        if base:
            parsed = urlparse(base)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        host = (server.get("host") or "127.0.0.1").strip()
        if host in ("0.0.0.0", "::", ""):  # nosec B104 — bind guard rewrites 0.0.0.0 to loopback, no external bind, reviewed false positive
            host = "127.0.0.1"
        port = int(server.get("port", 21080))
        return f"http://{host}:{port}"
    except Exception as exc:
        _log("resolve_base_url_failed", error=str(exc))
        return "http://127.0.0.1:21080"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="pheno-serve-dev supervisor")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--python", required=True, help="path to python.exe")
    parser.add_argument(
        "--interval", type=float, default=15.0, help="seconds between readyz polls"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=70.0,
        help="readyz HTTP timeout (must exceed the gateway's upstream probe bound of 60s)",
    )
    parser.add_argument(
        "--once", action="store_true", help="run a single check and exit"
    )
    parser.add_argument("--max-restarts", type=int, default=0, help="0 = unlimited")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not args.config.is_absolute():
        args.config = (REPO_ROOT / args.config).resolve()
    if not args.python:
        args.python = sys.executable

    base_url = _resolve_base_url(args.config)
    _log(
        "startup",
        config=str(args.config),
        python=args.python,
        base_url=base_url,
        interval=args.interval,
    )

    restarts = 0
    try:
        while True:
            ready, detail = _readyz_check(base_url, args.timeout)
            if ready:
                _log("readyz_ok", detail=detail)
            elif "status" in detail:
                # Gateway is up but reports not-ready (e.g. no routable
                # profiles because models are gated/purged). Keep it alive:
                # killing and relaunching cannot change admission state and
                # would turn a healthy-but-dormant gateway into a crash loop.
                # Only restart on connection-level failure (gateway dead).
                _log("readyz_not_ready", detail=detail)
            else:
                # Connection-level failure OR a bounded-probe timeout. Do not
                # trust a timeout alone: the gateway's readyz handler blocks
                # up to upstream_timeout_s (60s), so a 70s probe can still
                # time out on a slow upstream while the gateway is alive.
                # Only restart when the listen port is actually free.
                port = _listen_port(base_url)
                if _port_held(port):
                    _log("readyz_timeout_but_alive", port=port, detail=detail)
                else:
                    _log("readyz_fail", port=port, detail=detail)
                    pids = _list_gateway_pids()
                    if pids:
                        _log("kill_gw_pids", pids=pids)
                        _kill_pids(pids)
                    time.sleep(2)  # let the OS release the port
                    _launch_gateway(args.python, args.config, REPO_ROOT)
                    restarts += 1
                    if args.max_restarts and restarts > args.max_restarts:
                        _log("max_restarts_exceeded", restarts=restarts)
                        return 1
                    time.sleep(5)  # let the new gateway bind the port
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        _log("shutdown_signal")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
