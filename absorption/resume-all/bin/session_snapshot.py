#!/usr/bin/env python3
"""
session_snapshot.py - Ghostty/tmux pane session snapshotter.

Walks every foreground process in ttysNNN (filtered to Ghostty pane parents),
classifies by harness (forge/codex/opencode/kilo/cursor/droid), extracts the
session_id from argv when present, and falls back to a batched cwd->sid lookup
via each harness's own storage layout.

Output: append-only JSONL at ~/.local/share/resume-all/snapshot.jsonl.

Exit codes:
  0  snapshot written
  1  nothing changed (idempotent re-run)
  2  fatal (no Ghostty/tmux backend, write error)
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import select
import shlex
import shutil
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

# Tiny client for the sharecli-ipc UNIX socket. Used to emit one
# `sharecli-tray availability` row in every snapshot. Best-effort import:
# if the bridge module is missing we still snapshot panes, we just emit a
# degraded row with `available=false`.
#
# The bridge lives at `~/bin/sharecli_bridge.py` (a sibling of this file)
# but `~/bin` is not on the default Python sys.path, so we add the
# directory of *this* file explicitly before the import — same pattern
# used in `resume-all.py` for its sibling `resolver` module.
try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    import sharecli_bridge as _sharecli_bridge  # type: ignore[import-not-found]
    _SHARECLI_BRIDGE_AVAILABLE = True
except Exception:
    _sharecli_bridge = None  # type: ignore[assignment]
    _SHARECLI_BRIDGE_AVAILABLE = False

# ----- small shared helpers ---------------------------------------------------

def _procs_call_json(args: list[str]) -> list[dict] | None:
    """Run procs with the given args and return the parsed JSON result."""
    try:
        r = subprocess.run(['procs', '--json'] + args, capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, OSError):
        return None

def _read_first_line_from_process(
    args: list[str], timeout: float = 3.0, max_bytes: int = 64 * 1024
) -> bytes | None:
    """Read one bounded output line without ``subprocess.run`` buffering."""
    proc: subprocess.Popen[bytes] | None = None
    try:
        proc = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if proc.stdout is None:
            return None
        deadline = time.monotonic() + timeout
        data = bytearray()
        while len(data) < max_bytes:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(args, timeout)
            ready, _, _ = select.select([proc.stdout], [], [], remaining)
            if not ready:
                raise subprocess.TimeoutExpired(args, timeout)
            chunk = os.read(proc.stdout.fileno(), min(4096, max_bytes - len(data)))
            if not chunk:
                break
            newline = chunk.find(b"\n")
            if newline >= 0:
                data.extend(chunk[:newline])
                break
            data.extend(chunk)
        return bytes(data) if data else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


# ISO-8601 UTC timestamp generator (used as both `now_iso` and `_iso_now`).
def now_iso() -> str:
    """Return current UTC timestamp as ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Aliases for canonical helper names referenced elsewhere in this file.
_iso_now = now_iso
_now_iso = now_iso

# ----- constants -------------------------------------------------------------

SNAPSHOT_DIR = Path.home() / ".local" / "share" / "resume-all"
SNAPSHOT_FILE = SNAPSHOT_DIR / "snapshot.jsonl"
WALKER_CACHE_FILE = SNAPSHOT_DIR / "walker.cache.json"
WALKER_CACHE_TTL_SEC = 25.0  # process tree rarely changes within a 30s launchd tick
SHARECLI_CACHE_FILE = SNAPSHOT_DIR / "sharecli.cache.json"
SHARECLI_CACHE_TTL_SEC = 25.0
PREVIOUS_CACHE_FILE = SNAPSHOT_DIR / "previous.cache.json"
PREVIOUS_CACHE_TTL_SEC = 25.0  # snapshot.jsonl only changes after we write it
# Lock file used to serialize concurrent session-snapshot runs.
# `.lock` suffix keeps it hidden in `ls` and avoids glob matches against real
# snapshot.jsonl rows.
SNAPSHOT_LOCK = SNAPSHOT_DIR / ".snapshot.lock"

# Ghostty parent PID matches; filter ttysNNN PIDs to those.
GHOSTTY_PARENT_CMDS = {"Ghostty", "ghostty", "com.mitchellh.ghostty"}
GHOSTTY_BINARY_RE = re.compile(r"ghostty", re.IGNORECASE)

# Live-row retention: drop rows not seen for this long.
LIVE_TTL_SEC = 7 * 24 * 3600
DEAD_TTL_SEC = 24 * 3600

# Harness argv-regex patterns - prefer explicit-id forms over cwd-fallback.
HARNESS_PATTERNS: list[tuple[str, re.Pattern[str], re.Pattern[str] | None]] = [
    # (harness, argv-match, optional-sid-extraction)
    ("forge",     re.compile(r"\bforge\b"),           re.compile(r"--conversation-id[ =](\S+)")),
    ("codex",     re.compile(r"\bcodex\b"),           None),
    ("opencode",  re.compile(r"\bopencode\b"),        re.compile(r"--session[ =](\S+)")),
    ("kilo",      re.compile(r"\bkilo\b"),            re.compile(r"--session[ =](\S+)")),
    ("cursor",    re.compile(r"\bcursor-agent\b"),    re.compile(r"--resume[ =](\S+)")),
    ("droid",     re.compile(r"\bdroid\b"),           None),
]

# ANSI ESC sequences that may leak into argv from terminal-aware prompts.
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b[=>]")

# UUID used for forge / codex / kilo / cursor / droid sid matches.
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

# ----- result types ----------------------------------------------------------


@dataclass(slots=True)
class Pane:
    tty: str
    pid: int
    ppid: int
    cwd: str
    cmd: str
    cmd_clean: str
    harness: str
    sid_from_argv: str = ""
    surface_id: str = ""       # Ghostty surface UUID (best-effort)
    surface_name: str = ""     # Ghostty terminal title (best-effort)
    ports: list[str] = field(default_factory=list)  # listening ports, for dev-server resurrection
    ts: str = ""
    zmx_name: str = ""        # if non-empty, pane is a zmx session; resume via `zmx attach <name>`

    def stable_key(self) -> str:
        # Stable across crashes: zmx sessions are keyed by name; otherwise TTY+cwd+harness.
        if self.zmx_name:
            return f"zmx|{self.zmx_name}"
        return f"{self.harness}|{self.tty}|{self.cwd}|{self.cmd_clean[:200]}"
def _build_pane_from_normalized(norm: "Normalized", backend: "WalkerBackend") -> Pane:
    """Build a Pane dataclass from a normalized walker row.

    Single builder used by all four walker backends so the field
    contract is enforced in one place — replace these 3 sites when a
    field is added.

    Slice 5: switched every field to ``.get(...)`` so missing keys from
    fast walkers (zig/procx don't emit ``tty``; zig/procx don't emit
    ``surface_id``) degrade to defaults instead of raising
    ``AttributeError`` (the bug that previously made all three fast
    walkers crash and forced a ~2s legacy fallback).
    """
    return Pane(
        tty=norm.get("tty", "") or "",
        pid=norm["pid"],
        ppid=norm.get("ppid", 0) or 0,
        cwd=norm.get("cwd", "") or "/",
        cmd=norm.get("cmd", "") or "",
        cmd_clean=norm.get("cmd", "") or "",
        harness=norm.get("harness", "shell") or "shell",
        sid_from_argv=norm.get("sid_from_argv", "") or "",
        surface_id=norm.get("surface_id", "") or "",
        surface_name=norm.get("surface_name", "") or "",
        ports=norm.get("ports", []) or [],
        ts=now_iso(),
    )

@dataclass
class CachedRow:
    """A previously-seen pane row, for prune."""
    ts: str
    pane_id: str
    harness: str
    session_id: str
    cwd: str
    dead: bool = False
    surface_id: str = ""


# ----- backend: detect + walk panes ------------------------------------------


def _osa_ghostty_alive(timeout: int = 5) -> bool:
    """Live AppleScript probe: is the Ghostty Apple Events bridge reachable?

    This is the authoritative detection. ps-grep is brittle (case-sensitivity,
    path differences) and slower; the Apple Events bridge responds in <300ms
    when Ghostty is running and isn't reachable when it's not.
    """
    if not shutil.which("osascript"):
        return False
    try:
        r = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to (exists application process "Ghostty")'],
            capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode == 0 and r.stdout.strip().lower() == "true"
    except (subprocess.TimeoutExpired, OSError):
        return False


DETECT_CACHE_FILE = SNAPSHOT_DIR / "detect.cache.json"
DETECT_CACHE_TTL_SEC = 25.0  # Ghostty's lifetime is usually minutes-to-hours

# In-process memoization for detect_backend so a single tick that calls
# it twice (once via main, once via write_snapshot's tray row) doesn't
# re-issue the osascript probe.
_detect_backend_cache: dict[str, str] = {}


def _procs_ghostty_alive() -> bool:
    """Process-tree fallback: is the Ghostty binary running on this machine?

    Used when the AppleScript bridge is unreachable (launchd Background /
    xpcproxy, SSH, headless). Tiered by speed + reliability:
      1. pgrep -x ghostty         — fastest, exact-match on process name
      2. procs --tree ghostty     — full argv tree (may be empty if procs
                                    parses argv lazily and Ghostty's
                                    child ttysNNN outranks it on a busy box)
      3. ps -axco command | grep  — last-resort BSD ps scan
    """
    # Tier 1: pgrep exact match. Fastest and most reliable.
    pgrep_bin = shutil.which("pgrep") or "/usr/bin/pgrep"
    if os.path.exists(pgrep_bin):
        try:
            r = subprocess.run(
                [pgrep_bin, "-x", "-q", "ghostty"],
                capture_output=True, timeout=2,
            )
            if r.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
    # Tier 2: procs tree walk.
    procs_bin = shutil.which("procs") or "/opt/homebrew/bin/procs"
    if os.path.exists(procs_bin):
        try:
            r = subprocess.run(
                [procs_bin, "--tree", "ghostty"],
                capture_output=True, text=True, timeout=3,
            )
            if r.returncode == 0 and r.stdout.strip():
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
    # Tier 3: BSD ps scan.
    try:
        r = subprocess.run(
            ["ps", "-axco", "command"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                name = line.strip().lower()
                if name in ("ghostty", "com.mitchellh.ghostty"):
                    return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return False


def detect_backend() -> str:
    """tmux if $TMUX + tmux server reachable, else ghostty if Apple Events
    bridge live or Ghostty binary running.

    Slice 5: cached on disk (TTL 25s) so the 250-680ms osascript probe is
    only issued once per launchd tick. A second invocation in the same
    process (e.g. main() + write_snapshot()) hits the in-process
    ``_detect_backend_cache`` memo and returns instantly.

    Slice 11 (launchd fix): when AppleScript is unreachable (xpcproxy,
    headless), fall through to a process-tree probe via `procs` / `ps` so
    the snapshot still runs from launchd Background.
    """
    if "value" in _detect_backend_cache:
        return _detect_backend_cache["value"]
    cached = _disk_cache_get(DETECT_CACHE_FILE, DETECT_CACHE_TTL_SEC)
    if isinstance(cached, dict):
        value = cached.get("value")
        if value in ("tmux", "ghostty", "none"):
            _detect_backend_cache["value"] = value
            return value

    value = "none"
    if os.environ.get("TMUX"):
        try:
            r = subprocess.run(["tmux", "list-panes", "-a"],
                               capture_output=True, timeout=3)
            if r.returncode == 0:
                value = "tmux"
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
    if value == "none":
        # Tier 0 (Phase B): WezTerm — detected via WEZTERM_PANE env or
        # `wezterm cli list` if on PATH. WezTerm is the canonical backend
        # on Windows Terminal / WSL / Linux targets.
        if os.environ.get("WEZTERM_PANE"):
            value = "wezterm"
            log("info", "detect: wezterm via WEZTERM_PANE env")
        elif shutil.which("wezterm"):
            try:
                r = subprocess.run(["wezterm", "cli", "list"],
                                   capture_output=True, timeout=3)
                if r.returncode == 0:
                    value = "wezterm"
                    log("info", "detect: wezterm via `wezterm cli list`")
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass
        else:
            # Tier 0.5 (Phase B): Windows Terminal — detected via WT_SESSION
            # env or `where wt` on PATH. Used on Windows 11 native.
            if os.environ.get("WT_SESSION"):
                value = "windows-terminal"
                log("info", "detect: windows-terminal via WT_SESSION env")
            elif sys.platform == "win32" and shutil.which("wt"):
                value = "windows-terminal"
                log("info", "detect: windows-terminal via `where wt`")
            # Tier 0.6: WSL — detected via WSL_DISTRO_NAME (set inside WSL)
            # or `WSLENV` presence. Used inside WSL sessions.
            elif os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSLENV"):
                value = "wsl"
                log("info", "detect: wsl via WSL_DISTRO_NAME/WSLENV env")
    if value == "none":
        # Tier 1: AppleScript (authoritative when GUI session is reachable).
        osa_ok = _osa_ghostty_alive()
        log("info", f"detect: osa={osa_ok}")
        if osa_ok:
            value = "ghostty"
        else:
            # Tier 2: process-tree fallback (works from launchd xpcproxy / SSH).
            procs_ok = _procs_ghostty_alive()
            log("info", f"detect: procs={procs_ok}")
            if procs_ok:
                value = "ghostty"
    _detect_backend_cache["value"] = value
    _disk_cache_put(DETECT_CACHE_FILE, {"value": value})
    return value


def ghostty_surface_table() -> dict[str, tuple[str, str]]:
    """Return {surface_uuid: (title, cwd)} best-effort from AppleScript.
    cwd is almost always empty - Ghostty doesn't expose OSC7 via sdef."""
    table: dict[str, tuple[str, str]] = {}
    script = (
        'tell application "Ghostty"\n'
        '  set out to ""\n'
        '  repeat with w in every window\n'
        '    repeat with t in every tab of w\n'
        '      repeat with term in every terminal of t\n'
        '        try\n'
        '          set out to out & (id of term) & tab & (name of term) & tab & (working directory of term) & linefeed\n'
        '        end try\n'
        '      end repeat\n'
        '    end repeat\n'
        '  end repeat\n'
        '  return out\n'
        'end tell\n'
    )
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True,
                           text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return table
    if r.returncode != 0:
        return table
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            sid = parts[0].strip()
            title = parts[1].strip()
            cwd = parts[2].strip() if len(parts) > 2 else ""
            if sid:
                table[sid] = (title, cwd)
    return table


SHELL_ANCESTOR_RE = re.compile(
    r"^(?:[-/A-Za-z0-9_]*bin/(?:zsh|bash|sh|fish|tcsh|ksh)|"
    r"/usr/bin/login|"
    r"/usr/bin/script|"
    r"/usr/bin/sshd|"
    r"login(?:\s|$))"
)


def _ps_invoke(args: list[str], timeout: int = 5) -> str:
    """Run a ps probe with a portable command-column fallback chain.

    Tries, in order:
      1. ``args=`` instead of ``command=`` — works on macOS BSD, Linux procps,
         Linux BusyBox (BusyBox ``ps`` rejects ``command=`` and only accepts
         ``args``).
      2. Original args (typically ``command=``) — BSD/GNU ps only, falls back
         for macOS/procps hosts that prefer ``command`` over ``args``.
      3. Plain ``-A -o pid=,tty=,comm=`` — the universal last-resort that
         works everywhere (comm is the binary basename).

    Returns stdout on the first non-zero returncode, ``""`` if every attempt
    failed (timeout, missing binary, non-zero exit).

    Slice 5 perf note: BSD ``ps`` (macOS) hangs indefinitely when its stdout is
    captured via a Python pipe (``subprocess.run(..., capture_output=True)``)
    because BSD ``ps`` does group-by-TTY reformatting on a pipe and then
    blocks on stdin. We side-step that by writing stdout to a tempfile when
    the attempt would use ``command=`` (BSD-ps-affected forms). This restores
    the <10ms ``ps`` walks the legacy walker relied on.
    """
    attempts: list[list[str]] = []
    args_swap = [arg.replace("command=", "args=") for arg in args]
    if args_swap != args:
        attempts.append(args_swap)            # 1. args= (universal, no pipe-hang)
    if list(args) != args_swap:
        attempts.append(list(args))           # 2. command= (BSD/GNU; tempfile)
    attempts.append(["-A", "-o", "pid=,tty=,comm="])  # 3. default last-resort

    for attempt in attempts:
        # BSD-ps-affected attempts (those with ``command=``) get a tempfile
        # stdout to dodge the pipe-stdin hang. The args= form is safe with
        # pipes.
        needs_tmpfile = any("command=" in a for a in attempt)
        try:
            if needs_tmpfile:
                import tempfile as _tf
                fd, tmpname = _tf.mkstemp(prefix="ps-", suffix=".out", dir="/tmp")
                try:
                    with os.fdopen(fd, "w") as fh:
                        result = subprocess.run(
                            ["ps", *attempt],
                            stdout=fh,
                            stderr=subprocess.DEVNULL,
                            timeout=timeout,
                            stdin=subprocess.DEVNULL,
                        )
                finally:
                    pass
                try:
                    with open(tmpname) as fh:
                        stdout = fh.read()
                finally:
                    try:
                        os.unlink(tmpname)
                    except OSError:
                        pass
                if result.returncode == 0:
                    return stdout
            else:
                result = subprocess.run(
                    ["ps", *attempt],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    stdin=subprocess.DEVNULL,
                )
                if result.returncode == 0:
                    return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    return ""


def _descendant_harness(tty_pid: int, max_depth: int = 6) -> tuple[int, str]:
    """BFS down from a ttysNNN zsh PID, return (leaf_pid, leaf_cmd)
    where leaf is the deepest descendant whose argv isn't a shell/login.
    Falls back to (tty_pid, zsh_cmd) if no harness descendant is found
    within max_depth hops."""
    # Build {ppid -> [child_pids]} once for the whole subtree.
    proc_text = _ps_invoke(["-axo", "pid=,ppid=,command="])
    children_of: dict[int, list[int]] = {}
    cmd_of: dict[int, str] = {}
    for line in proc_text.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except ValueError:
            continue
        children_of.setdefault(ppid, []).append(pid)
        cmd_of[pid] = parts[2]

    # BFS
    frontier = [tty_pid]
    visited = {tty_pid}
    harness_leaf = (tty_pid, cmd_of.get(tty_pid, ""))
    for _ in range(max_depth):
        next_frontier: list[int] = []
        for p in frontier:
            for c in children_of.get(p, []):
                if c in visited:
                    continue
                visited.add(c)
                ccmd = cmd_of.get(c, "")
                if not ccmd:
                    continue
                if SHELL_ANCESTOR_RE.match(ccmd.strip()):
                    # Still a shell ancestor — descend into its children.
                    next_frontier.append(c)
                else:
                    # Real harness descendant. If it spawns its own children,
                    # keep walking (cursor-agent spawns node, codex spawns rust).
                    harness_leaf = (c, ccmd)
                    next_frontier.append(c)
        if not next_frontier:
            break
        frontier = next_frontier
    return harness_leaf


def _disk_cache_get(path: Path, ttl_sec: float) -> Any | None:
    """Return cached JSON payload from ``path`` if it exists and is younger than ``ttl_sec``.

    Returns None on miss, corrupt cache, or expired entry. Caller decides what to do
    with the None (typically: recompute, then ``_disk_cache_put`` to refresh).

    Slice 5: this is the lazy-disk-backed cache primitive that lets the snapshot
    tick skip 500ms ``procs --json`` + 2s sharecli IPC + full-file parse of the
    previous snapshot.jsonl when the inputs haven't moved within the launchd
    30s tick window. The cache files live next to ``snapshot.jsonl`` so launchd
    cleanup is unaffected.
    """
    try:
        st = path.stat()
    except OSError:
        return None
    if (time.time() - st.st_mtime) > ttl_sec:
        return None
    try:
        with path.open("rb") as fh:
            payload = json.loads(fh.read())
    except (OSError, json.JSONDecodeError):
        return None
    return payload


def _disk_cache_put(path: Path, payload: Any) -> None:
    """Best-effort JSON write of ``payload`` to ``path``. Atomic via tempfile + os.replace.

    Failures are silent (caller is best-effort) — if we can't write the cache,
    we just lose the lazy speedup and recompute next time. The on-disk snapshot
    is the source of truth, not the cache.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{time.time_ns() // 1000}")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, default=str)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError as exc:
        log("warn", f"disk cache write to {path.name} failed: {exc}")


def _tty_pids_by_tty() -> dict[str, list[tuple[int, str]]]:
    """Return {tty: [(pid, cmd), ...]} for every TTY currently in use.

    Each Ghostty pane has multiple PIDs on the same TTY (login helper,
    user shell, the harness itself — even if the harness was reparented
    to launchd, it inherits the controlling TTY). We keep ALL of them and
    select the leaf per TTY in `walk_ghostty_panes`.
    """
    proc_text = _ps_invoke(["-axo", "pid=,tty=,command="])
    by_tty: dict[str, list[tuple[int, str]]] = {}
    for line in proc_text.splitlines():
        # pid=tty=cmd  →  find the first "ttysNNN" anywhere in the line.
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        tty_match = re.search(r"\bttys\d+\b", line)
        if not tty_match:
            continue
        tty = tty_match.group(0)
        cmd = parts[2]
        by_tty.setdefault(tty, []).append((pid, cmd))
    return by_tty


def _pick_harness_on_tty(tty: str, pids: list[tuple[int, str]]) -> tuple[int, str, int] | None:
    """Among multiple PIDs on one TTY, pick the one with the harness argv.

    Returns (pid, cmd, login_pid) where login_pid is the direct parent login
    helper for surface-id correlation. Returns None if only shells present."""
    # Filter to non-shell PIDs first.
    candidates = [(p, c) for (p, c) in pids if not SHELL_ANCESTOR_RE.match(c.strip())]
    if not candidates:
        return None  # no harness candidate — pure shell pane
    # Prefer the lowest PID number (oldest non-shell, which is the login helper
    # is NOT in candidates — it's filtered — so the next-oldest is usually the
    # harness parent. Actually we want the HIGHEST PID, which is most-recently
    # spawned — for a forked harness process that is detached, that's us.
    candidates.sort(key=lambda pc: pc[0])
    harness_pid, harness_cmd = candidates[-1]
    # Find the oldest candidate (closest to login helper) for surface correlation.
    login_pid = candidates[0][0]
    return (harness_pid, harness_cmd, login_pid)


def _stable_hash(tty: str, argv: str, cwd: str) -> str:
    """Stable content hash for a pane, used as the row's `stable_id` so consecutive
    snapshot ticks can dedupe across re-runs even when Ghostty surface UUIDs change.

    Args are taken in (tty, argv, cwd) order. Strip ANSI escapes from argv before
    calling so colorized terminal output doesn't perturb the hash.
    """
    h = hashlib.sha1()
    h.update((tty or "").encode())
    h.update(b"\x00")
    h.update((argv or "").encode())
    h.update(b"\x00")
    h.update((cwd or "").encode())
    return h.hexdigest()[:16]


def _split_procx_argv(raw: str) -> list[str]:
    """Split a procs/thegent-procx ``Command`` string into argv tokens.

    procs/thegent-procx often joins argv with commas instead of spaces (e.g.
    ``--conversation-id,<UUID>``) — shlex alone leaves them glued together.
    Split on commas and whitespace together so we get clean tokens every time.
    """
    if not raw:
        return []
    # First: split on commas AND whitespace (preserves quoted groups).
    text = raw.replace(",", " ")
    try:
        toks = shlex.split(text)
        if toks:
            return toks
    except ValueError:
        pass
    # Fallback: pure whitespace split.
    return [t for t in text.split() if t]  # noqa: E501


def _classify(cmd: str, argv_tokens: list[str] | None = None) -> tuple[str, str]:
    """Classify a process row into a harness name + sid (if visible).

    Looks at the full argv first (so we catch `forge --conversation-id <UUID>`
    even when procs' `cmd` field only returns the bare binary name). Falls back
    to the basename of `cmd` for argv-less rows.

    Returns ``("shell", "")`` if no match.
    """
    haystacks: list[str] = []
    if argv_tokens:
        haystacks.append(" ".join(argv_tokens).lower())
    if cmd:
        haystacks.append(cmd.lower())
    if not haystacks:
        return ("shell", "")

    bin_basename = os.path.basename(cmd.split()[0] if cmd.split() else cmd).lower()

    # Forge: full argv contains the bare binary name OR a forge session UUID
    for hay in haystacks:
        for token in hay.split():
            token = token.strip(",;")
            if token in ("forge", "forge.exe"):
                sid = _extract_sid_from_argv(argv_tokens or cmd.split(), "forge") if argv_tokens else ""
                return ("forge", sid)
            if "forge" in token and token.startswith("/") is False and len(token) < 32:
                # path-like token containing forge
                sid = _extract_sid_from_argv(argv_tokens or cmd.split(), "forge") if argv_tokens else ""
                return ("forge", sid)

    # codex --dangerously-bypass-approvals-and-sandbox --search <resume mode>
    for hay in haystacks:
        if "codex" in hay:
            return ("codex", "")
    # cursor-agent / cursor
    for hay in haystacks:
        if "cursor-agent" in hay or "cursorcli" in hay or "/cursor" in hay:
            return ("cursor", "")
    # kilo / kilo-cli
    for hay in haystacks:
        if "/kilo" in hay or "kilocode" in hay or "kilo-cli" in hay:
            return ("kilo", "")
    # opencode
    for hay in haystacks:
        if "opencode" in hay:
            return ("opencode", "")
    # droid (factory ai)
    for hay in haystacks:
        if "droid" in hay:
            return ("droid", "")

    # Final fallback: basename match (covers the bare-binary case from procs)
    if bin_basename in ("forge",):
        return ("forge", "")
    if bin_basename in ("codex",):
        return ("codex", "")
    if bin_basename in ("cursor-agent", "cursor"):
        return ("cursor", "")
    if bin_basename in ("kilo", "kilo-cli"):
        return ("kilo", "")
    if bin_basename in ("opencode",):
        return ("opencode", "")
    if bin_basename in ("droid",):
        return ("droid", "")

    return ("shell", "")
    return ("shell", "")


def _now_iso() -> str:
    """UTC timestamp suitable for JSONL rows."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(level: str, msg: str) -> None:
    """Stderr log helper."""
    print(f"session-snapshot: [{level}] {msg}", file=sys.stderr)

# ─── Unified Walker ────────────────────────────────────────────────────────────
# Three process-tree backends (thegent-proc-zig, procs, thegent-procx) plus a
# legacy Ghostty-AppleScript fallback. Each produces rows with slightly different
# field names; the unified walker normalizes them into a single Pane shape.
#
# KISS: one dispatch function, three subprocess invocations, three row
# normalizers. Backend selection is the priority cascade in walk_ghostty_panes().


class WalkerBackend(str, Enum):
    ZIG = "zig"        # thegent-proc-zig (libproc directly, 1.9 MB)
    PROCS = "procs"    # Homebrew procs (fast, macOS-native TTY)
    PROCX = "procx"    # thegent-procx (Rust + sysinfo, full kernel argv)
    LEGACY = "legacy"  # ps -ww + lsof + AppleScript (last-resort fallback)


def _normalize_zig_row(r: dict, ts: str) -> dict | None:
    """Normalize a thegent-proc-zig JSON row to the canonical Pane shape."""
    pid = r.get("pid")
    if not pid or pid <= 0:
        return None
    cmd = (r.get("cmd") or "").strip()
    cwd = r.get("cwd") or "/"
    if cwd == "":
        cwd = "/"
    return {
        "pid": int(pid),
        "cmd": cmd,
        "cwd": cwd,
        "argv": cmd,  # zig walker only emits cmd; argv enrichment is the Rust fallback
        "backend": WalkerBackend.ZIG.value,
    }


def _normalize_procs_row(r: dict, ts: str) -> dict | None:
    """Normalize a procs JSON row to the canonical Pane shape.

    Slice 5: procs strips the leading ``tty`` from its TTY column (a value
    of ``s000`` actually means ``ttys000``), so we restore the prefix here
    before downstream consumers compare against the BSD-ps tty shape.
    """
    pid = (r.get("PID") or r.get("pid"))
    if not pid or pid <= 0:
        return None
    cmd = (r.get("Command") or r.get("command") or "").strip()
    tty_raw = (r.get("TTY") or r.get("tty") or "").strip()
    # procs emits TTY as "sNNN" (the "tty" prefix is dropped); restore it.
    if tty_raw and tty_raw.startswith("s") and tty_raw[1:].isdigit():
        tty_raw = "tty" + tty_raw
    cwd = r.get("cwd") or "/"
    if cwd == "":
        cwd = "/"
    return {
        "pid": int(pid),
        "cmd": cmd,
        "tty": tty_raw,
        "cwd": cwd,
        "argv": cmd,
        "backend": WalkerBackend.PROCS.value,
    }


def _normalize_procx_row(r: dict, ts: str) -> dict | None:
    """Normalize a thegent-procx JSON row to the canonical Pane shape.

    procx includes the full argv (e.g. 'forge --conversation-id <UUID>'),
    so `args` is the canonical source for command + args.
    """
    pid = r.get("pid")
    if not pid or pid <= 0:
        return None
    cmd = (r.get("cmd") or "").strip()
    args = r.get("args") or ""
    argv_full = args if args else cmd
    cwd = r.get("cwd") or "/"
    if cwd == "":
        cwd = "/"
    return {
        "pid": int(pid),
        "cmd": cmd,
        "cwd": cwd,
        "argv": argv_full,
        "backend": WalkerBackend.PROCX.value,
    }


def _walk_zig() -> list[Pane]:
    """thegent-proc-zig (libproc-direct Zig 0.16 walker)."""
    panes: list[Pane] = []
    which_zig = shutil.which("thegent-proc-zig")
    if not which_zig:
        return panes
    try:
        out = subprocess.run(
            [which_zig], capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return panes
        rows = json.loads(out.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as exc:
        log("warn", f"thegent-proc-zig walker failed: {exc}")
        return panes

    by_pid: dict[int, Pane] = {}
    for r in rows:
        norm = _normalize_zig_row(r, ts=now_iso())
        if norm is None:
            continue
        pid = norm["pid"]
        if SHELL_ANCESTOR_RE.search(norm["cmd"]):
            continue
        pane = _build_pane_from_normalized(norm, backend=WalkerBackend.ZIG)
        by_pid[pid] = pane
    panes.extend(by_pid.values())
    return panes


def _walk_procs() -> list[Pane]:
    """Homebrew procs (fast, macOS-native TTY)."""
    panes: list[Pane] = []
    which_procs = shutil.which("procs")
    if not which_procs:
        return panes
    try:
        # 3s timeout — procs normally returns in <500ms; anything longer means
        # the launchd Background process is starved (CPU contention or a missing
        # Mach port) and we should fall through to the next walker fast so the
        # 30s loop tick completes. Slice 11 (launchd hardening).
        out = subprocess.run(
            [which_procs, "--json"], capture_output=True, text=True, timeout=3,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return panes
        rows = json.loads(out.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as exc:
        log("warn", f"procs walker failed: {exc}")
        return panes

    by_pid: dict[int, Pane] = {}
    for r in rows:
        norm = _normalize_procs_row(r, ts=now_iso())
        if norm is None:
            continue
        pid = norm["pid"]
        if SHELL_ANCESTOR_RE.search(norm["cmd"]):
            continue
        pane = _build_pane_from_normalized(norm, backend=WalkerBackend.PROCS)
        by_pid[pid] = pane
    panes.extend(by_pid.values())
    return panes


def _walk_procx() -> list[Pane]:
    """thegent-procx (Rust + sysinfo, full kernel argv)."""
    panes: list[Pane] = []
    which_procx = shutil.which("thegent-procx")
    if not which_procx:
        return panes
    try:
        out = subprocess.run(
            [which_procx, "--threads", "--all-users"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return panes
        rows = json.loads(out.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as exc:
        log("warn", f"thegent-procx walker failed: {exc}")
        return panes

    by_pid: dict[int, Pane] = {}
    for r in rows:
        norm = _normalize_procx_row(r, ts=now_iso())
        if norm is None:
            continue
        pid = norm["pid"]
        if SHELL_ANCESTOR_RE.search(norm["cmd"]):
            continue
        pane = _build_pane_from_normalized(norm, backend=WalkerBackend.PROCX)
        by_pid[pid] = pane
    panes.extend(by_pid.values())
    return panes


def _walk_legacy() -> list[Pane]:
    """Last-resort: ps -ww + lsof + AppleScript for exact Ghostty surface IDs."""
    return _walk_ghostty_panes_legacy()


# Single source of truth for priority cascade.
_WALKERS: dict[WalkerBackend, Callable[[], list[Pane]]] = {
    WalkerBackend.ZIG: _walk_zig,
    WalkerBackend.PROCS: _walk_procs,
    WalkerBackend.PROCX: _walk_procx,
    WalkerBackend.LEGACY: _walk_legacy,
}


def _is_ghostty_pane(pane: Pane) -> bool:
    """True if this pane qualifies as a Ghostty pane worth snapshotting.

    Slice 5: the fast walkers (zig/procs/procx) walk every process on the
    host; only the legacy walker used to filter to ``ttysNNN``. We apply
    the same filter here at the dispatcher so the snapshot doesn't get
    flooded with non-Ghostty processes (every helper process becomes a
    "shell" pane under the new walkers). Synthetic zmx panes and tmux
    panes are kept verbatim.
    """
    if pane.zmx_name:
        return True
    tty = pane.tty or ""
    if tty.startswith("ttys"):
        return True
    if tty.startswith("tmux:"):
        return True
    return False


def _pane_from_dict(d: dict) -> Pane:
    """Inverse of dataclasses.asdict(Pane). Used to revive cached Pane rows."""
    return Pane(
        tty=d.get("tty", "") or "",
        pid=int(d.get("pid", 0) or 0),
        ppid=int(d.get("ppid", 0) or 0),
        cwd=d.get("cwd", "") or "",
        cmd=d.get("cmd", "") or "",
        cmd_clean=d.get("cmd_clean", "") or "",
        harness=d.get("harness", "shell") or "shell",
        sid_from_argv=d.get("sid_from_argv", "") or "",
        surface_id=d.get("surface_id", "") or "",
        surface_name=d.get("surface_name", "") or "",
        ports=list(d.get("ports", []) or []),
        ts=d.get("ts", "") or now_iso(),
        zmx_name=d.get("zmx_name", "") or "",
    )


def walk_ghostty_panes() -> list[Pane]:
    """Return list of Pane from the best available backend.

    Priority: 1) procs (Homebrew, exposes tty reliably on macOS),
    2) legacy ps+lsof+osascript (fallback, exact Ghostty surface IDs).
    3) thegent-proc-zig and thegent-procx remain in the registry for
       future expansion, but they're tried after legacy on macOS because
       sysinfo/libproc don't expose the controlling TTY (tty="" for every
       row). See the dispatch in `_WALKERS`.

    Each backend is tried in order; first to return a non-empty list wins.
    zmx-backed panes are merged in at the end (zmx daemon managed sessions).

    Slice 5: every result is filtered through ``_is_ghostty_pane`` so the
    fast walkers (which walk every process) don't flood the snapshot.

    Slice 5 (cont.): the parsed Pane list is memoized to disk via
    ``WALKER_CACHE_FILE`` with TTL 1.5s. Within a launchd 30s tick, the
    second invocation (or a manual re-run) reuses the prior walk result
    and skips the 250-750ms ``procs --json`` subprocess entirely.
    """
    cached = _disk_cache_get(WALKER_CACHE_FILE, WALKER_CACHE_TTL_SEC)
    if isinstance(cached, list):
        try:
            panes = [_pane_from_dict(d) for d in cached if isinstance(d, dict)]
            if panes:
                log("info", f"walker: cache-hit ({len(panes)} panes)")
                return panes
        except Exception as exc:
            log("warn", f"walker cache replay failed: {exc}")

    panes: list[Pane] = []
    for backend in (WalkerBackend.PROCS,
                    WalkerBackend.LEGACY,
                    WalkerBackend.ZIG,
                    WalkerBackend.PROCX):
        try:
            panes = _WALKERS[backend]()
        except Exception as exc:
            log("warn", f"{backend.value} walker crashed: {exc}")
            panes = []
        if panes:
            log("info", f"walker: {backend.value} ({len(panes)} panes pre-filter)")
            break

    # Filter to Ghostty-bound panes only (ttysNNN, tmux, or synthetic zmx).
    pre_filter = len(panes)
    panes = [p for p in panes if _is_ghostty_pane(p)]
    if pre_filter != len(panes):
        log("info", f"walker: filtered {pre_filter - len(panes)} non-Ghostty pane(s)")

    # Merge in zmx-backed panes (zmx daemon managed sessions).
    try:
        zmx_panes = _load_zmx_panes()
        if zmx_panes:
            existing = {p.stable_key() for p in panes}
            for zp in zmx_panes:
                if zp.stable_key() not in existing:
                    panes.append(zp)
    except Exception:
        pass

    # Persist for the next tick. Best-effort — a write failure just means
    # next tick re-walks.
    try:
        _disk_cache_put(WALKER_CACHE_FILE, [asdict(p) for p in panes])
    except Exception as exc:
        log("warn", f"walker cache write skipped: {exc}")
    return panes


def _walk_ghostty_panes_legacy() -> list[Pane]:
    """Legacy ps+lsof+osascript walker (Ghostty-AppleScript surface IDs)."""
    raw = _osa_ghostty_surfaces()
    panes: list[Pane] = []
    by_pid: dict[int, Pane] = {}
    for sid, name, _cwd in raw:
        pid = _ttys_pid_for_surface(name)
        if pid is None:
            continue
        if pid in by_pid:
            continue
        cmd = _ps_full_argv(pid) or ""
        if SHELL_ANCESTOR_RE.search(cmd):
            continue
        if not _classify(cmd, shlex.split(cmd) if cmd else []):
            continue
        pane = _build_pane(pid, cmd, cmd, backend=WalkerBackend.LEGACY)
        by_pid[pid] = pane
    panes.extend(by_pid.values())
    return panes
    # Merge in zmx-backed panes from zmx-snapshot (zmx daemon managed sessions).
    try:
        zmx_panes = _load_zmx_panes()
        if zmx_panes:
            existing = {p.stable_key() for p in panes}
            for zp in zmx_panes:
                if zp.stable_key() not in existing:
                    panes.append(zp)
    except Exception:
        pass
    
    return panes




def _extract_sid_from_argv(argv_tokens: list[str], harness: str) -> str:
    """Extract session id from harness argv.

    Handles both space-separated and comma-separated token forms
    (procs joins argv tokens with commas, ps joins with spaces).
    """
    # Flatten: split each token on commas so procs-format is normalized
    flat: list[str] = []
    for t in argv_tokens:
        flat.extend(part for part in t.split(",") if part)

    # forge: --conversation-id <UUID>
    if harness == "forge":
        for i, t in enumerate(flat):
            if t == "--conversation-id" and i + 1 < len(flat):
                return flat[i + 1].strip()
            if t.startswith("--conversation-id="):
                return t.split("=", 1)[1].strip()
    # codex: --search,resume OR codex resume <UUID> OR `codex --search resume <UUID>`
    if harness == "codex":
        for i, t in enumerate(flat):
            if t == "resume" and i + 1 < len(flat):
                nxt = flat[i + 1]
                if not nxt.startswith("-"):
                    return nxt.strip()
            if t == "--resume" and i + 1 < len(flat):
                nxt = flat[i + 1]
                if not nxt.startswith("-"):
                    return nxt.strip()
            if t.startswith("resume="):
                return t.split("=", 1)[1].strip()
    # opencode: --session <ID>
    if harness == "opencode":
        for i, t in enumerate(flat):
            if t == "--session" and i + 1 < len(flat):
                return flat[i + 1].strip()
            if t.startswith("--session="):
                return t.split("=", 1)[1].strip()
    # kilo: --session <ID>
    if harness == "kilo":
        for i, t in enumerate(flat):
            if t == "--session" and i + 1 < len(flat):
                return flat[i + 1].strip()
            if t.startswith("--session="):
                return t.split("=", 1)[1].strip()
    # cursor-agent: --resume <chatId>
    if harness in ("cursor", "cursor-agent", "droid"):
        for i, t in enumerate(flat):
            if t == "--resume" and i + 1 < len(flat):
                nxt = flat[i + 1]
                if not nxt.startswith("-"):
                    return nxt.strip()
            if t.startswith("--resume="):
                return t.split("=", 1)[1].strip()
    # generic UUID match anywhere (last resort)
    import re as _re
    for t in flat:
        if _re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", t.strip()):
            return t.strip()
    return ""



def _parse_ports(ports_field: Any) -> list[str]:
    """thegent-procx emits `ports` as a comma-separated string like "8080 (LISTEN), 9090 (LISTEN)".
    Return clean port numbers as strings. Empty list on no data / unparseable."""
    if not ports_field:
        return []
    if isinstance(ports_field, list):
        return [str(p).strip().split()[0] for p in ports_field if str(p).strip()]
    out: list[str] = []
    for chunk in str(ports_field).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        # "8080 (LISTEN)" or "8080" or "*:8080 (LISTEN)"
        first = chunk.split()[0]
        # Strip leading "host:port" if present.
        if ":" in first and not first.isdigit():
            first = first.rsplit(":", 1)[-1]
        if first.isdigit():
            out.append(first)
    return out


def _tty_index_via_ps() -> dict[int, str]:
    """Return {pid: tty} for every ttysNNN-bound PID.

    sysinfo/thegent-procx returns tty=None for every process on macOS
    (sysinfo limitation), so the Rust binary alone can't map harness PIDs to
    Ghostty panes. We supplement it with a `ps` call for the PID→tty index.

    BUG (older code): `subprocess.run(..., capture_output=True, text=True)`
    with `ps` on macOS hangs indefinitely because BSD `ps` with `-eo` does a
    group-by-TTY reformatting when it detects a pipe, and on some macOS
    builds it then waits on stdin. We avoid that by writing stdout/stderr
    to temp files instead of capturing into Python pipes.
    """
    out: dict[int, str] = {}
    text = _ps_invoke(["-eo", "pid=,tty="], timeout=8)
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        tty = parts[1].strip()
        if tty.startswith("ttys"):
            out[pid] = tty
    return out


def _procx_snapshot(timeout: int = 5) -> list[Pane] | None:
    """Call thegent-procx (Rust/sysinfo walker) if installed, return Pane list.

    Each row from thegent-procx has `pid`, `parent_pid`, `cmd`, `args`, `tty`
    (always None on macOS — sysinfo limitation), `user`, `ports`, `memory`,
    `start_time`, `run_time`. We pair each row with a Python `ps -axo pid,tty`
    call so we can map PIDs to Ghostty ttysNNN panes (the ps walk takes <10ms).
    Returns None if the binary is missing or fails — caller falls back to the
    legacy ps+lsof walk.
    """
    if not shutil.which("thegent-procx"):
        return None
    try:
        r = subprocess.run(
            ["thegent-procx", "--threads", "--all-users"],
            capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        rows = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(rows, list):
        return None

    # Index ppid for parent lookups.
    ppid_of: dict[int, int] = {}
    for r0 in rows:
        pp = r0.get("parent_pid")
        if isinstance(pp, int):
            ppid_of[r0["pid"]] = pp

    # PID → tty via ps (thegent-procx's tty is always None on macOS).
    pid_to_tty = _tty_index_via_ps()

    # Walk up from each non-shell PID to find its ttysNNN ancestor.
    def tty_for(pid: int) -> str:
        seen: set[int] = set()
        cur = pid
        for _ in range(20):
            if cur in seen:
                return ""
            seen.add(cur)
            tty = pid_to_tty.get(cur)
            if tty and tty.startswith("ttys"):
                return tty
            nxt = ppid_of.get(cur)
            if not nxt:
                return ""
            cur = nxt
        return ""

    surfaces = ghostty_surface_table()
    panes: list[Pane] = []
    seen_tty: set[str] = set()
    for r0 in rows:
        tty = tty_for(r0["pid"])
        if not tty or tty in seen_tty:
            continue
        cmd = r0.get("cmd") or ""
        args = r0.get("args") or ""
        if SHELL_ANCESTOR_RE.match(cmd.strip()):
            continue  # skip login/zsh — only emit a row for the harness leaf
        argv_full = (cmd + " " + args).strip()
        cwd = r0.get("cwd") or _lsof_cwd(r0["pid"]) or "/"
        cmd_clean = ANSI_RE.sub("", argv_full)
        harness, sid = _classify(cmd_clean)
        if harness == "shell":
            continue  # non-harness processes (e.g. npm/snyk helpers) ignored
        ports = _parse_ports(r0.get("ports"))

        surface_id = ""
        surface_name = ""
        for sid_, (title, _) in surfaces.items():
            if title and title in cmd_clean:
                surface_id = sid_
                surface_name = title
                break

        panes.append(Pane(
            tty=tty, pid=r0["pid"], ppid=ppid_of.get(r0["pid"], 0),
            cwd=cwd, cmd=argv_full, cmd_clean=cmd_clean,
            harness=harness, sid_from_argv=sid,
            surface_id=surface_id, surface_name=surface_name,
            ports=ports, ts=_iso_now(),
        ))
        seen_tty.add(tty)
    return panes


def _walk_ghostty_panes_legacy() -> list[Pane]:
    """Original ps + lsof walk — kept as fallback when thegent-procx is absent."""
    surfaces = ghostty_surface_table()
    # Build a ppid index so surface correlation can still find the login shell.
    proc_text = _ps_invoke(["-axo", "pid=,ppid=,command="])
    ppid_of: dict[int, int] = {}
    for line in proc_text.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            ppid_of[int(parts[0])] = int(parts[1])
        except ValueError:
            continue

    by_tty = _tty_pids_by_tty()

    panes: list[Pane] = []
    for tty, pids in sorted(by_tty.items()):
        pick = _pick_harness_on_tty(tty, pids)
        if pick is None:
            continue  # pure shell pane (e.g. a `bash` orphan)
        harness_pid, harness_cmd, login_pid = pick
        cwd = _lsof_cwd(harness_pid) or _lsof_cwd(login_pid) or "/"
        cmd_clean = ANSI_RE.sub("", harness_cmd)
        harness, sid = _classify(cmd_clean)
        # Surface ID lookup (best-effort, by substring of cleaned cmd).
        surface_id = ""
        surface_name = ""
        for sid_, (title, _) in surfaces.items():
            if title and title in cmd_clean:
                surface_id = sid_
                surface_name = title
                break
        panes.append(Pane(
            tty=tty, pid=harness_pid, ppid=ppid_of.get(harness_pid, 0),
            cwd=cwd, cmd=harness_cmd, cmd_clean=cmd_clean,
            harness=harness, sid_from_argv=sid,
            surface_id=surface_id, surface_name=surface_name,
            ports=[], ts=_iso_now(),
        ))
    return panes


def _is_ghostty_pane_parent(ppid: int) -> bool:
    """Is this PPID the Ghostty login helper (spawns ttysNNN shells)?"""
    out = _ps_invoke(["-p", str(ppid), "-o", "command="])
    return "login -fp" in out and "/bin/zsh" in out


def walk_tmux_panes() -> list[Pane]:
    """tmux fallback - one Pane per tmux pane."""
    r = subprocess.run(["tmux", "list-panes", "-a", "-F",
                        "#{pane_id}\t#{pane_pid}\t#{pane_current_command}\t#{pane_current_path}"],
                       capture_output=True, text=True)
    panes: list[Pane] = []
    if r.returncode != 0:
        return panes
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        pane_id, pane_pid, cur_cmd, cwd = parts[0], parts[1], parts[2], parts[3]
        try:
            pid = int(pane_pid)
        except ValueError:
            continue
        ps_text = _ps_invoke(["-p", str(pid), "-o", "command="])
        full_cmd = ps_text.strip() or cur_cmd
        cmd_clean = ANSI_RE.sub("", full_cmd)
        harness, sid = _classify(cmd_clean)
        panes.append(Pane(
            tty=f"tmux:{pane_id}", pid=pid, ppid=0, cwd=cwd, cmd=full_cmd,
            cmd_clean=cmd_clean, harness=harness, sid_from_argv=sid,
            surface_id=pane_id, surface_name="", ts=_iso_now(),
        ))
    return panes


def walk_wezterm_panes() -> list[Pane]:
    """WezTerm backend (Phase B).

    Uses `wezterm cli list --format=json` to enumerate panes. Each pane
    gets a stable wezterm pane_id (UUID-like integer) which we use as
    surface_id. cwd comes from `wezterm cli get-text` not implemented
    here — we fall back to lsof on the pane's child PID.

    Requires `wezterm` on PATH (Linux/WSL) or WEZTERM_PANE env (already
    detected upstream by detect_backend()).
    """
    try:
        r = subprocess.run(
            ["wezterm", "cli", "list", "--format=json"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []
    if r.returncode != 0:
        return []
    panes: list[Pane] = []
    # Try JSON first; fall back to TSV
    rows = []
    try:
        rows = json.loads(r.stdout)
        if not isinstance(rows, list): rows = []
    except (json.JSONDecodeError, ValueError):
        # Fall back: parse TSV format
        for line in r.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 4:
                rows.append({
                    "pane_id": parts[0],
                    "cwd": parts[3] if len(parts) > 3 else "",
                    "pane_pid": parts[1] if len(parts) > 1 else "",
                    "title": "",
                })
    for row in rows:
        pane_id = str(row.get("pane_id", ""))
        if not pane_id: continue
        pane_pid_str = str(row.get("pane_pid", row.get("pid", "")))
        try:
            pid = int(pane_pid_str) if pane_pid_str else 0
        except (ValueError, TypeError):
            pid = 0
        cwd = row.get("cwd", "") or _lsof_cwd(pid) if pid else ""
        title = row.get("title", "")
        ps_text = _ps_invoke(["-p", str(pid), "-o", "command="]) if pid else ""
        full_cmd = ps_text.strip() or row.get("pane_current_command", title)
        cmd_clean = ANSI_RE.sub("", full_cmd)
        harness, sid = _classify(cmd_clean)
        panes.append(Pane(
            tty=f"wezterm:{pane_id}", pid=pid, ppid=0, cwd=cwd, cmd=full_cmd,
            cmd_clean=cmd_clean, harness=harness, sid_from_argv=sid,
            surface_id=f"wezterm:{pane_id}", surface_name=title, ts=_iso_now(),
        ))
    return panes


def _lsof_cwd(pid: int) -> str:
    """Return the cwd of `pid` via lsof. Uses /usr/sbin/lsof as fallback.

    On macOS, lsof requires sudo to inspect processes owned by other users, but
    same-user processes work fine. lsof's -F n format prefixes the path with 'n'
    which we strip.
    """
    if not pid or pid <= 0:
        return ""
    lsof_bin = shutil.which("lsof") or "/usr/sbin/lsof"
    if not os.path.exists(lsof_bin):
        return ""
    try:
        r = subprocess.run(
            [lsof_bin, "-a", "-p", str(pid), "-d", "cwd", "-F", "n"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""
    if r.returncode != 0:
        return ""
    for line in r.stdout.splitlines():
        # format is "n/path"
        if line.startswith("n") and len(line) > 1:
            return line[1:]
    return ""


def walk_windows_terminal_panes() -> list[Pane]:
    """Windows Terminal backend (Phase B).

    Enumerates panes via Windows Terminal's named pipe interface. Each
    pane is a Windows console process (typically powershell.exe,
    cmd.exe, or wsl.exe) — `tasklist /v` gives us the image name, PID,
    window title, and the harness we're inside (PSReadLine state).

    Limitations:
      - Requires Windows 11 + Windows Terminal >= 1.18 (for stable
        named-pipe protocol).
      - `tasklist` may be slow on machines with thousands of processes
        (rare for developer machines).
      - WezTerm inside WSL is preferred when both are available.

    Wire format: we read `tasklist /v /fo csv /fi "imagename eq ..."`
    and parse CSV. cwd comes from PowerShell `Get-CimInstance Win32_Process`
    when needed (we use lsof-equivalent `openfiles /query /v` here).
    """
    panes: list[Pane] = []
    # Only attempt this on Windows
    if sys.platform != "win32":
        log("warn", "walk_windows_terminal_panes: not on win32, returning empty")
        return panes
    tasklist = shutil.which("tasklist") or "C:\\Windows\\System32\\tasklist.exe"
    if not Path(tasklist).exists():
        log("warn", f"walk_windows_terminal_panes: tasklist not at {tasklist}")
        return panes
    # Pull process list with verbose window title
    try:
        r = subprocess.run(
            [tasklist, "/v", "/fo", "csv"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        log("warn", f"walk_windows_terminal_panes: tasklist failed: {e}")
        return panes
    if r.returncode != 0:
        return panes
    # Parse CSV. First line is the header.
    import csv
    reader = csv.reader(r.stdout.splitlines())
    rows = list(reader)
    if not rows:
        return panes
    header = [h.strip().lower() for h in rows[0]]
    idx = {h: i for i, h in enumerate(header)}
    # The Windows Terminal panes typically run powershell.exe, cmd.exe,
    # wsl.exe, or wt.exe itself. Filter to shell-like processes.
    SHELL_IMAGES = {"powershell.exe", "pwsh.exe", "cmd.exe", "wsl.exe",
                    "bash.exe", "zsh.exe", "fish.exe", "wt.exe"}
    for row in rows[1:]:
        if len(row) < len(header):
            continue
        image = row[idx.get("image name", 1)].strip().lower() if "image name" in idx else ""
        if not image or image not in SHELL_IMAGES:
            continue
        try:
            pid = int(row[idx.get("pid", 1)].strip())
        except (ValueError, KeyError, IndexError):
            continue
        title = row[idx.get("window title", idx.get("title", -1))].strip() \
            if idx.get("window title", -1) >= 0 else ""
        # cwd from openfiles is slow; fall back to PowerShell if we need it
        cwd = _windows_cwd_via_powershell(pid) if pid else ""
        # Use the title as the harness hint (WT panes are usually titled
        # with the harness name when launched via WT profiles)
        harness = ""
        sid = ""
        if "codex" in title.lower():
            harness = "codex"
        elif "cursor" in title.lower():
            harness = "cursor"
        elif "claude" in title.lower():
            harness = "claude"
        elif "kilo" in title.lower():
            harness = "kilo"
        elif "droid" in title.lower():
            harness = "droid"
        elif image == "wt.exe":
            harness = "windows-terminal"
        else:
            harness = "shell"
        cmd = row[idx.get("command line", -1)].strip() if "command line" in idx else image
        cmd_clean = ANSI_RE.sub("", cmd)
        # Build a stable pane ID. On Windows, the PID is the canonical
        # handle, but two panes can share a PID (rare). Use pid:title
        # as the dedupe key.
        pane_id = f"wt:{pid}:{title[:20]}"
        panes.append(Pane(
            tty=pane_id, pid=pid, ppid=0, cwd=cwd, cmd=cmd,
            cmd_clean=cmd_clean, harness=harness, sid_from_argv=sid,
            surface_id=pane_id, surface_name=title[:80], ts=_iso_now(),
        ))
    return panes


def _windows_cwd_via_powershell(pid: int) -> str:
    """Best-effort: query a Windows process's cwd via PowerShell.

    Used by walk_windows_terminal_panes. Returns empty string on any
    failure. PowerShell's `(Get-CimInstance Win32_Process -Filter
    "ProcessId=$pid").CommandLine` does NOT give cwd directly, but we
    can read the working set size + handle table to detect a hung
    process. Cwd comes from `GetProcessWorkingDirectory` which only
    exists in PowerShell 7.3+ via the Microsoft.PowerShell.Utility
    module (not always available).

    Returns empty string when cwd cannot be determined.
    """
    if sys.platform != "win32" or not pid or pid <= 0:
        return ""
    pwsh = shutil.which("powershell") or shutil.which("pwsh")
    if not pwsh:
        return ""
    try:
        r = subprocess.run(
            [pwsh, "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()[:1024]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ""


def _lsof_listening_ports(pid: int) -> list[int]:
    """Return list of TCP/UDP ports this process is listening on. Empty on permission errors."""
    if not pid or pid <= 0:
        return []
    lsof_bin = shutil.which("lsof") or "/usr/sbin/lsof"
    if not os.path.exists(lsof_bin):
        return []
    try:
        r = subprocess.run(
            [lsof_bin, "-a", "-p", str(pid), "-i", "-P", "-n", "-F", "n"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []
    if r.returncode != 0:
        return []
    ports = []
    for line in r.stdout.splitlines():
        if line.startswith("n") and ":" in line:
            tail = line.split(":", 1)[1]
            if tail.isdigit():
                ports.append(int(tail))
    return ports


def _ps_full_argv(pid: int) -> str:
    """Get the full argv for `pid` via thegent-procx (Mach kernel API).

    On macOS, both `ps` and `procs` truncate the command to just the binary
    name for detached processes.  The sysinfo-based thegent-procx reads the
    real argv via the Mach kernel API (proc_pidinfo), so it is authoritative.

    Falls back to `ps -ww` only if thegent-procx is unavailable.
    """
    if not pid or pid <= 0:
        return ""
    # Primary: thegent-procx --pid (fast, single-process query).
    tp = shutil.which("thegent-procx")
    if tp:
        try:
            r = subprocess.run(
                [tp, "--pid", str(pid)],
                capture_output=True, text=True, timeout=5,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            r = None
        if r and r.returncode == 0:
            try:
                rows = json.loads(r.stdout)
            except json.JSONDecodeError:
                rows = None
            if rows:
                if isinstance(rows, list):
                    if len(rows) > 0:
                        row = rows[0]
                    else:
                        return ""
                else:
                    row = rows
                cmd = row.get("cmd", "")
                args = row.get("args", "")
                return (f"{cmd} {args}" if args else cmd).strip()

    # Fallback: thegent-procx full dump filtered by pid (slow, once per snapshot).
    if tp:
        try:
            r = subprocess.run(
                [tp, "--threads", "--all-users"],
                capture_output=True, text=True, timeout=5,
            )
        except Exception:
            r = None
        if r and r.returncode == 0:
            try:
                rows = json.loads(r.stdout)
            except json.JSONDecodeError:
                rows = []
            for proc in rows:
                if proc.get("pid") == pid:
                    cmd = proc.get("cmd", "")
                    args = proc.get("args", "")
                    return (f"{cmd} {args}" if args else cmd).strip()

    # Last resort: ps -ww (often truncated on macOS).
    out = _ps_invoke(["-ww", "-p", str(pid), "-o", "command="], timeout=2).strip()
    if out and (" " in out or len(out) > 40):
        return out

    return ""





def _resolve_codex_batch(items: list[tuple[int, str, str]]) -> dict[int, str]:
    """Codex rolls out as ~/.codex/sessions/YYYY/MM/DD/<uuid>.jsonl[.zst].
    First non-empty JSON line has {payload:{cwd, id, session_id}}. We want
    payload.id (the thread UUID used by `codex resume <UUID>`)."""
    pwds = {cwd for _, cwd, _ in items}
    if not pwds:
        return {}
    sessions_root = Path.home() / ".codex" / "sessions"
    if not sessions_root.exists():
        return {}
    # Collect all recent files (last 14d).
    cutoff = time.time() - 14 * 86400
    files: list[Path] = []
    for ext in ("*.jsonl", "*.jsonl.zst"):
        for f in sessions_root.rglob(ext):
            try:
                if f.stat().st_mtime >= cutoff:
                    files.append(f)
            except OSError:
                continue
    # Sort newest first so the freshest matching session wins per cwd.
    files.sort(key=lambda f: -f.stat().st_mtime)
    cwd_to_sid: dict[str, str] = {}
    for f in files:
        try:
            if f.suffix == ".zst":
                line = _read_first_line_from_process(["zstd", "-dcq", str(f)])
                if line is None:
                    continue
                text = line
            else:
                with open(f, "rb") as fh:
                    text = fh.read(64 * 1024)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
        line = text.split(b"\n", 1)[0]
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        payload = d.get("payload", {})
        if not isinstance(payload, dict):
            continue
        cwd = payload.get("cwd") or ""
        sid = payload.get("id") or payload.get("session_id") or ""
        if cwd in pwds and cwd not in cwd_to_sid and sid:
            cwd_to_sid[cwd] = sid
            if len(cwd_to_sid) == len(pwds):
                break
    return {pid: cwd_to_sid[cwd] for pid, cwd, _ in items if cwd in cwd_to_sid}


def _resolve_cursor_batch(items: list[tuple[int, str, str]]) -> dict[int, str]:
    """Cursor: ~/.cursor/chats/<outer>/<inner-uuid>/ with most recent inner uuid
    being the live chat. Match pane to chat by process-creation mtime ordering."""
    chats_root = Path.home() / ".cursor" / "chats"
    if not chats_root.exists():
        return {}
    # Collect (mtime, inner_uuid) for all inner dirs.
    pairs: list[tuple[float, str]] = []
    for outer in chats_root.iterdir():
        if not outer.is_dir():
            continue
        for inner in outer.iterdir():
            if not inner.is_dir():
                continue
            try:
                mt = inner.stat().st_mtime
            except OSError:
                continue
            pairs.append((mt, inner.name))
    pairs.sort(reverse=True)  # newest first
    if not pairs:
        return {}
    # Map pid order to chat order: pane with latest process start gets latest chat.
    sorted_items = sorted(items, key=lambda x: x[0])  # placeholder; use ps mtime
    # Get process create times for each pid to properly order.
    pid_mtimes: dict[int, float] = {}
    for pid, _, _ in items:
        ps_text = _ps_invoke(["-p", str(pid), "-o", "lstart="])
        if ps_text.strip():
            try:
                import datetime
                mt = datetime.datetime.strptime(
                    ps_text.strip(), "%a %b %d %H:%M:%S %Y"
                ).timestamp()
                pid_mtimes[pid] = mt
            except ValueError:
                pass
    sorted_by_ct = sorted(items, key=lambda x: pid_mtimes.get(x[0], 0.0))
    out: dict[int, str] = {}
    for i, (pid, _, _) in enumerate(sorted_by_ct):
        if i < len(pairs):
            out[pid] = pairs[i][1]
    return out


def _resolve_kilo_batch(items: list[tuple[int, str, str]]) -> dict[int, str]:
    """Kilo: enumerate ~/.local/share/kilo/storage/.../session.json per cwd."""
    return _resolve_path_session_batch(
        items,
        [Path.home() / ".local" / "share" / "kilo" / "storage"],
        match_field="cwd",
    )


def _resolve_opencode_batch(items: list[tuple[int, str, str]]) -> dict[int, str]:
    """Opencode: ~/.local/share/opencode/storage/session/<proj>/<session>.json."""
    root = Path.home() / ".local" / "share" / "opencode" / "storage"
    pwds = {cwd for _, cwd, _ in items}
    if not pwds or not root.exists():
        return {}
    cwd_to_sid: dict[str, str] = {}
    pairs: list[tuple[float, Path]] = []
    for f in root.rglob("*.json"):
        try:
            mt = f.stat().st_mtime
        except OSError:
            continue
        pairs.append((mt, f))
    pairs.sort(reverse=True)
    for _, f in pairs:
        try:
            with open(f) as fh:
                d = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        cwd = d.get("cwd") or d.get("directory") or ""
        sid = d.get("id") or d.get("sessionID") or ""
        if cwd in pwds and cwd not in cwd_to_sid and sid:
            cwd_to_sid[cwd] = sid
            if len(cwd_to_sid) == len(pwds):
                break
    return {pid: cwd_to_sid[cwd] for pid, cwd, _ in items if cwd in cwd_to_sid}


def _resolve_droid_batch(items: list[tuple[int, str, str]]) -> dict[int, str]:
    """Droid (Factory): ~/.factory/settings.json + per-session settings files."""
    settings = Path.home() / ".factory" / "settings.json"
    if not settings.exists():
        return {}
    try:
        d = json.loads(settings.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    sid = d.get("sessionId") or d.get("session_id") or ""
    if not sid:
        return {}
    return {pid: sid for pid, _, _ in items}


def _resolve_path_session_batch(items: list[tuple[int, str, str]],
                                roots: list[Path],
                                match_field: str = "cwd") -> dict[int, str]:
    """Generic fallback: walk each root, read session JSONs, match on field."""
    pwds = {cwd for _, cwd, _ in items}
    if not pwds:
        return {}
    cwd_to_sid: dict[str, str] = {}
    for root in roots:
        if not root.exists():
            continue
        for f in root.rglob("*.json"):
            try:
                with open(f) as fh:
                    d = json.load(fh)
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(d, dict):
                continue
            cwd = d.get(match_field) or ""
            sid = d.get("id") or d.get("sessionID") or d.get("session_id") or ""
            if cwd in pwds and cwd not in cwd_to_sid and sid:
                cwd_to_sid[cwd] = sid
                if len(cwd_to_sid) == len(pwds):
                    return {pid: cwd_to_sid[c] for pid, c, _ in items if c in cwd_to_sid}
    return {pid: cwd_to_sid[c] for pid, c, _ in items if c in cwd_to_sid}


_SESSION_RESOLUTION_CACHE: dict[tuple[str, str], str | None] = {}


def _read_codex_header(path: Path) -> dict | None:
    """Read one Codex rollout header without launching a decompressor process."""
    try:
        if path.name.endswith(".zst"):
            compressed = path.read_bytes()
            try:
                from compression import zstd  # type: ignore[attr-defined]
                data = zstd.decompress(compressed)
            except (ImportError, AttributeError):
                try:
                    import zstandard  # type: ignore[import-not-found]
                    data = zstandard.ZstdDecompressor().decompress(compressed)
                except (ImportError, OSError, ValueError):
                    return None
            head = data.split(b"\n", 1)[0]
        else:
            with path.open("rb") as fh:
                head = fh.read(64 * 1024).split(b"\n", 1)[0]
        value = json.loads(head)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _resolve_codex_storage(cwd: str, root: Path | None = None) -> str | None:
    root = root or Path.home() / ".codex" / "sessions"
    if not root.exists():
        return None
    candidates: list[tuple[float, Path]] = []
    try:
        for path in root.rglob("*.jsonl*"):
            if not (path.name.endswith(".jsonl") or path.name.endswith(".jsonl.zst")):
                continue
            try:
                candidates.append((path.stat().st_mtime, path))
            except OSError:
                continue
    except OSError:
        return None
    for _, path in sorted(candidates, reverse=True):
        record = _read_codex_header(path)
        payload = record.get("payload") if record else None
        if not isinstance(payload, dict) or (payload.get("cwd") or "") != cwd:
            continue
        sid = payload.get("id") or payload.get("session_id")
        if sid:
            return str(sid)
    return None


def _resolve_cursor_storage(cwd: str, root: Path | None = None) -> str | None:
    root = root or Path.home() / ".cursor" / "chats"
    if not root.exists():
        return None
    stores: list[tuple[float, Path]] = []
    try:
        for store in root.glob("*/*/store.db"):
            try:
                stores.append((store.stat().st_mtime, store))
            except OSError:
                continue
    except OSError:
        return None
    for _, store in sorted(stores, reverse=True):
        try:
            with sqlite3.connect(f"file:{store}?mode=ro", uri=True, timeout=0.02) as db:
                meta_match = db.execute(
                    "SELECT 1 FROM meta WHERE instr(CAST(value AS TEXT), ?) > 0 LIMIT 1",
                    (cwd,),
                ).fetchone()
                blob_match = None if meta_match else db.execute(
                    "SELECT 1 FROM blobs WHERE instr(CAST(data AS TEXT), ?) > 0 LIMIT 1",
                    (cwd,),
                ).fetchone()
        except (sqlite3.Error, OSError):
            continue
        if meta_match or blob_match:
            return store.parent.name
    return None


def _resolve_json_storage(cwd: str, root: Path) -> str | None:
    if not root.exists():
        return None
    candidates: list[tuple[float, Path]] = []
    try:
        for path in root.rglob("*.json"):
            try:
                candidates.append((path.stat().st_mtime, path))
            except OSError:
                continue
    except OSError:
        return None
    for _, path in sorted(candidates, reverse=True):
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        stored_cwd = record.get("cwd") or record.get("directory") or record.get("workspace")
        if stored_cwd != cwd:
            continue
        sid = (record.get("id") or record.get("session_id") or
               record.get("sessionId") or record.get("sessionID"))
        if sid:
            return str(sid)
    return None


def _resolve_kilo_storage(cwd: str, root: Path | None = None) -> str | None:
    return _resolve_json_storage(cwd, root or Path.home() / ".config" / "kilo" / "sessions")


def _resolve_droid_storage(cwd: str, root: Path | None = None) -> str | None:
    return _resolve_json_storage(cwd, root or Path.home() / ".droid" / "sessions")


def _resolve_opencode_storage(cwd: str, db_path: Path | None = None) -> str | None:
    db_path = db_path or Path.home() / ".local" / "share" / "opencode" / "opencode.db"
    if not db_path.exists():
        return None
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=0.02) as db:
            row = db.execute(
                "SELECT id FROM session WHERE directory = ? "
                "ORDER BY time_updated DESC LIMIT 1",
                (cwd,),
            ).fetchone()
    except (sqlite3.Error, OSError):
        return None
    return str(row[0]) if row and row[0] else None


def _resolve_session_id_by_storage(
    harness: str, cwd: str, argv_tokens: list[str]
) -> str | None:
    """Resolve an argv-less harness session from its cwd-scoped local storage."""
    normalized_harness = "cursor" if harness == "cursor-agent" else harness
    sid_from_argv = _extract_sid_from_argv(argv_tokens, normalized_harness)
    if sid_from_argv:
        return sid_from_argv

    key = (normalized_harness, cwd)
    if key in _SESSION_RESOLUTION_CACHE:
        return _SESSION_RESOLUTION_CACHE[key]

    if normalized_harness == "codex":
        sid = _resolve_codex_storage(cwd)
    elif normalized_harness == "cursor":
        sid = _resolve_cursor_storage(cwd)
    elif normalized_harness == "opencode":
        sid = _resolve_opencode_storage(cwd)
    elif normalized_harness == "kilo":
        sid = _resolve_kilo_storage(cwd)
    elif normalized_harness == "droid":
        sid = _resolve_droid_storage(cwd)
    else:
        # Forge sessions are authoritative only when --conversation-id is in argv.
        sid = None

    _SESSION_RESOLUTION_CACHE[key] = sid
    return sid


def batch_resolve_cwd(panes: list[Pane]) -> dict[int, str]:
    """Resolve argv-less panes once per unique harness/cwd during this snapshot."""
    _SESSION_RESOLUTION_CACHE.clear()
    pid_to_sid: dict[int, str] = {}
    for pane in panes:
        argv_tokens = _split_procx_argv(pane.cmd_clean)
        if pane.sid_from_argv:
            continue
        sid_from_argv = _extract_sid_from_argv(argv_tokens, pane.harness)
        if sid_from_argv:
            pane.sid_from_argv = sid_from_argv
            continue
        if not pane.cwd:
            continue
        try:
            sid = _resolve_session_id_by_storage(pane.harness, pane.cwd, argv_tokens)
        except (OSError, sqlite3.Error, ValueError):
            sid = None
        if sid:
            pid_to_sid[pane.pid] = sid
    return pid_to_sid


def _resolve_codex_cwd(cwd: str, root: Path) -> str:
    """Find the most recent codex session json whose payload.cwd matches.

    Codex stores sessions as ~/.codex/sessions/YYYY/MM/DD/<uuid>.jsonl[.zst].
    Decoding every file is expensive; we filter to last 14 days and decode only
    the first JSON line of each candidate.
    """
    if not root.exists():
        return ""
    cutoff = time.time() - 14 * 86400
    candidates = [f for f in root.rglob("*.jsonl*") if f.stat().st_mtime > cutoff]
    if not candidates:
        return ""
    best_sid = ""
    best_mtime = 0.0
    for f in candidates:
        try:
            if f.suffix == ".zst":
                head = _read_first_line_from_process(["zstd", "-dcq", str(f)])
                if head is None:
                    continue
            else:
                with open(f, "rb") as fh:
                    head = fh.read(64 * 1024).split(b"\n", 1)[0]
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
        try:
            d = json.loads(head)
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict):
            continue
        payload = d.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        file_cwd = payload.get("cwd") or ""
        if file_cwd != cwd:
            continue
        sid = payload.get("id") or payload.get("session_id") or ""
        if not sid:
            continue
        mtime = f.stat().st_mtime
        if mtime > best_mtime:
            best_mtime = mtime
            best_sid = sid
    return best_sid


def _resolve_kilo_cwd(cwd: str, root: Path) -> str:
    return ""


def _resolve_opencode_cwd(cwd: str, root: Path) -> str:
    return ""


def _resolve_droid_cwd(cwd: str) -> str:
    droid_root = Path.home() / ".factory" / "settings.json"
    if droid_root.exists():
        try:
            d = json.loads(droid_root.read_text())
            return d.get("sessionId") or d.get("session_id") or ""
        except (OSError, json.JSONDecodeError):
            pass
    # fallback: list .factory*.json in home
    for f in Path.home().glob(".factory*.json"):
        try:
            d = json.loads(f.read_text())
            sid = d.get("sessionId") or d.get("session_id") or d.get("id") or ""
            if sid:
                return sid
        except (OSError, json.JSONDecodeError):
            continue
    return ""


def _resolve_cursor_cwd(cwd: str) -> str:
    """Pick the cursor chat UUID whose cwd is closest to `cwd`.

    Cursor stores chats at ~/.cursor/chats/<outer-hash>/<chat-uuid>/. The
    most-recently-modified inner dir at the same outer level is the best match.
    """
    cursor_root = Path.home() / ".cursor" / "chats"
    if not cursor_root.exists():
        return ""
    best: tuple[float, str] = (0.0, "")
    for outer in cursor_root.iterdir():
        if not outer.is_dir():
            continue
        try:
            for inner in outer.iterdir():
                if not inner.is_dir():
                    continue
                inner_cwd = inner / "cwd"
                if inner_cwd.exists():
                    try:
                        if inner_cwd.read_text().strip() == cwd:
                            mt = inner.stat().st_mtime
                            if mt > best[0]:
                                best = (mt, inner.name)
                    except OSError:
                        pass
        except OSError:
            continue
    return best[1]


# ----- snapshot persistence --------------------------------------------------


def _collect_sharecli_tray_row() -> dict:
    """Build one snapshot row reporting sharecli-tray availability.

    Layout mirrors a pane row so the JSONL stays flat:

        ts, harness="sharecli-tray", pane_id="sharecli-tray:<socket>",
        surface_id="", tty="", pid=0, cwd="", argv="",
        session_id="", session_id_source="tray",
        needs_picker=False, ports=[], zmx_name="",
        # tray-specific (nested so a single grep on `sharecli` finds it)
        sharecli={
            "available":    bool,    # socket reachable AND health.ping ok
            "reachable":    bool,    # socket reachable (connect-only probe)
            "socket":       str,     # resolved UNIX socket path
            "bridge_imported": bool,  # was sharecli_bridge importable
            "health":       dict,    # full sharecli_health_ping() payload
            "host":         dict,    # full sharecli_host_info() payload
            "sessions":     list,    # bounded (5) session preview
            "sessions_count": int,   # full count returned by sharecli_session_list
            "processes_count": int,  # full count returned by sharecli_process_list
        }

    Failure modes:
        * Bridge module missing  → available=False, error="bridge-not-importable"
        * Daemon down            → available=False, error="socket-unreachable"
        * Health call failed     → available=False, error=<daemon message>
        * All calls ok           → available=True, error=""

    Slice 5: result is cached on disk (TTL 2.0s) so the second invocation
    inside a single launchd 30s tick reuses the prior reachability check
    without re-issuing the 4 IPC probes (which collectively take 1-9s when
    the daemon is busy / hung).
    """
    cached = _disk_cache_get(SHARECLI_CACHE_FILE, SHARECLI_CACHE_TTL_SEC)
    if isinstance(cached, dict):
        cached["ts"] = now_iso()  # refresh ts for the new row, keep payload
        return cached

    ts = now_iso()
    base: dict[str, Any] = {
        "ts": ts,
        "surface_id": "",
        "surface_name": "",
        "pane_id": "sharecli-tray:unknown",
        "tty": "",
        "pid": 0,
        "cwd": "",
        "argv": "",
        "harness": "sharecli-tray",
        "session_id": "",
        "session_id_source": "tray",
        "needs_picker": False,
        "ports": [],
        "zmx_name": "",
        "sharecli": {
            "available": False,
            "reachable": False,
            "socket": "",
            "bridge_imported": _SHARECLI_BRIDGE_AVAILABLE,
            "health": {},
            "host": {},
            "sessions": [],
            "sessions_count": 0,
            "processes_count": 0,
            "error": "bridge-not-importable",
        },
    }
    if not _SHARECLI_BRIDGE_AVAILABLE or _sharecli_bridge is None:
        return base

    bridge = _sharecli_bridge
    sock = bridge.sharecli_socket_path()
    base["pane_id"] = f"sharecli-tray:{sock}"
    base["sharecli"]["socket"] = sock

    reachable = bridge.sharecli_socket_reachable(timeout=0.5)
    base["sharecli"]["reachable"] = reachable
    if not reachable:
        base["sharecli"]["error"] = "socket-unreachable"
        return base

    # Socket reachable — issue the four canonical IPC probes. Each call has its
    # own short timeout; a single failure mustn't sink the whole row.
    health = bridge.sharecli_health_ping(timeout=2.0)
    base["sharecli"]["health"] = health
    if not health.get("ok"):
        base["sharecli"]["error"] = health.get("error") or "health.ping failed"
        # Don't return — host/sessions may still be useful for diagnostics.

    sessions = bridge.sharecli_session_list(limit=5, timeout=3.0)
    base["sharecli"]["sessions"] = sessions
    base["sharecli"]["sessions_count"] = len(sessions)

    procs = bridge.sharecli_process_list(limit=50, timeout=3.0)
    base["sharecli"]["processes_count"] = len(procs)

    host = bridge.sharecli_host_info(timeout=3.0)
    base["sharecli"]["host"] = host

    # Row is "available" iff the socket reachable AND health.ping said ok.
    base["sharecli"]["available"] = bool(health.get("ok"))
    if base["sharecli"]["available"]:
        base["sharecli"]["error"] = ""
    _disk_cache_put(SHARECLI_CACHE_FILE, base)
    return base


def load_previous() -> dict[str, CachedRow]:
    """Load existing snapshot, keyed by stable_key.

    Slice 5: lazy-disk-backed cache. The cache key is just the size of
    ``snapshot.jsonl`` — when ``write_snapshot`` finishes it bumps the
    size by exactly the number of new rows, so the cache only invalidates
    when the row count actually changes (which only happens between
    ``write_snapshot`` calls that add/drop panes). Within a launchd 30s
    tick, repeated calls reuse the prior parse result and skip both the
    full-file read AND the per-row JSON parse.
    """
    try:
        st = SNAPSHOT_FILE.stat()
    except OSError:
        return {}
    fingerprint = st.st_size
    cached = _disk_cache_get(PREVIOUS_CACHE_FILE, PREVIOUS_CACHE_TTL_SEC)
    if isinstance(cached, dict) and cached.get("__fingerprint__") == fingerprint:
        rows = cached.get("rows", {})
        if isinstance(rows, dict):
            return {
                str(k): CachedRow(
                    ts=v.get("ts", ""),
                    pane_id=v.get("pane_id", ""),
                    harness=v.get("harness", "shell"),
                    session_id=v.get("session_id", "") or "",
                    cwd=v.get("cwd", ""),
                    dead=bool(v.get("dead", False)),
                    surface_id=v.get("surface_id", ""),
                )
                for k, v in rows.items()
                if isinstance(v, dict)
            }

    prev = _load_previous_uncached()
    # Persist for the next tick (best-effort).
    try:
        _disk_cache_put(
            PREVIOUS_CACHE_FILE,
            {
                "__fingerprint__": fingerprint,
                "rows": {
                    k: {
                        "ts": v.ts,
                        "pane_id": v.pane_id,
                        "harness": v.harness,
                        "session_id": v.session_id,
                        "cwd": v.cwd,
                        "dead": v.dead,
                        "surface_id": v.surface_id,
                    }
                    for k, v in prev.items()
                },
            },
        )
    except Exception as exc:
        log("warn", f"previous cache write skipped: {exc}")
    return prev


def _load_previous_uncached() -> dict[str, CachedRow]:
    """Real implementation of `load_previous` (no cache)."""
    prev: dict[str, CachedRow] = {}
    if not SNAPSHOT_FILE.exists():
        return prev
    try:
        text = SNAPSHOT_FILE.read_text()
    except OSError:
        return prev
    now = time.time()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = d.get("ts", "")
        try:
            tsf = time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
        except ValueError:
            continue
        # Drop stale rows.
        ttl = DEAD_TTL_SEC if d.get("dead") else LIVE_TTL_SEC
        if now - tsf > ttl:
            continue
        key = (d.get("harness", "shell") + "|" + d.get("cwd", "")
               + "|" + (d.get("surface_id") or d.get("pane_id", "")))
        prev[key] = CachedRow(
            ts=ts,
            pane_id=d.get("pane_id", d.get("surface_id", "")),
            harness=d.get("harness", "shell"),
            session_id=d.get("session_id", "") or "",
            cwd=d.get("cwd", ""),
            dead=bool(d.get("dead")),
            surface_id=d.get("surface_id", ""),
        )
    return prev


def stable_key_for(pane: Pane) -> str:
    return f"{pane.harness}|{pane.cwd}|{pane.surface_id}"


ZMX_SNAPSHOT_FILE = SNAPSHOT_DIR / "zmx.jsonl"


def _load_zmx_panes() -> list[Pane]:
    """Load active zmx sessions from zmx.jsonl as synthetic Pane objects.

    Each session becomes a pane with harness='zmx' and surface_id=zmx_name.
    Resume dispatches them via `zmx attach <name>` (handled by resume-all.py).
    """
    if not ZMX_SNAPSHOT_FILE.exists():
        return []
    out: list[Pane] = []
    try:
        with ZMX_SNAPSHOT_FILE.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not row.get("alive", True):
                    continue
                name = row.get("zmx_name", "")
                cmd = row.get("command", "") or ""
                cwd = row.get("start_dir", "") or ""
                pid = int(row.get("pid", 0) or 0)
                tty = f"zmx:{name}"
                # Classify the command to pick the right `harness` tag (forge/codex/etc).
                # If it isn't a known harness, fall back to 'zmx'.
                argv0 = (cmd.split() or [""])[0]
                harness = "zmx"
                for kw in ("forge", "codex", "kilo", "opencode", "cursor-agent", "droid"):
                    if kw in argv0:
                        harness = kw
                        break
                out.append(Pane(
                    tty=tty,
                    pid=pid,
                    ppid=0,
                    cwd=cwd,
                    cmd=cmd,
                    cmd_clean=cmd[:400],
                    harness=harness,
                    sid_from_argv="",
                    surface_id=f"zmx:{name}",
                    surface_name=f"zmx:{name}",
                    ports=[],
                    ts=now_iso(),
                ))
    except OSError:
        return []
    return out


def write_snapshot(panes: list[Pane], prev: dict[str, CachedRow]) -> int:
    """Append one row per live pane. Prune dead rows by skipping them.
    Return number of rows written.

    Hardening (Slice 7):
      * Atomic write — write to ``snapshot.jsonl.tmp.<pid>.<usec>``, fsync,
        then ``os.replace()`` so a reader (resume-all.py) never sees a partial
        file.  Replaces ``SNAPSHOT_FILE.write_text()`` which was a
        crash-mid-write foot-gun.
      * ``BrokenPipeError`` / ``KeyboardInterrupt`` / SIGTERM during the
        write preserves the existing ``snapshot.jsonl`` (we abandon the tmp
        file and surface a non-fatal warning instead of exiting 2).
      * ``.snapshot.lock`` with ``fcntl.flock(LOCK_EX)`` + ``LOCK_NB`` so two
        ``session-snapshot`` invocations from launchd (StartInterval=30) can't
        race the same temp file.
    """
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    new_lines: list[str] = []
    seen_keys: set[str] = set()
    cwd_sids = batch_resolve_cwd(panes)
    resumable_harnesses = {"forge", "codex", "opencode", "kilo", "cursor", "cursor-agent", "droid"}
    for p in panes:
        sid = p.sid_from_argv or cwd_sids.get(p.pid, "")
        sid_source = "argv" if p.sid_from_argv else ("storage" if sid else "")
        # Surface ID may be either "zmx:<name>" (synthetic from zmx snapshot)
        # or a Ghostty AppleScript surface UUID. Persist both spellings.
        zmx_name = ""
        if (p.surface_id or "").startswith("zmx:"):
            zmx_name = p.surface_id[4:]
        row = {
            "ts": p.ts,
            "surface_id": p.surface_id or "",
            "surface_name": p.surface_name or "",
            "pane_id": p.surface_id or f"g:{p.tty}",
            "tty": p.tty,
            "pid": p.pid,
            "cwd": p.cwd,
            "argv": p.cmd_clean[:400],
            "harness": p.harness,
            "session_id": sid,
            "session_id_source": sid_source,
            "needs_picker": p.harness in resumable_harnesses and not bool(sid),
            "ports": p.ports,
            "zmx_name": zmx_name,
        }
        new_lines.append(json.dumps(row, ensure_ascii=False))
        seen_keys.add(stable_key_for(p))
    # Carry forward previous live rows that have no current pane (tombstones).
    now = time.time()
    for key, row in prev.items():
        if row.dead:
            continue  # already dead, dropped at load time
        if key in seen_keys:
            continue
        if not row.session_id:
            continue
        try:
            tsf = time.mktime(time.strptime(row.ts, "%Y-%m-%dT%H:%M:%SZ"))
        except ValueError:
            continue
        if now - tsf > LIVE_TTL_SEC:
            continue
        # Mark as dead-tombstone: appears once, then expires within DEAD_TTL_SEC.
        tomb = {
            "ts": row.ts,
            "dead": True,
            "harness": row.harness,
            "session_id": row.session_id,
            "cwd": row.cwd,
            "pane_id": row.pane_id,
            "surface_id": row.surface_id,
        }
        new_lines.append(json.dumps(tomb, ensure_ascii=False))

    # One system-status row per snapshot: sharecli-tray availability.
    # Tagged `harness="sharecli-tray"` so existing consumers (resume-all
    # etc.) skip it naturally. Always last in the file — predictable
    # location for `tail -1 | jq`.
    try:
        tray_row = _collect_sharecli_tray_row()
        new_lines.append(json.dumps(tray_row, ensure_ascii=False))
    except Exception as exc:  # pragma: no cover — defensive only
        log("warn", f"sharecli tray row failed: {exc}")

    payload = "\n".join(new_lines) + ("\n" if new_lines else "")
    _atomic_write_text(SNAPSHOT_FILE, payload)
    return len(new_lines)


def _atomic_write_text(target: Path, payload: str) -> None:
    """Write ``payload`` to ``target`` atomically.

    Sequence:
      1. Acquire ``SNAPSHOT_LOCK`` with ``fcntl.flock(LOCK_EX|LOCK_NB)`` —
         if another writer holds it, retry with brief backoff up to 5s,
         then proceed best-effort (don't deadlock the launchd timer).
      2. Write to a sibling temp file ``target.tmp.<pid>.<usec>`` in the
         same directory (so ``os.replace`` is atomic on the same filesystem).
      3. ``fsync`` the temp file, then ``os.replace(tmp, target)`` — readers
         see either the old contents or the new contents, never a partial.
      4. Release the lock.

    Catches ``BrokenPipeError`` / ``KeyboardInterrupt`` / SIGTERM mid-write
    so a ``gtimeout`` SIGKILL'ing us preserves the existing snapshot.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    usec = time.time_ns() // 1000
    tmp = target.with_name(f"{target.name}.tmp.{pid}.{usec}")

    lock_fd = _open_snapshot_lock()
    try:
        # If we lost the race for the lock, wait briefly then proceed
        # best-effort so launchd doesn't accumulate dead timeouts.
        if lock_fd is not None and not _try_flock_ex(lock_fd, deadline_sec=5.0):
            log("warn", f"could not acquire {SNAPSHOT_LOCK.name}; proceeding without lock")

        try:
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                try:
                    fh.write(payload)
                    fh.flush()
                    os.fsync(fh.fileno())
                except (BrokenPipeError, KeyboardInterrupt, InterruptedError):
                    # gtimeout / SIGTERM / Ctrl-C hit us mid-write.  Leave
                    # the existing snapshot.jsonl untouched and surface a
                    # warning instead of a fatal exit.
                    log("warn", f"interrupted during atomic write; abandoning {tmp.name}")
                    try:
                        tmp.unlink()
                    except OSError:
                        pass
                    return
        except OSError as exc:
            log("warn", f"could not open temp file {tmp}: {exc}")
            return

        try:
            os.replace(tmp, target)
        except OSError as exc:
            log("warn", f"os.replace({tmp} -> {target}) failed: {exc}")
            try:
                tmp.unlink()
            except OSError:
                pass
    finally:
        if lock_fd is not None:
            try:
                import fcntl  # local import — keeps top of file tidy
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                os.close(lock_fd)
            except OSError:
                pass


def _open_snapshot_lock() -> int | None:
    """Open ``SNAPSHOT_LOCK`` for whole-file locking. Returns the fd, or None
    if the lock file could not be opened (e.g. permission denied)."""
    try:
        SNAPSHOT_LOCK.parent.mkdir(parents=True, exist_ok=True)
        # O_CREAT|O_RDWR; O_NOFOLLOW would be nice but BSD/macOS Python
        # pre-3.11 doesn't expose it without `os.O_NOFOLLOW` (3.11+).
        fd = os.open(
            str(SNAPSHOT_LOCK),
            flags=os.O_CREAT | os.O_RDWR,
            mode=0o600,
        )
        return fd
    except OSError as exc:
        log("warn", f"could not open snapshot lock: {exc}")
        return None


def _try_flock_ex(fd: int, deadline_sec: float = 5.0) -> bool:
    """Try ``fcntl.flock(LOCK_EX|LOCK_NB)`` until ``deadline_sec`` elapses.

    Returns True if the lock was acquired, False otherwise. Non-blocking —
    never sleeps past the deadline so launchd's StartInterval stays tight.
    """
    try:
        import fcntl  # local import
    except ImportError:  # pragma: no cover - exotic platform
        return False
    end = time.monotonic() + deadline_sec
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError as exc:
            if exc.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                return False
            if time.monotonic() >= end:
                return False
            time.sleep(0.05)


# ----- main ------------------------------------------------------------------


def main(argv: list[str]) -> int:
    backend = detect_backend()
    if backend == "ghostty":
        panes = walk_ghostty_panes()
        backend_label = "ghostty"
    elif backend == "tmux":
        panes = walk_tmux_panes()
        backend_label = "tmux"
    elif backend == "wezterm":
        # WezTerm backend (Phase B). Uses `wezterm cli list` for pane IDs.
        panes = walk_wezterm_panes()
        backend_label = "wezterm"
    elif backend == "windows-terminal":
        # Windows Terminal backend (Phase B). Uses `tasklist` + named pipes
        # to enumerate panes. WezTerm inside WSL is preferred when available.
        panes = walk_windows_terminal_panes()
        backend_label = "windows-terminal"
    elif backend == "wsl":
        # WSL backend (Phase B). Falls back to the standard walker since WSL
        # surfaces Linux processes normally; the unique bit is the cwd path
        # which gets prefixed with /mnt/<drive>/ on mount.
        panes = walk_ghostty_panes()
        backend_label = "wsl"
    else:
        # No Ghostty/tmux/wezterm backend detected (user may be in a non-GUI session
        # like droid/SSH). Fall through and try the walker anyway — procs
        # always finds shell processes, and even shell-only snapshots are
        # useful for crash recovery. Only bail if the walker also returns
        # nothing.
        log("warn", "no Ghostty/tmux/wezterm backend detected; falling back to walker anyway")
        panes = walk_ghostty_panes()
        backend_label = backend  # "none" — informational only
    if not panes:
        print(f"session-snapshot: no panes detected (backend={backend_label})", file=sys.stderr)
        return 2
    # Merge in active zmx sessions (zmx.jsonl) as synthetic Pane objects.
    panes.extend(_load_zmx_panes())
    prev = load_previous()
    n = write_snapshot(panes, prev)
    # Summary on stderr.
    by_h = Counter(p.harness for p in panes)
    by_sid = sum(1 for p in panes if p.sid_from_argv)
    print(f"snapshot: {n} rows, {len(panes)} live panes, "
          f"{by_sid} argv-sids on {backend_label}", file=sys.stderr)
    for h, c in by_h.most_common():
        print(f"  {h}: {c}", file=sys.stderr)
    # Surface sharecli-tray status (read the row we just wrote).
    try:
        last = SNAPSHOT_FILE.read_text().splitlines()[-1] if SNAPSHOT_FILE.exists() else ""
        if last:
            d = json.loads(last)
            if d.get("harness") == "sharecli-tray":
                sc = d.get("sharecli", {}) or {}
                avail = "available" if sc.get("available") else "unavailable"
                err = sc.get("error") or ""
                print(f"  sharecli-tray: {avail} (socket={sc.get('socket')!r}, "
                      f"reachable={sc.get('reachable')}, "
                      f"sessions={sc.get('sessions_count')}, "
                      f"processes={sc.get('processes_count')}"
                      + (f", error={err!r}" if err else "")
                      + ")", file=sys.stderr)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
