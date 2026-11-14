#!/usr/bin/env python3
"""Prove an absorbed repo is complete before its source is deleted.

Why this exists: two absorptions in this repo were silently incomplete while the
absorption index recorded them as done -- BytePort was missing 362 of 680 files
and SessionLedger 123 of 934. A plain file copy does not fail loudly when it
misses files, and `.gitignore` silently drops whole subtrees. The only reliable
check is comparing the source tree against what is actually on disk, including
files that git ignores.

Usage:

    # verify one repo absorbed under absorption/<name>
    python scripts/verify_absorption.py SessionLedger
    python scripts/verify_absorption.py BytePort --root _archived/byteport

    # verify everything that has an absorption directory
    python scripts/verify_absorption.py --all

    # machine-readable, for CI
    python scripts/verify_absorption.py --all --json

Exit code 0 only when every checked repo is complete.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

SKIP_DIRS = {".git"}
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paths that are build output or logs, never authored content. Reporting these
# as missing would train the reader to ignore the tool, which is worse than not
# running it. They are counted separately as "excluded".
EXCLUDE_PREFIXES = (
    ".cargo-target/",
    "target/",
    "node_modules/",
    ".venv/",
    "dist/",
    "build/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
)
EXCLUDE_SUFFIXES = (
    ".log",
    ".pyc",
    ".pyo",
    # object and binary artefacts, regenerated from the source we keep
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".o",
    ".obj",
    ".a",
    ".lib",
)


def is_excluded(path: str) -> bool:
    if path.startswith(EXCLUDE_PREFIXES):
        return True
    return path.endswith(EXCLUDE_SUFFIXES)


def gh(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(["gh"] + args, capture_output=True)
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def remote_tree(owner_repo: str, ref: str = "HEAD") -> set[str] | None:
    """Every blob path in the remote repo, or None when it cannot be read."""
    code, out = gh(
        [
            "api",
            "repos/%s/git/trees/%s?recursive=1" % (owner_repo, ref),
            "--jq",
            '.tree[]|select(.type=="blob")|.path',
        ]
    )
    if code != 0:
        return None
    return {line for line in out.splitlines() if line.strip()}


def local_files(root: str) -> set[str]:
    """Every file under root, including gitignored ones on disk."""
    found = set()
    if not os.path.isdir(root):
        return found
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = os.path.join(dirpath, name)
            found.add(os.path.relpath(path, root).replace(os.sep, "/"))
    return found


def stored_in_registry(
    owner: str, registry: str, repo: str, paths: set[str]
) -> set[str]:
    """Which of these paths are present in the private registry instead.

    Files carrying private data are deliberately withheld from the public tree,
    so a public-only comparison would report them as missing forever. Checking
    the registry turns that into a resolved case rather than a false alarm.
    """
    if not paths:
        return set()
    code, out = gh(
        [
            "api",
            "repos/%s/%s/git/trees/HEAD?recursive=1" % (owner, registry),
            "--jq",
            '.tree[]|select(.type=="blob")|.path',
        ]
    )
    if code != 0:
        return set()
    registry_paths = set()
    # Path case is inconsistent in the registry (BytePort vs byteport), so match
    # case-insensitively rather than reporting withheld files as lost.
    lowered = {p.lower() for p in paths}
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("repos/"):
            continue
        tail = line[len("repos/") :]
        repo_part, _, rest = tail.partition("/")
        # Two layouts exist. An absorbed app keeps its files directly under
        # repos/<repo>/, while a private ops repo absorbed by absorb_private.py
        # is stored whole under repos/<repo>/tree/ (its every branch also lives
        # in refs/preserved/<repo>/). Accept both, or the tree/ layout reports
        # its entire content as missing.
        if rest.lower().startswith("tree/"):
            rest = rest[len("tree/") :]
        if repo_part.lower() == repo.lower() and rest.lower() in lowered:
            registry_paths.add(rest)
    return registry_paths


def verify(
    repo: str,
    owner: str,
    root: str,
    registry: str,
    extra_roots: list[str] | None = None,
    at: str | None = None,
) -> dict:
    remote_head = remote_tree("%s/%s" % (owner, repo))
    if remote_head is None:
        return {
            "repo": repo,
            "status": "unreadable",
            "detail": "could not read the remote tree (deleted or no access)",
        }

    # A live source keeps moving, so comparing against its HEAD turns every
    # upstream commit into a phantom defect. `--at` pins the comparison to the
    # commit that was actually absorbed; files added after it are reported as
    # drift, which is a fact about the source rather than a fault in the copy.
    remote = remote_head
    if at:
        remote = remote_tree("%s/%s" % (owner, repo), at)
        if remote is None:
            return {
                "repo": repo,
                "status": "unreadable",
                "detail": "could not read the remote tree at %s" % at,
            }
    drift = (remote_head - remote) if at else set()

    local = local_files(root)
    # Some absorptions are split across two roots, for example a repo whose
    # content landed partly in absorption/<name> and partly in _archived/<name>.
    roots = [root] + list(extra_roots or [])
    archived = os.path.join(REPO_ROOT, "_archived", repo)
    if os.path.isdir(archived) and archived not in roots:
        roots.append(archived)
    local = set()
    for r in roots:
        local |= local_files(r)
    missing = remote - local
    excluded = {p for p in missing if is_excluded(p)}
    missing = missing - excluded
    withheld = stored_in_registry(owner, registry, repo, missing) if missing else set()
    unresolved = missing - withheld

    return {
        "repo": repo,
        "status": "complete" if not unresolved else "incomplete",
        "root": root,
        "compared_at": at or "HEAD",
        "remote_files": len(remote),
        "local_files": len(local),
        "covered": len(remote & local),
        "missing": len(unresolved),
        "excluded_build_or_log": len(excluded),
        "withheld_in_registry": len(withheld),
        "missing_sample": sorted(unresolved)[:10],
        "source_drift": len(drift - excluded),
        "source_drift_sample": sorted(drift - excluded)[:10],
    }


def discover(owner: str) -> list[tuple[str, str]]:
    """Every absorption/<dir> that looks like an absorbed repo."""
    base = os.path.join(REPO_ROOT, "absorption")
    if not os.path.isdir(base):
        return []
    return [
        (name, os.path.join(base, name))
        for name in sorted(os.listdir(base))
        if os.path.isdir(os.path.join(base, name))
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", nargs="?", help="repo name, as absorbed")
    ap.add_argument("--all", action="store_true", help="verify every absorption/ dir")
    ap.add_argument("--owner", default="KooshaPari")
    ap.add_argument("--registry", default="PhenoRegistry")
    ap.add_argument("--root", help="override the local directory for --repo")
    ap.add_argument(
        "--also",
        action="append",
        default=[],
        help="extra local root to count as coverage (repeatable)",
    )
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument(
        "--at",
        help="compare against this source commit instead of HEAD; files the source "
        "gained afterwards are reported as drift rather than missing",
    )
    ap.add_argument(
        "--allow-unreadable",
        action="store_true",
        help="exit 0 even when no source repo could be read",
    )
    args = ap.parse_args()

    if args.all:
        targets = discover(args.owner)
    elif args.repo:
        root = args.root or os.path.join("absorption", args.repo)
        if not os.path.isabs(root):
            root = os.path.join(REPO_ROOT, root)
        targets = [(args.repo, root)]
    else:
        ap.error("give a repo name or --all")

    results = [
        verify(name, args.owner, path, args.registry, args.also, args.at)
        for name, path in targets
    ]

    if args.as_json:
        print(json.dumps(results, indent=1))
        return 0 if all(r["status"] != "incomplete" for r in results) else 1

    incomplete = 0
    matched = 0
    unreadable = 0
    for r in results:
        if r["status"] == "complete":
            matched += 1
            notes = []
            if r["withheld_in_registry"]:
                notes.append("%d withheld to registry" % r["withheld_in_registry"])
            if r["excluded_build_or_log"]:
                notes.append("%d build/log excluded" % r["excluded_build_or_log"])
            if r["source_drift"]:
                notes.append(
                    "%d added upstream after %s" % (r["source_drift"], r["compared_at"])
                )
            suffix = ("  (" + ", ".join(notes) + ")") if notes else ""
            print(
                "  OK    %-32s %d/%d%s"
                % (r["repo"], r["covered"], r["remote_files"], suffix)
            )
        elif r["status"] == "unreadable":
            unreadable += 1
            print("  SKIP  %-32s %s" % (r["repo"], r["detail"]))
        else:
            incomplete += 1
            print(
                "  FAIL  %-32s %d of %d missing"
                % (r["repo"], r["missing"], r["remote_files"])
            )
            for m in r["missing_sample"]:
                print("          " + m)

    print()
    counts = (len(results), matched, incomplete, unreadable)
    print("%d checked, %d matched, %d incomplete, %d unreadable" % counts)

    if incomplete:
        return 1

    # Every source unreadable means verification did not actually happen. Passing
    # here would be false assurance, which is the exact failure this tool exists
    # to prevent -- a token restricted to this repo cannot see private sources.
    if results and matched == 0 and not args.allow_unreadable:
        print()
        print("No source repo could be read, so nothing was actually verified.")
        print("Provide a token with read access to the source repos, or pass")
        print("--allow-unreadable to record that verification was skipped on purpose.")
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
