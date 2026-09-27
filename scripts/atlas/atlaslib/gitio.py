"""Git plumbing: the repository is the only source of truth for the atlas."""

from __future__ import annotations

import os
import subprocess


def git(root: str, *args: str) -> bytes:
    proc = subprocess.run(["git", "-C", root, *args], capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(
            "git " + " ".join(args) + " failed: " + proc.stderr.decode("utf-8", "replace").strip()
        )
    return proc.stdout


def repo_root(explicit: str | None = None) -> str:
    if explicit:
        return os.path.abspath(explicit)
    return git(os.getcwd(), "rev-parse", "--show-toplevel").decode().strip()


def tracked_paths(root: str) -> list[str]:
    """Every tracked path, sorted, from `git ls-files`.

    Sorted so downstream ordering is stable and the artifacts are byte-identical
    across runs. Only the index is consulted, so build output and untracked
    files cannot leak into the inventory.
    """
    raw = git(root, "ls-files", "-z")
    return sorted(p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p)


def revision(root: str) -> tuple[str, str]:
    full = git(root, "rev-parse", "HEAD").decode().strip()
    return full, full[:12]


def commit_dates(root: str) -> dict[str, str]:
    """path -> most recent author date (YYYY-MM-DD).

    A single `git log` pass with NUL-delimited output, rather than one
    `git log -1 -- <path>` per package, which would be ~600 subprocess spawns.
    Records starting with 0x01 are date markers; the following records are the
    paths touched by that commit. `setdefault` keeps the newest date because
    `git log` walks newest-first.
    """
    raw = git(root, "log", "--format=%x01%aI", "--name-only", "-z")
    dates: dict[str, str] = {}
    current: str | None = None
    for token in raw.split(b"\0"):
        if not token:
            continue
        if token.startswith(b"\x01"):
            current = token[1:].decode("ascii", "replace").strip()[:10]
            continue
        if current:
            dates.setdefault(token.decode("utf-8", "surrogateescape"), current)
    return dates


def head_date(root: str) -> str:
    return git(root, "log", "-1", "--format=%aI").decode().strip()[:10]
