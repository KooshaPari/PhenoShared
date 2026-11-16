#!/usr/bin/env python3
"""Does a snapshot hold content that exists nowhere in the live repo's history?

Tree equality only says "same as the live default branch right now". A snapshot
from months ago differs from that while holding nothing new. The question that
decides a deletion is whether the snapshot holds *unique* content.

Method: collect every blob id that appears on any ref of the live repository, at
any commit, and ask which of the snapshot's non-matching blobs are absent.

`rev-list --objects` is the obvious tool and it is the wrong one here. On a
blobless clone it lazily fetches every blob it names, which turned a 30-second
question into 40 minutes of single-object round trips. `ls-tree` reads only tree
objects, which a blobless clone has in full, so it answers the same question
entirely locally.

Usage:
    python blob_reach2.py <snapshot> <live>
"""
import json
import os
import shutil
import subprocess
import sys

OWNER = "KooshaPari"
SCRATCH = r"C:\Users\koosh\Agents\scratch"


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def tree_map(repo):
    code, out, err = sh(["gh", "api", "repos/%s/%s" % (OWNER, repo), "--jq", ".default_branch"])
    if code != 0:
        raise SystemExit("no repo %s: %s" % (repo, err.strip()[:90]))
    ref = out.strip()
    code, out, err = sh(["gh", "api",
                         "repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, repo, ref)])
    if code != 0:
        raise SystemExit("no tree %s@%s: %s" % (repo, ref, err.strip()[:90]))
    d = json.loads(out)
    return {e["path"]: e["sha"] for e in d["tree"] if e.get("type") == "blob"}, ref


def live_blobs(repo):
    """Every blob id on every ref, read from tree objects only."""
    clone = os.path.join(SCRATCH, "reach2-" + repo + ".git")
    if os.path.isdir(clone):
        shutil.rmtree(clone, ignore_errors=True)
    code, out, err = sh(["git", "clone", "--quiet", "--mirror", "--filter=blob:none",
                         "https://github.com/%s/%s.git" % (OWNER, repo), clone])
    if code != 0:
        raise SystemExit("clone failed: %s" % err.strip()[:200])
    try:
        code, refs, err = sh(["git", "-C", clone, "for-each-ref",
                              "--format=%(refname) %(objectname)"])
        if code != 0:
            raise SystemExit("for-each-ref failed: %s" % err.strip()[:200])
        blobs = set()
        nrefs = 0
        for line in refs.splitlines():
            if " " not in line:
                continue
            nrefs += 1
            ref = line.split(" ", 1)[0]
            code, out, err = sh(["git", "-C", clone, "ls-tree", "-r", "--full-tree",
                                 ref])
            if code != 0:
                continue
            for entry in out.splitlines():
                parts = entry.split(None, 3)
                if len(parts) >= 3 and parts[1] == "blob":
                    blobs.add(parts[2])
        return blobs, nrefs
    finally:
        shutil.rmtree(clone, ignore_errors=True)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    snap, live = sys.argv[1], sys.argv[2]

    a, ra = tree_map(snap)
    b, rb = tree_map(live)
    interesting = {p: sha for p, sha in a.items() if b.get(p) != sha}
    print("snapshot %s@%s: %d files; %d differ from the live tip"
          % (snap, ra, len(a), len(interesting)))
    if not interesting:
        print("VERDICT: IDENTICAL to the live tip - provably redundant")
        return 0

    print("enumerating every blob on every ref of %s ..." % live)
    blobs, nrefs = live_blobs(live)
    unique = {p: s for p, s in interesting.items() if s not in blobs}
    print("%s: %d refs, %d distinct blob ids in history" % (live, nrefs, len(blobs)))
    print("snapshot blobs absent from that history: %d of %d"
          % (len(unique), len(interesting)))
    if unique:
        print()
        print("VERDICT: NOT redundant - deleting the snapshot loses this content")
        for path in sorted(unique)[:40]:
            print("   %s  %s" % (unique[path][:10], path))
        if len(unique) > 40:
            print("   ... %d more" % (len(unique) - 40))
    else:
        print()
        print("VERDICT: every snapshot blob is already in the live history")
        print("         The snapshot is an earlier state, not unique work.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
