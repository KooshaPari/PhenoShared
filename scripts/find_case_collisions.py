#!/usr/bin/env python3
"""Find ref names that collide on a case-insensitive filesystem.

Windows cannot check out two refs whose paths differ only by case. A repo with
such refs (e.g. release-preview-a and release-preview-A) cannot be fetched into
a worktree at all, which breaks `git bundle` and any clone-and-push fallback.
The refs themselves are fine on GitHub; only the local materialisation fails.
"""
import subprocess
import sys


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def main():
    repos = sys.argv[1:]
    if not repos:
        print("usage: find_case_collisions.py <repo> [repo ...]")
        return 2
    total_collisions = 0
    for repo in repos:
        code, out, err = sh(["git", "ls-remote", "--refs",
                             "https://github.com/KooshaPari/%s.git" % repo])
        if code != 0:
            print("%-40s ls-remote failed: %s" % (repo, err.strip()[:120]))
            continue
        names = [line.split("\t")[1] for line in out.splitlines() if "\t" in line]
        low = {}
        for n in names:
            low.setdefault(n.lower(), []).append(n)
        coll = {k: v for k, v in low.items() if len(v) > 1}
        if coll:
            total_collisions += len(coll)
            print("%-40s %d refs, %d CASE COLLISIONS" % (repo, len(names), len(coll)))
            for v in coll.values():
                print("    %s" % "  vs  ".join(sorted(v)))
        else:
            print("%-40s %d refs, clean" % (repo, len(names)))
    print()
    print("case-colliding names total: %d" % total_collisions)
    return 1 if total_collisions else 0


if __name__ == "__main__":
    sys.exit(main())
