#!/usr/bin/env python3
"""Prove an absorbed tree is a real branch of the preserved history.

`repos/<repo>/tree` is supposed to be the repository's default branch at the
moment it was absorbed. A tree copied from the wrong branch would still look
complete — same file count, plausible content — so counting files proves
nothing here. Comparing the grafted tree id against the tree ids of the
preserved branch refs does: a match names exactly which branch was copied.

    python scripts/verify_preserved.py nexus host-ops
    python scripts/verify_preserved.py --all
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile


def sh(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def git(repo, *args):
    code, out, err = sh(["git", "-C", repo] + list(args))
    if code != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), err.strip()[:200]))
    return out.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repos", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--owner", default="KooshaPari")
    ap.add_argument("--registry", default="PhenoRegistry")
    args = ap.parse_args()

    work = tempfile.mkdtemp(prefix="verify-preserved-")
    clone = os.path.join(work, "registry")

    # Blobless: branch and tree ids are all this needs, so the registry's
    # content never has to be downloaded.
    code, _, err = sh(["gh", "repo", "clone", "%s/%s" % (args.owner, args.registry),
                       clone, "--", "--filter=blob:none", "--no-checkout"])
    if code != 0:
        print("cannot clone registry: %s" % err.strip()[:200])
        return 2
    code, _, err = sh(["git", "-C", clone, "fetch", "-q", "origin",
                       "+refs/preserved/*:refs/check/*", "main:refs/check/main"])
    if code != 0:
        print("cannot fetch preserved refs: %s" % err.strip()[:200])
        return 2

    if args.all:
        repos = sorted({r.split("refs/check/")[1].split("/heads/")[0]
                        for r in git(clone, "for-each-ref", "--format=%(refname)",
                                     "refs/check/").splitlines()
                        if "/heads/" in r})
    else:
        repos = args.repos
    if not repos:
        print("give repo names or --all")
        return 2

    all_paths = git(clone, "ls-tree", "-r", "--full-tree", "--name-only",
                    "refs/check/main").splitlines()

    failures = 0
    for repo in repos:
        prefix = "repos/%s/tree" % repo
        has_tree = any(p.startswith(prefix + "/") for p in all_paths)
        if not has_tree:
            print("%-24s no absorbed tree" % repo)
            failures += 1
            continue
        subtree = git(clone, "rev-parse", "refs/check/main:%s" % prefix)

        matches = []
        for ref in git(clone, "for-each-ref", "--format=%(refname)",
                       "refs/check/%s/heads/" % repo).splitlines():
            if git(clone, "rev-parse", "%s^{tree}" % ref) == subtree:
                matches.append(ref.split("/heads/")[-1])

        if matches:
            print("%-24s tree %s == branch %s" % (repo, subtree[:10], ", ".join(matches)))
        else:
            print("%-24s tree %s matches NO preserved branch" % (repo, subtree[:10]))
            failures += 1

    print()
    print("matched %d, unmatched %d" % (len(repos) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
