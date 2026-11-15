#!/usr/bin/env python3
"""Compare a repository snapshot against a local absorbed tree, by content hash.

Git blob ids are content hashes, so a file matches when its computed blob id
equals the one GitHub reports. That makes the comparison exact without cloning
and without trusting file sizes.

This answers whether a restored repository adds anything to the absorbed copy
that already exists in PhenoShared.

Usage:
    python snapshot_vs_tree.py <repo> <local-dir>
"""
import hashlib
import json
import os
import subprocess
import sys

OWNER = "KooshaPari"


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def blob_id(path):
    with open(path, "rb") as f:
        data = f.read()
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def repo_tree(repo):
    code, out, err = sh(["gh", "api", "repos/%s/%s" % (OWNER, repo), "--jq", ".default_branch"])
    if code != 0:
        raise SystemExit("no repo %s" % repo)
    ref = out.strip()
    code, out, err = sh(["gh", "api",
                         "repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, repo, ref)])
    if code != 0:
        raise SystemExit("no tree for %s" % repo)
    d = json.loads(out)
    if d.get("truncated"):
        raise SystemExit("tree truncated; comparison would be partial")
    return {e["path"]: e["sha"] for e in d["tree"] if e.get("type") == "blob"}, ref


def local_tree(root):
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "target")]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace("\\", "/")
            try:
                found[rel] = blob_id(full)
            except OSError:
                continue
    return found


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    repo, root = sys.argv[1], sys.argv[2]
    if not os.path.isdir(root):
        raise SystemExit("no such directory: %s" % root)

    a, ref = repo_tree(repo)
    b = local_tree(root)
    same = [p for p in set(a) & set(b) if a[p] == b[p]]
    diff = [p for p in set(a) & set(b) if a[p] != b[p]]
    only_repo = sorted(set(a) - set(b))
    only_local = sorted(set(b) - set(a))

    print("repo %s@%s: %d files" % (repo, ref, len(a)))
    print("local %s: %d files" % (root, len(b)))
    print()
    print("identical      %d" % len(same))
    print("differing      %d" % len(diff))
    print("only in repo   %d" % len(only_repo))
    print("only in local  %d" % len(only_local))
    print()
    if only_repo:
        print("paths the repo has that the absorbed tree lacks (would be added):")
        for p in only_repo[:25]:
            print("   %s" % p)
        if len(only_repo) > 25:
            print("   ... %d more" % (len(only_repo) - 25))
        print()
    if diff:
        print("paths present on both sides with different content:")
        for p in diff[:25]:
            print("   %s" % p)
        if len(diff) > 25:
            print("   ... %d more" % (len(diff) - 25))
        print()
    if not only_repo and not diff:
        print("VERDICT: the absorbed tree already holds every file the repo has.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
