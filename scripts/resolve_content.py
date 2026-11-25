#!/usr/bin/env python3
"""Find where a repository's content actually lives inside PhenoShared.

The inventory classified twelve repositories as `absorb-or-keep` because no
absorbed directory matched their name at the usual three locations. That is a
name-based check, and BytePort already proved name-based checks wrong: its files
sit in two trees at once, and one of them was not where the name suggested.

So this searches the whole working tree for directory names that could belong to
each repository, then measures coverage against every candidate with git blob ids.

A repository is only "not absorbed" if the content is nowhere, and that needs a
search rather than a lookup.

Usage:
    python resolve_content.py <repo> [repo ...]
"""
import hashlib
import json
import os
import re
import subprocess
import sys

OWNER = "KooshaPari"
SHARED = r"C:\Users\koosh\PhenoShared"
MAX_DEPTH = 4
SKIP_DIRS = {".git", "node_modules", "target", "dist", "build", ".venv", "venv"}


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def candidate_dirs():
    """Map normalised directory name -> list of relative paths."""
    found = {}
    root = SHARED
    base_depth = root.rstrip("\\").count("\\")
    for dirpath, dirnames, _ in os.walk(root):
        depth = dirpath.count("\\") - base_depth
        if depth >= MAX_DEPTH:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel = os.path.relpath(dirpath, root).replace("\\", "/")
        if rel == ".":
            continue
        found.setdefault(norm(os.path.basename(dirpath)), []).append(rel)
    return found


def blob_id(path):
    with open(path, "rb") as f:
        data = f.read()
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def local_blobs(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace("\\", "/")
            try:
                out[rel] = blob_id(full)
            except OSError:
                continue
    return out


def repo_tree(repo):
    code, out, err = sh(["gh", "api", "repos/%s/%s" % (OWNER, repo), "--jq", ".default_branch"])
    if code != 0:
        return None
    ref = out.strip()
    code, out, err = sh(["gh", "api",
                         "repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, repo, ref)])
    if code != 0:
        return None
    d = json.loads(out)
    if d.get("truncated"):
        return None
    return {e["path"]: e["sha"] for e in d["tree"] if e.get("type") == "blob"}


def main():
    repos = sys.argv[1:]
    if not repos:
        print(__doc__)
        return 2

    index = candidate_dirs()
    for repo in repos:
        print("=== %s ===" % repo)
        matches = index.get(norm(repo), [])
        # Also try a few name transforms that the layout actually uses.
        for variant in (repo.replace("-", ""), repo.replace("-", "_"),
                        "absorption-residue-" + repo):
            for p in index.get(norm(variant), []):
                if p not in matches:
                    matches.append(p)

        tree = repo_tree(repo)
        if tree is None:
            print("  cannot read the repository tree")
            print()
            continue
        print("  repository files: %d" % len(tree))

        if not matches:
            print("  no directory in PhenoShared has a matching name")
            print("  => content is NOT absorbed under any recognisable name")
            print()
            continue

        for rel in matches:
            full = os.path.join(SHARED, rel.replace("/", os.sep))
            blobs = local_blobs(full)
            common = set(tree) & set(blobs)
            same = [p for p in common if tree[p] == blobs[p]]
            diff = [p for p in common if tree[p] != blobs[p]]
            missing = sorted(set(tree) - set(blobs))
            print("  candidate %-52s %d files" % (rel[:52], len(blobs)))
            print("     identical %-6d different %-6d repo-only %d"
                  % (len(same), len(diff), len(missing)))
            if missing and len(missing) <= 6:
                for p in missing:
                    print("        repo-only: %s" % p)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
