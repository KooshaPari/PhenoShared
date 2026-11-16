#!/usr/bin/env python3
"""Materialise the snapshot-only blobs of a repo into a local branch, for review.

The snapshots imported on 2026-11-14 hold blobs that exist nowhere in the live
repository's history. Recovering them means writing those exact bytes back, so
this reads each blob through the API (base64) rather than re-running any build,
and commits them on a new local branch. It does not push.

Classification matters before writing anything:
  NEW PATH   the path is absent from the live tip - a straight addition
  CHANGED    the path exists but holds different bytes - the snapshot may be
             older or newer, and that cannot be settled by hashes alone
  ARTIFACT   compiled output; skipped by default

Usage:
    python recover_blobs.py <snapshot> <live> <branch> [--include-changed]
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import time

OWNER = "KooshaPari"
SCRATCH = r"C:\Users\koosh\Agents\scratch"

# Compiled output is reproducible from source and does not belong in a recovery.
ARTIFACT_SUFFIXES = (".dylib", ".so", ".dll", ".exe", ".o", ".a", ".rlib", ".wasm")


def sh(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True)
    return p.returncode, p.stdout, p.stderr


def api(path):
    code, out, err = sh(["gh", "api", path])
    if code != 0:
        return None
    return out


def tree_map(repo):
    raw = api("repos/%s/%s" % (OWNER, repo))
    ref = json.loads(raw)["default_branch"]
    raw = api("repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, repo, ref))
    d = json.loads(raw)
    if d.get("truncated"):
        raise SystemExit("%s tree truncated by the API" % repo)
    return {e["path"]: e["sha"] for e in d["tree"] if e.get("type") == "blob"}, ref


def live_blob_set(repo):
    # A unique destination per run. A fixed path collides with whatever a
    # previous interrupted run left behind, and git reports that as "not a git
    # repository" from inside its own repack step rather than as a stale dir.
    clone = os.path.join(SCRATCH, "blobs-%s-%d.git" % (repo, int(time.time())))
    code, _, err = sh(["git", "clone", "--quiet", "--mirror", "--filter=blob:none",
                       "https://github.com/%s/%s.git" % (OWNER, repo), clone])
    if code != 0:
        raise SystemExit("clone failed: %s" % err.decode("utf-8", "replace")[:200])
    try:
        _, refs, _ = sh(["git", "-C", clone, "for-each-ref",
                         "--format=%(refname)"])
        blobs = set()
        for ref in refs.decode("utf-8", "replace").split():
            _, out, _ = sh(["git", "-C", clone, "ls-tree", "-r", "--full-tree", ref])
            for entry in out.decode("utf-8", "replace").splitlines():
                parts = entry.split(None, 3)
                if len(parts) >= 3 and parts[1] == "blob":
                    blobs.add(parts[2])
        return blobs
    finally:
        shutil.rmtree(clone, ignore_errors=True)


def blob_bytes(sha):
    raw = api("repos/%s/%s/git/blobs/%s" % (OWNER, SNAPSHOT, sha))
    if raw is None:
        return None
    return base64.b64decode(json.loads(raw)["content"])


SNAPSHOT = None


def main():
    global SNAPSHOT
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    include_changed = "--include-changed" in sys.argv
    if len(args) < 3:
        print(__doc__)
        return 2
    SNAPSHOT, live, branch = args[0], args[1], args[2]

    a, aref = tree_map(SNAPSHOT)
    b, bref = tree_map(live)
    blobs = live_blob_set(live)

    unique = {p: s for p, s in a.items() if s not in blobs and b.get(p) != s}
    new_path, changed, artifact = {}, {}, {}
    for p, s in unique.items():
        if p.endswith(ARTIFACT_SUFFIXES):
            artifact[p] = s
        elif p not in b:
            new_path[p] = s
        else:
            changed[p] = s

    print("snapshot %s@%s vs live %s@%s" % (SNAPSHOT, aref, live, bref))
    print("unique blobs: %d  (new path %d, changed %d, artifact %d)"
          % (len(unique), len(new_path), len(changed), len(artifact)))
    print()
    for p in sorted(new_path):
        print("  NEW      %s" % p)
    for p in sorted(changed):
        print("  CHANGED  %s" % p)
    for p in sorted(artifact):
        print("  ARTIFACT %s  (skipped)" % p)
    print()

    selected = dict(new_path)
    if include_changed:
        selected.update(changed)
    if not selected:
        print("nothing selected for recovery")
        return 0

    work = os.path.join(SCRATCH, "recover-%s-%d" % (live, int(time.time())))
    code, _, err = sh(["git", "clone", "--quiet", "--depth", "1",
                       "https://github.com/%s/%s.git" % (OWNER, live), work])
    if code != 0:
        raise SystemExit("clone failed: %s" % err.decode("utf-8", "replace")[:200])

    sh(["git", "-C", work, "config", "user.name", "Koosha Paridehpour"])
    sh(["git", "-C", work, "config", "user.email",
        "42529354+KooshaPari@users.noreply.github.com"])
    code, _, _ = sh(["git", "-C", work, "checkout", "-q", "-b", branch])
    if code != 0:
        raise SystemExit("could not create branch %s" % branch)

    written = 0
    for path, sha in sorted(selected.items()):
        data = blob_bytes(sha)
        if data is None:
            print("  FAILED to read blob for %s" % path)
            continue
        dest = os.path.join(work, path.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        written += 1

    sh(["git", "-C", work, "add", "-A"])
    code, out, err = sh(["git", "-C", work, "commit", "-q", "-m",
                         "recover: restore %d blobs that exist only in the "
                         "audit-snapshot-%s import" % (written, live)])
    if code != 0:
        print("commit failed: %s" % err.decode("utf-8", "replace")[:300])
        return 2

    _, stat, _ = sh(["git", "-C", work, "show", "--stat", "--oneline", "HEAD"])
    print(stat.decode("utf-8", "replace")[-2000:])
    print()
    print("branch %s built in %s" % (branch, work))
    print("not pushed. review, then push with:")
    print("  git -C %s push -u origin %s" % (work, branch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
