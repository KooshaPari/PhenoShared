#!/usr/bin/env python3
"""
airlock-v2 auto-commit daemon.

Periodically (every 15 minutes) walks ~/CodeProjects/Phenotype/repos/ for git
working trees with a dirty index and creates a `wip/<YYYY-MM-DD-HHMM>-auto`
branch with the staged work, pushing to upstream when available.

Design goals:
  * Idempotent — re-running on a clean tree is a no-op.
  * Re-entrant — only one instance at a time via fcntl lockfile.
  * Conservative — never deletes branches or force-pushes.
  * Aggressive — commits dirty work so it can never be lost.
  * Graceful shutdown on SIGTERM / SIGINT.
  * Logs to ~/.airlock-v2/logs/auto-commit.log with structured fields.
  * Skips a repo if the airlock v1 daemon is busy (socket present but
    unresponsive to a quick health probe).
  * Skips worktrees that are themselves checked out as a branch already
    named wip/* (avoids branch-name collisions across worktrees).

Invocation:
  python3 auto-commit-daemon.py             # run once and exit (smoke test)
  python3 auto-commit-daemon.py --loop     # run forever on 15min timer
  python3 auto-commit-daemon.py --once     # explicit single-pass

Exit codes:
  0 : clean run (including no-op when nothing is dirty)
  1 : configuration error (missing repo root, etc.)
  2 : operational error (one or more repos errored but others succeeded)
"""
from __future__ import annotations

import argparse
import errno
import fcntl
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

# ---------- config ----------
REPO_ROOT = Path(os.environ.get(
    "AIRLOCK_V2_ROOT",
    os.path.expanduser("~/CodeProjects/Phenotype/repos"),
))
LOG_DIR = Path(os.environ.get(
    "AIRLOCK_V2_LOG_DIR",
    os.path.expanduser("~/.airlock-v2/logs"),
))
LOCK_PATH = Path(os.environ.get(
    "AIRLOCK_V2_LOCK_PATH",
    "/tmp/airlock-v2.auto-commit.lock",
))
INTERVAL_SECONDS = int(os.environ.get("AIRLOCK_V2_INTERVAL", "900"))  # 15 minutes
HEALTH_PROBE_TIMEOUT = 2  # seconds
PER_REPO_TIMEOUT = 45     # seconds per repo
DRY_RUN = os.environ.get("AIRLOCK_V2_DRY_RUN", "0") == "1"
AUTHOR_NAME = f"airlock-v2 [auto-commit]"
AUTHOR_EMAIL_FMT = "airlock-v2-auto@{hostname}.local"

# The legacy airlock daemon owns a socket at ~/.airlock/socket. We probe it
# before sweeping so we don't pile on if it's already busy. The path can be
# overridden (e.g. by the smoke test, which points at a non-existent path so
# the busy check always reports "not busy").
AIRLOCK_SOCKET_PATH = Path(os.environ.get(
    "AIRLOCK_V2_AIRLOCK_SOCKET",
    os.path.expanduser("~/.airlock/socket"),
))

# Containers/manifests that are NOT individual repos and should be skipped
# wholesale. The container policy is "do not treat repos/ as a git worktree";
# we honor that here.
SKIP_TOP_LEVEL_PATHS = {
    ".research-airlock-daemon-2026-07-15.md",
    ".research-agent-integration-2026-07-15.md",
    "AGENTS.md",
    "01-AUTH-TRIAGE.md",
    "02-ORG-AUDITS-PLAN.md",
    "03-APPS-PLAN.md",
    "04-ARCHIVE-PLAN.md",
    "05-MIGRATION-CHECKLIST.md",
    "06-RISKS-AND-OPEN-QUESTIONS.md",
    "PHENOTYPE_DOGFOOD_COMPLIANCE_AUDIT.md",
    "PHENOTYPE_GOVERNANCE.md",
    "PILLAR-TAXONOMY-v2.md",
    "POLYREPO.md",
    "bun.lock",
    "Makefile",
    "Taskfile.yml",
    "compute-infra-audit-comparison.json",
    "cost-verbosity-index.html",
    "BytePort-audit.json",
    "MelosViz-audit.json",
    "PhenoCompose-audit.json",
    "pheno-audit.json",
    "nanovms-audit.json",
    "omniroute-rust-audit.json",
    "semcheck.yaml",
    "uv.lock",
    "go.mod",
    "pyproject.toml",
    "VoxelWriteProxy",
}


# ---------- logging ----------
class Logger:
    """Structured single-line-per-event logger."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def _emit(self, level: str, msg: str, **fields) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        record = {
            "ts": ts,
            "level": level,
            "pid": os.getpid(),
            "msg": msg,
            **fields,
        }
        line = json.dumps(record, sort_keys=True)
        try:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            # Falling back to stderr so the daemon's loop never silently loses log lines.
            print(line, file=sys.stderr)

    def info(self, msg: str, **fields) -> None:
        self._emit("info", msg, **fields)

    def warn(self, msg: str, **fields) -> None:
        self._emit("warn", msg, **fields)

    def error(self, msg: str, **fields) -> None:
        self._emit("error", msg, **fields)


# ---------- subprocess wrappers ----------
@dataclass
class CmdResult:
    stdout: str
    stderr: str
    returncode: int


def run_git(repo: Path, *args: str, timeout: int = PER_REPO_TIMEOUT) -> CmdResult:
    """Run a git command in `repo`. Never raises — returns CmdResult."""
    try:
        cp = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return CmdResult(
            stdout=cp.stdout or "",
            stderr=cp.stderr or "",
            returncode=cp.returncode,
        )
    except subprocess.TimeoutExpired:
        return CmdResult(stdout="", stderr=f"timeout after {timeout}s", returncode=124)
    except FileNotFoundError:
        return CmdResult(stdout="", stderr="git not on PATH", returncode=127)


# ---------- airlock daemon health probe ----------
def airlock_daemon_busy() -> bool:
    """Best-effort probe: returns True only if the daemon socket is present
    but unresponsive to a quick health probe (i.e. busy). A missing or
    responsive daemon means we should proceed."""
    socket_path = AIRLOCK_SOCKET_PATH
    if not socket_path.exists():
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(HEALTH_PROBE_TIMEOUT)
            s.connect(str(socket_path))
            s.sendall(b'{"jsonrpc":"2.0","method":"health","id":1}\n')
            data = s.recv(4096)
            return b'"healthy":false' in data or b'"error"' in data
    except (socket.timeout, OSError):
        # The daemon is wedged or the kernel can't reach it — treat as busy
        # so we don't pile on.
        return True


# ---------- repo discovery ----------
def find_dirty_repos(root: Path) -> Iterable[Path]:
    """Yield git working trees under `root` that have a non-empty porcelain
    status. Does NOT recurse into bare mirrors."""
    if not root.is_dir():
        return
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if entry.name.startswith("."):
            # Hidden directories (other than .git) — skip entirely.
            continue
        if entry.name in SKIP_TOP_LEVEL_PATHS:
            continue
        if entry.is_dir():
            yield from _scan(entry)


def _scan(path: Path) -> Iterable[Path]:
    """Recurse but bail out as soon as we find a git dir."""
    # Honor the container policy: don't treat child worktrees as new repos.
    if (path / ".git").exists() and (path / ".git").is_dir():
        yield path
        return
    for entry in path.iterdir():
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            yield from _scan(entry)


# ---------- per-repo work ----------
@dataclass
class RepoResult:
    path: str
    status: str  # "skipped-clean" | "committed" | "skipped-busy" | "error" | "skipped-no-upstream-prefer"
    branch: Optional[str] = None
    sha: Optional[str] = None
    error: Optional[str] = None
    elapsed_ms: int = 0


def process_repo(repo: Path, log: Logger, hostname: str) -> RepoResult:
    start = time.monotonic()

    # Confirm it's still a working tree (might have been removed mid-walk).
    toplevel = run_git(repo, "rev-parse", "--show-toplevel")
    if toplevel.returncode != 0:
        return RepoResult(path=str(repo), status="error", error="not a git worktree")

    # Skip repos currently sitting on wip/* as their checked-out branch —
    # these are likely already in-flight or recently auto-saved. Re-branching
    # off them can create piles of nested wip branches.
    current_branch = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if current_branch.returncode == 0 and current_branch.stdout.strip().startswith("wip/"):
        return RepoResult(
            path=str(repo),
            status="skipped-clean",
            error="already on a wip/* branch; hook will handle it",
        )

    # Stage everything. Capture status to know if anything new arrived.
    add = run_git(repo, "add", "-A")
    if add.returncode != 0:
        return RepoResult(path=str(repo), status="error", error=f"git add -A failed: {add.stderr.strip()}")

    status = run_git(repo, "status", "--porcelain")
    if status.returncode != 0 or not status.stdout.strip():
        # Tree is clean — this is the steady state for most repos every cycle.
        return RepoResult(path=str(repo), status="skipped-clean")

    # Branch name: wip/YYYY-MM-DD-HHMM-auto
    ts_tag = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    branch = f"wip/{ts_tag}-auto"

    if DRY_RUN:
        return RepoResult(path=str(repo), status="committed", branch=branch)

    # Create or check out the branch (idempotent).
    sw = run_git(repo, "switch", "-c", branch)
    if sw.returncode != 0:
        # Probably already exists from a prior failed run.
        sw2 = run_git(repo, "switch", branch)
        if sw2.returncode != 0:
            return RepoResult(
                path=str(repo),
                status="error",
                error=f"could not switch to {branch}: {sw2.stderr.strip()}",
            )

    author_email = AUTHOR_EMAIL_FMT.format(hostname=hostname)
    body = (
        "airlock-v2 auto-commit (15min sweep)\n"
        "\n"
        f"agent:    auto-commit-daemon\n"
        f"repo:     {repo}\n"
        f"hostname: {hostname}\n"
        f"branch:   {branch}\n"
        f"created:  {datetime.now(timezone.utc).isoformat()}\n"
        "\n"
        "Background checkpoint created by auto-commit-daemon. The cleanup\n"
        "daemon will consolidate multiple wip/* into a single consolidated\n"
        "branch every 8 hours.\n"
        "\n"
        "[wip-managed]\n"
    )

    commit = subprocess.run(
        [
            "git",
            "-C", str(repo),
            "-c", f"user.name={AUTHOR_NAME}",
            "-c", f"user.email={author_email}",
            "commit", "--allow-empty", "-m", body,
        ],
        capture_output=True,
        text=True,
        timeout=PER_REPO_TIMEOUT,
        check=False,
    )
    if commit.returncode != 0:
        return RepoResult(
            path=str(repo),
            status="error",
            error=f"git commit failed: {commit.stderr.strip()}",
        )

    sha = run_git(repo, "rev-parse", "HEAD").stdout.strip()

    # Push (best-effort).
    push = run_git(repo, "push", "origin", f"{branch}:{branch}", timeout=PER_REPO_TIMEOUT)
    push_ok = push.returncode == 0 or (
        "already up" in push.stderr.lower() or "already up" in push.stdout.lower()
    )

    elapsed_ms = int((time.monotonic() - start) * 1000)
    return RepoResult(
        path=str(repo),
        status="committed" if push_ok else "committed-local-only",
        branch=branch,
        sha=sha,
        elapsed_ms=elapsed_ms,
    )


def sweep_once(log: Logger, hostname: str) -> list[RepoResult]:
    log.info("sweep_start", interval_seconds=INTERVAL_SECONDS)
    if airlock_daemon_busy():
        log.warn("sweep_skipped", reason="airlock-daemon-busy")
        return []

    results: list[RepoResult] = []
    for repo in find_dirty_repos(REPO_ROOT):
        try:
            r = process_repo(repo, log, hostname)
        except Exception as exc:  # noqa: BLE001 — logged, never re-raised
            log.error("repo_unhandled_exception", repo=str(repo), error=str(exc))
            continue
        results.append(r)
        if r.status.startswith("error"):
            log.error("repo_error", **r.__dict__)
        elif r.status == "committed":
            log.info("repo_committed", **r.__dict__)
        elif r.status == "committed-local-only":
            log.warn("repo_local_only", **r.__dict__)
        else:
            log.info("repo_skipped", **r.__dict__)

    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    log.info("sweep_done", **counts, total=len(results))
    return results


# ---------- single-instance lock ----------
class SingleInstance:
    """fcntl-based re-entrancy guard."""

    def __init__(self, path: Path):
        self.path = path
        self.fd: Optional[int] = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                os.close(self.fd)
                self.fd = None
                return False
            raise
        os.write(self.fd, f"{os.getpid()}\n".encode())
        return True

    def release(self) -> None:
        if self.fd is None:
            return
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
            self.fd = None


# ---------- signal handling ----------
_shutdown = False


def _handle_signal(signum, frame):  # noqa: ARG001
    global _shutdown
    _shutdown = True


# ---------- main ----------
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loop", action="store_true",
                        help="run forever on the configured interval")
    parser.add_argument("--once", action="store_true",
                        help="(default) run a single sweep and exit")
    args = parser.parse_args(argv)

    if not REPO_ROOT.is_dir():
        print(f"fatal: REPO_ROOT does not exist: {REPO_ROOT}", file=sys.stderr)
        return 1

    log = Logger(LOG_DIR / "auto-commit.log")
    hostname = socket.gethostname()

    sig = SingleInstance(LOCK_PATH)
    if not sig.acquire():
        log.warn("another_instance_already_running", lock=str(LOCK_PATH))
        return 0  # Treat as benign — the other instance is doing the work.

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGHUP, _handle_signal)

    try:
        log.info("daemon_started", interval_seconds=INTERVAL_SECONDS,
                 repo_root=str(REPO_ROOT), loop=bool(args.loop), dry_run=DRY_RUN)

        if not args.loop:
            results = sweep_once(log, hostname)
            errored = sum(1 for r in results if r.status.startswith("error"))
            return 0 if errored == 0 else 2

        # Loop mode.
        next_run = time.monotonic()
        while not _shutdown:
            sleep_for = max(1.0, next_run - time.monotonic())
            # Sleep in small chunks so SIGTERM is responsive.
            while sleep_for > 0 and not _shutdown:
                chunk = min(sleep_for, 5.0)
                time.sleep(chunk)
                sleep_for -= chunk
            if _shutdown:
                break
            try:
                sweep_once(log, hostname)
            except Exception as exc:  # noqa: BLE001
                log.error("sweep_unhandled_exception", error=str(exc))
            next_run = time.monotonic() + INTERVAL_SECONDS

        log.info("daemon_shutdown", reason="signal")
        return 0
    finally:
        sig.release()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
