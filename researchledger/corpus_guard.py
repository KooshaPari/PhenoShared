#!/usr/bin/env python3
"""corpus_guard.py - tripwires that protect the research-ledger corpus.

WHY THIS EXISTS
---------------
On 2026-10-15 the canonical corpus `research_ledger.sqlite` was destroyed when
a worker replaced the path with a symlink to a scratch file and then removed
the symlink. The original file's directory entry was gone; recovery was only
possible because a pre-fixup backup happened to exist.

The deeper problem was not that one worker. It was that every migrator and
builder defaulted `--db` to the canonical path, so nothing in the codebase
distinguished "the irreplaceable corpus" from "whatever file is at that path
today". Tooling could therefore be pointed at the corpus by accident, or
follow a symlink planted there.

DESIGN
------
- `CANONICAL` is the one true corpus path.
- `SEALED_BACKUP` is the read-only archive; it must never be written.
- `RETIRED_CANONICALS` are former corpus locations. Writing to one is refused,
  because it recreates the split-brain that this module exists to prevent.
- `guard_write_target()` is called by every writer before it opens its target.
- `assert_corpus_sane()` is an optional startup check for read paths.

The guard is deliberately a hard stop (SystemExit), not a warning.

2026-11-10: every path in this module had drifted off the real corpus, so the
guard was protecting nothing. `CANONICAL` pointed at a path that no longer
existed, `SEALED_BACKUP` likewise, while the live 21 GiB corpus sat at
`~/CodeProjects/docs/reports/Exports/analysis/research_ledger.sqlite`. The
constants below now resolve to reality, are overridable by environment, and
`assert_corpus_sane()` is the tripwire that would have caught the drift: run
`python3 corpus_guard.py` and it fails loudly when CANONICAL is not a real file.

2026-11-11: the sealed archive was recreated, so the "never writable" branch is
now live rather than theoretical. A dated archive filename would drift out of
the guard's view as soon as the next backup is taken, so protection is
directory-scoped: anything inside `SEALED_ARCHIVE_DIR` is refused whatever it is
named. That closes the drift class this module exists because of.
"""
from __future__ import annotations

import os
import stat
import sys

#: Override the corpus location without editing code (checkout, restore drill).
CANONICAL_ENV = "ANALYSIS_CANONICAL_DB"
SEALED_ENV = "ANALYSIS_SEALED_BACKUP"

CANONICAL = os.path.expanduser(
    os.environ.get(CANONICAL_ENV)
    or "~/CodeProjects/docs/reports/Exports/analysis/research_ledger.sqlite"
)

#: The read-only archive: the sealed copy of the corpus, chmod 444.
SEALED_BACKUP = os.path.expanduser(
    os.environ.get(SEALED_ENV)
    or "~/CodeProjects/backups/analysis/research_ledger.sqlite.sealed-20261111"
)

#: Everything in this directory is archival and refused for writes. Scoping the
#: refusal to the directory rather than only to SEALED_BACKUP's exact filename
#: means the next dated backup is protected automatically instead of silently
#: falling outside the guard, which is the 2026-11-10 failure mode.
SEALED_ARCHIVE_DIR = os.path.expanduser(
    os.environ.get("ANALYSIS_SEALED_DIR") or "~/CodeProjects/backups/analysis"
)

#: Retired corpus locations. Both are dead: the first no longer exists, the
#: second holds an 83-byte truncated corpse of the corpus. Writing to either
#: would split the corpus, so both are refused by name.
RETIRED_CANONICALS = (
    "~/Exports/analysis/research_ledger.sqlite",
    "~/CodeProjects/Exports/analysis/research_ledger.sqlite",
)

#: Pass this to deliberately target the canonical corpus.
ALLOW_FLAG = "--allow-canonical"

#: Set this for unattended pipelines that legitimately write the corpus, so a
#: cron job needs no argv change. Honouring it is logged, never silent.
ALLOW_ENV = "ANALYSIS_ALLOW_CANONICAL"

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _real(path: str) -> str:
    return os.path.realpath(os.path.expanduser(path))


def _inside(path: str, directory: str) -> bool:
    """True if *path* resolves to *directory* or to something beneath it."""
    d = _real(directory).rstrip(os.sep)
    p = _real(path)
    return p == d or p.startswith(d + os.sep)


def _env_allows_canonical() -> bool:
    return os.environ.get(ALLOW_ENV, "").strip().lower() in _TRUTHY


def guard_write_target(path: str, allow_canonical: bool = False) -> str:
    """Refuse to write the canonical corpus or the sealed archive.

    Call this with the *resolved source argument* before opening a connection
    in read-write mode.

    Raises:
        SystemExit: if the target is the sealed archive, is a retired corpus
            location, is the canonical corpus without an opt-in, or if the
            canonical path is currently a symlink or is missing (both are signs
            of the incident repeating).
    """
    target = _real(path)

    # 1. The sealed archive is never writable, by anyone, for any reason. No
    #    env var or flag overrides this. The whole archive directory is refused,
    #    not just the current dated filename, so a newer backup cannot drift
    #    outside the guard.
    if target == _real(SEALED_BACKUP) or _inside(target, SEALED_ARCHIVE_DIR):
        raise SystemExit(
            f"refusing to write the sealed archive: {SEALED_BACKUP}\n"
            f"The whole archive directory {SEALED_ARCHIVE_DIR} is read-only "
            "and is the last line of defence. Make a working copy instead."
        )

    # 2. A retired location is dead. Writing there creates a second corpus.
    for retired in RETIRED_CANONICALS:
        if target == _real(retired):
            raise SystemExit(
                f"refusing: {retired} is a RETIRED corpus location.\n"
                f"The live corpus is {CANONICAL}\n"
                "Writing here would split the corpus in two. "
                "Point --db at the live path."
            )

    # 3. A missing canonical corpus is a red flag, not an invitation to create
    #    an empty one over the top of whatever used to be there.
    if target == _real(CANONICAL) and not os.path.exists(CANONICAL):
        raise SystemExit(
            f"refusing: the canonical corpus is missing at {CANONICAL}\n"
            "Do not create it implicitly. Restore it deliberately, or write "
            "to a different --db target."
        )

    # 4. A symlinked canonical path is exactly how the 2026-10-15 loss began.
    if target == _real(CANONICAL) and os.path.islink(CANONICAL):
        dest = os.path.realpath(CANONICAL)
        raise SystemExit(
            f"refusing: {CANONICAL} is a SYMLINK -> {dest}\n"
            "This is the shape of the 2026-10-15 incident. Remove the symlink "
            "and restore the real file before writing."
        )

    # 5. Writing the canonical corpus requires a deliberate opt-in, by flag or
    #    by environment. The environment path is logged so an unattended run
    #    still leaves a trace.
    if target == _real(CANONICAL):
        if allow_canonical:
            return target
        if _env_allows_canonical():
            print(
                f"corpus_guard: {ALLOW_ENV} is set, allowing write to the "
                f"canonical corpus {CANONICAL}",
                file=sys.stderr,
            )
            return target
        raise SystemExit(
            f"refusing to write the canonical corpus without {ALLOW_FLAG}\n"
            f"  target: {CANONICAL}\n"
            "Prefer writing to a staging path, then promoting atomically. "
            f"If you truly mean to modify the corpus, re-run with {ALLOW_FLAG} "
            f"or set {ALLOW_ENV}=1."
        )

    return target


def assert_corpus_sane(path: str | None = None) -> None:
    """Cheap integrity tripwire for read paths.

    Verifies the canonical corpus exists, is a regular file (not a symlink),
    and is non-empty. Intended to be called at CLI startup so a wrecked corpus
    fails loudly rather than returning misleading empty results.
    """
    p = CANONICAL if path is None else os.path.expanduser(path)
    if not os.path.exists(p):
        raise SystemExit(f"corpus missing: {p}")
    if os.path.islink(p):
        raise SystemExit(
            f"corpus is a symlink -> {os.path.realpath(p)}: refusing to read "
            "through it"
        )
    if not os.path.isfile(p):
        raise SystemExit(f"corpus is not a regular file: {p}")
    if os.path.getsize(p) == 0:
        raise SystemExit(f"corpus is zero bytes: {p}")


if __name__ == "__main__":  # pragma: no cover - manual check
    print(f"CANONICAL      = {CANONICAL}")
    print(f"SEALED_BACKUP  = {SEALED_BACKUP}")
    print(f"SEALED_DIR     = {SEALED_ARCHIVE_DIR}")
    if os.path.exists(SEALED_BACKUP):
        ssize = os.path.getsize(SEALED_BACKUP)
        mode = oct(stat.S_IMODE(os.stat(SEALED_BACKUP).st_mode))
        print(
            f"sealed state   = PRESENT ({ssize:,} bytes, "
            f"{ssize / 2**30:.1f} GiB, mode {mode})"
        )
    else:
        print("sealed state   = ABSENT (no last line of defence)")
    for retired in RETIRED_CANONICALS:
        state = "exists" if os.path.exists(os.path.expanduser(retired)) else "absent"
        print(f"retired        = {retired}  ({state}, refused for writes)")
    print(f"{ALLOW_ENV} = {os.environ.get(ALLOW_ENV, '(unset)')}")
    try:
        assert_corpus_sane()
        size = os.path.getsize(CANONICAL)
        print(f"corpus state   = SANE ({size:,} bytes, {size / 2**30:.1f} GiB)")
    except SystemExit as exc:
        print(f"corpus state   = {exc}")
        sys.exit(1)
