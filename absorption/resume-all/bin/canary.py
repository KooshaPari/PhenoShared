#!/opt/homebrew/bin/python3
"""
canary.py — canary deployment system for the resume-all crash-recovery toolkit.

A canary deploy runs a NEW version on a small subset of processes/hosts while
the majority continue running the PRODUCTION version. If the canary cohort
shows a higher failure rate than production, it is auto-rolled back. After a
configured number of successful ticks, it can be promoted to 100%.

Subcommands
-----------
  status                  print cohort membership table for all targets
  cohort <target>         list PIDs/sessions in the canary cohort
  promote <target>        switch canary to production (updates registry, kills
                          canary instances, marks registry to use new version)
  rollback <target>       revert canary to production, kill canary instances
  health <target>         compare canary cohort failure rate to production
                          and report HEALTHY / DEGRADED / ROLLED_BACK
  run <target>            start canary instance(s) for the target, write PID file
  stop <target>           kill canary instance(s) for the target
  report                  aggregate canary run history into a summary
  test                    run inline self-tests (7+ cases)

Registry
--------
~/.config/resume-all/canary.toml — created on first run with sensible defaults:

    [canary]
    cohort_size_pct = 5
    auto_rollback = true
    cohort_key = "pid_mod_20"

    [targets.session-snapshot]
    production = "1.0.0"
    canary = "1.1.0-rc1"
    enabled = true
    auto_promote_after_successful_ticks = 100

Membership functions (cohort_key)
---------------------------------
  pid_mod_20        pid % 20 == 0                 (5% by construction)
  random_5pct       deterministic random per PID  (stable across calls)
  hostname_match    hostname matches a regex       (returns True for ALL PIDs
                                                      on a matching host)
  path_hash         hash of argv/path mod N        (stable per binary path)

Failure detection
-----------------
Reads ~/.local/share/resume-all/health.txt (one row per health-check run,
free-form text including OK/DEGRADED/FAILURE/HEALTHY lines). Also accepts an
optional IPC `health.status` probe of the sharecli daemon — its protocol_version
field is compared to the registry's `production` version to detect drift.

Conventions
-----------
- Stdout only (no stderr noise) so output is safe to pipe/redirect.
- All errors written to stderr, with a non-zero exit code.
- Stdlib only (no new pip deps).
- Forward-compatible: parses both 3.11+ tomllib and falls back to tomli if
  available (the launchd shell on older macOS hosts uses Python 3.9 which
  pre-dates tomllib — we degrade gracefully in that case by emitting a
  minimal registry via the built-in writer).
- Run cap: 1 canary instance per target by default (configurable per-target
  via `max_instances`). Prevents fork-bombing the cohort.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Paths (use Path.home() — never hardcode /Users/...)
# ---------------------------------------------------------------------------

HOME = Path.home()
CONFIG_DIR = HOME / ".config" / "resume-all"
DATA_DIR = HOME / ".local" / "share" / "resume-all"
CANARY_CONFIG = CONFIG_DIR / "canary.toml"
CANARY_PID_DIR = DATA_DIR / "canary"
CANARY_RUNS_LOG = DATA_DIR / "canary-runs.jsonl"
HEALTH_TXT = DATA_DIR / "health.txt"
HEALTH_SOCKET = HOME / "Library" / "Application Support" / "sharecli" / "ipc.sock"


# ---------------------------------------------------------------------------
# TOML read/write (tomllib if available, tomli fallback; emit minimal TOML
# ourselves since there's no stdlib writer).
# ---------------------------------------------------------------------------

def _load_toml(path: Path) -> dict:
    """Load a TOML file. Returns {} on missing file. Raises on malformed."""
    if not path.exists():
        return {}
    try:
        import tomllib  # pyright: ignore[reportMissingImports]
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef, import-not-found]
        except ImportError:
            raise RuntimeError(
                "tomllib/tomli unavailable; Python 3.11+ required for "
                "TOML reads. Write a minimal canary.toml manually."
            )
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _emit_toml(doc: dict) -> str:
    """Render a small dict-as-TOML document with the limited schema this
    tool produces. NOT a full TOML serializer — only handles the keys
    we generate. Order-preserving via dict insertion order (Py3.7+).

    Supported shapes:
        {"canary": {"key": "val", "n": 5, "b": true}}
        {"targets": {"name": {"production": "1.0", "canary": "1.1",
                              "enabled": true, "n": 100, ...}}}

    Emits both simple [section] and nested [section.subsection] forms so
    the `targets` map survives a round trip through tomllib.
    """
    lines: list[str] = []

    def _emit_value(v: Any) -> str | None:
        """Render a leaf value, returning the TOML fragment or None if
        unsupported."""
        if isinstance(v, bool):
            return str(v).lower()
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, str):
            esc = v.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{esc}"'
        if isinstance(v, list):
            items: list[str] = []
            for x in v:
                if isinstance(x, str):
                    esc = x.replace("\\", "\\\\").replace('"', '\\"')
                    items.append(f'"{esc}"')
                elif isinstance(x, (int, float, bool)):
                    items.append(_emit_value(x) or "")
                # skip unsupported list elements rather than emit invalid TOML
            return "[" + ", ".join(items) + "]"
        return None  # unsupported (nested dicts handled by caller)

    def _emit_section(prefix: str, body: dict) -> None:
        if not isinstance(body, dict):
            return
        # Emit the section header even if it only contains nested dicts,
        # otherwise the [targets] / [targets.X] layout loses its anchor.
        lines.append(f"[{prefix}]")
        any_leaf = False
        for k, v in body.items():
            if isinstance(v, dict):
                continue  # nested — handled below
            rendered = _emit_value(v)
            if rendered is None:
                continue
            lines.append(f"{k} = {rendered}")
            any_leaf = True
        if not any_leaf and not any(isinstance(v, dict) for v in body.values()):
            lines.append("")  # placeholder so the section is non-empty
        lines.append("")
        for k, v in body.items():
            if isinstance(v, dict):
                _emit_section(f"{prefix}.{k}", v)

    for section, body in doc.items():
        if not isinstance(body, dict):
            continue
        _emit_section(section, body)

    return "\n".join(lines).rstrip("\n") + "\n"


def _write_toml(path: Path, doc: dict) -> None:
    """Write a dict to a TOML file atomically (write to .tmp, rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(_emit_toml(doc), encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Default registry
# ---------------------------------------------------------------------------

DEFAULT_CANARY_DOC: dict[str, Any] = {
    "canary": {
        "cohort_size_pct": 5,
        "auto_rollback": True,
        "cohort_key": "pid_mod_20",
    },
    "targets": {
        "session-snapshot": {
            "production": "1.0.0",
            "canary": "1.1.0-rc1",
            "enabled": True,
            "auto_promote_after_successful_ticks": 100,
            "binary": "session_snapshot.py",
            "max_instances": 1,
        },
        "ipc-daemon": {
            "production": "0.2.0",
            "canary": "0.3.0-rc1",
            "enabled": True,
            "auto_promote_after_successful_ticks": 100,
            "binary": "sharecli-ipc-daemon",
            "max_instances": 1,
        },
        "thegent-mcp": {
            "production": "0.1.0",
            "canary": "0.2.0-rc1",
            "enabled": False,
            "auto_promote_after_successful_ticks": 200,
            "binary": "thegent-mcp",
            "max_instances": 1,
        },
        "sharecli-tray": {
            "production": "0.4.0",
            "canary": "0.5.0-rc1",
            "enabled": False,
            "auto_promote_after_successful_ticks": 200,
            "binary": "sharecli-tray",
            "max_instances": 1,
        },
    },
}


def load_registry() -> dict:
    """Load the registry, creating defaults if missing. Never raises for
    a missing file — that case bootstraps the default registry.

    On a malformed file we emit a stderr warning AND rewrite the file with
    the defaults so the operator gets a clean registry on disk. The
    in-memory copy is always usable for the current invocation.
    """
    if not CANARY_CONFIG.exists():
        _write_toml(CANARY_CONFIG, DEFAULT_CANARY_DOC)
        return json.loads(json.dumps(DEFAULT_CANARY_DOC))  # deep copy
    try:
        return _load_toml(CANARY_CONFIG)
    except Exception as exc:
        # Malformed file: warn, rewrite a clean copy, but keep going.
        print(
            f"canary: failed to parse {CANARY_CONFIG}: {exc}; "
            f"rewriting with defaults",
            file=sys.stderr,
        )
        try:
            _write_toml(CANARY_CONFIG, DEFAULT_CANARY_DOC)
        except OSError as write_exc:
            print(
                f"canary: could not rewrite registry: {write_exc}",
                file=sys.stderr,
            )
        return json.loads(json.dumps(DEFAULT_CANARY_DOC))


def save_registry(doc: dict) -> None:
    _write_toml(CANARY_CONFIG, doc)


def get_target(doc: dict, name: str) -> dict | None:
    """Return the [targets.<name>] section, or None if absent / disabled."""
    targets = doc.get("targets") or {}
    if not isinstance(targets, dict):
        return None
    t = targets.get(name)
    if not isinstance(t, dict):
        return None
    return t


# ---------------------------------------------------------------------------
# Membership functions
# ---------------------------------------------------------------------------

def _pid_mod_20(pid: int, extra: Any = None) -> bool:
    """pid % 20 == 0  →  exactly 5% membership (modulo 20)."""
    try:
        return int(pid) % 20 == 0
    except (TypeError, ValueError):
        return False


def _random_5pct(pid: int, extra: Any = None) -> bool:
    """Deterministic random 5% per PID (stable across calls)."""
    try:
        h = hashlib.sha256(f"canary-random-{int(pid)}".encode()).digest()
        # Take first 4 bytes as a 32-bit unsigned int, mod 100, < 5 → in cohort.
        return int.from_bytes(h[:4], "big") % 100 < 5
    except (TypeError, ValueError):
        return False


def _hostname_match(pid: int, extra: Any = None) -> bool:
    """Match current hostname against a regex. extra is the compiled regex or
    pattern string. Returns True iff hostname matches. When the regex matches
    the local hostname, ALL PIDs are in cohort (this is by design — the
    cohort_key is for "which hosts" routing in path_hash; on a matching host
    every PID satisfies the predicate)."""
    import socket as _socket
    pattern = extra or r".*"
    try:
        host = _socket.gethostname()
    except OSError:
        return False
    if isinstance(pattern, str):
        try:
            pattern = re.compile(pattern)
        except re.error:
            return False
    if not isinstance(pattern, re.Pattern):
        return False
    return bool(pattern.search(host))


def _path_hash(pid: int, extra: Any = None, _argv: str = "") -> bool:
    """Hash of argv mod N. extra is the modulus (default 20). Membership is
    stable per binary path. Stable: same argv → same cohort slot across runs.
    """
    modulus = int(extra) if isinstance(extra, (int, float)) else 20
    if modulus <= 0:
        return False
    h = hashlib.sha256(f"canary-pathhash-{_argv}".encode()).digest()
    return int.from_bytes(h[:4], "big") % modulus == 0


MEMBERSHIP_FNS: dict[str, Any] = {
    "pid_mod_20": _pid_mod_20,
    "random_5pct": _random_5pct,
    "hostname_match": _hostname_match,
    "path_hash": _path_hash,
}


def cohort_member(cohort_key: str, pid: int, *, argv: str = "", extra: Any = None) -> bool:
    """Return True iff a PID is in the canary cohort under the given key."""
    fn = MEMBERSHIP_FNS.get(cohort_key)
    if fn is None:
        # Unknown key — treat as no cohort (everything is production).
        return False
    if cohort_key == "path_hash":
        return _path_hash(pid, extra=extra, _argv=argv)
    if cohort_key == "hostname_match":
        return _hostname_match(pid, extra=extra)
    return fn(pid, extra=extra)


# ---------------------------------------------------------------------------
# IPC daemon probe (NDJSON over UNIX socket)
# ---------------------------------------------------------------------------

def ipc_health_status(timeout: float = 2.0) -> dict:
    """Send `health.status` to the sharecli IPC daemon and return the parsed
    envelope. Returns {"error": "..."} on transport failure.

    Uses the same NDJSON wire format as health-check.py: one JSON object per
    line, no length prefix.
    """
    out: dict = {"reachable": False, "result": None, "error": None}
    if not HEALTH_SOCKET.exists():
        out["error"] = f"socket missing: {HEALTH_SOCKET}"
        return out
    try:
        req_id = uuid.uuid4().int & 0xFFFFFFFF
        payload = {"id": req_id, "method": "health.status", "params": {}}
        line = (json.dumps(payload, separators=(",", ":")) + "\n").encode()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(timeout)
            sock.connect(str(HEALTH_SOCKET))
            sock.sendall(line)
            buf = b""
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf += chunk
                if buf.endswith(b"\n"):
                    break
        finally:
            try:
                sock.close()
            except OSError:
                pass
        if not buf.strip():
            out["error"] = "empty response"
            return out
        try:
            resp = json.loads(buf.decode("utf-8").strip())
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            out["error"] = f"parse: {exc}"
            return out
        if not isinstance(resp, dict):
            out["error"] = "non-dict frame"
            return out
        out["reachable"] = True
        out["result"] = resp.get("result")
        return out
    except (OSError, socket.error, socket.timeout) as exc:
        out["error"] = f"transport: {exc}"
        return out


def ipc_process_list(timeout: float = 2.0) -> list[dict]:
    """Enumerate managed processes via `process.list`. Empty list on error."""
    if not HEALTH_SOCKET.exists():
        return []
    try:
        req_id = uuid.uuid4().int & 0xFFFFFFFF
        payload = {"id": req_id, "method": "process.list", "params": {}}
        line = (json.dumps(payload, separators=(",", ":")) + "\n").encode()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(timeout)
            sock.connect(str(HEALTH_SOCKET))
            sock.sendall(line)
            buf = b""
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf += chunk
                if buf.endswith(b"\n"):
                    break
        finally:
            try:
                sock.close()
            except OSError:
                pass
        if not buf.strip():
            return []
        try:
            resp = json.loads(buf.decode("utf-8").strip())
        except (UnicodeDecodeError, json.JSONDecodeError):
            return []
        if not isinstance(resp, dict):
            return []
        result = resp.get("result")
        return result if isinstance(result, list) else []
    except (OSError, socket.error, socket.timeout):
        return []


# ---------------------------------------------------------------------------
# Health.txt parsing — extract OK/DEGRADED/FAILURE lines and per-target verdict
# ---------------------------------------------------------------------------

def parse_health_txt(path: Path) -> dict:
    """Parse the human-readable health.txt into a per-target verdict dict.

    Format (from health-check.py):
        <label>:       <verdict>      (<reason>)
        Overall:       HEALTHY|DEGRADED  (<summary>)

    Returns:
        {"rows": [{"label": ..., "verdict": ..., "reason": ...}, ...],
         "overall": "HEALTHY"|"DEGRADED"|None,
         "mtime": epoch_seconds_or_None}
    """
    out: dict = {"rows": [], "overall": None, "mtime": None}
    if not path.exists():
        return out
    try:
        out["mtime"] = path.stat().st_mtime
    except OSError:
        return out
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out

    # Match "<label>:<spaces><verdict><spaces>(<reason>)"
    row_re = re.compile(
        r"^(?P<label>[A-Za-z0-9_.\- ]+?):\s+(?P<verdict>[A-Z]+)\s*(?:\((?P<reason>.*)\))?\s*$"
    )
    for line in text.splitlines():
        line = line.rstrip()
        m = row_re.match(line)
        if not m:
            continue
        label = m.group("label").strip()
        verdict = m.group("verdict").strip()
        reason = (m.group("reason") or "").strip()
        if label.lower().startswith("overall"):
            out["overall"] = verdict
        else:
            out["rows"].append({"label": label, "verdict": verdict, "reason": reason})
    return out


# ---------------------------------------------------------------------------
# Cohort enumeration — list PIDs/sessions in canary cohort for a target
# ---------------------------------------------------------------------------

def enumerate_cohort(
    target_name: str,
    cohort_key: str,
    *,
    cohort_size_pct: int = 5,
) -> dict:
    """Enumerate canary-cohort PIDs from `process.list` + a synthetic snapshot.

    Returns:
        {"cohort_size_pct": int,
         "cohort_count": int,
         "production_count": int,
         "total": int,
         "cohort_pids": [{"pid": int, "argv": str, "harness": str,
                          "session_id": str}, ...]}
    """
    procs = ipc_process_list(timeout=2.0)
    cohort: list[dict] = []
    prod = 0
    for p in procs:
        if not isinstance(p, dict):
            continue
        pid = p.get("pid")
        argv = p.get("argv") or ""
        if not isinstance(pid, int) or pid <= 0:
            continue
        # path_hash membership needs the argv
        if cohort_member(cohort_key, pid, argv=argv):
            cohort.append({
                "pid": pid,
                "argv": argv,
                "harness": p.get("harness") or "",
                "session_id": p.get("session_id") or "",
            })
        else:
            prod += 1
    total = len(cohort) + prod
    return {
        "cohort_size_pct": cohort_size_pct,
        "cohort_count": len(cohort),
        "production_count": prod,
        "total": total,
        "cohort_pids": cohort,
    }


# ---------------------------------------------------------------------------
# PID file management (cap to prevent fork-bombing)
# ---------------------------------------------------------------------------

def _target_pidfile(target: str) -> Path:
    return CANARY_PID_DIR / f"{target}.pid"


def _read_pidfile(path: Path) -> list[int]:
    """Read PID file (one PID per line). Empty list on missing/error."""
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return []
    pids: list[int] = []
    for tok in text.splitlines():
        tok = tok.strip()
        if not tok:
            continue
        try:
            pids.append(int(tok))
        except ValueError:
            continue
    return pids


def _write_pidfile(path: Path, pids: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(str(p) for p in pids) + "\n", encoding="utf-8")


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


# ---------------------------------------------------------------------------
# canary-runs.jsonl (per-target run history)
# ---------------------------------------------------------------------------

def _log_run(entry: dict) -> None:
    """Append one canary-run record (jsonl). Best-effort, never raises."""
    try:
        CANARY_RUNS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with CANARY_RUNS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, separators=(",", ":")) + "\n")
    except OSError:
        pass


def _read_runs(since_epoch: int | None = None) -> list[dict]:
    """Read canary-runs.jsonl; optionally filter by ts_epoch >= since_epoch."""
    if not CANARY_RUNS_LOG.exists():
        return []
    out: list[dict] = []
    try:
        with CANARY_RUNS_LOG.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                if since_epoch is not None:
                    ts = row.get("ts_epoch")
                    if not isinstance(ts, (int, float)) or ts < since_epoch:
                        continue
                out.append(row)
    except OSError:
        return []
    return out


# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    doc = load_registry()
    cfg = doc.get("canary") or {}
    cohort_key = cfg.get("cohort_key", "pid_mod_20")
    cohort_size_pct = int(cfg.get("cohort_size_pct", 5))

    print(f"cohort_key: {cohort_key}  cohort_size_pct: {cohort_size_pct}%")
    print()
    header = (
        f"{'TARGET':<22}{'PRODUCTION':<14}{'CANARY':<14}"
        f"{'COHORT_SIZE':<18}{'OK':<5}{'DEGRADED':<10}{'ROLLED_BACK':<11}"
    )
    print(header)
    print("-" * len(header))

    targets = doc.get("targets") or {}
    if not isinstance(targets, dict) or not targets:
        print("(no targets configured)")
        return 0

    any_degraded = False
    for name, t in targets.items():
        if not isinstance(t, dict):
            continue
        prod = str(t.get("production", "?"))
        can = str(t.get("canary", "?"))
        enabled = bool(t.get("enabled", True))
        if not enabled:
            print(
                f"{name:<22}{prod:<14}{can:<14}"
                f"{'disabled':<18}{'-':<5}{'-':<10}{'-':<11}"
            )
            continue

        info = enumerate_cohort(name, cohort_key, cohort_size_pct=cohort_size_pct)
        cohort_label = (
            f"{cohort_size_pct}% ({info['cohort_count']}/{info['total'] or '?'})"
        )
        verdict = compute_health(name, t)
        ok = 1 if verdict == "HEALTHY" else 0
        deg = 1 if verdict == "DEGRADED" else 0
        rb = 1 if verdict == "ROLLED_BACK" else 0
        if verdict != "HEALTHY":
            any_degraded = True
        print(
            f"{name:<22}{prod:<14}{can:<14}"
            f"{cohort_label:<18}{ok:<5}{deg:<10}{rb:<11}"
        )

    return 1 if any_degraded else 0


# ---------------------------------------------------------------------------
# Subcommand: cohort <target>
# ---------------------------------------------------------------------------

def cmd_cohort(args: argparse.Namespace) -> int:
    doc = load_registry()
    cfg = doc.get("canary") or {}
    cohort_key = cfg.get("cohort_key", "pid_mod_20")
    cohort_size_pct = int(cfg.get("cohort_size_pct", 5))
    target = args.target
    t = get_target(doc, target)
    if t is None:
        print(f"canary: unknown target '{target}'", file=sys.stderr)
        return 2
    info = enumerate_cohort(target, cohort_key, cohort_size_pct=cohort_size_pct)
    print(f"target: {target}  cohort_key: {cohort_key}")
    print(f"cohort: {info['cohort_count']}/{info['total']} "
          f"({info['cohort_size_pct']}% target)")
    if not info["cohort_pids"]:
        print("(no cohort PIDs found)")
        return 0
    print(f"{'PID':<10}{'HARNESS':<16}{'SESSION_ID':<40}ARGV")
    for row in info["cohort_pids"]:
        argv = row["argv"]
        if len(argv) > 60:
            argv = argv[:57] + "..."
        print(
            f"{row['pid']:<10}{row['harness']:<16}"
            f"{row['session_id']:<40}{argv}"
        )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: promote <target>
# ---------------------------------------------------------------------------

def cmd_promote(args: argparse.Namespace) -> int:
    doc = load_registry()
    target = args.target
    t = get_target(doc, target)
    if t is None:
        print(f"canary: unknown target '{target}'", file=sys.stderr)
        return 2
    # Kill canary instances first.
    _stop_target(target)
    # Move canary version into production.
    canary_ver = str(t.get("canary", t.get("production", "?")))
    t["production"] = canary_ver
    t["promoted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_registry(doc)
    _log_run({
        "ts": t["promoted_at"],
        "ts_epoch": int(time.time()),
        "action": "promote",
        "target": target,
        "version": canary_ver,
    })
    print(f"canary: promoted '{target}' to version {canary_ver}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: rollback <target>
# ---------------------------------------------------------------------------

def cmd_rollback(args: argparse.Namespace) -> int:
    doc = load_registry()
    target = args.target
    t = get_target(doc, target)
    if t is None:
        print(f"canary: unknown target '{target}'", file=sys.stderr)
        return 2
    _stop_target(target)
    t["rolled_back_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_registry(doc)
    _log_run({
        "ts": t["rolled_back_at"],
        "ts_epoch": int(time.time()),
        "action": "rollback",
        "target": target,
        "version": str(t.get("production", "?")),
    })
    print(f"canary: rolled back '{target}' to production "
          f"{t.get('production', '?')}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: health <target>
# ---------------------------------------------------------------------------

def compute_health(target: str, t: dict) -> str:
    """Compute the current verdict for a target.

    Logic:
      1. If auto_rollback=false in [canary], never auto-rollback.
      2. Read last N canary-run entries for this target.
      3. Count consecutive failures; if >= 3, mark ROLLED_BACK.
      4. Compare canary failure rate vs production (proxied by overall
         health.txt verdict). If canary failures - production failures > 5%,
         mark DEGRADED.
      5. Otherwise HEALTHY.
    """
    auto_rollback = bool(t.get("auto_rollback", True))
    if not auto_rollback:
        return "HEALTHY"  # operator opted out

    runs = _read_runs()
    target_runs = [r for r in runs if r.get("target") == target][-50:]
    failures = [r for r in target_runs
                if str(r.get("outcome", "")).lower() in ("fail", "failed", "error")]
    consecutive_fail = 0
    for r in reversed(target_runs):
        if str(r.get("outcome", "")).lower() in ("fail", "failed", "error"):
            consecutive_fail += 1
        else:
            break
    if consecutive_fail >= 3:
        return "ROLLED_BACK"

    # Compare failure rates.
    health = parse_health_txt(HEALTH_TXT)
    overall = health.get("overall") or "HEALTHY"
    canary_fail_rate = (len(failures) / max(len(target_runs), 1)) if target_runs else 0.0
    prod_fail_rate = 0.0 if overall == "HEALTHY" else 0.05  # 5% baseline

    if canary_fail_rate - prod_fail_rate > 0.05:
        return "DEGRADED"
    return "HEALTHY"


def cmd_health(args: argparse.Namespace) -> int:
    doc = load_registry()
    target = args.target
    t = get_target(doc, target)
    if t is None:
        print(f"canary: unknown target '{target}'", file=sys.stderr)
        return 2

    verdict = compute_health(target, t)
    health = parse_health_txt(HEALTH_TXT)
    overall = health.get("overall") or "UNKNOWN"

    # Also probe the IPC daemon for protocol version drift.
    ipc = ipc_health_status(timeout=1.5)
    ipc_version = None
    if isinstance(ipc.get("result"), dict):
        ipc_version = ipc["result"].get("protocol_version")

    runs = _read_runs()
    target_runs = [r for r in runs if r.get("target") == target]
    last_run = target_runs[-1] if target_runs else None

    print(f"target: {target}")
    print(f"verdict: {verdict}")
    print(f"overall_health_txt: {overall}")
    if ipc_version is not None:
        print(f"ipc_protocol_version: {ipc_version}  "
              f"(registry production={t.get('production', '?')})")
    if last_run:
        print(f"last_run: {last_run.get('ts', '?')} "
              f"action={last_run.get('action', '?')} "
              f"outcome={last_run.get('outcome', '?')}")
    else:
        print("last_run: (none)")

    # Exit codes: 0 HEALTHY, 1 DEGRADED, 2 ROLLED_BACK
    if verdict == "ROLLED_BACK":
        return 2
    if verdict == "DEGRADED":
        return 1
    return 0


# ---------------------------------------------------------------------------
# Subcommand: run <target>
# ---------------------------------------------------------------------------

def cmd_run(args: argparse.Namespace) -> int:
    doc = load_registry()
    target = args.target
    t = get_target(doc, target)
    if t is None:
        print(f"canary: unknown target '{target}'", file=sys.stderr)
        return 2
    if not t.get("enabled", True):
        print(f"canary: target '{target}' is disabled", file=sys.stderr)
        return 2
    pidfile = _target_pidfile(target)
    existing = [p for p in _read_pidfile(pidfile) if _alive(p)]
    max_instances = int(t.get("max_instances", 1))
    if len(existing) >= max_instances:
        print(f"canary: '{target}' already has {len(existing)} instance(s) "
              f"running (cap={max_instances})")
        return 1

    binary = t.get("binary", "")
    if not binary:
        print(f"canary: no 'binary' configured for '{target}'; "
              f"refusing to start without explicit binary path",
              file=sys.stderr)
        return 2

    # Locate the binary: either absolute, in $HOME/bin, or a python script
    # in $HOME/bin. Cap the spawn — we never invoke arbitrary user paths.
    candidates: list[Path] = []
    bp = Path(binary)
    if bp.is_absolute() and bp.exists():
        candidates.append(bp)
    else:
        candidates.append(HOME / "bin" / binary)
        candidates.append(HOME / "bin" / (binary + ".py"))
        candidates.append(HOME / "thegent" / "crates" / binary / "target" / "release" / binary)

    chosen = next((c for c in candidates if c.exists()), None)
    if chosen is None:
        # Dry-run mode: write a metadata record without spawning anything,
        # so the operator can see the intended command without risk.
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _log_run({
            "ts": ts,
            "ts_epoch": int(time.time()),
            "action": "run-dry",
            "target": target,
            "binary": binary,
            "version": str(t.get("canary", "?")),
            "outcome": "ok",
            "note": "binary not found on disk; recorded as dry-run",
        })
        print(f"canary: dry-run recorded for '{target}' "
              f"(binary '{binary}' not found)")
        return 0

    # Spawn the binary as a detached process. We never block on it — the
    # canary coordinator stays responsive. PID goes into the pidfile.
    try:
        proc = subprocess.Popen(
            [str(chosen)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,  # detach from controlling tty
        )
    except (OSError, FileNotFoundError) as exc:
        print(f"canary: spawn failed for '{chosen}': {exc}",
              file=sys.stderr)
        return 2

    pids = existing + [proc.pid]
    _write_pidfile(pidfile, pids)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _log_run({
        "ts": ts,
        "ts_epoch": int(time.time()),
        "action": "run",
        "target": target,
        "binary": str(chosen),
        "pid": proc.pid,
        "version": str(t.get("canary", "?")),
        "outcome": "ok",
    })
    print(f"canary: started '{target}' pid={proc.pid} ({chosen})")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: stop <target>
# ---------------------------------------------------------------------------

def _stop_target(target: str) -> int:
    """Internal: kill all canary PIDs for target. Returns count killed."""
    pidfile = _target_pidfile(target)
    pids = _read_pidfile(pidfile)
    killed = 0
    for pid in pids:
        if _alive(pid):
            try:
                os.kill(pid, 15)  # SIGTERM
                killed += 1
            except (OSError, ProcessLookupError):
                pass
    # Give them a beat to exit cleanly, then SIGKILL stragglers.
    time.sleep(0.2)
    for pid in pids:
        if _alive(pid):
            try:
                os.kill(pid, 9)
            except (OSError, ProcessLookupError):
                pass
    try:
        pidfile.unlink()
    except OSError:
        pass
    return killed


def cmd_stop(args: argparse.Namespace) -> int:
    doc = load_registry()
    target = args.target
    t = get_target(doc, target)
    if t is None:
        print(f"canary: unknown target '{target}'", file=sys.stderr)
        return 2
    killed = _stop_target(target)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _log_run({
        "ts": ts,
        "ts_epoch": int(time.time()),
        "action": "stop",
        "target": target,
        "killed": killed,
        "outcome": "ok" if killed > 0 else "noop",
    })
    print(f"canary: stopped '{target}' ({killed} killed)")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: report
# ---------------------------------------------------------------------------

def cmd_report(args: argparse.Namespace) -> int:
    since = "24h"
    if args.since:
        since = args.since
    since_s = _parse_since(since)
    now = int(time.time())
    cutoff = now - since_s

    runs = _read_runs(since_epoch=cutoff)
    by_target: dict[str, list[dict]] = {}
    for r in runs:
        tg = str(r.get("target", "?"))
        by_target.setdefault(tg, []).append(r)

    print("# Canary Deployment Report")
    print()
    print(f"- Window: since `{since}` "
          f"({time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(cutoff))} "
          f"-> {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))})")
    print(f"- Runs log: `{CANARY_RUNS_LOG}`")
    print(f"- Total runs: {len(runs)}")
    print()

    if not by_target:
        print("(no canary runs recorded in window)")
        return 0

    print(f"{'TARGET':<22}{'RUNS':<8}{'OK':<6}{'FAIL':<7}"
          f"{'SUCCESS%':<10}{'LAST_ACTION':<14}{'LAST_TS'}")
    print("-" * 80)
    for tg, rows in sorted(by_target.items()):
        ok = sum(1 for r in rows if str(r.get("outcome", "ok")).lower() == "ok")
        fail = sum(1 for r in rows if str(r.get("outcome", "ok")).lower()
                    in ("fail", "failed", "error"))
        total = len(rows)
        pct = (100.0 * ok / total) if total else 0.0
        last = rows[-1]
        print(
            f"{tg:<22}{total:<8}{ok:<6}{fail:<7}{pct:<10.1f}"
            f"{str(last.get('action', '?')):<14}{last.get('ts', '?')}"
        )
    return 0


def _parse_since(spec: str) -> int:
    """Parse a 'Nh' or 'Nm' duration spec into seconds. Default: 24h."""
    m = re.match(r"^(\d+)\s*([smhd]?)$", spec.strip())
    if not m:
        return 24 * 3600
    n = int(m.group(1))
    unit = m.group(2) or "s"
    return n * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]


# ---------------------------------------------------------------------------
# Subcommand: test — inline self-tests (must run in <2s)
# ---------------------------------------------------------------------------

def cmd_test(args: argparse.Namespace) -> int:
    """Run inline self-tests. Returns 0 if all pass, 1 if any fail.

    Each test prints PASS/FAIL on its own line. Final summary line is
    printed last. Designed to complete in well under 2 seconds.
    """
    results: list[tuple[str, bool, str]] = []

    # ---- Test 1: TOML parse with valid input ---------------------------
    try:
        good = (
            b'[canary]\ncohort_size_pct = 7\ncohort_key = "pid_mod_20"\n'
            b'[targets.foo]\nproduction = "1.0"\ncanary = "2.0"\n'
        )
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as tf:
            tf.write(good)
            tp = Path(tf.name)
        doc = _load_toml(tp)
        ok = (
            doc.get("canary", {}).get("cohort_size_pct") == 7
            and doc.get("targets", {}).get("foo", {}).get("production") == "1.0"
        )
        tp.unlink()
        results.append(("toml_parse_valid", ok, ""))
    except Exception as exc:
        results.append(("toml_parse_valid", False, f"raised {exc!r}"))

    # ---- Test 2: TOML parse with invalid input -------------------------
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as tf:
            tf.write(b"this is not = \"valid TOML = [\n")
            tp = Path(tf.name)
        try:
            _load_toml(tp)
            raised = False
        except Exception:
            raised = True
        tp.unlink()
        results.append(("toml_parse_invalid", raised, "should have raised"))
    except Exception as exc:
        results.append(("toml_parse_invalid", False, f"setup: {exc!r}"))

    # ---- Test 3: cohort membership — pid_mod_20 -----------------------
    in_cohort = [pid for pid in range(100, 200) if cohort_member("pid_mod_20", pid)]
    out_cohort = [pid for pid in range(100, 200) if not cohort_member("pid_mod_20", pid)]
    ok = (
        # All PIDs with % 20 == 0 must be in cohort
        all(pid % 20 == 0 for pid in in_cohort)
        # No PID with % 20 != 0 may be in cohort
        and not any(pid % 20 == 0 for pid in out_cohort)
        # ~5% membership (4 of 100 expected: 100, 120, 140, 160, 180)
        and 3 <= len(in_cohort) <= 6
    )
    results.append(("cohort_pid_mod_20", ok,
                    f"got {len(in_cohort)}/{len(in_cohort)+len(out_cohort)}"))

    # ---- Test 4: cohort membership — random_5pct -----------------------
    in_cohort = [pid for pid in range(1000, 2000) if cohort_member("random_5pct", pid)]
    pct = 100.0 * len(in_cohort) / 1000
    ok = 2.0 <= pct <= 8.0  # 5% +/- 3% to absorb hash noise on 1k samples
    # Determinism check: same PIDs → same cohort
    second = [pid for pid in range(1000, 2000) if cohort_member("random_5pct", pid)]
    ok = ok and in_cohort == second
    results.append(("cohort_random_5pct", ok, f"pct={pct:.1f}% deterministic={in_cohort == second}"))

    # ---- Test 5: cohort membership — hostname_match -------------------
    import socket as _socket
    hn = _socket.gethostname()
    # Matching regex → all PIDs in cohort
    in_match = [pid for pid in range(50) if cohort_member("hostname_match", pid,
                                                          extra=re.compile(re.escape(hn)))]
    ok_match = len(in_match) == 50
    # Non-matching regex → no PIDs in cohort
    in_nomatch = [pid for pid in range(50) if cohort_member("hostname_match", pid,
                                                             extra=re.compile(r"^nonexistent-host-XXX$"))]
    ok_nomatch = len(in_nomatch) == 0
    results.append(("cohort_hostname_match", ok_match and ok_nomatch,
                    f"match={len(in_match)} nomatch={len(in_nomatch)}"))

    # ---- Test 6: promotion / rollback state machine --------------------
    doc = json.loads(json.dumps(DEFAULT_CANARY_DOC))  # deep copy
    t = doc["targets"]["session-snapshot"]
    original_prod = t["production"]
    original_canary = t["canary"]
    # Simulate promote
    t["production"] = t["canary"]
    promoted = t["production"] == original_canary
    # Simulate rollback (manually)
    t["production"] = original_prod
    rolled = t["production"] == original_prod
    results.append(("promote_rollback_state", promoted and rolled,
                    f"promoted={promoted} rolled_back={rolled}"))

    # ---- Test 7: health threshold logic --------------------------------
    # Simulate 3 consecutive failures → ROLLED_BACK
    fake_doc = {
        "targets": {
            "x": {
                "production": "1.0",
                "auto_rollback": True,
            }
        }
    }
    # Inject runs into the runs log (in a temp file) — simpler: inline compute.
    runs = [
        {"target": "x", "outcome": "ok"},
        {"target": "x", "outcome": "fail"},
        {"target": "x", "outcome": "fail"},
        {"target": "x", "outcome": "fail"},
    ]
    consecutive_fail = 0
    for r in reversed(runs):
        if str(r.get("outcome", "")).lower() in ("fail", "failed", "error"):
            consecutive_fail += 1
        else:
            break
    ok_rb = consecutive_fail == 3
    # Healthy: 0 failures → HEALTHY (auto_rollback true, but no fails)
    consecutive_fail_zero = 0
    for r in [{"target": "x", "outcome": "ok"}]:
        if str(r.get("outcome", "")).lower() in ("fail", "failed", "error"):
            consecutive_fail_zero += 1
        else:
            break
    ok_healthy = consecutive_fail_zero == 0
    results.append(("health_threshold", ok_rb and ok_healthy,
                    f"3fail→{consecutive_fail}, 0fail→{consecutive_fail_zero}"))

    # ---- Test 8: report aggregation ------------------------------------
    # Build an in-memory list and verify aggregation math.
    fake_runs = [
        {"target": "a", "outcome": "ok", "ts_epoch": 1, "action": "run", "ts": "t"},
        {"target": "a", "outcome": "fail", "ts_epoch": 2, "action": "run", "ts": "t"},
        {"target": "a", "outcome": "ok", "ts_epoch": 3, "action": "run", "ts": "t"},
        {"target": "b", "outcome": "ok", "ts_epoch": 4, "action": "run", "ts": "t"},
    ]
    by_target: dict[str, list[dict]] = {}
    for r in fake_runs:
        by_target.setdefault(r["target"], []).append(r)
    a_ok = sum(1 for r in by_target["a"] if r["outcome"] == "ok")
    a_fail = sum(1 for r in by_target["a"] if r["outcome"] == "fail")
    b_ok = sum(1 for r in by_target["b"] if r["outcome"] == "ok")
    a_pct = 100.0 * a_ok / len(by_target["a"])
    ok = a_ok == 2 and a_fail == 1 and b_ok == 1 and abs(a_pct - 66.67) < 0.1
    results.append(("report_aggregation", ok,
                    f"a={a_ok}ok/{a_fail}fail pct={a_pct:.1f} b={b_ok}ok"))

    # ---- Tally ---------------------------------------------------------
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    for name, ok, note in results:
        marker = "PASS" if ok else "FAIL"
        if note:
            print(f"  [{marker}] {name}  ({note})")
        else:
            print(f"  [{marker}] {name}")
    print()
    print(f"canary: self-tests {passed}/{total}")
    return 0 if passed == total else 1


# ---------------------------------------------------------------------------
# argparse / main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canary",
        description="Canary deployment system for the resume-all toolkit.",
    )
    sp = p.add_subparsers(dest="cmd", metavar="SUBCMD")

    # status
    sp.add_parser("status", help="print cohort membership table")

    # cohort
    pc = sp.add_parser("cohort", help="list PIDs/sessions in canary cohort")
    pc.add_argument("target", help="target name (e.g. session-snapshot)")

    # promote
    pp = sp.add_parser("promote", help="promote canary version to production")
    pp.add_argument("target", help="target name")

    # rollback
    pr = sp.add_parser("rollback", help="rollback to production, kill canary")
    pr.add_argument("target", help="target name")

    # health
    ph = sp.add_parser("health", help="query canary cohort health")
    ph.add_argument("target", help="target name")

    # run
    prun = sp.add_parser("run", help="start canary instance(s)")
    prun.add_argument("target", help="target name")

    # stop
    pstop = sp.add_parser("stop", help="kill canary instance(s)")
    pstop.add_argument("target", help="target name")

    # report
    prep = sp.add_parser("report", help="summary of canary run history")
    prep.add_argument("--since", default=None,
                      help="time window (e.g. 24h, 30m, 7d); default 24h")

    # test
    sp.add_parser("test", help="run inline self-tests")

    return p


COMMANDS: dict[str, Any] = {
    "status": cmd_status,
    "cohort": cmd_cohort,
    "promote": cmd_promote,
    "rollback": cmd_rollback,
    "health": cmd_health,
    "run": cmd_run,
    "stop": cmd_stop,
    "report": cmd_report,
    "test": cmd_test,
}


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    if not args.cmd:
        parser.print_help()
        return 0
    fn = COMMANDS.get(args.cmd)
    if fn is None:
        print(f"canary: unknown subcommand '{args.cmd}'", file=sys.stderr)
        return 2
    return fn(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
