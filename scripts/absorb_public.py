#!/usr/bin/env python3
"""Absorb a public repository's working tree into PhenoShared, proven complete.

Private repositories go to PhenoRegistry via absorb_private.py. Public code has no
equivalent tool, so public absorptions were done by hand - which is how a tree can
be "absorbed" at one revision and drift unnoticed afterwards.

This does the same job for the public side: shallow-clone the repository, copy its
default branch into apps/<name>/ or libs/<name>/, then prove the result by git blob
id. Blob ids are content hashes, so an equal id at the same path means the same
bytes; a file count proves nothing.

Nothing is deleted here. It prints ABSORBED only when the comparison passes.

Usage:
    python absorb_public.py app:<repo> [lib:<repo> ...]
    python absorb_public.py --verify app:<repo>
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

OWNER = "KooshaPari"
SHARED = r"C:\Users\koosh\PhenoShared"
SKIP_DIRS = {".git", "node_modules", "target", "dist", "build", ".venv", "venv",
             "__pycache__", ".next", ".turbo"}


def sh(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, errors="replace")
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
        return None, "no repository"
    ref = out.strip()
    code, out, err = sh(["gh", "api",
                         "repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, repo, ref)])
    if code != 0:
        return None, "no tree"
    d = json.loads(out)
    if d.get("truncated"):
        return None, "tree truncated by the API"
    return {e["path"]: e["sha"] for e in d["tree"] if e.get("type") == "blob"}, ref


def local_tree(root):
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace("\\", "/")
            try:
                found[rel] = blob_id(full)
            except OSError:
                continue
    return found


def verify(dest, repo):
    want, ref = repo_tree(repo)
    if want is None:
        return False, ref
    have = local_tree(dest)
    missing = sorted(set(want) - set(have))
    differ = [p for p in set(want) & set(have) if want[p] != have[p]]
    if missing:
        return False, "%d of %d files missing (e.g. %s)" % (len(missing), len(want), missing[0])
    if differ:
        return False, "%d of %d files differ in content" % (len(differ), len(want))
    return True, "%d/%d files exact at %s" % (len(want), len(want), ref)


def absorb(kind, repo):
    if kind not in ("app", "lib"):
        return False, "kind must be app or lib"
    dest = os.path.join(SHARED, "apps" if kind == "app" else "libs", repo)

    work = os.path.join(os.environ.get("KCODE_SCRATCH_DIR") or os.path.expanduser("~/Agents/scratch"),
                        "absorb-public-%s-%d" % (repo, os.getpid()))
    if os.path.isdir(work):
        shutil.rmtree(work, ignore_errors=True)
    # core.autocrlf must be off. A default Windows clone rewrites LF to CRLF in
    # the working tree, which changes every text file's blob id and makes a
    # correct copy look like it differs in 1,950 of 2,061 files. The comparison is
    # a content hash, so the bytes on disk have to be the bytes in the object.
    code, out, err = sh(["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf",
                         "clone", "--quiet", "--depth", "1",
                         "https://github.com/%s/%s.git" % (OWNER, repo), work])
    if code != 0:
        return False, "clone failed: %s" % err.strip()[:120]

    try:
        if os.path.isdir(dest):
            shutil.rmtree(dest, ignore_errors=True)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copytree(work, dest, ignore=shutil.ignore_patterns(*SKIP_DIRS))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    return verify(dest, repo)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    verify_only = "--verify" in args
    args = [a for a in args if not a.startswith("--")]

    failures = 0
    for spec in args:
        kind, _, repo = spec.partition(":")
        if not repo:
            print("bad spec %r, want app:<repo> or lib:<repo>" % spec)
            failures += 1
            continue
        print("== %s (%s)" % (repo, kind))
        if verify_only:
            dest = os.path.join(SHARED, "apps" if kind == "app" else "libs", repo)
            ok, detail = verify(dest, repo)
        else:
            ok, detail = absorb(kind, repo)
        print("   %s %s" % ("verified" if ok else "INCOMPLETE", detail))
        if not ok:
            failures += 1
        else:
            print("   ABSORBED %s" % repo)

    print()
    print("absorbed %d, incomplete %d" % (len(args) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
