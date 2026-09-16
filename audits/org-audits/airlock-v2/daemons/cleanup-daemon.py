#!/usr/bin/env python3
"""
airlock-v2 cleanup daemon.

Runs every 8 hours and:
  1. For every git working tree under ~/CodeProjects/Phenotype/repos/:
     a. Gather all `wip/*` branches (locally and on origin).
     b. Find the most recent consolidated branch (the head of any
        `wip/*-consolidated` branch on origin). If one exists, base the new
        consolidation on its tip; otherwise base on the current default branch.
     c. Create a NEW branch `wip/<YYYY-MM-DD-HHMM>-consolidated` on top of the
        base; for each wip/* branch (in chronological order), cherry-pick or
        merge it. We prefer merge (--no-ff) because it preserves the chain of
        intermediate states and is far more robust against cross-branch
        conflicts than cherry-pick. We fall back to squash-only when the wip
        branches have no mergeable history (rare; happens with bare-init
        restores).
     d. Force-push (with --force-with-lease) the consolidated branch to
        upstream. Per spec: "force-pushes to remote" of the consolidated
        branch. Force-with-lease prevents the worst race (clobbering an
        external commit) and is widely considered safer than --force.
     e. After the consolidated branch is verified on origin (via
        `git ls-remote`), delete the source `wip/*` branches locally AND
        on origin. SAFETY: this only happens if the consolidated branch is
        verified to contain every source wip branch's tip (otherwise we
        leave the source branches untouched and log a warning).

  2. Walk `~/.airlock/repos/` looking for entries with `current_stage='stale'`
     or `created_at` older than 30 days. For each:
     a. tar.zst the bare-mirror subtree to
        `~/CodeProjects/Phenotype/repos/_phenofleet-decisions/airlock-cleanup/<id>.tar.zst`
        with a sidecar `<id>.sha256` containing the digest.
     b. leave the airlock entry untouched but log that it has been archived.
     c. SAFETY: we do NOT delete the original airlock entry. Only mark it in
        our local log so the next phase can decide. We do NOT call back into
        the daemon for deletion — that's a separate, human-approved step.

Design goals:
  * Idempotent — re-running on a clean tree is a no-op.
  * Re-entrant — only one instance at a time via fcntl lockfile.
  * Conservative — any delete operation is gated on a remote-confirmed backup.
  * Aggressive — consolidates every wip/* cluster into a single tracked branch.
  * Graceful shutdown on SIGTERM / SIGINT.
  * Logs to ~/.airlock-v2/logs/cleanup.log with structured fields.
"""
from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
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
    "/tmp/airlock-v2.cleanup.lock",
))
ARCHIVE_DIR = REPO_ROOT / "_phenofleet-decisions" / "airlock-cleanup"
AIRLOCK_DB = Path(os.path.expanduser("~/.airlock/state.sqlite"))
AIRLOCK_REPOS_DIR = Path(os.path.expanduser("~/.airlock/repos"))
STALE_AGE_DAYS = int(os.environ.get("AIRLOCK_V2_STALE_DAYS", "30"))
ARCHIVE_AGE_DAYS = int(os.environ.get("AIRLOCK_V2_ARCHIVE_DAYS", "30"))
PER_REPO_TIMEOUT = 120  # cleanup is heavier than auto-commit
DRY_RUN = os.environ.get("AIRLOCK_V2_DRY_RUN", "0") == "1"
CONSOLIDATE_BRANCH_RE = re.compile(r"^wip/(\d{4}-\d{2}-\d{2}(?:-\d{4})?-)(?:.*-)?consolidated$")
WIP_BRANCH_RE = re.compile(r"^wip/")


# ---------- logging ----------
class Logger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def _emit(self, level: str, msg: str, **fields) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        record = {"ts": ts, "level": level, "pid": os.getpid(), "msg": msg, **fields}
        line = json.dumps(record, sort_keys=True)
        try:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            print(line, file=sys.stderr)

    def info(self, msg: str, **fields) -> None:  self._emit("info", msg, **fields)
    def warn(self, msg: str, **fields) -> None:  self._emit("warn", msg, **fields)
    def error(self, msg: str, **fields) -> None: self._emit("error", msg, **fields)


# ---------- subprocess wrapper ----------
@dataclass
class CmdResult:
    stdout: str
    stderr: str
    returncode: int


def run_git(repo: Path, *args: str, timeout: int = PER_REPO_TIMEOUT) -> CmdResult:
    try:
        cp = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return CmdResult(stdout=cp.stdout or "", stderr=cp.stderr or "", returncode=cp.returncode)
    except subprocess.TimeoutExpired:
        return CmdResult(stdout="", stderr=f"timeout after {timeout}s", returncode=124)
    except FileNotFoundError:
        return CmdResult(stdout="", stderr="git not on PATH", returncode=127)


# ---------- repo discovery ----------
def find_repos(root: Path) -> Iterable[Path]:
    """All git working trees (not bare) under `root`, recursing only into
    directories that don't already contain a .git."""
    if not root.is_dir():
        return

    # Honor container policy: skip top-level files/dirs that are not repos.
    SKIP_TOP = {
        ".research-airlock-daemon-2026-07-15.md",
        ".research-agent-integration-2026-07-15.md",
        "AGENTS.md",
        "BytePort-audit.json",
        "Makefile",
        "MelosViz-audit.json",
        "PHENOTYPE_DOGFOOD_COMPLIANCE_AUDIT.md",
        "PHENOTYPE_GOVERNANCE.md",
        "PILLAR-TAXONOMY-v2.md",
        "POLYREPO.md",
        "PhenoCompose-audit.json",
        "Taskfile.yml",
        "VoxelWriteProxy",
        "bun.lock",
        "compute-infra-audit-comparison.json",
        "cost-verbosity-index.html",
        "go.mod",
        "nanovms-audit.json",
        "omniroute-rust-audit.json",
        "pheno-audit.json",
        "pyproject.toml",
        "semcheck.yaml",
        "uv.lock",
        "_archive",
        "_cockpit",
        "_inbox",
        "_loose-inbox",
        "_phenofleet-decisions",
        "_session_preserved",
        "~",
        "{",
    }

    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if entry.name.startswith(".") and entry.name != ".git":
            continue
        if entry.name in SKIP_TOP:
            continue
        if entry.is_dir():
            yield from _scan(entry)


def _scan(path: Path) -> Iterable[Path]:
    if (path / ".git").is_dir():
        yield path
        return
    for entry in path.iterdir():
        if entry.name.startswith(".") and entry.name != ".git":
            continue
        if entry.is_dir():
            yield from _scan(entry)


# ---------- wip consolidation ----------
@dataclass
class ConsolidationResult:
    repo: str
    status: str  # "consolidated" | "skipped-clean" | "skipped-no-wip" | "error" | "skipped-no-upstream" | "partial"
    source_branches: list[str]
    consolidated_branch: Optional[str] = None
    remote_verified: bool = False
    deleted_count: int = 0
    skipped_delete_count: int = 0
    error: Optional[str] = None


def list_wip_branches(repo: Path) -> list[str]:
    """All wip/* branches present locally AND on origin (deduped)."""
    local = run_git(repo, "for-each-ref", "--format=%(refname:short)",
                    "refs/heads/wip/")
    origin = run_git(repo, "for-each-ref", "--format=%(refname:short)",
                     "refs/remotes/origin/wip/")
    names = set()
    for out in (local.stdout, origin.stdout):
        for ln in out.splitlines():
            n = ln.strip()
            if n.startswith("wip/"):
                # Strip the "origin/" prefix that git adds for remote-tracking.
                names.add(n.removeprefix("origin/"))
    # Exclude the most recent consolidated branch (we want only wip/*-auto
    # and wip/*-agent-event_id branches as input).
    return sorted(n for n in names if not CONSOLIDATE_BRANCH_RE.match(n))


def list_consolidated_branches(repo: Path) -> list[str]:
    """All wip/*-consolidated branches on origin (newest-first)."""
    out = run_git(repo, "for-each-ref", "--format=%(refname:short)",
                  "refs/remotes/origin/wip/")
    names = []
    for ln in out.stdout.splitlines():
        n = ln.strip().removeprefix("origin/")
        if CONSOLIDATE_BRANCH_RE.match(n):
            names.append(n)
    return sorted(names, reverse=True)


def find_default_branch(repo: Path) -> Optional[str]:
    """Best-effort: HEAD → upstream/HEAD → 'main' → 'master'."""
    head = run_git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if head.returncode == 0 and head.stdout.strip():
        ref = head.stdout.strip().removeprefix("origin/")
        if ref:
            return ref
    for cand in ("main", "master", "develop", "trunk"):
        chk = run_git(repo, "rev-parse", "--verify", f"refs/remotes/origin/{cand}")
        if chk.returncode == 0:
            return cand
    return None


def merge_wip_branches(repo: Path, branch: str, sources: list[str], base: str, log: Logger) -> tuple[bool, str]:
    """Create `branch` on top of `base` and merge each source in order.
    Returns (success, error_message)."""
    # Create the branch off the base.
    co = run_git(repo, "switch", "-c", branch, base)
    if co.returncode != 0:
        # Already exists from a prior failed run — switch to it.
        co2 = run_git(repo, "switch", branch)
        if co2.returncode != 0:
            return False, f"could not create/switch to {branch}: {co2.stderr.strip()}"
    for src in sources:
        merge = subprocess.run(
            [
                "git", "-C", str(repo),
                "merge", "--no-ff", "--no-edit",
                "-m", f"airlock-v2 cleanup: merge {src} into {branch}",
                f"origin/{src}" if "/" not in src else src,
            ],
            capture_output=True,
            text=True,
            timeout=PER_REPO_TIMEOUT,
            check=False,
        )
        if merge.returncode != 0 and merge.returncode != 1:
            # 0 = clean, 1 = conflict resolved or already merged; any other is fatal.
            return False, f"merge of {src} failed (rc={merge.returncode}): {merge.stderr.strip()}"
        # If a real conflict, abort the merge and continue with the others using --allow-unrelated-histories.
        if merge.returncode != 0 and "CONFLICT" in merge.stdout + merge.stderr:
            abort = run_git(repo, "merge", "--abort")
            log.warn("merge_conflict_retrying", source=src,
                     abort_ok=(abort.returncode == 0))
            # Squash import as fallback.
            sq = subprocess.run(
                [
                    "git", "-C", str(repo),
                    "merge", "--squash", f"origin/{src}" if "/" not in src else src,
                ],
                capture_output=True,
                text=True,
                timeout=PER_REPO_TIMEOUT,
                check=False,
            )
            if sq.returncode != 0:
                run_git(repo, "merge", "--abort")
                return False, f"squash import of {src} failed: {sq.stderr.strip()}"
            # Commit the squash manually.
            subprocess.run(
                [
                    "git", "-C", str(repo),
                    "commit",
                    "--no-edit",
                    "-m", f"airlock-v2 cleanup: import {src} (squash)",
                ],
                capture_output=True, text=True, timeout=PER_REPO_TIMEOUT, check=False,
            )
    return True, ""


def consolidate_repo(repo: Path, log: Logger, hostname: str) -> ConsolidationResult:
    sources = list_wip_branches(repo)
    if not sources:
        return ConsolidationResult(repo=str(repo), status="skipped-no-wip", source_branches=[])

    # Refuse to operate on a repo with no remote — we cannot verify the
    # consolidated branch made it anywhere.
    rev_remote = run_git(repo, "remote")
    if "origin" not in rev_remote.stdout.split():
        return ConsolidationResult(
            repo=str(repo), status="skipped-no-upstream",
            source_branches=sources,
            error="no origin remote configured; cannot verify backup",
        )

    # Pick a base: most recent *pushed* consolidated branch, else default branch.
    consolidated = list_consolidated_branches(repo)
    base_branch = consolidated[0] if consolidated else find_default_branch(repo)
    if base_branch is None:
        return ConsolidationResult(
            repo=str(repo), status="error", source_branches=sources,
            error="no default branch found on origin",
        )
    # Resolve to a concrete SHA.
    base_sha = run_git(repo, "rev-parse", "--verify", f"origin/{base_branch}").stdout.strip()
    if not base_sha:
        return ConsolidationResult(
            repo=str(repo), status="error", source_branches=sources,
            error=f"base {base_branch} does not resolve on origin",
        )

    ts_tag = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    new_branch = f"wip/{ts_tag}-consolidated"

    if DRY_RUN:
        log.info("cleanup_dry_run", repo=str(repo), source_count=len(sources),
                 target=new_branch, base=base_branch)
        return ConsolidationResult(
            repo=str(repo), status="consolidated", source_branches=sources,
            consolidated_branch=new_branch,
        )

    # Fetch latest refs first so we know what's on origin.
    fetch = run_git(repo, "fetch", "origin", "--prune", timeout=PER_REPO_TIMEOUT)
    if fetch.returncode != 0:
        log.warn("fetch_failed", repo=str(repo), stderr=fetch.stderr.strip())

    # Stash any in-progress work so we can checkout safely.
    has_stash = False
    status = run_git(repo, "status", "--porcelain")
    if status.stdout.strip():
        stash = run_git(repo, "stash", "push", "-u", "-m", "airlock-v2-cleanup-temp")
        has_stash = stash.returncode == 0

    try:
        ok, err = merge_wip_branches(repo, new_branch, sources, f"origin/{base_branch}", log)
        if not ok:
            return ConsolidationResult(
                repo=str(repo), status="error", source_branches=sources,
                error=err,
            )

        # Force-push with --force-with-lease.
        push = subprocess.run(
            [
                "git", "-C", str(repo),
                "push", "--force-with-lease", "origin",
                f"{new_branch}:{new_branch}",
            ],
            capture_output=True,
            text=True,
            timeout=PER_REPO_TIMEOUT,
            check=False,
        )
        if push.returncode != 0:
            return ConsolidationResult(
                repo=str(repo), status="partial", source_branches=sources,
                consolidated_branch=new_branch,
                error=f"force-push failed: {push.stderr.strip()}",
            )

        # Verify on origin (ls-remote returns the SHA we expect).
        new_sha = run_git(repo, "rev-parse", "HEAD").stdout.strip()
        verify = run_git(repo, "ls-remote", "--heads", "origin", new_branch)
        remote_verified = new_sha in verify.stdout

        # SAFETY: only delete source branches if the consolidated branch is
        # verified on origin. Otherwise, leave them in place and report.
        deleted: list[str] = []
        skipped: list[str] = []
        if remote_verified:
            for src in sources:
                # Locally: only delete if the consolidated branch contains
                # the source tip (belt-and-braces check).
                src_sha = run_git(repo, "rev-parse", f"origin/{src}").stdout.strip()
                contained = run_git(
                    repo, "merge-base", "--is-ancestor", src_sha, "HEAD",
                )
                if contained.returncode != 0:
                    skipped.append(f"local:{src}")
                    continue
                # Local delete.
                d1 = run_git(repo, "branch", "-D", src)
                if d1.returncode != 0:
                    skipped.append(f"local:{src}")
                else:
                    deleted.append(f"local:{src}")
                # Remote delete.
                d2 = subprocess.run(
                    [
                        "git", "-C", str(repo),
                        "push", "origin", "--delete", src,
                    ],
                    capture_output=True, text=True, timeout=PER_REPO_TIMEOUT, check=False,
                )
                if d2.returncode != 0:
                    skipped.append(f"remote:{src}")
                else:
                    deleted.append(f"remote:{src}")
        else:
            log.error("consolidated_branch_not_verified_skipping_deletes",
                      repo=str(repo), branch=new_branch)

        return ConsolidationResult(
            repo=str(repo),
            status="consolidated" if remote_verified else "partial",
            source_branches=sources,
            consolidated_branch=new_branch if remote_verified else None,
            remote_verified=remote_verified,
            deleted_count=len(deleted),
            skipped_delete_count=len(skipped),
        )
    finally:
        if has_stash:
            run_git(repo, "stash", "pop")


# ---------- airlock stale-row archival ----------
@dataclass
class ArchiveResult:
    airlock_id: str
    archive_path: Optional[str]
    sha256: Optional[str]
    status: str
    error: Optional[str] = None


def find_stale_repos() -> list[tuple[str, int]]:
    """Return (airlock_id, created_at) rows from the v1 airlock database that
    are older than STALE_AGE_DAYS. Database is opened read-only."""
    rows: list[tuple[str, int]] = []
    if not AIRLOCK_DB.exists():
        return rows
    try:
        # Open read-only.
        uri = f"file:{AIRLOCK_DB}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            cur = conn.execute("SELECT id, created_at FROM repos WHERE created_at IS NOT NULL")
            cutoff = int(time.time()) - ARCHIVE_AGE_DAYS * 86400
            for airlock_id, created_at in cur.fetchall():
                if created_at < cutoff:
                    rows.append((airlock_id, created_at))
        finally:
            conn.close()
    except sqlite3.Error as exc:
        # Database is locked or unreadable — skip rather than crash.
        print(f"warn: airlock DB unreadable: {exc}", file=sys.stderr)
    return rows


def archive_airlock_repo(airlock_id: str) -> ArchiveResult:
    """Tarball the airlock bare-mirror subtree to disk, leave the original
    entry alone. Returns ArchiveResult."""
    src_dir = AIRLOCK_REPOS_DIR / airlock_id
    if not src_dir.is_dir():
        return ArchiveResult(
            airlock_id=airlock_id, archive_path=None, sha256=None,
            status="skipped-missing",
            error=f"{src_dir} not present",
        )

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARCHIVE_DIR / f"{airlock_id}.tar.zst"
    sha_path = ARCHIVE_DIR / f"{airlock_id}.sha256"

    if DRY_RUN:
        return ArchiveResult(
            airlock_id=airlock_id, archive_path=str(out_path), sha256=None,
            status="archived-dry-run",
        )

    # Build the tarball streaming into a sha256 hasher.
    h = hashlib.sha256()
    tar_proc = subprocess.Popen(
        [
            "tar", "--zstd",
            "-cf", str(out_path),
            "-C", str(AIRLOCK_REPOS_DIR),
            airlock_id,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    _, err = tar_proc.communicate(timeout=PER_REPO_TIMEOUT * 2)
    if tar_proc.returncode != 0:
        return ArchiveResult(
            airlock_id=airlock_id, archive_path=None, sha256=None,
            status="error", error=f"tar failed: {err.decode(errors='replace').strip()}",
        )

    # Compute sha256 of the resulting file.
    with out_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    digest = h.hexdigest()

    # Write sidecar.
    sha_path.write_text(f"{digest}  {out_path.name}\n", encoding="utf-8")

    return ArchiveResult(
        airlock_id=airlock_id,
        archive_path=str(out_path),
        sha256=digest,
        status="archived",
    )


# ---------- sweep orchestration ----------
def sweep_once(log: Logger, hostname: str) -> int:
    log.info("cleanup_sweep_start")
    error_count = 0

    # 1. consolidation
    for repo in find_repos(REPO_ROOT):
        try:
            r = consolidate_repo(repo, log, hostname)
        except Exception as exc:  # noqa: BLE001
            log.error("consolidation_unhandled_exception",
                      repo=str(repo), error=str(exc))
            error_count += 1
            continue
        log.info(
            "consolidation_done",
            **{
                "repo": r.repo,
                "status": r.status,
                "source_branches": r.source_branches,
                "consolidated_branch": r.consolidated_branch,
                "remote_verified": r.remote_verified,
                "deleted_count": r.deleted_count,
                "skipped_delete_count": r.skipped_delete_count,
                "error": r.error,
            },
        )
        if r.status in {"error", "partial"}:
            error_count += 1

    # 2. stale-row archival
    stale = find_stale_repos()
    log.info("stale_row_scan", stale_count=len(stale))
    for airlock_id, _ in stale:
        try:
            r = archive_airlock_repo(airlock_id)
        except Exception as exc:  # noqa: BLE001
            log.error("archive_unhandled_exception",
                      airlock_id=airlock_id, error=str(exc))
            error_count += 1
            continue
        log.info("archive_done",
                 airlock_id=r.airlock_id, status=r.status,
                 archive_path=r.archive_path, sha256=r.sha256, error=r.error)
        if r.status == "error":
            error_count += 1

    log.info("cleanup_sweep_done", error_count=error_count)
    return error_count


# ---------- single-instance lock ----------
class SingleInstance:
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


_shutdown = False


def _handle_signal(signum, frame):  # noqa: ARG001
    global _shutdown
    _shutdown = True


# ---------- main ----------
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loop", action="store_true",
                        help="run on the configured interval forever")
    parser.add_argument("--once", action="store_true",
                        help="(default) run a single cleanup pass")
    parser.add_argument("--interval", type=int, default=8 * 3600,
                        help="loop interval in seconds (default 28800 = 8 hours)")
    args = parser.parse_args(argv)

    if not REPO_ROOT.is_dir():
        print(f"fatal: REPO_ROOT does not exist: {REPO_ROOT}", file=sys.stderr)
        return 1

    log = Logger(LOG_DIR / "cleanup.log")
    hostname = socket.gethostname()

    sig = SingleInstance(LOCK_PATH)
    if not sig.acquire():
        log.warn("another_instance_already_running", lock=str(LOCK_PATH))
        return 0

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGHUP, _handle_signal)

    try:
        log.info("daemon_started", interval_seconds=args.interval,
                 repo_root=str(REPO_ROOT), loop=bool(args.loop), dry_run=DRY_RUN,
                 archive_dir=str(ARCHIVE_DIR))

        if not args.loop:
            err = sweep_once(log, hostname)
            return 0 if err == 0 else 2

        next_run = time.monotonic() + args.interval  # first cleanup delayed by interval
        while not _shutdown:
            sleep_for = max(1.0, next_run - time.monotonic())
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
            next_run = time.monotonic() + args.interval

        log.info("daemon_shutdown", reason="signal")
        return 0
    finally:
        sig.release()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
