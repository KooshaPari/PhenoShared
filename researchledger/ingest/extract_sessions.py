#!/usr/bin/env python3
"""
extract_sessions.py — Session ledger driver + CLI.

Drives the per-harness extractors in extractors.py and the opencode-usage
aggregator in aggregate_opencode_usage.py. All extraction logic lives in
those modules; this file handles:
  - DB schema (open_db)
  - row insertion (insert_session)
  - Mac + Windows sources via SSH (run_mac, run_desk)
  - Python interpreter resolution (_resolve_desk_python)
  - SQLite merge from remote desk (run_desk, _merge_remote_db)
  - CLI (main)

Usage:
  python3 extract_sessions.py --device mac
  python3 extract_sessions.py --device desk --ssh koosh@100.96.135.160
  python3 extract_sessions.py --device both
  python3 extract_sessions.py --device both --assert-min "jcode/mac:30" --assert-min "codex/desk:2900"
"""
import argparse
import os
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from extractors import (
    extract_codex, extract_claude, extract_gemini,
    extract_helioslite, extract_opencode,
    APR_1_2025, DEFAULT_DB,
)
from ledger_db import open_db
from jcode_extractor import extract_jcode
from spend_extractor import extract_spend

# Schema + write contract (was in extractors.py before round-4 split)
# These are defined below in this file.

def run_mac(conn):
    """Extract from local (Mac) sources."""
    counts = {}
    counts["codex"] = extract_codex(conn, "mac", os.path.expanduser("~/.codex"))
    counts["claude"] = extract_claude(conn, "mac", os.path.expanduser("~/.claude"))
    counts["gemini"] = extract_gemini(conn, "mac", os.path.expanduser("~/.gemini"))
    counts["jcode"] = extract_jcode(conn, "mac", os.path.expanduser("~/.jcode"), "jcode")
    counts["kcode"] = extract_jcode(conn, "mac", os.path.expanduser("~/.kcode"), "kcode")
    counts["helioslite"] = extract_helioslite(conn, "mac", os.path.expanduser("~/.helioslite"))
    counts["opencode"] = extract_opencode(conn, "mac", os.path.expanduser("~/.local/share/opencode/log"))
    # Round-4 Blk 1 close: ingest jcode's already-aggregated spend files.
    counts["provider_spend"] = extract_spend(conn)
    return counts


def ssh_run(ssh_target, cmd, timeout=60):
    """Run cmd on remote via SSH, return (returncode, stdout, stderr)."""
    p = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes", ssh_target, cmd],
        capture_output=True, text=True, timeout=timeout,
    )
    return p.returncode, p.stdout, p.stderr


def _resolve_desk_python(ssh_target):
    """Resolve the Windows desk Python interpreter path.

    Resolution order:
      1. WINDOWS_PYTHON_PATH env var (operator override; takes precedence)
      2. `where python` probe on the remote (most Windows installs register python in PATH)
      3. C:/Python313/python.exe (last-known-good, the install we know works)
      4. Loud failure with install instructions.

    Returns the path string on success, raises RuntimeError on failure.
    """
    env_path = os.environ.get("WINDOWS_PYTHON_PATH")
    if env_path:
        # Verify it actually runs before trusting it
        rc, out, err = ssh_run(ssh_target, f'"{env_path}" -V', timeout=30)
        if rc == 0:
            print(f"[desk] python (env var): {out.strip()}")
            return env_path
        print(f"[desk] WINDOWS_PYTHON_PATH={env_path} probe FAILED: {err.strip()[:200]}")
    # Probe `where python` on the remote
    rc, out, err = ssh_run(ssh_target, "where python", timeout=30)
    if rc == 0 and out.strip():
        candidate = out.strip().splitlines()[0].strip()
        rc2, out2, err2 = ssh_run(ssh_target, f'"{candidate}" -V', timeout=30)
        if rc2 == 0:
            print(f"[desk] python (where probe): {out2.strip()}  at {candidate}")
            return candidate
        print(f"[desk] `where python` returned {candidate!r} but it failed to run: {err2.strip()[:200]}")
    # Last-known-good fallback (the install we know works on this desk)
    fallback = "C:/Python313/python.exe"
    rc, out, err = ssh_run(ssh_target, f'"{fallback}" -V', timeout=30)
    if rc == 0:
        print(f"[desk] python (fallback): {out.strip()}")
        return fallback
    # Loud failure with instructions
    raise RuntimeError(
        f"[desk] FATAL: cannot locate a working Windows Python interpreter.\n"
        f"  Tried: WINDOWS_PYTHON_PATH env var (unset or failed)\n"
        f"         `where python` (no PATH python)\n"
        f"         {fallback} (not present)\n"
        f"  Fix: set WINDOWS_PYTHON_PATH=C:/path/to/python.exe in your shell env, OR\n"
        f"       install Python 3.10+ for Windows and ensure `python` is on PATH."
    )


def run_desk(conn, ssh_target="koosh@100.96.135.160"):
    """Extract from Windows desk via SSH. Uses /mnt/c/Users/koosh paths."""
    # The Windows /tmp directory (C:\tmp\) is polluted with ad-hoc scripts (e.g.
    # inspect.py, audit.py) that shadow Python stdlib modules when Python runs
    # with cwd=C:\tmp. We must run in a clean subdir to avoid stdlib shadowing.
    # This is a real bug discovered in round-4: C:\tmp\inspect.py shadowed the
    # stdlib inspect module and broke argparse in the remote extraction.
    here = os.path.abspath(__file__)
    remote_base = "/tmp/session_ledger_run"
    remote_path = f"{remote_base}/extract_sessions_remote.py"
    print(f"[desk] creating clean run dir on {ssh_target}:{remote_base}")
    # Windows cmd.exe: rmdir /S /Q + mkdir; POSIX: rm -rf + mkdir -p. The remote
    # SSH shell on Windows is cmd.exe. Use the Windows form unconditionally; the
    # /tmp path resolves to C:\tmp on the Windows side.
    rc, out, err = ssh_run(
        ssh_target,
        f'rmdir /S /Q {remote_base} 2>NUL & mkdir {remote_base} 2>NUL & echo OK',
        timeout=30,
    )
    if rc != 0 or "OK" not in out:
        print(f"[desk] failed to create {remote_base} on remote (rc={rc}): {err.strip()[:200]}")
        return {}
    print(f"[desk] copying extractor + supporting modules to {ssh_target}:{remote_base}/")
    # The script imports from sibling modules (extractors, jcode_extractor,
    # ledger_db, spend_extractor). We must scp all of them; otherwise the
    # remote import fails with ModuleNotFoundError.
    here_dir = os.path.dirname(here)
    modules = [
        os.path.basename(here),
        "extractors.py", "jcode_extractor.py", "ledger_db.py",
        "spend_extractor.py", "aggregate_opencode_usage.py",
    ]
    for mod in modules:
        mod_path = os.path.join(here_dir, mod)
        if not os.path.isfile(mod_path):
            print(f"[desk] missing module on local side: {mod_path}")
            continue
        scp = subprocess.run(
            ["scp", "-o", "StrictHostKeyChecking=no", mod_path, f"{ssh_target}:{remote_base}/{mod}"],
            capture_output=True, text=True, timeout=60,
        )
        if scp.returncode != 0:
            print(f"[desk] scp FAILED for {mod}: {scp.stderr.strip()}")
            return {}
    # Run remote with --device desk and a separate db file
    remote_db = f"{remote_base}/session_ledger_desk.sqlite"
    # Resolve Python interpreter (env var > where probe > last-known-good)
    try:
        py = _resolve_desk_python(ssh_target)
    except RuntimeError as e:
        print(str(e))
        return {}
    # Run with the script's dir as CWD (the script does os.chdir(__file__'s dir)
    # at startup so stdlib-shadowing .py files in C:\tmp don't break us).
    cmd = f'"{py}" {remote_path} --device desk --db {remote_db} --local-extract'
    print(f"[desk] running remote extraction...")
    rc, out, err = ssh_run(ssh_target, cmd, timeout=300)
    if rc != 0:
        print(f"[desk] remote extraction FAILED rc={rc}: {err.strip()[:200]}")
        return {}
    # Pull db back
    local_db = "/tmp/session_ledger_desk_pull.sqlite"
    print(f"[desk] pulling {remote_db} -> {local_db}")
    scp2 = subprocess.run(
        ["scp", "-o", "StrictHostKeyChecking=no", f"{ssh_target}:{remote_db}", local_db],
        capture_output=True, text=True, timeout=60,
    )
    if scp2.returncode != 0:
        print(f"[desk] scp pull FAILED: {scp2.stderr.strip()}")
        return {}
    # Merge into our conn
    return _merge_remote_db(conn, local_db)


def _merge_remote_db(conn, remote_db):
    """Merge sessions/opencode_usage rows from remote_db into conn."""
    if not os.path.isfile(remote_db):
        return {}
    src = sqlite3.connect(remote_db)
    src.row_factory = sqlite3.Row
    counts = {}
    for tbl in ("sessions", "opencode_usage"):
        try:
            r = src.execute(f"SELECT COUNT(*) AS n FROM {tbl}").fetchone()
            counts[tbl] = r["n"] if r else 0
        except sqlite3.OperationalError:
            counts[tbl] = 0
            continue
    # Use ATTACH so we can do INSERT OR IGNORE with the PK constraint
    try:
        conn.execute(f"ATTACH DATABASE ? AS remote", (remote_db,))
        conn.execute(
            "INSERT OR IGNORE INTO sessions SELECT * FROM remote.sessions"
        )
        conn.execute(
            "INSERT OR IGNORE INTO opencode_usage (timestamp, profile, session_id, model, cached_tokens, uncached_tokens, reasoning_tokens, retry_count, http_status, session_header_present, quota_window, raw_line, source_path) "
            "SELECT timestamp, profile, session_id, model, cached_tokens, uncached_tokens, reasoning_tokens, retry_count, http_status, session_header_present, quota_window, raw_line, source_path FROM remote.opencode_usage"
        )
        conn.execute("DETACH DATABASE remote")
        conn.commit()
    except sqlite3.Error as e:
        print(f"[merge] ATTACH failed: {e}; falling back to row-by-row")
        try:
            conn.execute("DETACH DATABASE remote")
        except sqlite3.Error:
            pass
        # Fallback: row-by-row insert
        for row in src.execute("SELECT * FROM sessions"):
            cols = "harness, session_id, device, host, started_at, ended_at, title, model, provider, tokens_total, cwd, git_branch, path, extra_json"
            conn.execute(
                f"INSERT OR IGNORE INTO sessions ({cols}) VALUES ({','.join('?'*14)})",
                row,
            )
        for row in src.execute("SELECT * FROM opencode_usage"):
            cols = "timestamp, profile, session_id, model, cached_tokens, uncached_tokens, reasoning_tokens, retry_count, http_status, session_header_present, quota_window, raw_line, source_path"
            conn.execute(
                f"INSERT OR IGNORE INTO opencode_usage ({cols}) VALUES ({','.join('?'*13)})",
                row[1:],  # skip rowid
            )
        conn.commit()
    src.close()
    return counts


def device_is_windows():
    """Best-effort: are we on Windows (WSL or native)?"""
    if os.name == "nt":
        return True
    # WSL detection
    try:
        with open("/proc/version", "r") as f:
            return "Microsoft" in f.read() or "WSL" in f.read()
    except OSError:
        return False


def _desk_home():
    """Return the home root for the current Windows host (WSL or native)."""
    if os.name == "nt":
        # Native Windows — use the actual user profile.
        return os.path.expanduser("~")
    # WSL — translate via /mnt/c
    return "/mnt/c/Users/koosh"




# ====================================================================
# Schema + write contract (was in extractors.py before round-4 split)
# ====================================================================



def main():
    # Defend against CWD-pollution shadowing of stdlib modules. If the script
    # was scp'd to C:\tmp\ and C:\tmp contains inspect.py / json.py / etc., those
    # shadow the stdlib and break argparse, dataclasses, etc. Always chdir to
    # the script's own directory on startup. (Round-4 bug fix.)
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except OSError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", choices=["mac", "desk", "both"], default="both")
    ap.add_argument("--ssh", default="koosh@100.96.135.160", help="SSH target for desk")
    ap.add_argument("--db", default=DEFAULT_DB, help="Output sqlite path")
    ap.add_argument("--local-extract", action="store_true",
                    help="Internal: used by remote-driver when scp'd to Windows")
    ap.add_argument(
        "--assert-min", action="append", default=[], metavar="HARNESS/DEVICE:COUNT",
        help="Assert minimum row count for (harness, device); e.g., jcode/mac:30. "
             "Repeatable. Exits 1 if any count is below the minimum. Use for tests "
             "with live-counted harnesses (jcode, kcode) where exact-match is wrong."
    )
    args = ap.parse_args()

    if args.local_extract:
        # Remote-driver mode: run local extraction on this host
        # The Windows desk machine uses native Windows paths (C:\\Users\\koosh)
        # when run under C:\\Python313\\python.exe, or /mnt/c/... under WSL.
        conn = open_db(args.db)
        conn.row_factory = sqlite3.Row
        if device_is_windows():
            desk_home = _desk_home()
            from pathlib import Path
            dh = Path(desk_home)
            counts = {
                "codex": extract_codex(conn, "desk", str(dh / ".codex")),
                "claude": extract_claude(conn, "desk", str(dh / ".claude")),
                "gemini": extract_gemini(conn, "desk", str(dh / ".gemini")),
                "jcode": extract_jcode(conn, "desk", str(dh / ".jcode"), "jcode"),
                "kcode": extract_jcode(conn, "desk", str(dh / ".kcode"), "kcode"),
                "helioslite": extract_helioslite(conn, "desk", str(dh / ".helioslite")),
                "opencode": extract_opencode(conn, "desk", str(dh / ".local" / "share" / "opencode" / "log")),
            }
        else:
            counts = run_mac(conn)
        conn.execute("UPDATE sessions SET host = 'kooshapari-desk' WHERE device = 'desk'")
        conn.commit()
        print(f"[remote-driver] counts={counts}")
        return

    conn = open_db(args.db)
    conn.row_factory = sqlite3.Row
    # Auto-aggregate opencode usage after extraction (single source of truth)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "agg",
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "aggregate_opencode_usage.py"),
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            log_dir_mac = os.path.expanduser("~/.local/share/opencode/log")
            if os.path.isdir(log_dir_mac):
                mod.main_with_args(db=args.db, log_dir=log_dir_mac, device="mac",
                                    profile="opencode-go")
    except Exception as e:
        print(f"[warn] auto-aggregate failed: {e}", file=sys.stderr)
    print(f"=== extract_sessions ===  db={args.db}  device={args.device}")
    t0 = time.time()
    totals = {"sessions": 0, "opencode_usage": 0}
    if args.device in ("mac", "both"):
        print("[mac] extracting...")
        mac_counts = run_mac(conn)
        for h, n in mac_counts.items():
            print(f"  [mac/{h}] {n} sessions")
            totals["sessions"] += n
    if args.device in ("desk", "both"):
        print(f"[desk] extracting via SSH {args.ssh}...")
        desk_counts = run_desk(conn, args.ssh)
        for k, n in desk_counts.items():
            print(f"  [desk/{k}] {n} rows")
            if k == "sessions":
                totals["sessions"] += n
            else:
                totals["opencode_usage"] += n
    # Read opencode_usage count from DB (auto-aggregator writes directly)
    totals["opencode_usage"] = conn.execute("SELECT COUNT(*) FROM opencode_usage").fetchone()[0]
    elapsed = time.time() - t0
    # Final summary
    print(f"\n=== DONE in {elapsed:.1f}s ===")
    print(f"  total sessions: {totals['sessions']}")
    print(f"  opencode_usage rows: {totals['opencode_usage']}")
    # Per-harness, per-device summary
    rows = conn.execute(
        "SELECT harness, device, COUNT(*) AS n FROM sessions GROUP BY harness, device ORDER BY harness, device"
    ).fetchall()
    print("\n  per-harness/device breakdown:")
    breakdown = {}
    for r in rows:
        print(f"    {r['harness']:12s} {r['device']:6s} {r['n']:>7d}")
        breakdown[f"{r['harness']}/{r['device']}"] = r["n"]
    # Optional: enforce minimums (for tests with live-counted harnesses)
    if args.assert_min:
        print(f"\n  --assert-min checks:")
        failed = []
        for spec in args.assert_min:
            if ":" not in spec:
                print(f"    [skip] {spec!r}  (malformed, want HARNESS/DEVICE:COUNT)")
                continue
            key, _, min_str = spec.rpartition(":")
            try:
                min_n = int(min_str)
            except ValueError:
                print(f"    [skip] {spec!r}  (count not int)")
                continue
            actual = breakdown.get(key, 0)
            ok = actual >= min_n
            mark = "OK" if ok else "FAIL"
            print(f"    [{mark}] {key:24s}  actual={actual:>5d}  min={min_n}")
            if not ok:
                failed.append((key, min_n, actual))
        if failed:
            print(f"\n  --assert-min FAILED on {len(failed)} key(s); exiting 1")
            sys.exit(1)


if __name__ == "__main__":
    main()
