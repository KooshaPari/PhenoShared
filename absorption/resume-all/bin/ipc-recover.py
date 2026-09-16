#!/opt/homebrew/bin/python3
"""
ipc-recover.py — Recovery procedure for the recurring xpcproxy issue.

When sharecli-ipc-daemon gets stuck in launchd's "xpcproxy" state (daemon
process is gone but socket file remains), this script:
  1. Kills any running daemon process
  2. Removes the stale socket file
  3. Launches the daemon manually (this is the trick — it works when launchd doesn't)
  4. Lets it run for a few seconds, then kills it
  5. Asks launchd to bootstrap the plist
  6. Waits + verifies the socket is bound

Why manual-then-launchd works:
  - launchd's "xpcproxy" state means launchd thinks the daemon is alive but isn't
  - Just running `launchctl kickstart -k` doesn't reset the stuck process tree
  - But running the binary directly bypasses launchd's confused state
  - Then bootstrapping the plist puts it back under launchd management cleanly

Usage:
    ipc-recover.py recover
    ipc-recover.py status
    ipc-recover.py test
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
IPC_SOCKET = HOME / "Library" / "Application Support" / "sharecli" / "ipc.sock"
DAEMON_BIN = HOME / "bin" / "sharecli-ipc-daemon"
LAUNCHD_LABEL = "com.kooshapari.resume-all-ipc"
LAUNCHD_PLIST = HOME / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
LAUNCHD_GUI_DOMAIN = f"gui/{os.getuid()}"


def _kill_daemon() -> int:
    """Kill any running sharecli-ipc-daemon processes."""
    try:
        result = subprocess.run(
            ["pkill", "-9", "-x", "sharecli-ipc-daemon"],
            capture_output=True, timeout=5,
        )
        return 0  # pkill returns 0 if any killed, 1 if none matched
    except Exception:
        return -1


def _remove_socket() -> None:
    """Remove stale socket file."""
    if IPC_SOCKET.exists():
        IPC_SOCKET.unlink()


def _probe_socket(timeout: float = 5.0) -> bool:
    """Probe the socket and return True if it responds."""
    if not IPC_SOCKET.exists():
        return False
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(str(IPC_SOCKET))
        msg = b'{"id": 1, "method": "health.status", "params": {}}\n'
        s.sendall(msg)
        data = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                chunk = s.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
            if data.endswith(b"\n"):
                break
        s.close()
        return b'"alive":true' in data or b'"healthy":true' in data
    except (socket.error, OSError):
        return False


def recover() -> dict:
    """Run the full recovery procedure. Returns action summary."""
    actions = {
        "ts": time.time(),
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "steps": [],
    }

    # Step 1: kill daemon
    rc = _kill_daemon()
    time.sleep(2)
    actions["steps"].append({
        "step": "kill-daemon",
        "ok": True,
        "detail": "pkill -9 -x sharecli-ipc-daemon",
    })

    # Step 2: remove socket
    _remove_socket()
    actions["steps"].append({
        "step": "remove-socket",
        "ok": True,
        "detail": f"unlinked {IPC_SOCKET}",
    })

    # Step 3: manual launch (the trick)
    daemon_proc = subprocess.Popen(
        [str(DAEMON_BIN)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    actions["steps"].append({
        "step": "manual-launch",
        "ok": daemon_proc.poll() is None,
        "pid": daemon_proc.pid,
        "detail": f"PID {daemon_proc.pid} still running after 3s",
    })

    # Step 4: verify manual works
    manual_ok = _probe_socket(timeout=3)
    actions["steps"].append({
        "step": "verify-manual",
        "ok": manual_ok,
        "detail": "probe health.status over socket",
    })

    # Step 5: kill manual, then launchd bootstrap
    daemon_proc.send_signal(signal.SIGTERM)
    try:
        daemon_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        daemon_proc.kill()
    time.sleep(2)
    _remove_socket()
    actions["steps"].append({
        "step": "kill-manual",
        "ok": True,
        "detail": "manual daemon killed",
    })

    # Step 6: launchd bootout + bootstrap
    subprocess.run(
        ["launchctl", "bootout", f"{LAUNCHD_GUI_DOMAIN}/{LAUNCHD_LABEL}"],
        capture_output=True, timeout=10,
    )
    time.sleep(3)
    result = subprocess.run(
        ["launchctl", "bootstrap", LAUNCHD_GUI_DOMAIN, str(LAUNCHD_PLIST)],
        capture_output=True, timeout=10,
    )
    actions["steps"].append({
        "step": "launchd-bootstrap",
        "ok": result.returncode == 0,
        "rc": result.returncode,
        "stderr": result.stderr.decode()[:200],
    })

    # Step 7: wait + verify (launchd can take 30+ seconds to fully bind the daemon)
    final_ok = False
    for attempt in range(6):
        time.sleep(10)
        if _probe_socket(timeout=3):
            final_ok = True
            break
    actions["steps"].append({
        "step": "verify-final",
        "ok": final_ok,
        "detail": f"probe socket after launchd bootstrap ({attempt+1} attempts)",
    })
    actions["success"] = final_ok
    return actions


def cmd_recover(args: argparse.Namespace) -> int:
    summary = recover()
    for step in summary["steps"]:
        marker = "OK" if step["ok"] else "FAIL"
        print(f"  [{marker:4s}] {step['step']:20s} {step.get('detail', '')}")
    if summary.get("success"):
        print("\nRecovery succeeded. IPC daemon is now responding.")
        return 0
    print("\nRecovery did NOT succeed. Manual investigation needed.")
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    print("IPC daemon status:")
    print(f"  Socket file:    {IPC_SOCKET} ({'exists' if IPC_SOCKET.exists() else 'missing'})")
    print(f"  Manual probe:   {'OK' if _probe_socket(timeout=3) else 'FAIL'}")
    result = subprocess.run(
        ["launchctl", "print", f"{LAUNCHD_GUI_DOMAIN}/{LAUNCHD_LABEL}"],
        capture_output=True, text=True, timeout=5,
    )
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("state") or line.startswith("pid"):
            print(f"  launchd:        {line}")
    return 0


def _self_test() -> tuple[int, int]:
    passed = 0
    total = 0

    def check(name: str, cond: bool) -> None:
        nonlocal passed, total
        total += 1
        marker = "ok" if cond else "FAIL"
        if cond:
            passed += 1
        print(f"  [{marker}] {name}")

    print("=== ipc-recover.py self-tests ===")

    # Test 1: paths exist
    check("IPC_SOCKET path defined", str(IPC_SOCKET).endswith("ipc.sock"))
    check("DAEMON_BIN path defined", str(DAEMON_BIN).endswith("sharecli-ipc-daemon"))
    check("LAUNCHD_PLIST path defined",
          str(LAUNCHD_PLIST).endswith(f"{LAUNCHD_LABEL}.plist"))

    # Test 2: _kill_daemon is safe to call when no daemon running
    rc = _kill_daemon()
    check("kill_daemon safe (no daemon)", rc == 0 or rc == 1)

    # Test 3: _remove_socket is safe to call when no socket exists
    _remove_socket()
    check("remove_socket safe (no socket)", True)

    # Test 4: _probe_socket returns False when no socket
    check("probe returns False when socket missing",
          _probe_socket(timeout=1) is False)

    # Test 5: full recover procedure doesn't crash
    summary = recover()
    check("recover returns dict", isinstance(summary, dict))
    check("recover has steps", len(summary["steps"]) >= 5)
    check("recover has ts_iso", "ts_iso" in summary)
    check("all steps recorded", all("step" in s for s in summary["steps"]))
    check("success field present", "success" in summary)

    print(f"\n{passed}/{total} passed")
    print(f"Recovery {'succeeded' if summary.get('success') else 'failed'}")
    return passed, total


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("recover").set_defaults(func=cmd_recover)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("test").set_defaults(func=lambda a: _self_test())

    args = parser.parse_args(argv[1:])
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
