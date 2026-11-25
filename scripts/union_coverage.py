#!/usr/bin/env python3
"""Is every file of a repository present, identically, across several local trees?

A single absorbed directory is often not the whole record: the same project can be
split between `absorption/<name>` and `_archived/<name>`, which is what BytePort
turned out to be. Asking one tree at a time produces a large and entirely
spurious "missing" count.

This takes a repository and any number of local roots and reports, per repository
path, whether some root holds the same bytes anywhere.

Usage:
    python union_coverage.py <repo> <root> [root ...]
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


def blob_id(data):
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
    d = json.loads(out)
    if d.get("truncated"):
        raise SystemExit("tree truncated")
    return {e["path"]: e["sha"] for e in d["tree"] if e.get("type") == "blob"}, ref


def local_blobs(root):
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "target")]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace("\\", "/")
            try:
                with open(full, "rb") as f:
                    found[rel] = blob_id(f.read())
            except OSError:
                continue
    return found


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    repo = sys.argv[1]
    roots = sys.argv[2:]

    a, ref = repo_tree(repo)
    trees = [(r, local_blobs(r)) for r in roots]

    covered = {}
    missing_path = []
    wrong_content = []
    for path, sha in a.items():
        hit = None
        for root, blobs in trees:
            if path in blobs:
                hit = (root, blobs[path])
                break
        if hit is None:
            missing_path.append(path)
        elif hit[1] != sha:
            wrong_content.append((path, hit[0]))
        else:
            covered[path] = hit[0]

    print("repo %s@%s: %d files" % (repo, ref, len(a)))
    for root, blobs in trees:
        print("  root %s: %d files" % (root, len(blobs)))
    print()
    print("covered identically       %d" % len(covered))
    print("present but different     %d" % len(wrong_content))
    print("absent from every root    %d" % len(missing_path))
    print()
    if missing_path:
        print("absent paths:")
        for p in missing_path[:25]:
            print("   %s" % p)
        if len(missing_path) > 25:
            print("   ... %d more" % (len(missing_path) - 25))
        print()
    if wrong_content:
        print("different content (first root that has the path):")
        for p, root in wrong_content[:15]:
            print("   %s   [%s]" % (p, os.path.basename(root)))
        if len(wrong_content) > 15:
            print("   ... %d more" % (len(wrong_content) - 15))
        print()
    if not missing_path:
        print("VERDICT: every repository path exists in at least one local tree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
