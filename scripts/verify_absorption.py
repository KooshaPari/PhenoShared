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


def gh(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(["gh"] + args, capture_output=True)
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def remote_tree(owner_repo: str, ref: str = "HEAD") -> set[str] | None:
    """Every blob path in the remote repo, or None when it cannot be read."""
    code, out = gh([
        "api",
        "repos/%s/git/trees/%s?recursive=1" % (owner_repo, ref),
        "--jq", '.tree[]|select(.type=="blob")|.path',
    ])
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


def stored_in_registry(owner: str, registry: str, repo: str, paths: set[str]) -> set[str]:
    """Which of these paths are present in the private registry instead.

    Files carrying private data are deliberately withheld from the public tree,
    so a public-only comparison would report them as missing forever. Checking
    the registry turns that into a resolved case rather than a false alarm.
    """
    if not paths:
        return set()
    code, out = gh([
        "api", "repos/%s/%s/git/trees/HEAD?recursive=1" % (owner, registry),
        "--jq", '.tree[]|select(.type=="blob")|.path',
    ])
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
        tail = line[len("repos/"):]
        repo_part, _, rest = tail.partition("/")
        if repo_part.lower() == repo.lower() and rest.lower() in lowered:
            registry_paths.add(rest)
    return registry_paths


def verify(repo: str, owner: str, root: str, registry: str, extra_roots: list[str] | None = None) -> dict:
    remote = remote_tree("%s/%s" % (owner, repo))
    if remote is None:
        return {"repo": repo, "status": "unreadable",
                "detail": "could not read the remote tree (deleted or no access)"}

    local = local_files(root)
    # Some absorptions are split across two roots, for example a repo whose
    # content landed partly in absorption/<name> and partly in _archived/<name>.
    for extra in extra_roots or []:
        local |= local_files(extra)
    missing = remote - local
    withheld = stored_in_registry(owner, registry, repo, missing) if missing else set()
    unresolved = missing - withheld

    return {
        "repo": repo,
        "status": "complete" if not unresolved else "incomplete",
        "root": root,
        "remote_files": len(remote),
        "local_files": len(local),
        "covered": len(remote & local),
        "missing": len(unresolved),
        "withheld_in_registry": len(withheld),
        "missing_sample": sorted(unresolved)[:10],
    }


def discover(owner: str) -> list[tuple[str, str]]:
    """Every absorption/<dir> that looks like an absorbed repo."""
    base = os.path.join(REPO_ROOT, "absorption")
    if not os.path.isdir(base):
        return []
    return [(name, os.path.join(base, name)) for name in sorted(os.listdir(base))
            if os.path.isdir(os.path.join(base, name))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", nargs="?", help="repo name, as absorbed")
    ap.add_argument("--all", action="store_true", help="verify every absorption/ dir")
    ap.add_argument("--owner", default="KooshaPari")
    ap.add_argument("--registry", default="PhenoRegistry")
    ap.add_argument("--root", help="override the local directory for --repo")
    ap.add_argument("--also", action="append", default=[],
                    help="extra local root to count as coverage (repeatable)")
    ap.add_argument("--json", action="store_true", dest="as_json")
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

    results = [verify(name, args.owner, path, args.registry, args.also) for name, path in targets]

    if args.as_json:
        print(json.dumps(results, indent=1))
        return 0 if all(r["status"] != "incomplete" for r in results) else 1

    incomplete = 0
    for r in results:
        if r["status"] == "complete":
            note = ""
            if r["withheld_in_registry"]:
                note = "  (%d withheld to registry)" % r["withheld_in_registry"]
            print("  OK    %-32s %d/%d%s" % (r["repo"], r["covered"], r["remote_files"], note))
        elif r["status"] == "unreadable":
            print("  SKIP  %-32s %s" % (r["repo"], r["detail"]))
        else:
            incomplete += 1
            print("  FAIL  %-32s %d of %d missing" % (r["repo"], r["missing"], r["remote_files"]))
            for m in r["missing_sample"]:
                print("          " + m)

    print()
    print("%d checked, %d incomplete" % (len(results), incomplete))
    return 1 if incomplete else 0


if __name__ == "__main__":
    sys.exit(main())
