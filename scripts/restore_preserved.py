#!/usr/bin/env python3
"""Restore a repository from the refs preserved in the private registry.

Forks must never be deleted, but eleven were, before that rule existed. Every
ref of each was preserved under `refs/preserved/<repo>/`, so they are fully
recoverable: the commits, trees and blobs are still there under a different ref
namespace, verified name by name and sha by sha at the time of preservation.

What cannot be restored is the fork relationship and the GitHub-side metadata
(issues, stars, the parent link). A restore produces an ordinary repository
containing the same history.

Safe by default: without `--create` it only fetches and reports what it would
restore. Nothing is created on GitHub and nothing is pushed.

    python scripts/restore_preserved.py --list
    python scripts/restore_preserved.py zz-aa-dep-Bifrost
    python scripts/restore_preserved.py zz-aa-dep-Bifrost --create --private
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

OWNER_DEFAULT = "KooshaPari"
REGISTRY_DEFAULT = "PhenoRegistry"


def sh(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def preserved_namespaces(owner: str, registry: str) -> dict[str, int]:
    code, out, err = sh(["git", "ls-remote", "--refs",
                         "https://github.com/%s/%s.git" % (owner, registry),
                         "refs/preserved/*"])
    if code != 0:
        raise SystemExit("cannot list preserved refs: %s" % err.strip()[:200])
    counts: dict[str, int] = {}
    for line in out.splitlines():
        if "\t" not in line:
            continue
        name = line.partition("\t")[2]
        rest = name[len("refs/preserved/"):]
        repo, _, _tail = rest.partition("/")
        counts[repo] = counts.get(repo, 0) + 1
    return counts


def restore(repo: str, owner: str, registry: str, create: bool, private: bool) -> int:
    work = tempfile.mkdtemp(prefix="restore-%s-" % repo)
    clone = os.path.join(work, repo)
    url = "https://github.com/%s/%s.git" % (owner, registry)

    code, _, err = sh(["git", "init", "-q", "--bare", clone])
    if code != 0:
        print("init failed: %s" % err.strip()[:200])
        return 2
    sh(["git", "-C", clone, "remote", "add", "origin", url])

    # Map the preserved namespace back onto ordinary branch and tag names so the
    # result behaves like the repository it came from.
    refspec = ("+refs/preserved/%s/heads/*:refs/heads/*" % repo,
               "+refs/preserved/%s/tags/*:refs/tags/*" % repo)
    code, _, err = sh(["git", "-C", clone, "fetch", "-q", "origin", *refspec])
    if code != 0:
        print("fetch failed - is '%s' preserved? %s" % (repo, err.strip()[:200]))
        return 2

    code, out, _ = sh(["git", "-C", clone, "for-each-ref",
                       "--format=%(refname)", "refs/heads/", "refs/tags/"])
    refs = [r for r in out.splitlines() if r.strip()]
    code, count, _ = sh(["git", "-C", clone, "rev-list", "--all", "--count"])
    print("%s: %d refs, %s commits fetched into %s"
          % (repo, len(refs), count.strip(), clone))
    for r in refs[:15]:
        print("   %s" % r)
    if len(refs) > 15:
        print("   ... and %d more" % (len(refs) - 15))

    if not create:
        print("dry run: nothing created on GitHub, nothing pushed.")
        print("re-run with --create to publish as %s/%s" % (owner, repo))
        return 0

    args = ["gh", "repo", "create", "%s/%s" % (owner, repo), "--private" if private else "--public"]
    code, _, err = sh(args)
    if code != 0:
        print("repo create failed: %s" % err.strip()[:300])
        return 2
    code, _, err = sh(["git", "-C", clone, "push", "--mirror", "origin"])
    if code != 0:
        print("push failed: %s" % err.strip()[:300])
        return 2
    print("restored %s/%s" % (owner, repo))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", nargs="?")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--create", action="store_true")
    ap.add_argument("--private", action="store_true", default=True)
    ap.add_argument("--owner", default=OWNER_DEFAULT)
    ap.add_argument("--registry", default=REGISTRY_DEFAULT)
    args = ap.parse_args()

    if args.list or not args.repo:
        counts = preserved_namespaces(args.owner, args.registry)
        print("%-40s %s" % ("namespace", "refs"))
        for repo in sorted(counts):
            print("%-40s %d" % (repo, counts[repo]))
        print("\ntotal namespaces: %d, total refs: %d" % (len(counts), sum(counts.values())))
        return 0

    return restore(args.repo, args.owner, args.registry, args.create, args.private)


if __name__ == "__main__":
    sys.exit(main())
