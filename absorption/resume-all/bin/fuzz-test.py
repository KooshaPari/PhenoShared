#!/usr/bin/env python3
"""
fuzz-test — fuzz the resume-all JSON-RPC parsers.

Phase F06. Generates malformed NDJSON requests and feeds them to a TEMP IPC
daemon (custom socket path, never touches production). Reports any crashes,
panics, timeouts, or stdout corruption to ~/.local/share/resume-all/fuzz-results.jsonl.

Usage:
    fuzz-test run                     # run all fuzz cases
    fuzz-test report                  # summarize results
    fuzz-test test                    # inline self-tests (no daemon spawned)

CRITICAL: NEVER spawn the production daemon. Always pass --socket=/tmp/fuzz-ipc.sock.
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
import tempfile
import time
import uuid
from pathlib import Path

FUZZ_SOCKET = "/tmp/fuzz-ipc.sock"
DAEMON_BIN = "/Users/kooshapari/bin/sharecli-ipc-daemon"
MCP_BIN = "/Users/kooshapari/bin/thegent-mcp"
RESULTS_FILE = Path.home() / ".local/share/resume-all/fuzz-results.jsonl"
TIMEOUT_S = 2.0

# ---------------------------------------------------------------------------
# Fuzz case generators — each returns a list[str] of inputs to send.
# ---------------------------------------------------------------------------

def case_empty() -> list[str]:
    return [""]

def case_only_newlines() -> list[str]:
    return ["\n", "\n\n\n", "\n\n\n\n\n\n"]

def case_truncated_json() -> list[str]:
    return [
        '{"jsonrpc":"2.0","id":1,"method":',
        '{"jsonrpc":',
        '{"jsonrpc":"2.0","id":1,"method":"health.status","params":',
        '{"',
        '{',
    ]

def case_garbage_bytes() -> list[str]:
    """Random binary noise that doesn't look like JSON at all."""
    return [
        b"\x00\xff" * 512,
        b"\xfe\xed\xfa\xce" * 256,
        b"\n\r\n\r" * 128,
    ]

def case_huge_string() -> list[str]:
    return [
        '{"jsonrpc":"2.0","id":1,"method":"' + ("A" * (1024 * 1024)) + '","params":{}}',
    ]

def case_wrong_types() -> list[str]:
    return [
        '{"jsonrpc":42,"id":1,"method":"health.status"}',
        '{"jsonrpc":"2.0","id":"not-a-number","method":42}',
        '{"jsonrpc":"2.0","id":null,"method":"health.status"}',
        '{"jsonrpc":"2.0","id":[1,2,3],"method":"health.status"}',
        '{"jsonrpc":"2.0","id":{"nested":"obj"},"method":"health.status"}',
    ]

def case_missing_required() -> list[str]:
    return [
        '{"jsonrpc":"2.0"}',
        '{"id":1}',
        '{"method":"health.status"}',
        '{}',
        '{"jsonrpc":"2.0","id":1}',
        '{"jsonrpc":"2.0","method":"health.status"}',
    ]

def case_unknown_method() -> list[str]:
    return [
        '{"jsonrpc":"2.0","id":1,"method":"definitely.not.a.real.method","params":{}}',
        '{"jsonrpc":"2.0","id":1,"method":"","params":{}}',
        '{"jsonrpc":"2.0","id":1,"method":"../etc/passwd","params":{}}',
        '{"jsonrpc":"2.0","id":1,"method":"__import__","params":{}}',
    ]

def case_nested_weird() -> list[str]:
    return [
        '{"jsonrpc":"2.0","id":{"$ref":"$"},"method":"health.status","params":{"$ref":"$"}}',
        '{"jsonrpc":"2.0","id":1,"method":"health.status","params":{"__proto__":{"polluted":true}}}',
    ]

def case_unicode_edge() -> list[str]:
    return [
        '{"jsonrpc":"2.0","id":1,"method":"\u0000\u0001\u0002","params":{}}',
        '{"jsonrpc":"2.0","id":1,"method":"health.status","params":{"k":"\\u0000\\ud800"}}',
    ]

def case_oversized_params() -> list[str]:
    big_array = "[" + ",".join(["1"] * 10000) + "]"
    return [f'{{"jsonrpc":"2.0","id":1,"method":"health.status","params":{{"x":{big_array}}}}}']

def case_methods_with_weird_params() -> list[str]:
    """All 4 known methods, each with empty/null/weird params."""
    cases = []
    for method in ("health.status", "process.list", "status.snapshot", "monitoring.report"):
        cases.append(f'{{"jsonrpc":"2.0","id":1,"method":"{method}","params":{{}}}}')
        cases.append(f'{{"jsonrpc":"2.0","id":1,"method":"{method}","params":null}}')
        cases.append(f'{{"jsonrpc":"2.0","id":1,"method":"{method}"}}')
        cases.append(f'{{"jsonrpc":"2.0","id":1,"method":"{method}","params":"string-not-object"}}')
    return cases

def case_frame_attacks() -> list[str]:
    return [
        "A" * (2 * 1024 * 1024),  # 2MB single line
        "no newline at end of frame",
        '{"jsonrpc":"2.0","id":1,"method":"health.status","params":{}}',  # no \n at end
    ]

def case_rapid_repeat() -> list[str]:
    """100 copies of a valid request in one frame."""
    valid = '{"jsonrpc":"2.0","id":1,"method":"health.status","params":{}}'
    return [("\n".join([valid] * 100)) + "\n"]

ALL_CASES = [
    ("empty", case_empty),
    ("only_newlines", case_only_newlines),
    ("truncated_json", case_truncated_json),
    ("garbage_bytes", case_garbage_bytes),
    ("huge_string", case_huge_string),
    ("wrong_types", case_wrong_types),
    ("missing_required", case_missing_required),
    ("unknown_method", case_unknown_method),
    ("nested_weird", case_nested_weird),
    ("unicode_edge", case_unicode_edge),
    ("oversized_params", case_oversized_params),
    ("methods_with_weird_params", case_methods_with_weird_params),
    ("frame_attacks", case_frame_attacks),
    ("rapid_repeat", case_rapid_repeat),
]

# ---------------------------------------------------------------------------
# Crash detection
# ---------------------------------------------------------------------------

CRASH_MARKERS = (b"panic", b"FATAL", b"abort", b"Segmentation fault", b"Abort trap")

def is_crashed(stderr: bytes, returncode: int) -> bool:
    if returncode < 0:
        return True  # killed by signal
    if returncode != 0 and returncode not in (None,):
        # Some servers may exit non-zero on malformed input — only count it as crash if stderr has a marker
        return any(m in stderr for m in CRASH_MARKERS)
    return any(m in stderr for m in CRASH_MARKERS)

def verify_ndjson_stdout(stdout: bytes) -> tuple[bool, int, str]:
    """Verify that stdout is valid NDJSON: each line is parseable JSON or empty."""
    if not stdout:
        return True, 0, "empty"
    try:
        text = stdout.decode("utf-8", errors="replace")
    except Exception as e:
        return False, 0, f"decode error: {e}"
    lines = [l for l in text.split("\n") if l.strip()]
    parsed = 0
    for line in lines:
        try:
            json.loads(line)
            parsed += 1
        except json.JSONDecodeError as e:
            return False, parsed, f"non-JSON line: {line[:60]!r} ({e})"
    return True, parsed, "ok"

# ---------------------------------------------------------------------------
# Spawn temp IPC daemon
# ---------------------------------------------------------------------------

def cleanup_old_socket() -> None:
    try:
        os.unlink(FUZZ_SOCKET)
    except FileNotFoundError:
        pass

def spawn_temp_daemon() -> subprocess.Popen | None:
    """Spawn a temp IPC daemon on FUZZ_SOCKET. Returns None if spawn failed."""
    cleanup_old_socket()
    if not Path(DAEMON_BIN).exists():
        return None
    env = os.environ.copy()
    env["HOME"] = str(Path.home())
    env["SHARECLI_IPC_SOCKET"] = FUZZ_SOCKET  # override default socket path
    try:
        proc = subprocess.Popen(
            [DAEMON_BIN],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait for socket to bind
        for _ in range(30):
            if Path(FUZZ_SOCKET).exists():
                return proc
            time.sleep(0.1)
        proc.kill()
        return None
    except Exception:
        return None

def kill_proc(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=2)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Probe targets
# ---------------------------------------------------------------------------

def probe_ipd_daemon(payload) -> dict:
    """Send payload over NDJSON to temp IPC daemon, capture response."""
    result = {
        "target": "ipc",
        "input_kind": "?",
        "crashed": False,
        "stderr_excerpt": "",
        "stdout_lines": 0,
        "ndjson_ok": False,
        "error": None,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    # Spawn temp daemon
    proc = spawn_temp_daemon()
    if proc is None:
        result["error"] = "spawn_failed"
        return result
    try:
        if isinstance(payload, str):
            payload_bytes = payload.encode("utf-8")
        elif isinstance(payload, bytes):
            payload_bytes = payload
        else:
            payload_bytes = str(payload).encode("utf-8")

        # Connect, send, read response
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT_S)
        try:
            sock.connect(FUZZ_SOCKET)
            sock.sendall(payload_bytes)
            data = b""
            try:
                while True:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    data += chunk
            except socket.timeout:
                pass
        finally:
            sock.close()

        # Check if daemon is still alive
        time.sleep(0.05)
        alive = proc.poll() is None

        # Capture stderr by reading non-blocking (peek)
        stderr_data = proc.stderr.read1(4096) if proc.stderr else b""

        result["ndjson_ok"], result["stdout_lines"], msg = verify_ndjson_stdout(data)
        result["stderr_excerpt"] = stderr_data[:200].decode("utf-8", errors="replace").strip()
        result["crashed"] = is_crashed(stderr_data, proc.returncode) if not alive else False
        if not alive and not result["crashed"]:
            # Exited but no crash marker — still a finding
            result["crashed"] = True
            result["stderr_excerpt"] += f" [exit={proc.returncode}]"
    except Exception as e:
        result["error"] = str(e)
    finally:
        kill_proc(proc)
        cleanup_old_socket()
    return result

def probe_mcp_server(payload) -> dict:
    """Send payload over stdio to MCP server, capture response."""
    result = {
        "target": "mcp",
        "input_kind": "?",
        "crashed": False,
        "stderr_excerpt": "",
        "stdout_lines": 0,
        "ndjson_ok": False,
        "error": None,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if not Path(MCP_BIN).exists():
        result["error"] = "mcp_binary_missing"
        return result
    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
    elif isinstance(payload, bytes):
        payload_bytes = payload
    else:
        payload_bytes = str(payload).encode("utf-8")
    try:
        proc = subprocess.Popen(
            [MCP_BIN],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout, stderr = proc.communicate(payload_bytes, timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            result["crashed"] = True
            result["stderr_excerpt"] = "timeout"
        alive = proc.returncode is None or proc.returncode == 0
        result["ndjson_ok"], result["stdout_lines"], msg = verify_ndjson_stdout(stdout)
        result["stderr_excerpt"] = stderr[:200].decode("utf-8", errors="replace").strip()
        if is_crashed(stderr, proc.returncode):
            result["crashed"] = True
    except Exception as e:
        result["error"] = str(e)
    finally:
        kill_proc(proc)
    return result

# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def write_result(r: dict) -> None:
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_FILE.open("a") as f:
        f.write(json.dumps(r) + "\n")

def run_all() -> dict:
    summary = {"cases_run": 0, "ipc_crashes": 0, "mcp_crashes": 0, "errors": 0, "total_inputs": 0}
    # Clear old results
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text("")
    started = time.time()
    for kind, gen in ALL_CASES:
        inputs = gen()
        for payload in inputs:
            summary["cases_run"] += 1
            summary["total_inputs"] += len(inputs)
            for target, fn in (("ipc", probe_ipd_daemon), ("mcp", probe_mcp_server)):
                r = fn(payload)
                r["input_kind"] = kind
                write_result(r)
                if r.get("error"):
                    summary["errors"] += 1
                if r["crashed"]:
                    summary[f"{target}_crashes"] += 1
            # Bail if taking too long
            if time.time() - started > 60:
                print(f"fuzz-test: hit 60s limit, stopping at {summary['cases_run']} cases")
                return summary
    return summary

def report() -> str:
    if not RESULTS_FILE.exists():
        return "fuzz-test: no results yet — run `fuzz-test run` first"
    rows = [json.loads(l) for l in RESULTS_FILE.read_text().splitlines() if l.strip()]
    by_target: dict[str, list] = {"ipc": [], "mcp": []}
    for r in rows:
        by_target.setdefault(r["target"], []).append(r)
    lines = ["# Fuzz Test Report", ""]
    lines.append(f"- Total inputs tested: {len(rows)}")
    for target, rs in by_target.items():
        crashes = [r for r in rs if r["crashed"]]
        errors = [r for r in rs if r.get("error")]
        non_ndjson = [r for r in rs if not r["ndjson_ok"]]
        lines.append(f"## {target}")
        lines.append(f"- Inputs: {len(rs)}")
        lines.append(f"- Crashes: {len(crashes)}")
        lines.append(f"- Errors (probe failed): {len(errors)}")
        lines.append(f"- Non-NDJSON stdout: {len(non_ndjson)}")
        if crashes:
            lines.append("### Crash details")
            for c in crashes[:10]:
                lines.append(f"- `{c['input_kind']}` → stderr: `{c['stderr_excerpt'][:100]}`")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Self-tests (no daemon spawned)
# ---------------------------------------------------------------------------

def self_tests() -> int:
    """3+ inline self-tests. Returns 0 on pass, 1 on fail."""
    print("=== fuzz-test self-tests ===")
    failed = 0

    # 1. case generators return non-empty lists
    for name, gen in ALL_CASES:
        out = gen()
        if not out or len(out) == 0:
            print(f"  [{name}] FAIL: empty output")
            failed += 1
        else:
            print(f"  [{name}] ok ({len(out)} cases)")
    if all(gen() for _, gen in ALL_CASES):
        print("  [1] all case generators produce inputs  ok")

    # 2. verify_ndjson_stdout parses valid JSON
    valid = b'{"a":1}\n{"b":2}\n'
    ok, n, msg = verify_ndjson_stdout(valid)
    if ok and n == 2:
        print("  [2] valid NDJSON parses  ok")
    else:
        print(f"  [2] valid NDJSON parses  FAIL ({msg})")
        failed += 1

    # 3. verify_ndjson_stdout rejects garbage
    bad = b'{"a":1}\nthis is not json\n'
    ok, n, msg = verify_ndjson_stdout(bad)
    if not ok:
        print(f"  [3] garbage NDJSON rejected  ok ({msg[:50]})")
    else:
        print("  [3] garbage NDJSON rejected  FAIL (accepted)")
        failed += 1

    # 4. is_crashed detects "panic" in stderr
    if is_crashed(b"thread 'main' panicked at foo", 0):
        print("  [4] panic detection  ok")
    else:
        print("  [4] panic detection  FAIL")
        failed += 1

    # 5. is_crashed ignores normal stderr
    if not is_crashed(b"normal log output", 0):
        print("  [5] normal stderr ignored  ok")
    else:
        print("  [5] normal stderr ignored  FAIL")
        failed += 1

    print(f"=== {'PASS' if failed == 0 else 'FAIL'} ({failed} failures) ===")
    return failed

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Fuzz resume-all JSON-RPC parsers")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="run all fuzz cases")
    sub.add_parser("report", help="summarize previous results")
    sub.add_parser("test", help="inline self-tests (no daemon spawned)")

    args = parser.parse_args()

    if args.cmd == "test":
        return self_tests()
    if args.cmd == "report":
        print(report())
        return 0
    if args.cmd == "run":
        print("fuzz-test: spawning temp daemon on", FUZZ_SOCKET)
        summary = run_all()
        print(f"fuzz-test: {summary}")
        print(f"results: {RESULTS_FILE}")
        # Non-zero exit if any crashes found
        return 1 if (summary["ipc_crashes"] or summary["mcp_crashes"]) else 0

    return 1

if __name__ == "__main__":
    sys.exit(main())
