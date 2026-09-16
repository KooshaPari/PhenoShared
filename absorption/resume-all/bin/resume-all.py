#!/usr/bin/env python3
# resume-all.py — backend dispatcher for resume-all.
#
# Reads the JSONL snapshot, collapses to one row per pane_id, and dispatches
# each row through the chosen backend (tmux or Ghostty AppleScript).
#
# Usage:
#   resume-all.py <snapshot.jsonl> <only-harness-or-empty> <0|1 dry-run> <tmux|ghostty>
#
# tmux branch:
#   - respawn the existing pane if still alive
#   - else new-window + respawn-pane
#
# Ghostty branch:
#   - if Ghostty isn't running, open -na Ghostty.app
#   - for each row, AppleScript:
#       tell application "Ghostty"
#         set cfg to make new surface configuration ...
#         set focused to focused terminal of selected tab of front window
#         set newTerm to split focused direction right with configuration cfg
#       end tell
#
# Ghostty's `input text` is bracketed-paste. To launch a command we put it
# in the surface configuration `command` field, which Ghostty feeds to the
# user's shell exactly as if they had typed it on the prompt line.

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Per-pane history replay knobs. The shell hook writes one log file per tty under
# RESUME_ALL_PANE_LOG_DIR; we hash the tty the same way (sha256, first 24 chars)
# so we can find the right log file when reopening a pane.
PANE_LOG_DIR = os.environ.get(
    "RESUME_ALL_PANE_LOG_DIR",
    os.path.expanduser("~/.local/share/resume-all/pane-logs"),
)
PANE_LOG_MAX_AGE_SEC = int(os.environ.get(
    "RESUME_ALL_PANE_LOG_MAX_AGE_SEC", str(24 * 3600),
))
PANE_LOG_REPLAY_LINES = int(os.environ.get(
    "RESUME_ALL_PANE_LOG_REPLAY_LINES", "50",
))
PANE_LOG_REPLAY_COLS = int(os.environ.get(
    "RESUME_ALL_PANE_LOG_REPLAY_COLS", "100",
))

# Lazy import of resolver — optional so resume-all still works if the resolver
# module is missing or broken on this machine.  The argv-wins guarantee is
# preserved either way: we only call the resolver for rows whose session_id
# is empty (i.e. argv didn't supply --conversation-id / --session / --resume).
try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    import resolver as _resolver  # type: ignore
except Exception as _resolver_err:  # pragma: no cover — defensive
    _resolver = None
    print(
        f"resume-all: resolver unavailable ({type(_resolver_err).__name__}: "
        f"{_resolver_err}); argv-less panes will fall through to picker",
        file=sys.stderr,
    )

# Lazy import of sharecli-ipc — optional. resume-all works without the Tray
# daemon; we just skip the "restored N sessions" notification when the helper
# can't be imported. The helper itself is defensive about the socket being
# unreachable, so a present-but-broken module still degrades to a no-op.
#
# NOTE: the file is named sharecli-ipc.py (dash) because that's what the
# launcher + audit conventions use, but Python's import grammar only allows
# identifiers (underscores). We import it lazily via importlib so the import
# error path can degrade to a no-op without ever raising.
import importlib.util as _importlib_util  # always available; lightweight
try:
    _SHARECLI_IPC_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "sharecli-ipc.py",
    )
    _SHARECLI_IPC_SPEC = _importlib_util.spec_from_file_location(
        "sharecli_ipc", _SHARECLI_IPC_PATH,
    )
    if _SHARECLI_IPC_SPEC is None or _SHARECLI_IPC_SPEC.loader is None:
        raise ImportError(f"no spec for {_SHARECLI_IPC_PATH}")
    _sharecli_ipc = _importlib_util.module_from_spec(_SHARECLI_IPC_SPEC)
    _SHARECLI_IPC_SPEC.loader.exec_module(_sharecli_ipc)
except Exception as _sharecli_err:  # pragma: no cover — defensive
    _sharecli_ipc = None
    print(
        f"resume-all: sharecli-ipc unavailable ({type(_sharecli_err).__name__}: "
        f"{_sharecli_err}); Tray notifications disabled",
        file=sys.stderr,
    )

# Module-level counter so each backend's dispatch loop can bump the same
# total. We only call sharecli_notify() when (a) this is a real apply
# (NOT dry-run) and (b) at least one session was actually restored.
_restored_total = 0

# Slice 7 hardening: every resume attempt (dispatched, skipped, preserved,
# errored, dry-run) gets one JSONL row appended to AUDIT_LOG.  The log is
# append-only and bounded by the rotation script in `~/.forge/bin/`; we just
# write one line per outcome and never block the dispatcher on logging
# failures (audit-write errors are surfaced to stderr but never abort the
# dispatch).
AUDIT_LOG = os.environ.get(
    "RESUME_ALL_AUDIT_LOG",
    os.path.expanduser("~/.local/share/resume-all/audit.log"),
)


def _audit_log_path() -> str:
    """Resolve the audit log path at call-time so test sandboxes that
    set ``RESUME_ALL_AUDIT_LOG`` after ``resume-all`` is imported are
    honoured.  The module-level ``AUDIT_LOG`` is preserved for callers
    that already cached the value (it stays correct for the default
    invocation path)."""
    return os.environ.get("RESUME_ALL_AUDIT_LOG", AUDIT_LOG)

def _audit_log(outcome: str, *, harness: str = "", pane_id: str = "",
               cwd: str = "", sid: str = "", detail: str = "") -> None:
    """Append one JSONL row to AUDIT_LOG.  Never raises.

    The row schema is intentionally flat so it can be grep'd with
    `awk -F'\\t'` or parsed with `jq -c`.  All writes are best-effort:
    an ENOSPC / EACCES is logged to stderr and the dispatcher keeps going.

    Implementation note: we use ``os.O_APPEND`` (atomic append on POSIX for
    writes <= PIPE_BUF, ~4 KiB; our rows are <512 B) instead of the
    tmp+os.replace pattern used for snapshot writes — replacing would
    clobber previous rows on every call.  fsync is best-effort.
    """
    try:
        row = {
            "ts": _iso_now(),
            "outcome": outcome,
            "harness": harness,
            "pane_id": pane_id,
            "cwd": cwd,
            "session_id": sid,
            "detail": detail[:240],  # truncate to keep log rows compact
        }
        audit_log = _audit_log_path()
        os.makedirs(os.path.dirname(audit_log), exist_ok=True)
        line = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
        fd = os.open(
            audit_log,
            flags=os.O_WRONLY | os.O_APPEND | os.O_CREAT,
            mode=0o600,
        )
        try:
            os.write(fd, line)
            try:
                os.fsync(fd)
            except OSError:
                pass  # some filesystems (e.g. some FUSE) reject fsync
        finally:
            os.close(fd)
    except Exception as _e:  # pragma: no cover — defensive
        print(
            f"resume-all: audit log write failed "
            f"({type(_e).__name__}: {_e})",
            file=sys.stderr,
        )


def _iso_now() -> str:
    """ISO-8601 UTC timestamp with second precision.  Used by the audit log."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

# Harnesses that have a real storage layout we can walk when argv is silent.
# Forge is intentionally NOT here — its conversations do not record cwd, so
# the resolver deterministically returns None and we let the picker run.
_RESOLVABLE_HARNESSES = {
    "codex", "cursor", "cursor-agent", "kilo", "droid", "opencode",
}

# ---------------------------------------------------------------------------
# Bookmarks (Phase E10) — named shortcuts for partial restore.
#
# Configured at ~/.config/resume-all/bookmarks.toml.  A bookmark is a set of
# category rules (cwd_prefixes, harnesses, tty_pattern).  Matching semantics:
#
#   OR within a category   (any rule in the list satisfies that category)
#   AND across categories  (pane must satisfy every category that has rules)
#   empty/absent category  is a wildcard (does not constrain)
#
# argv-supplied panes (session_id_source == "argv") ALWAYS win — the
# bookmark filter cannot drop a pane the user explicitly started with
# --conversation-id / --resume / --session.  argv is sacred.
#
# Loader returns {<name>: <rule_dict>, ...}, omitting the "default" key and
# any section whose name begins with "_" (the documented disable prefix).
# ---------------------------------------------------------------------------
BOOKMARKS_PATH = os.path.expanduser("~/.config/resume-all/bookmarks.toml")
# ---------------------------------------------------------------------------
# Workspaces (Phase E11) — named groups of panes, project-keyed.
#
# Configured at ~/.config/resume-all/workspaces.toml.  A workspace is a set
# of category rules (cwd_prefixes, harnesses) keyed by name.  Matching
# semantics mirror bookmarks (OR within a category, AND across, empty
# category = wildcard, argv-wins).  Workspaces do NOT carry tty_pattern
# (that's a bookmark concern); they are project groupings that span ttys.
#
# Layout: `[[workspace]]` array-of-tables, each with `name`, optional
# `cwd_prefixes`, optional `harnesses`, optional `description`.  See
# ~/.config/resume-all/workspaces.toml for examples.
# ---------------------------------------------------------------------------
WORKSPACES_PATH = os.path.expanduser("~/.config/resume-all/workspaces.toml")


def _load_workspaces() -> list:
    """Parse WORKSPACES_PATH and return the [[workspace]] rows.

    Missing file → [].  Malformed file → [] plus a stderr warning.  The
    same fail-soft contract as _load_bookmarks — workspaces are opt-in.
    """
    if not os.path.exists(WORKSPACES_PATH):
        return []
    try:
        import tomllib  # Python 3.11+ stdlib
    except ImportError:  # pragma: no cover — pre-3.11 fallback
        try:
            import tomli as tomllib  # type: ignore[import-not-found]
        except ImportError:
            print(
                "resume-all: tomllib/tomli not available; workspaces disabled",
                file=sys.stderr,
            )
            return []
    try:
        with open(WORKSPACES_PATH, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(
            f"resume-all: failed to parse {WORKSPACES_PATH}: "
            f"{type(exc).__name__}: {exc}; workspaces disabled",
            file=sys.stderr,
        )
        return []
    if not isinstance(data, dict):
        return []
    rows = data.get("workspace") or []
    if not isinstance(rows, list):
        return []
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        name = r.get("name")
        if not isinstance(name, str) or not name or name.startswith("_"):
            continue  # "_draft" workspaces are disabled
        out.append(r)
    return out


def _load_bookmarks() -> dict:
    """Parse BOOKMARKS_PATH and return the {name: rule_dict} map.

    Missing file → {}.  Malformed file / missing tomllib → {} plus a
    stderr warning.  Never raises — bookmarks are an opt-in feature.
    """
    if not os.path.exists(BOOKMARKS_PATH):
        return {}
    try:
        import tomllib  # Python 3.11+ stdlib
    except ImportError:  # pragma: no cover — pre-3.11 fallback
        try:
            import tomli as tomllib  # type: ignore[import-not-found]
        except ImportError:
            print(
                "resume-all: tomllib/tomli not available; bookmarks disabled",
                file=sys.stderr,
            )
            return {}
    try:
        with open(BOOKMARKS_PATH, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(
            f"resume-all: failed to parse {BOOKMARKS_PATH}: "
            f"{type(exc).__name__}: {exc}; bookmarks disabled",
            file=sys.stderr,
        )
        return {}
    if not isinstance(data, dict):
        return {}
    rules: dict = {}
    for name, rule in data.items():
        if name == "default":
            continue  # consumed separately via _bookmark_default()
        if not isinstance(name, str) or name.startswith("_"):
            continue  # "_draft" sections are disabled bookmarks
        if not isinstance(rule, dict):
            continue
        rules[name] = rule
    return rules


def _bookmark_default(rules: dict, raw_default) -> str:
    """Return the configured default bookmark name, or "" for "restore all"."""
    if not isinstance(raw_default, str):
        return ""
    if raw_default == "all":
        return ""
    if raw_default in rules:
        return raw_default
    print(
        f"resume-all: bookmarks.toml default={raw_default!r} does not "
        f"match any bookmark; falling back to 'all'",
        file=sys.stderr,
    )
    return ""


def _bookmark_default_from_disk() -> str:
    """Return the configured default key from the TOML, or "" if absent."""
    if not os.path.exists(BOOKMARKS_PATH):
        return ""
    try:
        import tomllib
    except ImportError:
        return ""
    try:
        with open(BOOKMARKS_PATH, "rb") as fh:
            data = tomllib.load(fh)
    except Exception:
        return ""
    if not isinstance(data, dict):
        return ""
    return _bookmark_default(data.get("bookmarks", data) if False else data,
                             data.get("default"))


def _bookmark_match_pane(row: dict, rule: dict) -> bool:
    """Does `row` satisfy the bookmark `rule`?

    Returns True iff the row satisfies every category that has rules.
    Categories with empty/missing values are wildcards (do not constrain).
    A pane with `session_id_source == "argv"` is ALWAYS treated as a match
    (argv-wins); callers should pre-check that and short-circuit before
    calling this function, but we also defend in depth here.
    """
    if row.get("session_id_source") == "argv":
        return True

    cwd_prefixes = rule.get("cwd_prefixes") or []
    harnesses = rule.get("harnesses") or []
    tty_pattern = rule.get("tty_pattern") or ""

    if cwd_prefixes:
        cwd = row.get("cwd") or ""
        if not any(cwd == p or cwd.startswith(p.rstrip("/") + "/") or cwd.startswith(p)
                   for p in cwd_prefixes if isinstance(p, str)):
            return False
    if harnesses:
        harness = row.get("harness") or ""
        if harness not in harnesses:
            return False
    if tty_pattern:
        import re as _re
        tty = row.get("tty") or ""
        try:
            if not _re.search(tty_pattern, tty):
                return False
        except _re.error:
            # Malformed regex — treat as no match (fail-closed).
            return False
    # All non-empty categories satisfied.
    return True


def _workspace_match_pane(row: dict, ws: dict) -> bool:
    """Does `row` satisfy the workspace `ws`?

    Mirrors _bookmark_match_pane but drops the tty_pattern category
    (workspaces are project groupings, not tty clusters).  argv-supplied
    panes (session_id_source == "argv") ALWAYS pass — the user explicitly
    started them and the workspace filter cannot drop them.
    """
    if row.get("session_id_source") == "argv":
        return True

    cwd_prefixes = ws.get("cwd_prefixes") or []
    harnesses = ws.get("harnesses") or []

    if cwd_prefixes:
        cwd = row.get("cwd") or ""
        if not any(cwd == p or cwd.startswith(p.rstrip("/") + "/") or cwd.startswith(p)
                   for p in cwd_prefixes if isinstance(p, str)):
            return False
    if harnesses:
        harness = row.get("harness") or ""
        if harness not in harnesses:
            return False
    return True


def _print_bookmarks_and_exit(bookmarks: dict, default_name: str) -> None:
    """Pretty-print the loaded bookmarks + default and exit 0."""
    print("resume-all bookmarks:")
    if not bookmarks:
        print("  (no bookmarks configured — ~/.config/resume-all/bookmarks.toml missing or empty)")
    for name in sorted(bookmarks.keys()):
        rule = bookmarks[name]
        cwd_n = len(rule.get("cwd_prefixes") or [])
        hs = rule.get("harnesses") or []
        tty_pat = rule.get("tty_pattern") or ""
        cwd_str = f"cwd={cwd_n} prefixes"
        h_str = f"harnesses={len(hs)}"
        if hs:
            h_str += " (" + ", ".join(hs) + ")"
        tty_str = f"tty_pattern={tty_pat}" if tty_pat else "tty_pattern=<any>"
        print(f"  {name}: {cwd_str}, {h_str}, {tty_str}")
    if default_name:
        print(f"  default behavior: restore only '{default_name}' bookmark")
    else:
        print("  default behavior: restore all")
    sys.exit(0)


def _print_workspaces_and_exit(workspaces: list) -> None:
    """Pretty-print the configured workspaces and exit 0.

    Mirrors _print_bookmarks_and_exit but uses the [[workspace]] array
    layout.  No default key in workspaces.toml — every workspace is
    explicitly opt-in via --workspace=<name>.
    """
    print("resume-all workspaces:")
    if not workspaces:
        print("  (no workspaces configured — ~/.config/resume-all/workspaces.toml missing or empty)")
    for ws in workspaces:
        name = ws.get("name", "<unnamed>")
        cwd_n = len(ws.get("cwd_prefixes") or [])
        hs = ws.get("harnesses") or []
        desc = ws.get("description", "")
        cwd_str = f"cwd={cwd_n} prefixes"
        if hs:
            h_str = f"harnesses={len(hs)} (" + ", ".join(hs) + ")"
        else:
            h_str = "harnesses=<any>"
        print(f"  {name}: {cwd_str}, {h_str}")
        if desc:
            print(f"    description: {desc}")
    sys.exit(0)


def _parse_cli(argv):
    # Preserve the zsh wrapper's historical four-position argument contract.
    # An optional 5th positional (replay_history) is accepted in the same order.
    # The 4-positional path is ONLY taken when argv[0..3] look like the
    # historical 4-positional contract AND argv[4] is either absent or
    # the literal "1" (replay_history=1).  Anything else — including
    # argv[4] like "--workspace=thegent" — falls through to argparse so
    # new flags can be added without breaking the legacy callers.
    if (len(argv) >= 4 and not argv[0].startswith("-")
            and (len(argv) < 5 or argv[4] in ("0", "1"))
            and not any(a.startswith("-") for a in argv[5:])):
        replay = argv[4] == "1" if len(argv) >= 5 else False
        # Historical 4-positional contract: positional 5 cannot carry
        # --no-fork, so default to False here.
        return argv[0], argv[1], argv[2] == "1", argv[3], False, False, replay, False, "", ""

    # Argparse fallback: pre-process the 4- or 5-positional prefix into
    # the named flags argparse understands.  The zsh wrapper always emits
    # `(snapshot, only, dry_run, backend, replay_history)` followed by
    # optional --flags; we translate the prefix so argparse sees a clean
    # flag-only argv.
    translated: list[str] = []
    if len(argv) >= 4 and not argv[0].startswith("-"):
        translated += ["--snapshot-file", argv[0], "--only", argv[1]]
        if argv[2] == "1":
            translated.append("--dry-run")
        translated += ["--backend", argv[3]]
        if len(argv) >= 5 and argv[4] == "1":
            translated.append("--replay-history")
        argv = argv[5:]

    parser = argparse.ArgumentParser(description="Resume saved harness sessions")
    parser.add_argument(
        "--snapshot-file",
        default=str(os.path.expanduser("~/.local/share/resume-all/snapshot.jsonl")),
    )
    parser.add_argument("--only", default="")
    parser.add_argument("--backend", choices=("tmux", "ghostty", "zmx"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--require-auto-resolution", action="store_true",
        help="Exit non-zero if any argv-less pane failed to resolve its session_id.",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument(
        "--replay-history",
        action="store_true",
        help="Replay the last ~50 lines of each pane's history log at the top of the new pane. Ghostty only.",
    )
    parser.add_argument(
        "--no-fork",
        action="store_true",
        dest="no_fork",
        help="Skip dispatching panes whose harness is already running locally "
             "(checked via snapshot row pid + pgrep pattern). The launcher's "
             "core AppleScript-free `open -na Ghostty.app` dispatch is untouched; "
             "this only adds an early-skip guard.",
    )
    parser.add_argument(
        "--workspace", default="",
        help="Restore only panes matching this workspace group (Phase E11). "
             "Applied AFTER argv-supplied panes (which always win) and BEFORE "
             "--only. If no panes match, exit 3 (same as --only).",
    )
    parser.add_argument(
        "--rank", action="store_true",
        help="Reorder panes by score (recency, harness, session_id, cwd depth, "
             "etc.) via rank-sessions.py. Most valuable panes are dispatched "
             "first. Default order is snapshot order.",
    )
    parser.add_argument(
        "--rank-top", type=int, default=0,
        help="When --rank is set, only resume the top N panes (0 = all).",
    )
    parser.add_argument(
        "--template", default="",
        help="Apply a workspace template (Phase E14) — only resume panes "
             "matching the template's pane patterns and harnesses. Uses "
             "workspace-templates.py. Examples: rust-dev, data-eng, ai-ml.",
    )
    parser.add_argument(
        "--cross-host", action="store_true",
        help="When session_id is missing for a pane, try to look it up via "
             "resume-cross.py. Otherwise argv-less panes stay unresolved.",
    )
    parser.add_argument(
        "--cross-host-target", default="desk",
        help="SSH host target for --cross-host lookups (default: desk). "
             "Should be reachable via ~/.ssh/config or use --host flag.",
    )
    subparsers = parser.add_subparsers(dest="cmd")
    bookmarks_p = subparsers.add_parser(
        "bookmarks",
        help="Print the configured bookmarks (Phase E10) and exit.",
    )
    workspaces_p = subparsers.add_parser(
        "workspaces",
        help="Print the configured workspaces (Phase E11) and exit.",
    )
    args = parser.parse_args(argv)
    backend = args.backend
    if not backend:
        backend = "tmux" if os.environ.get("TMUX") and shutil.which("tmux") else "ghostty"
    return (
        args.snapshot_file,
        args.only,
        args.dry_run,
        backend,
        args.require_auto_resolution,
        args.json_output,
        args.replay_history,
        args.no_fork,
        getattr(args, "cmd", "") or "",
        args.workspace or "",
        args.rank,
        args.rank_top,
        args.template or "",
        getattr(args, "cross_host", False),
        getattr(args, "cross_host_target", "desk"),
    )


(snapshot_path, only_filter, dry_run, backend,
 require_auto_resolution, json_output, replay_history, no_fork,
 _cli_cmd, workspace_filter, rank_enabled, rank_top_n,
 template_filter, cross_host_enabled, cross_host_target) = _parse_cli(sys.argv[1:])

# ----------------------------------------------------------------------------
# Bookmarks subcommand dispatch (Phase E10).
#
# `resume-all bookmarks` prints the configured bookmark rules and exits 0
# without ever loading the snapshot or touching the backend.  This must
# happen BEFORE the snapshot-load block below so the bookmarks command
# works even when the snapshot is empty / missing.
# ----------------------------------------------------------------------------
_bookmarks_rules: dict = {}
_bookmark_default_name: str = ""
if _cli_cmd == "bookmarks":
    raw_data: dict = {}
    if os.path.exists(BOOKMARKS_PATH):
        try:
            import tomllib
            with open(BOOKMARKS_PATH, "rb") as fh:
                raw_data = tomllib.load(fh)
        except Exception as _exc:
            print(
                f"resume-all: failed to parse {BOOKMARKS_PATH}: "
                f"{type(_exc).__name__}: {_exc}",
                file=sys.stderr,
            )
    _bookmarks_rules = _load_bookmarks()
    _bookmark_default_name = _bookmark_default(
        _bookmarks_rules, raw_data.get("default") if isinstance(raw_data, dict) else None,
    )
    _print_bookmarks_and_exit(_bookmarks_rules, _bookmark_default_name)

# ----------------------------------------------------------------------------
# Workspaces subcommand dispatch (Phase E11).
#
# `resume-all workspaces` prints the configured workspace groups and exits 0
# without ever loading the snapshot or touching the backend.  Mirrors the
# bookmarks subcommand above.
# ----------------------------------------------------------------------------
_workspaces_rules: list = []
if _cli_cmd == "workspaces":
    _workspaces_rules = _load_workspaces()
    _print_workspaces_and_exit(_workspaces_rules)

# ----------------------------------------------------------------------------
# Backend-availability probe (used by dry-run exit-code contract: 0/1/2).
# Slice 7: replaced the old "2 = no Ghostty/tmux" free-form code with a
# deterministic 3-state contract.
# ----------------------------------------------------------------------------
def _backend_available(backend: str) -> bool:
    if backend == "tmux":
        if not shutil.which("tmux"):
            return False
        try:
            r = subprocess.run(
                ["tmux", "list-sessions"],
                capture_output=True, text=True, timeout=3,
            )
            # tmux can auto-start a server; treat any non-error returncode
            # as available.  exit-code != 0 here only if the server is
            # wedged — still usable as a target for `new-session`.
            return r.returncode in (0, 1)
        except (subprocess.TimeoutExpired, OSError):
            return False
    if backend == "ghostty":
        # `open -na Ghostty.app` auto-launches Ghostty if missing, so the
        # backend is effectively always available as long as the .app exists
        # and `open` is on PATH (which is always true on macOS).
        return (
            shutil.which("open") is not None
            and os.path.exists("/Applications/Ghostty.app")
        )
    if backend == "zmx":
        return shutil.which("zmx") is not None
    return False


def _is_already_running(row: dict) -> bool:
    """Best-effort: is the harness already running locally for this row?

    Strategy:
      1. snapshot row pid (if > 0) → ``os.kill(pid, 0)``.  Permission denied
         counts as "alive" (process exists, we just can't signal it).
      2. pgrep for the harness's sid-flag pattern (forge/codex/opencode/kilo/
         cursor-agent all accept a sid flag we can grep for).

    Returns False on any error so ``--no-fork`` never blocks a restore that
    *might* succeed.
    """
    pid = row.get("pid") or 0
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        pid = 0
    if pid > 0:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            pass
        except PermissionError:
            # Process exists but isn't ours — treat as alive.
            return True
        except OSError:
            pass

    harness = row.get("harness", "") or ""
    sid = row.get("session_id", "") or ""
    if not harness or not sid or len(sid) < 8:
        return False

    pat_map = {
        "forge":        f"forge.*{sid[:8]}",
        "codex":        f"codex.*{sid[:8]}",
        "opencode":     f"opencode.*{sid[:8]}",
        "kilo":         f"kilo.*{sid[:8]}",
        "cursor":       f"cursor-agent.*{sid[:8]}",
        "cursor-agent": f"cursor-agent.*{sid[:8]}",
    }
    pat = pat_map.get(harness)
    if not pat:
        return False
    try:
        r = subprocess.run(
            ["pgrep", "-fl", pat],
            capture_output=True, text=True, timeout=3,
        )
        return bool(r.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


rows = []
_jsonl_parse_errors = 0
try:
    with open(snapshot_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                _jsonl_parse_errors += 1
except OSError as exc:
    print(f"resume-all: cannot read snapshot {snapshot_path}: {exc}", file=sys.stderr)
    if dry_run:
        sys.exit(2)
    sys.exit(1)

by_pane = {}
for r in rows:
    if r.get("dead") or r.get("pending"): continue
    pid = r["pane_id"]
    cur = by_pane.get(pid)
    if cur is None or r["ts"] > cur["ts"]:
        by_pane[pid] = r

# Split zmx-backed panes from AppleScript-backed panes so each goes to the
# right backend dispatch (zmx attach vs AppleScript split cascade).
zmx_panes = []
applescript_panes = []
for pane_id, r in by_pane.items():
    if r.get("harness") == "zmx" and r.get("zmx_name"):
        zmx_panes.append((pane_id, r))
    else:
        applescript_panes.append((pane_id, r))

# Use the zmx-filtered set for dispatch
by_pane = {p[0]: p[1] for p in applescript_panes}

# ----------------------------------------------------------------------------
# Bookmarks pre-filter (Phase E10).
#
# Apply the `--only=<bookmark>` filter BEFORE the resolver + dispatch loops
# so (a) the resolver doesn't burn time on panes we'll never restore and
# (b) the "0 panes matched" check can exit early with rc=3.
#
# Filter semantics (see _bookmark_match_pane for the underlying matcher):
#
#   only_filter == ""                  → keep all panes (default restore)
#   only_filter is a bookmark name     → keep panes matching the bookmark
#                                        OR argv-supplied panes (argv-wins)
#   only_filter is anything else       → keep only panes whose harness
#                                        equals only_filter (back-compat;
#                                        the "zmx" string still selects
#                                        only zmx-backed panes)
#
# argv-supplied panes (session_id_source == "argv") ALWAYS pass — they were
# started with --conversation-id / --resume / --session and the user
# explicitly asked for them, so the bookmark filter cannot drop them.
# ----------------------------------------------------------------------------
def _apply_bookmarks_prefilter(only_filter_value: str, snapshot_path_value: str,
                                by_pane_in: dict, zmx_panes_in: list) -> tuple[dict, list, int]:
    """Apply the bookmarks pre-filter and return (by_pane_out, zmx_panes_out, matched_count).

    - If only_filter_value is empty, returns the inputs unchanged with
      matched_count = len(by_pane_in) + len(zmx_panes_in).
    - Otherwise loads the bookmarks TOML and applies the predicate.
    - Caller is responsible for sys.exit(3) when matched_count == 0
      (the function returns (empty, [], 0) so the caller can detect).

    Pure function: never sys.exits, never prints (the caller does).  This
    makes it directly unit-testable from the test_bookmarks suite.
    """
    if not only_filter_value:
        return by_pane_in, zmx_panes_in, len(by_pane_in) + len(zmx_panes_in)
    rules = _load_bookmarks()
    matched_rule = rules.get(only_filter_value)
    bookmark_default_name = ""

    def _bookmark_filter_pane(row: dict) -> bool:
        if row.get("session_id_source") == "argv":
            return True  # argv-wins
        if matched_rule is not None:
            return _bookmark_match_pane(row, matched_rule)
        return (row.get("harness") or "") == only_filter_value

    def _bookmark_filter_zmx(row: dict) -> bool:
        if row.get("session_id_source") == "argv":
            return True  # argv-wins
        if matched_rule is not None:
            return _bookmark_match_pane(row, matched_rule)
        return only_filter_value == "zmx"

    out_by_pane = {
        pane_id: row for pane_id, row in by_pane_in.items()
        if _bookmark_filter_pane(row)
    }
    out_zmx = [
        (pane_id, row) for pane_id, row in zmx_panes_in
        if _bookmark_filter_zmx(row)
    ]
    return out_by_pane, out_zmx, len(out_by_pane) + len(out_zmx)


# ----------------------------------------------------------------------------
# Workspaces pre-filter (Phase E11).
#
# Apply the `--workspace=<name>` filter BEFORE the bookmarks/--only
# prefilter so:
#   1. argv-supplied panes (session_id_source == "argv") always win
#      (handled inside _workspace_match_pane, which short-circuits)
#   2. the resolver doesn't burn time on panes we'll never restore
#   3. the "0 panes matched" check exits early with rc=3
#   4. when --workspace is combined with --only=<bookmark>, the workspace
#      filter narrows the set first, then the bookmark filter applies on
#      top — same semantics as running both on the original snapshot
#
# argv-supplied panes ALWAYS pass — they were started with
# --conversation-id / --resume / --session and the user explicitly asked
# for them, so the workspace filter cannot drop them.
#
# Filter semantics (see _workspace_match_pane for the matcher):
#   workspace_filter == ""    → keep all panes (no workspace filter)
#   workspace_filter is a name → keep panes matching the workspace
#                                OR argv-supplied panes (argv-wins)
#   workspace_filter unknown  → 0 panes match → rc=3
# ----------------------------------------------------------------------------
def _apply_workspaces_prefilter(workspace_filter_value: str, by_pane_in: dict,
                                 zmx_panes_in: list) -> tuple[dict, list, int]:
    """Apply the workspace pre-filter and return (by_pane_out, zmx_panes_out, matched_count).

    - If workspace_filter_value is empty, returns the inputs unchanged with
      matched_count = len(by_pane_in) + len(zmx_panes_in).
    - Otherwise loads the workspaces TOML and applies the predicate.
    - Caller is responsible for sys.exit(3) when matched_count == 0.

    Pure function: never sys.exits, never prints.  The pre-filter is also
    deterministic: the output preserves the input ordering of by_pane /
    zmx_panes (dict insertion order, list order), but callers that need
    explicit reproducibility should sort by (tty, harness).
    """
    if not workspace_filter_value:
        return by_pane_in, zmx_panes_in, len(by_pane_in) + len(zmx_panes_in)
    rows = _load_workspaces()
    matched_rule = next(
        (r for r in rows if r.get("name") == workspace_filter_value),
        None,
    )
    if matched_rule is None:
        # Unknown workspace — zero matches.  We do not silently fall through
        # to "all panes" because the user explicitly asked for a workspace
        # that does not exist; the rc=3 path is the right behaviour.
        return {}, [], 0

    # Sort the surviving panes by (workspace_name, tty, harness) so the
    # filter output is deterministic across runs (the snapshot writer
    # uses ts-based ordering which can shift between two snapshots of
    # the same set of panes).  The workspace_name is constant within a
    # single call, so the effective sort key is (tty, harness).
    def _sort_key(item):
        _, row = item
        return (row.get("tty", ""), row.get("harness", ""))

    out_by_pane = dict(sorted(
        ((pane_id, row) for pane_id, row in by_pane_in.items()
         if _workspace_match_pane(row, matched_rule)),
        key=_sort_key,
    ))
    out_zmx = sorted(
        ((pane_id, row) for pane_id, row in zmx_panes_in
         if _workspace_match_pane(row, matched_rule)),
        key=_sort_key,
    )
    return out_by_pane, out_zmx, len(out_by_pane) + len(out_zmx)


if workspace_filter:
    by_pane, zmx_panes, _ws_matched_count = _apply_workspaces_prefilter(
        workspace_filter, by_pane, zmx_panes,
    )
    if _ws_matched_count == 0:
        print(
            f"resume-all: --workspace={workspace_filter!r} matched 0 pane(s) "
            f"in snapshot {snapshot_path}; aborting with rc=3",
            file=sys.stderr,
        )
        sys.exit(3)
    print(
        f"resume-all: --workspace={workspace_filter!r} kept "
        f"{_ws_matched_count} pane(s) ({len(by_pane)} non-zmx + "
        f"{len(zmx_panes)} zmx)",
        file=sys.stderr,
    )

if only_filter:
    by_pane, zmx_panes, _matched_count = _apply_bookmarks_prefilter(
        only_filter, snapshot_path, by_pane, zmx_panes,
    )
    if _matched_count == 0:
        print(
            f"resume-all: --only={only_filter!r} matched 0 pane(s) in "
            f"snapshot {snapshot_path}; aborting with rc=3",
            file=sys.stderr,
        )
        sys.exit(3)
    print(
        f"resume-all: --only={only_filter!r} kept {_matched_count} pane(s) "
        f"({len(by_pane)} non-zmx + {len(zmx_panes)} zmx)",
        file=sys.stderr,
    )


# ----------------------------------------------------------------------------
# Optional template filter (Phase E14). When --template is set, call
# workspace-templates.py to filter panes by pane patterns + harnesses + cwd.
# ----------------------------------------------------------------------------
if template_filter:
    try:
        _wt_proc = subprocess.run(
            [sys.executable, str(os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "workspace-templates.py")),
             "apply", template_filter, "--snapshot", snapshot_path],
            capture_output=True, text=True, timeout=30,
        )
        # Parse current-workspace.json written by workspace-templates apply
        SNAPSHOT_DIR = Path(os.path.expanduser("~/.local/share/resume-all"))
        _wt_current = SNAPSHOT_DIR / "current-workspace.json"
        if _wt_current.exists():
            _wt_data = json.loads(_wt_current.read_text())
            _wt_pane_ids = set(_wt_data.get("row_ids", []))
            _before = len(by_pane)
            by_pane = {pid: row for pid, row in by_pane.items()
                       if pid in _wt_pane_ids}
            zmx_panes = [(pid, row) for pid, row in zmx_panes
                         if pid in _wt_pane_ids]
            print(
                f"resume-all: --template={template_filter!r} kept "
                f"{len(by_pane)}/{_before} panes",
                file=sys.stderr,
            )
            if not by_pane and not zmx_panes:
                print(
                    f"resume-all: --template={template_filter!r} matched 0 "
                    f"pane(s); aborting with rc=3",
                    file=sys.stderr,
                )
                sys.exit(3)
        else:
            print(
                f"resume-all: --template={template_filter!r} did not produce "
                f"current-workspace.json",
                file=sys.stderr,
            )
    except Exception as _wt_err:
        print(
            f"resume-all: --template failed ({type(_wt_err).__name__}: "
            f"{_wt_err}); ignoring filter",
            file=sys.stderr,
        )


# ----------------------------------------------------------------------------
# Optional ranking (Phase E12). When --rank is set, call rank-sessions.py to
# reorder panes by composite score (recency, harness, session_id, cwd depth,
# tty freshness, pid relevance, argv-sid bonus). Most valuable panes are
# dispatched first. --rank-top N keeps only the top N panes.
# ----------------------------------------------------------------------------
if rank_enabled:
    try:
        _rank_proc = subprocess.run(
            [sys.executable, str(os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "rank-sessions.py")),
             snapshot_path, "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if _rank_proc.returncode == 0:
            _scored = json.loads(_rank_proc.stdout)
            _score_by_pane = {r["pane_id"]: r["_score"] for r in _scored
                              if "pane_id" in r}
            # Reorder by_pane and zmx_panes by score (desc)
            by_pane = dict(sorted(
                by_pane.items(),
                key=lambda kv: (-_score_by_pane.get(kv[0], 0.0),
                                kv[1].get("ts_epoch", 0)),
            ))
            zmx_panes = sorted(
                zmx_panes,
                key=lambda kv: (-_score_by_pane.get(kv[0], 0.0),
                                kv[1].get("ts_epoch", 0)),
            )
            print(
                f"resume-all: --rank ordered {len(by_pane)} panes by score "
                f"(top: {list(_score_by_pane.items())[:3]})",
                file=sys.stderr,
            )
            if rank_top_n and rank_top_n > 0:
                _before = len(by_pane)
                by_pane = dict(list(by_pane.items())[:rank_top_n])
                print(
                    f"resume-all: --rank-top {rank_top_n} kept "
                    f"{len(by_pane)}/{_before} panes",
                    file=sys.stderr,
                )
    except Exception as _rank_err:
        print(
            f"resume-all: --rank failed ({type(_rank_err).__name__}: "
            f"{_rank_err}); falling back to snapshot order",
            file=sys.stderr,
        )


# ----------------------------------------------------------------------------
# Resolve session_ids for argv-less panes by walking each harness's storage.
# argv ALWAYS wins: rows with a non-empty session_id (argv-supplied) are
# untouched.  Rows with an empty session_id get exactly one resolver call;
# the resolver itself does NOT see argv (kept argv-free by design).
# ----------------------------------------------------------------------------
_resolver_attempts = 0
_resolver_hits = 0
if _resolver is not None:
    # Parallelise: with ~30 panes and ~30-60ms per resolver call (sqlite
    # open + read + cwd-score over a list), sequential dispatch adds 1-2s
    # to resume-all latency. ThreadPoolExecutor with a small worker pool
    # keeps the main thread free for the dispatch loop while a handful
    # of workers fan out the (mostly I/O-bound) resolver calls.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    _pool_workers = min(8, max(2, (os.cpu_count() or 4) * 2))
    _resolver_jobs = []
    for _pane_id, _row in by_pane.items():
        if _row.get("session_id"):
            continue
        _h = _row.get("harness", "")
        if _h not in _RESOLVABLE_HARNESSES:
            continue
        _cwd = _row.get("cwd", "")
        if not _cwd:
            continue
        _resolver_jobs.append((_pane_id, _row, _h, _cwd))
    if _resolver_jobs:
        _resolver_attempts = len(_resolver_jobs)

        def _resolve_one(job):
            pane_id, row, harness, cwd = job
            try:
                sid = _resolver.resolve_session_id(
                    harness, cwd, hint_pid=row.get("pid"),
                )
            except Exception as e:  # pragma: no cover — defensive
                return (pane_id, row, None,
                        f"{type(e).__name__}: {e}")
            return (pane_id, row, sid, "")

        with ThreadPoolExecutor(max_workers=_pool_workers) as _pool:
            for _pane_id, _row, _sid, _err in _pool.map(
                _resolve_one, _resolver_jobs,
            ):
                if _err:
                    print(
                        f"resume-all: resolver failed for "
                        f"{_row.get('harness','')}:{_pane_id} ({_err})",
                        file=sys.stderr,
                    )
                    continue
                if _sid:
                    _row["session_id"] = _sid
                    _row["session_id_source"] = "storage"
                    _resolver_hits += 1
if _resolver_attempts:
    print(
        f"resume-all: resolver {_resolver_hits}/{_resolver_attempts} "
        f"harness sid(s) recovered from storage",
        file=sys.stderr,
    )

# ----------------------------------------------------------------------------
# Cross-host session_id lookup (Phase B integration).
#
# When --cross-host is set, look up any remaining unresolved pane's
# session_id by querying the remote snapshot via resume-cross.py.
# This is the Phase B integration point that lets a session started on
# one host (e.g. WSL Fedora) be resumed on the same host from a different
# machine (e.g. macOS trigger via SSH).
# ----------------------------------------------------------------------------
_cross_host_attempts = 0
_cross_host_hits = 0
if cross_host_enabled:
    # Find panes that still lack session_id after local resolver pass
    _cross_jobs = [(pid, row) for pid, row in by_pane.items()
                   if not row.get("session_id")
                   and row.get("cwd")]  # need a cwd to look up
    if _cross_jobs:
        print(
            f"resume-all: --cross-host looking up {len(_cross_jobs)} pane(s) "
            f"on {cross_host_target} via resume-cross.py",
            file=sys.stderr,
        )
        try:
            _cross_host_attempts = len(_cross_jobs)
            for _pane_id, _row in _cross_jobs:
                # Call resume-cross.py resume --dry-run to get the
                # session_id field (now wired in this session).
                try:
                    _cross_proc = subprocess.run(
                        ["/Users/kooshapari/bin/resume-cross.py", "resume",
                         "--dry-run", cross_host_target, _pane_id],
                        capture_output=True, text=True, timeout=10,
                    )
                    if _cross_proc.returncode == 0:
                        try:
                            _cross_out = json.loads(_cross_proc.stdout)
                            _cross_sid = _cross_out.get("session_id", "")
                            if _cross_sid:
                                _row["session_id"] = _cross_sid
                                _row["session_id_source"] = "cross-host"
                                _cross_host_hits += 1
                        except (json.JSONDecodeError, ValueError):
                            pass
                except subprocess.TimeoutExpired:
                    print(
                        f"resume-all: --cross-host timeout for {_pane_id}",
                        file=sys.stderr,
                    )
                except Exception as _ce:
                    print(
                        f"resume-all: --cross-host error for {_pane_id}: "
                        f"{type(_ce).__name__}: {_ce}",
                        file=sys.stderr,
                    )
        except Exception as _ce:
            print(
                f"resume-all: --cross-host failed: {type(_ce).__name__}: {_ce}",
                file=sys.stderr,
            )
    if _cross_host_attempts:
        print(
            f"resume-all: --cross-host {_cross_host_hits}/{_cross_host_attempts} "
            f"remote sid(s) recovered",
            file=sys.stderr,
        )

# ----------------------------------------------------------------------------
# zmx backend — detached session manager (zmx run <name> -d <cmd>).
#
# Each zmx pane has a stable `zmx_name`; on resume we just `zmx attach <name>`.
# If the session died since the last snapshot, fall back to recreating it
# with `zmx run <name> -d '<original-command>'`.
# ----------------------------------------------------------------------------
def zmx_resume():
    if not shutil_which("zmx"):
        print("resume-all: zmx not on PATH", file=sys.stderr)
        return

    restored = 0
    recreated = 0
    for pane_id, r in zmx_panes:
        name = r["zmx_name"]
        # NOTE: the --only=<bookmark> filter is applied upstream in the
        # bookmarks pre-filter block; zmx_panes here is already pre-filtered
        # so this loop just dispatches whatever survived.
        if dry_run:
            print(f"# zmx attach {name}  # cwd={r.get('cwd','')} cmd={r.get('command','')[:60]!r}")
            _audit_log(
                "dry_run", harness="zmx", pane_id=pane_id,
                cwd=r.get("cwd", ""), sid=name,
                detail="zmx-attach-dry-run",
            )
            restored += 1
            continue
        # Probe liveness
        probe = subprocess.run(
            ["zmx", "list"], capture_output=True, text=True
        ).stdout
        alive = any(f"name={name}" in line for line in probe.splitlines())
        if alive:
            subprocess.Popen(
                ["zmx", "attach", name],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            _audit_log(
                "restored", harness="zmx", pane_id=pane_id,
                cwd=r.get("cwd", ""), sid=name,
                detail="zmx-attach-alive",
            )
            restored += 1
        else:
            cmd = r.get("command", "")
            cwd = r.get("cwd", "")
            if not cmd:
                _audit_log(
                    "skipped", harness="zmx", pane_id=pane_id,
                    cwd=cwd, sid=name,
                    detail="zmx-no-command-on-recreate",
                )
                continue
            subprocess.run(
                ["zmx", "run", name, "-d", "cd '{}' && {}".format(cwd.replace("'", "'\\''"), cmd)],
                check=False,
            )
            _audit_log(
                "restored", harness="zmx", pane_id=pane_id,
                cwd=cwd, sid=name,
                detail="zmx-recreate",
            )
            recreated += 1
    print(f"resume-all: zmx {restored} attached, {recreated} recreated "
          f"(snapshot: {snapshot_path})")
    global _restored_total
    # zmx "recreated" is also a real restore (a brand-new session that fills
    # the gap left by a dead one). Sum both for the Tray notification.
    _restored_total += restored + recreated

def shutil_which(name):
    from shutil import which
    return which(name)

def shq(s):
    return "'" + s.replace("'", "'\\''") + "'"

def build_cmd(harness, sid, cwd):
    if not sid:
        return None
    if harness == "forge":
        return f"exec forge --conversation-id {shq(sid)} -C {shq(cwd)}"
    if harness == "codex":
        return f"cd {shq(cwd)} && exec codex resume {shq(sid)}"
    if harness == "opencode":
        return f"cd {shq(cwd)} && exec opencode --session {shq(sid)}"
    if harness == "kilo":
        return f"cd {shq(cwd)} && exec kilo --session {shq(sid)}"
    if harness in ("cursor", "cursor-agent"):
        return f"cd {shq(cwd)} && exec cursor-agent --resume {shq(sid)}"
    return None


def _auto_resolution_failures():
    """Return argv-less panes whose session_id could not be auto-resolved.

    Slice 7 hardening (final): forge sessions are intentionally NOT counted
    as auto-resolution failures. Forge conversations do not record cwd on
    disk (see ``resolver._resolve_forge`` — header is
    ``{kind, conversation_id, created_at}`` with no cwd field), so the
    resolver deterministically returns None and the picker is the
    documented, correct fallback. A forge argv-less pane going to the
    picker is therefore expected behavior, NOT a failure that should
    block ``--require-auto-resolution``.

    Only harnesses with a cwd-matchable storage layout (codex, cursor,
    kilo, opencode, droid) are scored here. If those harnesses produce an
    unresolved argv-less row, it's a real failure — the operator almost
    certainly wants the launchd timer to surface it.
    """
    auto_resolvable = {"codex", "opencode", "kilo", "cursor", "cursor-agent", "droid"}
    failures = []
    for pane_id, row in sorted(
        [(pane_id, row) for pane_id, row in by_pane.items()] + zmx_panes,
        key=lambda item: item[1].get("cwd", ""),
    ):
        if row.get("harness") not in auto_resolvable:
            continue
        # by_pane + zmx_panes are pre-filtered by the --only=<bookmark>
        # block; this loop only inspects the surviving set.
        if row.get("session_id_source") == "argv":
            continue
        if row.get("session_id_source") != "storage" or not row.get("session_id"):
            failures.append({
                "pane_id": pane_id,
                "harness": row.get("harness", ""),
                "cwd": row.get("cwd", ""),
            })
    return failures


auto_resolution_failures = _auto_resolution_failures()
if require_auto_resolution and auto_resolution_failures:
    details = ", ".join(
        f"{row['harness']}:{row['pane_id']} ({row['cwd']})"
        for row in auto_resolution_failures
    )
    print(
        f"resume-all: auto-resolution required; unresolved argv-less pane(s): {details}",
        file=sys.stderr,
    )
    if json_output:
        print(json.dumps({
            "auto_resolution_ok": False,
            "unresolved": auto_resolution_failures,
            "sessions": [],
        }, indent=2))
    sys.exit(1)

if dry_run and json_output:
    sessions = []
    # Both by_pane and zmx_panes are pre-filtered upstream by the
    # --only=<bookmark> block, so we just enumerate the surviving rows.
    for pane_id, row in sorted(by_pane.items(), key=lambda item: item[1].get("cwd", "")):
        cmd = build_cmd(row.get("harness", ""), row.get("session_id", ""), row.get("cwd", ""))
        if cmd:
            sessions.append({
                "pane_id": pane_id,
                "harness": row.get("harness", ""),
                "cwd": row.get("cwd", ""),
                "session_id": row.get("session_id", ""),
                "command": cmd,
            })
    for pane_id, row in zmx_panes:
        sessions.append({
            "pane_id": pane_id,
            "harness": "zmx",
            "cwd": row.get("cwd", ""),
            "session_id": row.get("zmx_name", ""),
            "command": f"zmx attach {row.get('zmx_name', '')}",
        })
    print(json.dumps({
        "auto_resolution_ok": not auto_resolution_failures,
        "unresolved": auto_resolution_failures,
        "sessions": sessions,
    }, indent=2))
    sys.exit(0)

# ----------------------------------------------------------------------------
# tmux backend
# ----------------------------------------------------------------------------
def tmux_resume():
    def run(*args, check=True):
        return subprocess.run(["tmux", *args], check=check,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if not dry_run:
        probe = run("list-sessions", check=False)
        if probe.returncode != 0:
            run("new-session", "-d", "-s", "main")

    if dry_run:
        live = set(run("list-panes", "-a", "-F", "#{pane_id}", check=False).stdout.splitlines())
    else:
        live = None

    count = 0
    # by_pane is pre-filtered upstream by the --only=<bookmark> block;
    # this loop just dispatches whatever survived.
    for pane_id, r in sorted(by_pane.items(), key=lambda kv: kv[1].get("cwd", "")):
        cmd = build_cmd(r["harness"], r["session_id"], r["cwd"])
        if not cmd:
            _audit_log(
                "skipped", harness=r.get("harness", ""), pane_id=pane_id,
                cwd=r.get("cwd", ""), sid=r.get("session_id", ""),
                detail="build_cmd-returned-none",
            )
            continue
        title = f"{r['harness']}:{r['session_id'][:8]}"
        if dry_run:
            if pane_id in (live or set()):
                print(f"# tmux respawn-pane -k -t {pane_id}  # {title}")
                print(f"  {cmd}")
            else:
                print(f"# tmux new-window -d -n '{title}'; tmux respawn-pane -k  # {pane_id}")
                print(f"  {cmd}")
        else:
            probe = run("list-panes", "-a", "-F", "#{pane_id}", check=False)
            if pane_id in probe.stdout.splitlines():
                run("respawn-pane", "-k", "-t", pane_id, cmd)
            else:
                run("new-window", "-d", "-n", title)
                new_pid = run("display-message", "-p", "#{pane_id}").stdout.strip()
                run("respawn-pane", "-k", "-t", new_pid, cmd)
        _audit_log(
            "restored",
            harness=r.get("harness", ""), pane_id=pane_id,
            cwd=r.get("cwd", ""), sid=r.get("session_id", ""),
            detail="tmux-respawn-or-new-window",
        )
        count += 1
    global _restored_total
    _restored_total += count
    print(f"resume-all: {count} session(s) {'would be' if dry_run else 'were'} restored "
          f"(backend: tmux, snapshot: {snapshot_path})")

# ----------------------------------------------------------------------------
# Ghostty backend (AppleScript)
#
# AppleScript syntax (verified against /Applications/Ghostty.app/Contents/Resources/Ghostty.sdef
# in Ghostty 1.3.x):
#
#   tell application "Ghostty"
#       set cfg to make new surface configuration with properties {¬
#           initial working directory:"/path", ¬
#           command:"the harness launch command", ¬
#           wait after command:false}
#       set focused to focused terminal of selected tab of front window
#       split focused direction right with configuration cfg
#   end tell
#
# We batch all rows into ONE AppleScript invocation so we get one round-trip
# to the Ghostty process and the user sees all panes materialise together.
# ----------------------------------------------------------------------------
OSA_BATCH_TMPL = r'''
use framework "Foundation"
use scripting additions

on run argv
    set configList to {}
    repeat with i from 1 to (count of items of argv)
        set item i of argv to (current application's NSString's stringWithString:(item i of argv))
    end repeat

    set i to 1
    repeat while i <= (count of items of argv)
        set cwd to item i of argv
        set cmd to item (i + 1) of argv
        set cfg to make new surface configuration with properties {¬
            initial working directory:cwd, ¬
            command:cmd, ¬
            wait after command:false}
        set end of configList to cfg
        set i to i + 2
    end repeat

    try
        tell application "Ghostty"
            if (count of windows) = 0 then
                make new window
            end if

            set focusedTerm to focused terminal of selected tab of front window
            set firstCfg to item 1 of configList
            set prevTerm to split focusedTerm direction right with configuration firstCfg

            repeat with c from 2 to (count of configList)
                set nextCfg to item c of configList
                set prevTerm to split prevTerm direction below with configuration nextCfg
            end repeat
        end tell
        return "OK"
    on error errMsg
        return "ERR:" & errMsg
    end try
end run
'''

def _ghostty_open(cwd: str, cmd: str, only_filter: str | None, dry_run: bool, label: str,
                  replay_lines: str | None = None, pane_id_for_log: str = "",
                  pane_id: str = "", harness: str = "", sid: str = ""):
    """Spawn a single Ghostty window via `open -na Ghostty.app`.

    Each harness session gets its **own** independent Ghostty process.
    No AppleScript `split` → no focus stealing, no cursor stealing.

    When `replay_lines` is provided, it is written to a temp file and
    prepended to the shell command via `cat <file> &&` so the user sees
    a "session history replay" block at the top of the new pane.

    Slice 7 hardening: every `open -na` invocation is wrapped in
    try/except + a short synchronous ``wait()`` so we surface launch
    failures (Ghostty.app missing, ``open`` not on PATH, permission
    denied on the working directory, etc.) **before** we move on to
    the next pane. Previously the launcher fired Popen and walked
    away, so a missing-binary or perms problem was silently swallowed
    and the user just saw "restored 0 sessions" on stderr.

    On failure we return ``False`` AND emit an audit row with
    outcome="errored" so the failure mode is reconstructable after the
    fact. The audit row is written by the caller (ghostty_resume) so
    the row schema stays consistent across all backends.
    """
    if dry_run:
        print(f"#   {label}")
        print(f"#     cwd={cwd}")
        print(f"#     cmd={cmd}")
        if replay_lines:
            print(f"#     replay_block (pane={pane_id_for_log}):")
            for line in replay_lines.splitlines():
                print(f"#       | {line}")
        return True

    # Strip "exec " prefix and "cd <path> && exec " wrappers so we end
    # up with the bare harness command.  Cwd is handled by Ghostty via
    # --working-directory below, so we don't need to embed `cd <cwd> &&`
    # in the -e arg (which would duplicate the chdir and add ~40 chars
    # to every dispatch).
    c = cmd.strip()
    if c.startswith("exec "):
        c = c[len("exec "):]
    if c.startswith("cd ") and " && " in c:
        c = c.split(" && ", 1)[-1]
        if c.startswith("exec "):
            c = c[len("exec "):]

    # Prepend the replay block (if any) by routing it through a temp file.
    # This avoids any shell-escaping issues for ANSI sequences and log lines.
    # The cwd is NOT embedded in -e (--working-directory handles it); only
    # the harness launch command goes there.
    shell_cmd = c
    if replay_lines:
        try:
            import tempfile
            fd, replay_path = tempfile.mkstemp(
                prefix=f"pane-replay-{pane_id_for_log}-",
                suffix=".txt",
                dir="/tmp",
            )
            with os.fdopen(fd, "w") as f:
                f.write(replay_lines)
            os.chmod(replay_path, 0o600)
        except Exception as e:
            print(f"resume-all: failed to write replay temp file: {e}", file=sys.stderr)
            replay_path = None

        if replay_path:
            shell_cmd = f"cat {shlex.quote(replay_path)} && {shell_cmd}"

    try:
        proc = subprocess.Popen(
            ["open", "-na", "Ghostty.app", "--args",
             "--working-directory", cwd,
             "-e", shell_cmd],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
    except (FileNotFoundError, OSError, PermissionError) as e:
        # `open` is missing or not executable / Ghostty.app is in a
        # weird state.  Surface this synchronously so the all-or-nothing
        # dispatch in ghostty_resume() can abort the batch.
        print(
            f"resume-all: failed to launch ghostty window "
            f"(pane={pane_id} cwd={cwd}): {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        _audit_log(
            "errored", harness=harness, pane_id=pane_id, cwd=cwd, sid=sid,
            detail=f"open-popen-failed:{type(e).__name__}:{e}",
        )
        return False

    # ``open -na Ghostty.app`` is async-fire-and-hand-off: the launching
    # ``open`` process exits as soon as it has told LaunchServices to
    # start the app.  Wait briefly so we surface early failures
    # (Ghostty.app missing -> ``open`` exits non-zero; .app present but
    # broken -> ``open`` exits cleanly but stderr has a warning).  If
    # ``open`` is still running after 2s we trust that the launch has
    # been handed off and return True.
    try:
        out, err = proc.communicate(timeout=2.0)
    except subprocess.TimeoutExpired:
        # Launch is in progress / handed off; nothing to do.
        return True
    except (OSError, PermissionError) as e:
        # ``open`` crashed mid-launch with a process-level error.
        print(
            f"resume-all: ghostty launch raised mid-flight "
            f"(pane={pane_id} cwd={cwd}): {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        _audit_log(
            "errored", harness=harness, pane_id=pane_id, cwd=cwd, sid=sid,
            detail=f"open-communicate-failed:{type(e).__name__}:{e}",
        )
        return False

    if proc.returncode != 0:
        err_text = (err or b"").decode("utf-8", errors="replace").strip()
        print(
            f"resume-all: ghostty launch exited with code "
            f"{proc.returncode} (pane={pane_id} cwd={cwd}): {err_text}",
            file=sys.stderr,
        )
        _audit_log(
            "errored", harness=harness, pane_id=pane_id, cwd=cwd, sid=sid,
            detail=f"open-nonzero:{proc.returncode}:{err_text[:120]}",
        )
        return False

    # ``open`` exited 0 — treat as success.  We can't observe whether
    # Ghostty actually drew a window without a deep AppleScript probe,
    # which is out of scope for the Slice 7 failure-mode hardening.
    return True

def _pane_log_path_for_tty(tty: str) -> str | None:
    """Return the pane-log file path for a given tty, or None if no tty."""
    if not tty:
        return None
    # Mirror the zsh hook: hash tty with sha256, take first 24 hex chars.
    h = hashlib.sha256(tty.encode("utf-8")).hexdigest()[:24]
    return os.path.join(PANE_LOG_DIR, f"{h}.log")


def _read_replay_lines(tty: str) -> str | None:
    """Read the last N lines from the pane-log for `tty`, age-gated.

    Returns the raw block (no ANSI framing). The caller adds the border.
    """
    path = _pane_log_path_for_tty(tty)
    if not path or not os.path.exists(path):
        return None
    try:
        age = time.time() - os.path.getmtime(path)
        if age > PANE_LOG_MAX_AGE_SEC:
            return None
    except OSError:
        return None
    try:
        # Use `tail` for memory-bounded reads of up to 1 MiB log files.
        result = subprocess.run(
            ["tail", "-n", str(PANE_LOG_REPLAY_LINES), path],
            capture_output=True, text=True, check=False,
        )
        text = result.stdout
    except (FileNotFoundError, OSError):
        return None
    if not text.strip():
        return None
    return text


def _format_replay_block(text: str, pane_id: str) -> str:
    """Wrap `text` in a compact ANSI-bordered block ready for `cat`-ing.

    Format:
        ┌─ session history replay (pane=<id>) ─
        │ 2026-08-01T11:11:27Z | 10s | echo hello
        │ ...
        └──────────────────────────────────────
    """
    width = PANE_LOG_REPLAY_COLS
    border_top = "┌─ session history replay"
    border_bot = "└" + "─" * (width - 1)
    # Fold long lines so the block stays within `width` columns.
    # Using `fold -s` would split on whitespace; we use `-w` (chunks) for
    # predictability.
    try:
        folded = subprocess.run(
            ["fold", "-w", str(width - 4), "-s"],
            input=text, capture_output=True, text=True, check=False,
        ).stdout
    except (FileNotFoundError, OSError):
        folded = text

    prefix = "│ "
    out_lines = [border_top]
    for line in folded.splitlines():
        out_lines.append(prefix + line)
    out_lines.append(border_bot)
    return "\n".join(out_lines) + "\n"


def ghostty_resume():
    """Dispatch every pane to its own `open -na Ghostty.app` window.

    Slice 7 failure-mode hardening: this is a two-pass, all-or-nothing
    per-pane dispatch.

    Pass 1 — pre-validation.  Walk every row, classify it
      - ``skip``      → build_cmd returned None (harness unknown, no sid)
      - ``preserve``  → --no-fork + already running (no spawn)
      - ``dispatch``  → would spawn ``open -na Ghostty.app``
      - ``abort``     → cwd missing / unreadable → fatal precondition
    A single ``abort`` row aborts the batch *before* any spawn so we
    never partial-dispatch against a broken working directory.

    Pass 2 — dispatch.  For each ``dispatch`` row, call ``_ghostty_open``
    which now synchronously waits for ``open`` to exit (or 2s timeout).
    On a non-zero returncode we set ``dispatch_aborted=True`` and stop
    further spawns.  Already-spawned panes are NOT rolled back (we
    cannot unsend ``open -na``), but the audit log records exactly
    which pane failed so the operator can kill the half-launched set
    by hand if needed.

    Every outcome (``skipped``, ``preserved``, ``restored``, ``errored``,
    ``dry_run``) writes one JSONL row to ``AUDIT_LOG`` so the dispatch
    history is reconstructable after the fact.
    """
    restored = 0
    skipped = 0
    preserved = 0  # --no-fork counter: harness already running, dispatch skipped.
    err_rows = 0

    # ---- Pass 1: classify every row, pre-validate fatal preconditions ----
    plan: list[tuple[str, dict, str | None, str | None, str]] = []
    # schema: (pane_id, row, cmd|None, label, fatal_or_None)
    fatal: list[tuple[str, str, str]] = []  # (pane_id, reason, cwd)
    # by_pane is pre-filtered upstream by the --only=<bookmark> block.
    for pane_id, r in sorted(by_pane.items(), key=lambda kv: kv[1].get("cwd", "")):
        cmd = build_cmd(r["harness"], r["session_id"], r["cwd"])
        if not cmd:
            skipped += 1
            _audit_log(
                "skipped", harness=r.get("harness", ""), pane_id=pane_id,
                cwd=r.get("cwd", ""), sid=r.get("session_id", ""),
                detail="build_cmd-returned-none",
            )
            continue
        # Fatal precondition: cwd must exist.  Otherwise `open -na` will
        # ghost-launch a window and then the shell will fail with
        # "no such file or directory" — the user sees a terminal they
        # didn't ask for.  We treat this as a batch-level abort.
        cwd = r.get("cwd", "")
        if not cwd or not os.path.isdir(cwd):
            fatal.append((pane_id, r.get("harness", ""), cwd))
            _audit_log(
                "errored", harness=r.get("harness", ""), pane_id=pane_id,
                cwd=cwd, sid=r.get("session_id", ""),
                detail=f"precondition-failed:cwd-not-directory",
            )
            continue
        label = f"{r['harness']} / {r.get('session_id', '')[:8]}"
        plan.append((pane_id, r, cmd, label, None))

    if fatal:
        details = ", ".join(f"{h}:{p}({c})" for p, h, c in fatal)
        print(
            f"resume-all: aborting batch — fatal precondition(s) "
            f"on {len(fatal)} pane(s): {details}",
            file=sys.stderr,
        )
        _audit_log(
            "aborted", cwd=os.getcwd(),
            detail=f"fatal-precondition:{len(fatal)}-pane(s)",
        )
        sys.exit(1)

    # ---- Pass 2: dispatch in cwd-sorted order, abort on first launch fail ----
    dispatch_aborted = False
    for pane_id, r, cmd, label, _ in plan:
        # Build replay block (if --replay-history is set and a fresh log exists).
        replay_block = None
        replay_pane_id = ""
        if replay_history:
            tty = r.get("tty", "")
            raw = _read_replay_lines(tty)
            if raw is not None:
                replay_block = _format_replay_block(raw, pane_id)
                replay_pane_id = pane_id

        # --no-fork guard: if the harness is already running locally for this
        # row, skip the open -na spawn and count it as preserved.  The core
        # launcher (open -na Ghostty.app) below is intentionally NOT changed.
        if no_fork and _is_already_running(r):
            preserved += 1
            _audit_log(
                "preserved", harness=r.get("harness", ""), pane_id=pane_id,
                cwd=r.get("cwd", ""), sid=r.get("session_id", ""),
                detail="no-fork-already-running",
            )
            if dry_run:
                print(f"# no-fork: {label} preserved (harness already running)")
            continue

        if dispatch_aborted:
            # A previous pane failed; do not dispatch any more.
            _audit_log(
                "skipped", harness=r.get("harness", ""), pane_id=pane_id,
                cwd=r.get("cwd", ""), sid=r.get("session_id", ""),
                detail="dispatch-aborted-by-prior-failure",
            )
            err_rows += 1
            continue

        if _ghostty_open(
            r["cwd"], cmd, only_filter, dry_run, label,
            replay_lines=replay_block, pane_id_for_log=replay_pane_id,
            pane_id=pane_id, harness=r.get("harness", ""),
            sid=r.get("session_id", ""),
        ):
            restored += 1
            if dry_run:
                # Dry-run is a preview only — never write a real "restored"
                # audit row, so the audit log only reflects actual dispatches.
                print(f"# would restore: {cmd}  # pane={pane_id}")
            else:
                _audit_log(
                    "restored",
                    harness=r.get("harness", ""), pane_id=pane_id,
                    cwd=r.get("cwd", ""), sid=r.get("session_id", ""),
                    detail="open-na-success",
                )
        else:
            dispatch_aborted = True
            err_rows += 1
            # _ghostty_open already logged "errored" with the reason.
            # We log the batch-level abort here.
            _audit_log(
                "aborted", cwd=os.getcwd(),
                detail=f"dispatch-aborted-after-pane:{pane_id}",
            )
            print(
                f"resume-all: aborting batch — launch failed on pane "
                f"{pane_id} ({r.get('harness', '')}); "
                f"already-spawned {restored} window(s) will not be rolled back",
                file=sys.stderr,
            )

    global _restored_total
    # Only count actually-dispatched panes; "preserved" panes (--no-fork)
    # were already running before resume-all, so they don't represent a
    # fresh restoration event.
    _restored_total += restored

    if dispatch_aborted:
        # Slice 7 contract: launch failure is a non-zero exit so the
        # launchd timer / cron driver can detect the partial state and
        # alert the operator.
        print(
            f"resume-all: {restored} session(s) restored, "
            f"{err_rows} errored (batch aborted)",
            file=sys.stderr,
        )
        sys.exit(1)

    if restored == 0 and preserved == 0:
        print(f"resume-all: nothing to restore (skipped {skipped}, snapshot: {snapshot_path})")
        return

    msg = (
        f"resume-all: {restored} session(s) {'would be' if dry_run else 'were'} "
        f"restored (backend: open -na, snapshot: {snapshot_path})"
    )
    if preserved:
        msg += f", {preserved} preserved (--no-fork)"
    if dry_run:
        print(f"# {msg}")
    else:
        print(msg)

if dry_run:
    # In dry-run we do NOT actually invoke the backend. Print a
    # preview summary, then fall through to the exit-code block at
    # the bottom which decides rc=0/1/2. This is what makes the
    # `rc=2 = backend unavailable` path work cleanly: without this
    # guard, tmux_resume() / ghostty_resume() / zmx_resume() would
    # shell out to the (missing) binary and crash with
    # FileNotFoundError before we ever reached the availability
    # check.
    n_panes = len(by_pane)
    print(f"# resume-all --dry-run: would dispatch {n_panes} pane(s) "
          f"via backend={backend!r}, snapshot={snapshot_path}")
elif backend == "tmux":
    tmux_resume()
elif backend == "ghostty":
    ghostty_resume()
elif backend == "zmx":
    pass  # zmx_resume handles everything below
else:
    print(f"resume-all: unknown backend '{backend}'", file=sys.stderr)
    sys.exit(2)

# Always dispatch zmx-backed panes regardless of main backend.
# zmx panes were split out on lines 49-55 and stored in zmx_panes,
# but zmx_resume() was only reachable when backend=="zmx". This
# patch ensures they get dispatched on any backend. Skipped in
# dry-run so a missing `zmx` binary never crashes the preview.
if zmx_panes and not dry_run:
    zmx_resume()

# ----------------------------------------------------------------------------
# Dry-run exit-code contract (Slice 7).
#
#   0 = dispatchable (snapshot parsed cleanly AND backend is available)
#   1 = JSONL parse error (≥1 row could not be decoded)
#   2 = backend unavailable (binary missing, no Ghostty .app, etc.)
#
# Replaces the previous "2 = no Ghostty/tmux" free-form exit code, which
# conflated "no backend" with "snapshot could not be read".
# ----------------------------------------------------------------------------
if dry_run:
    if _jsonl_parse_errors > 0:
        sys.exit(1)
    if not _backend_available(backend):
        sys.exit(2)
    sys.exit(0)

# Slice 6: emit a single "restored N sessions" notification to the ShareCLI
# Tray when restore actually dispatched at least one session. Dry-run is
# excluded on purpose so preview runs don't spam the tray.
# notify failures are non-fatal; we just log and continue.
if not dry_run and _restored_total > 0 and _sharecli_ipc is not None:
    try:
        _notify_summary = _sharecli_ipc.sharecli_notify(
            _restored_total, source="resume-all",
        )
    except Exception as _sharecli_err:  # pragma: no cover — defensive
        _notify_summary = {"error": f"{type(_sharecli_err).__name__}: {_sharecli_err}"}
        print(
            f"resume-all: sharecli_notify raised "
            f"({type(_sharecli_err).__name__}: {_sharecli_err})",
            file=sys.stderr,
        )
    if isinstance(_notify_summary, dict):
        if _notify_summary.get("delivered"):
            print(
                f"resume-all: sharecli notify delivered "
                f"(pathway={_notify_summary.get('pathway')}, "
                f"count={_restored_total})",
                file=sys.stderr,
            )
        else:
            print(
                f"resume-all: sharecli notify not delivered "
                f"(pathway={_notify_summary.get('pathway') or 'none'}, "
                f"error={_notify_summary.get('error')})",
                file=sys.stderr,
            )
