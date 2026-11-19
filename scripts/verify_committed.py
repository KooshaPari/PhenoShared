#!/usr/bin/env python3
"""Does the committed tree match the source repository, byte for byte?

absorb_public.py verifies the working tree. That is not the same claim as "what
was committed is correct", because git normalises line endings on the way in via
.gitattributes. If the normalisation changed any byte, the commit would differ from
the source even though the copy was right, and every future verification would be
against the wrong object.

This compares git's own blob ids for the paths under apps/<name>/ or libs/<name>/
in a commit against the source repository's tree.

Usage:
    python verify_committed.py <ref> app:<repo> [lib:<repo> ...]
"""
import json
import subprocess
import sys

OWNER = "KooshaPari"
SHARED = r"C:\Users\koosh\PhenoShared"


def sh(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout, p.stderr


def source_tree(repo):
    code, out, _ = sh(["gh", "api", "repos/%s/%s" % (OWNER, repo), "--jq", ".default_branch"])
    if code != 0:
        return None
    ref = out.strip()
    code, out, _ = sh(["gh", "api", "repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, repo, ref)])
    if code != 0:
        return None
    d = json.loads(out)
    return {e["path"]: e["sha"] for e in d["tree"] if e.get("type") == "blob"}


def committed_tree(ref, prefix):
    code, out, _ = sh(["git", "-C", SHARED, "ls-tree", "-r", ref, "--", prefix])
    if code != 0:
        return None
    found = {}
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) >= 4 and parts[1] == "blob":
            rel = parts[3][len(prefix):].lstrip("/")
            found[rel] = parts[2]
    return found


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    ref = sys.argv[1]
    specs = sys.argv[2:]
    bad = 0
    for spec in specs:
        kind, _, repo = spec.partition(":")
        prefix = "apps/%s/" % repo if kind == "app" else "libs/%s/" % repo
        src = source_tree(repo)
        com = committed_tree(ref, prefix)
        if src is None or com is None:
            print("%-32s UNREADABLE" % repo)
            bad += 1
            continue
        missing = sorted(set(src) - set(com))
        differ = [p for p in set(src) & set(com) if src[p] != com[p]]
        if missing or differ:
            print("%-32s MISMATCH  missing=%d differ=%d" % (repo, len(missing), len(differ)))
            for p in differ[:5]:
                print("    differs: %s" % p)
            bad += 1
        else:
            print("%-32s OK  %d/%d blobs identical in %s" % (repo, len(src), len(src), ref))
    print()
    print("mismatched %d of %d" % (bad, len(specs)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
