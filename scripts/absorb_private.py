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

Re-running it for a repo that was already absorbed refreshes the registry's
snapshot to the source's current default branch; it is not append-only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

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
    # A repo absorbed on an earlier pass already has its old snapshot at this
    # prefix, and `read-tree --prefix` refuses to write over any path that is
    # already in the index ("Entry 'x' overlaps with 'x'.  Cannot bind.").
    # Dropping the stale snapshot from the index first is what makes a second
    # run a refresh instead of a hard failure. This is index-only, so no
    # working-tree file is touched and nothing is lost: the new tree is compared
    # against the source blob-for-blob below exactly as on a first run.
    prefix = "repos/%s/tree/" % repo
    git(registry_clone, "rm", "-r", "-q", "-f", "--cached", "--ignore-unmatch",
        prefix.rstrip("/"))
    code, _, err = git(registry_clone, "read-tree", "--prefix=" + prefix,
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

    # Verify by reading back from the registry what we actually pushed. Retried
    # because the ref update can lose the race with the push that just landed
    # and fail with "cannot lock ref ... unable to resolve reference", which is
    # a transient local condition, not evidence that the absorption failed.
    for attempt in range(3):
        code, _, err = git(registry_clone, "fetch", "-q", "origin", "main:refs/reg/main")
        if code == 0:
            break
        if attempt == 2:
            return False, "re-fetch failed: %s" % err.strip()[:150]
        time.sleep(2)
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

    workdir = tempfile.mkdtemp(prefix="absorb-private-",
                               dir=os.path.expanduser("~/CodeProjects/temp"))
    registry_clone = os.path.join(workdir, "registry")
    url_registry = "https://github.com/%s/%s.git" % (args.owner, args.registry)

    # A full clone, not a blobless one. Pushing a *refresh* of an
    # already-absorbed repo makes pack-objects delta the new blobs against the
    # snapshot already at repos/<repo>/tree/, and a --filter=blob:none clone
    # does not have those old blobs. Each one then becomes its own lazy fetch:
    # a measured 10+ minutes of single-object round trips with no progress. The
    # registry is ~450 MB, so cloning it whole is cheaper than that storm.
    code, _, err = sh(["gh", "repo", "clone", "%s/%s" % (args.owner, args.registry),
                       registry_clone, "--", "--no-checkout"])
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
