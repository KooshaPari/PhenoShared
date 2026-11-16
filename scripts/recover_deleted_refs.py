#!/usr/bin/env python3
"""Recover refs that `preserve_refs.py` deleted from the registry.

Deleting a git ref does not immediately delete its objects. They become
unreachable and survive until the host runs gc, which on GitHub is not immediate.
So a ref deleted minutes ago can often still be found by scanning for dangling
commits and matching them against the branch names that were removed.

This is a recovery tool, not a routine check. It clones the registry with full
history, runs fsck to enumerate unreachable commits, and reports each one whose
subject or author date could correspond to a named lost branch.

Usage:
    python recover_deleted_refs.py <repo> <branch>[:<expected-tip-hint>] ...
"""
import os
import re
import subprocess
import sys

OWNER = "KooshaPari"
REGISTRY = "PhenoRegistry"


def sh(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    repo = sys.argv[1]
    branches = sys.argv[2:]

    work = "C:/Users/koosh/Agents/scratch/recover-%s" % repo
    if not os.path.isdir(work):
        rc, out, err = sh(["git", "clone", "--quiet", "--no-checkout",
                           "https://github.com/%s/%s.git" % (OWNER, REGISTRY), work])
        if rc != 0:
            print("clone failed: %s" % err.strip()[:300])
            return 2
    # Make sure every preserved namespace is present locally.
    sh(["git", "-C", work, "fetch", "--quiet", "origin", "+refs/*:refs/all/*"])

    rc, out, _ = sh(["git", "-C", work, "fsck", "--unreachable", "--no-reflogs",
                     "--no-progress"])
    dangling = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "commit":
            dangling.append(parts[2])
    print("unreachable commits in the registry: %d" % len(dangling))
    if not dangling:
        print("nothing recoverable by this method; the objects have been collected")
        return 1

    # Index their subjects so a branch name can be matched to a candidate.
    rc, log, _ = sh(["git", "-C", work, "log", "--no-walk=unsorted",
                     "--format=%H\t%ad\t%s", "--date=short"] + dangling)
    index = []
    for line in log.splitlines():
        fields = line.split("\t")
        if len(fields) >= 3:
            index.append((fields[0], fields[1], fields[2]))

    STOP = {"fix", "feat", "chore", "the", "and", "for", "with", "from", "into",
            "wip", "tmp", "test", "main", "master", "dev", "ci", "docs"}
    found = 0
    for branch in branches:
        words = [w.lower() for w in re.split(r"[/_.-]", branch)
                 if w and w.lower() not in STOP and len(w) > 2]
        hits = [(sha, date, subj) for sha, date, subj in index
                if all(w in subj.lower() for w in words)] if words else []
        if hits:
            found += len(hits)
            print("%-52s %d candidate(s)" % (branch, len(hits)))
            for sha, date, subj in hits[:3]:
                print("    %s %s %s" % (sha[:10], date, subj[:66]))
        else:
            print("%-52s no candidate among unreachable commits" % branch)

    print()
    print("candidates found: %d" % found)
    print("registry clone kept at %s" % work)
    return 0


if __name__ == "__main__":
    sys.exit(main())
