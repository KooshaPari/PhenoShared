#!/usr/bin/env python3
"""Is a snapshot repository redundant with a live one?

A snapshot and its live counterpart are compared by content, not by name or by
file count. Git blob ids are content hashes, so a path that holds the same blob
id on both sides holds the same bytes. Comparing the maps is therefore exact:

  IDENTICAL   every path matches - the snapshot is provably redundant
  DIFFERS     some paths differ; it holds content the live repo does not
  SUBSET      every snapshot path is in the live repo, but the live one has more
  ORPHAN      nothing comparable, so redundancy cannot be claimed

"Probably duplicated" is not grounds for deleting 22,552 files, which is why
this exists. Read-only.

Usage:
    python tree_compare.py snapshot:live [snapshot:live ...]
"""
import json
import subprocess
import sys

OWNER = "KooshaPari"


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def tree_map(repo, ref=None):
    """path -> blob sha for the whole tree at ref (default branch if None)."""
    if ref is None:
        code, out, err = sh(["gh", "api", "repos/%s/%s" % (OWNER, repo),
                             "--jq", ".default_branch"])
        if code != 0:
            return None, "no repo: %s" % err.strip()[:70]
        ref = out.strip()

    code, out, err = sh(["gh", "api",
                         "repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, repo, ref)])
    if code != 0:
        return None, "no tree for %s@%s: %s" % (repo, ref, err.strip()[:70])
    d = json.loads(out)
    if d.get("truncated"):
        return None, "tree truncated by the API; comparison would be partial"
    return {e["path"]: e["sha"] for e in d.get("tree", [])
            if e.get("type") == "blob"}, ref


def main():
    pairs = sys.argv[1:]
    if not pairs:
        print(__doc__)
        return 2
    for pair in pairs:
        snap, _, live = pair.partition(":")
        if not live:
            print("bad pair %r, want snapshot:live" % pair)
            continue
        print("=== %s  vs  %s ===" % (snap, live))
        a, ra = tree_map(snap)
        if a is None:
            print("   SKIP  %s" % ra)
            continue
        b, rb = tree_map(live)
        if b is None:
            print("   SKIP  %s" % rb)
            continue

        common = set(a) & set(b)
        same = [p for p in common if a[p] == b[p]]
        diff = [p for p in common if a[p] != b[p]]
        only_a = set(a) - set(b)
        only_b = set(b) - set(a)

        print("   %s@%s: %d files" % (snap, ra, len(a)))
        print("   %s@%s: %d files" % (live, rb, len(b)))
        print("   shared path: %d identical, %d differing" % (len(same), len(diff)))
        print("   only in snapshot: %d" % len(only_a))
        print("   only in live:     %d" % len(only_b))

        if not only_a and not diff and not only_b:
            print("   VERDICT: IDENTICAL - provably redundant")
        elif not only_a and not diff:
            print("   VERDICT: SUBSET - snapshot adds nothing, live has more")
        elif len(only_a) == 0 and len(diff) == 0:
            print("   VERDICT: IDENTICAL")
        else:
            print("   VERDICT: DIFFERS - snapshot holds content the live repo lacks")
            for p in sorted(only_a)[:8]:
                print("      snapshot-only %s" % p)
            for p in sorted(diff)[:5]:
                print("      differs %s" % p)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
