#!/usr/bin/env python3
"""Record exactly what an absorbed tree is missing, and why.

absorb_public.py proves the working tree matches the source, and verify_committed.py
proves which blobs actually reached the commit. Neither says what was dropped. The
first run of these tools left 509 files out of the commit - 452 in one repository -
and nothing in the tree recorded their absence.

An absorption manifest is that record. For each repository it captures:

  source        repository, ref, total files at that ref
  committed     blobs actually present under apps/<name>/ or libs/<name>/
  identical     committed blobs whose id equals the source blob id
  differs       committed blobs whose bytes were normalised on the way in
  excluded      source paths absent from the commit, each with the reason:
                a build-artifact directory skipped at copy time, or a .gitignore
                rule matched at commit time

The manifest is written beside the ledger, not inside the absorbed tree, so the
tree stays a faithful copy and the record does not become part of the thing it
describes.

Usage:
    python record_exclusions.py app:<repo> [lib:<repo> ...]
    python record_exclusions.py --check app:<repo>      # fail if a manifest is stale
"""
import json
import os
import subprocess
import sys

OWNER = "KooshaPari"
SHARED = r"C:\Users\koosh\PhenoShared"
OUT = os.path.join(SHARED, "docs", "absorption-ledger", "absorptions")

# Directories skipped when copying, because they are build output rather than
# source. Recorded here so the manifest can name the reason for each exclusion.
SKIP_DIRS = {".git", "node_modules", "target", "dist", "build", ".venv", "venv",
             "__pycache__", ".next", ".turbo"}


def sh(args, cwd=SHARED):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout, p.stderr


def norm_git_path(path):
    """Normalise a pathname from git output for comparison.

    git -v/check-ignore may quote paths and, on Windows, emit CRLF-terminated
    lines that leave a trailing \r. With core.quotePath/git quoting this can
    appear as a quoted path ending in the two-character escape sequence \\r as
    well as a literal CR. Strip surrounding quotes, trailing CR/\\r escapes, and
    a leading '/' so keys match the candidate paths we look up.
    """
    if path is None:
        return path
    p = path.rstrip("\r\n")
    if len(p) >= 2 and p[0] == '"' and p[-1] == '"':
        p = p[1:-1]
    # Strip git's quoted CR escape sequence(s) and any literal CR characters.
    while p.endswith("\\r") or p.endswith("\r"):
        if p.endswith("\\r"):
            p = p[:-2]
        if p.endswith("\r"):
            p = p[:-1]
    return p.lstrip("/")


def source_tree(repo):
    code, out, _ = sh(["gh", "api", "repos/%s/%s" % (OWNER, repo), "--jq", ".default_branch"])
    if code != 0:
        return None, None
    ref = out.strip()
    code, out, _ = sh(["gh", "api",
                       "repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, repo, ref)])
    if code != 0:
        return None, None
    d = json.loads(out)
    return {e["path"]: e["sha"] for e in d["tree"] if e.get("type") == "blob"}, ref


def committed_blobs(prefix):
    code, out, _ = sh(["git", "ls-tree", "-r", "HEAD", "--", prefix])
    if code != 0:
        return {}
    found = {}
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) >= 4 and parts[1] == "blob":
            found[parts[3][len(prefix):].lstrip("/")] = parts[2]
    return found


def ignored_under(prefix, candidates):
    """Which of the candidate paths does .gitignore suppress, and by which rule.

    Both the paths we feed git and the paths it reports are normalised with
    norm_git_path so quoted/CRLF/leading-slash forms compare equal.
    """
    if not candidates:
        return {}
    norm_prefix = norm_git_path(prefix)
    norm_candidates = [norm_git_path(c) for c in candidates]
    proc = subprocess.run(["git", "check-ignore", "-v", "--no-index", "--stdin"],
                          cwd=SHARED, capture_output=True, text=True,
                          errors="replace",
                          input="\n".join(norm_prefix + c for c in norm_candidates))
    rules = {}
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        src, _, pattern = parts[0].partition(":")
        reported = norm_git_path(parts[1])
        if reported.startswith(norm_prefix):
            reported = reported[len(norm_prefix):]
        else:
            reported = norm_git_path(reported)
        rules[reported] = "%s:%s" % (os.path.basename(src), pattern)
    return rules


def build_manifest(kind, repo):
    prefix = "apps/%s/" % repo if kind == "app" else "libs/%s/" % repo
    src, ref = source_tree(repo)
    if src is None:
        return None
    com = committed_blobs(prefix)
    identical = [p for p in set(src) & set(com) if src[p] == com[p]]
    differ = sorted(p for p in set(src) & set(com) if src[p] != com[p])
    absent = sorted(set(src) - set(com))

    skip_hit = {}
    ignore_hit = {}
    remaining = []
    for path in absent:
        top = path.split("/")[0]
        if top in SKIP_DIRS or any("/%s/" % d in "/" + path for d in SKIP_DIRS):
            skip_hit[path] = "build-artifact directory skipped at copy time"
        else:
            remaining.append(path)
    if remaining:
        norm_remaining = [norm_git_path(p) for p in remaining]
        for path, rule in ignored_under(prefix, norm_remaining).items():
            ignore_hit[path] = rule
        for path in norm_remaining:
            if path not in ignore_hit:
                ignore_hit[path] = "absent but not matched by gitignore"

    return {
        "repo": repo,
        "kind": kind,
        "destination": prefix,
        "source_ref": ref,
        "source_files": len(src),
        "committed_files": len(com),
        "identical": len(identical),
        "differs": differ,
        "excluded_skipped_dirs": skip_hit,
        "excluded_by_gitignore": ignore_hit,
        "excluded_total": len(absent),
        "faithful": not differ and not absent,
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    if not args:
        print(__doc__)
        return 2
    os.makedirs(OUT, exist_ok=True)
    stale = 0
    for spec in args:
        kind, _, repo = spec.partition(":")
        m = build_manifest(kind, repo)
        if m is None:
            print("%-32s UNREADABLE" % repo)
            stale += 1
            continue
        path = os.path.join(OUT, "%s.json" % repo)
        state = "FAITHFUL" if m["faithful"] else "INCOMPLETE"
        print("%-32s %-11s %d/%d committed, %d identical, %d differ, %d excluded"
              % (repo, state, m["committed_files"], m["source_files"],
                 m["identical"], len(m["differs"]), m["excluded_total"]))
        if check:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    old = json.load(f)
                if old.get("source_files") != m["source_files"] or \
                        old.get("committed_files") != m["committed_files"]:
                    print("   STALE manifest: source or commit changed")
                    stale += 1
            else:
                print("   MISSING manifest")
                stale += 1
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(m, f, indent=1, sort_keys=True)
    if check:
        print()
        print("stale or missing: %d of %d" % (stale, len(args)))
        return 1 if stale else 0
    print()
    print("manifests written to %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
