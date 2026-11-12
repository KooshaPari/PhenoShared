#!/usr/bin/env python3
"""Absorb a private repo into the private registry, proven complete.

Private ops repositories are data, not code, so they belong in PhenoRegistry
rather than PhenoShared. Each one is absorbed as two things:

  repos/<repo>/tree/     the working tree, readable and browsable
  refs/preserved/<repo>/ every branch and tag, full history

The completeness proof is exact rather than sampled: git object ids are content
hashes, so comparing the source tree's blob ids against the pushed tree's blob
ids proves every file arrived byte for byte. Nothing is deleted here; the
script prints DELETE-AUTHORISED only when the comparison passes.

    python scripts/absorb_private.py nexus host-ops
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

OWNER_DEFAULT = "KooshaPari"
REGISTRY_DEFAULT = "PhenoRegistry"


def sh(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def git(repo, *args):
    return sh(["git", "-C", repo] + list(args))


def must(repo, *args):
    code, out, err = git(repo, *args)
    if code != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), err.strip()[:200]))
    return out.strip()


def ls_blobs(repo: str, treeish: str) -> dict[str, str]:
    """Map path -> blob sha for every file in a tree."""
    out = must(repo, "ls-tree", "-r", "--full-tree", treeish)
    result = {}
    for line in out.splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob":
            result[path] = parts[2]
    return result


def absorb(registry_clone: str, url_registry: str, owner: str, repo: str,
           workdir: str) -> tuple[bool, str]:
    mirror = os.path.join(workdir, "%s.git" % repo)
    code, _, err = sh(["gh", "repo", "clone", "%s/%s" % (owner, repo), mirror, "--", "--mirror"])
    if code != 0:
        return False, "mirror clone failed: %s" % err.strip()[:150]

    code, out, _ = sh(["gh", "api", "repos/%s/%s" % (owner, repo)])
    if code != 0:
        return False, "cannot read repo metadata"
    # Not `symbolic-ref HEAD`: for a fork, `gh repo clone` points HEAD at the
    # *upstream* default branch rather than the fork's own, which would absorb
    # the wrong branch's content.
    branch = json.loads(out).get("default_branch") or "main"
    try:
        source_tree = must(mirror, "rev-parse", "%s^{tree}" % branch)
    except RuntimeError as exc:
        return False, str(exc)

    # Prepare refs: registry state, source content, source history.
    for args in (("fetch", "-q", "origin", "main:refs/reg/main"),
                 ("fetch", "-q", mirror, "%s:refs/src/%s" % (branch, repo)),
                 ("fetch", "-q", mirror,
                  "+refs/heads/*:refs/hist/%s/heads/*" % repo,
                  "+refs/tags/*:refs/hist/%s/tags/*" % repo)):
        code, _, err = git(registry_clone, *args)
        if code != 0:
            return False, "fetch failed (%s): %s" % (args[0], err.strip()[:150])

    # Graft the whole source tree under repos/<repo>/tree in one commit, keeping
    # the registry's own content intact.
    git(registry_clone, "read-tree", "refs/reg/main")
    code, _, err = git(registry_clone, "read-tree", "--prefix=repos/%s/tree/" % repo,
                       "refs/src/%s^{tree}" % repo)
    if code != 0:
        return False, "read-tree failed: %s" % err.strip()[:150]
    tree = must(registry_clone, "write-tree")
    commit = must(registry_clone, "commit-tree", tree, "-p", "refs/reg/main",
                  "-m", "chore(absorb): %s tree and history" % repo)

    code, _, err = git(registry_clone, "push", "-q", "origin", "%s:main" % commit)
    if code != 0:
        return False, "push tree failed: %s" % err.strip()[:150]

    code, _, err = git(registry_clone, "push", "-q", "origin",
                       "+refs/hist/%s/*:refs/preserved/%s/*" % (repo, repo))
    if code != 0:
        return False, "push history failed: %s" % err.strip()[:150]

    # Verify by reading back from the registry what we actually pushed.
    code, _, err = git(registry_clone, "fetch", "-q", "origin", "main:refs/reg/main")
    if code != 0:
        return False, "re-fetch failed: %s" % err.strip()[:150]
    pushed = ls_blobs(registry_clone, "refs/reg/main")
    prefix = "repos/%s/tree/" % repo
    got = {p[len(prefix):]: sha for p, sha in pushed.items() if p.startswith(prefix)}

    want = ls_blobs(mirror, source_tree)
    if got != want:
        missing = sorted(set(want) - set(got))
        extra = sorted(set(got) - set(want))
        differ = sorted(p for p in set(want) & set(got) if want[p] != got[p])
        return False, ("tree mismatch: %d missing, %d extra, %d differing"
                       % (len(missing), len(extra), len(differ)))

    heads = must(registry_clone, "ls-remote", url_registry, "refs/preserved/%s/*" % repo)
    nrefs = len([l for l in heads.splitlines() if l.strip()])
    return True, "%d files exact, %d refs, %d commits" % (
        len(want), nrefs, int(must(mirror, "rev-list", "--all", "--count")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repos", nargs="+")
    ap.add_argument("--owner", default=OWNER_DEFAULT)
    ap.add_argument("--registry", default=REGISTRY_DEFAULT)
    args = ap.parse_args()

    workdir = tempfile.mkdtemp(prefix="absorb-private-")
    registry_clone = os.path.join(workdir, "registry")
    url_registry = "https://github.com/%s/%s.git" % (args.owner, args.registry)

    # Blobless: we only need tree metadata plus our own new blobs, so the
    # registry's existing content never has to be downloaded.
    code, _, err = sh(["gh", "repo", "clone", "%s/%s" % (args.owner, args.registry),
                       registry_clone, "--", "--filter=blob:none", "--no-checkout"])
    if code != 0:
        print("cannot clone registry: %s" % err.strip()[:200])
        return 2

    failures = 0
    for repo in args.repos:
        ok, detail = absorb(registry_clone, url_registry, args.owner, repo, workdir)
        print("== %s" % repo)
        if ok:
            print("   absorbed  %s" % detail)
            print("   DELETE-AUTHORISED %s" % repo)
        else:
            print("   REFUSED   %s" % detail)
            failures += 1

    print()
    print("absorbed %d, blocked %d" % (len(args.repos) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
