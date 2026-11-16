#!/usr/bin/env python3
"""Prove a repository is empty before authorising its deletion.

"0 KB" from the API is not proof. A repo can hold a README, a licence, or a
single commit with real work and still round to zero in the size field, because
that field is disk usage of packed objects, not content.

So this walks every ref and lists every file path. A repository is reported
EMPTY only when no ref carries a single file. Anything else is reported with the
paths it holds, so a deletion cannot quietly discard work.

Read-only. It deletes nothing.

Usage:
    python prove_empty.py <repo> [repo ...]
"""
import json
import subprocess
import sys

OWNER = "KooshaPari"


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def refs_of(repo):
    code, out, err = sh(["git", "ls-remote", "--refs",
                         "https://github.com/%s/%s.git" % (OWNER, repo)])
    if code != 0:
        return None, err
    return [l.split("\t")[1] for l in out.splitlines() if "\t" in l], None


def tree_of(repo, ref):
    """All paths under a ref, via the API so nothing is cloned."""
    sha = ref.split("/")[-1]
    path = "repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, repo, sha)
    # The ref's *commit* has to be resolved to a tree first.
    code, out, err = sh(["git", "ls-remote",
                         "https://github.com/%s/%s.git" % (OWNER, repo), ref])
    if code != 0:
        return None
    commit = out.split("\t")[0].strip()
    code, out, err = sh(["gh", "api", "repos/%s/%s/git/commits/%s"
                         % (OWNER, repo, commit), "--jq", ".tree.sha"])
    if code != 0:
        return None
    treesha = out.strip()
    code, out, err = sh(["gh", "api",
                         "repos/%s/%s/git/trees/%s?recursive=1"
                         % (OWNER, repo, treesha), "--jq",
                         '.tree[] | select(.type=="blob") | .path'])
    if code != 0:
        return None
    return [p for p in out.splitlines() if p.strip()]


def main():
    repos = sys.argv[1:]
    if not repos:
        print(__doc__)
        return 2
    empty, nonempty, failed = [], [], []
    for repo in repos:
        refs, err = refs_of(repo)
        if refs is None:
            print("%-40s UNREACHABLE %s" % (repo, str(err).strip()[:60]))
            failed.append(repo)
            continue
        if not refs:
            print("%-40s EMPTY (no refs at all)" % repo)
            empty.append(repo)
            continue
        allpaths = []
        for ref in refs:
            paths = tree_of(repo, ref)
            if paths is None:
                allpaths = None
                break
            allpaths.extend(paths)
        if allpaths is None:
            print("%-40s UNREADABLE tree (%d refs)" % (repo, len(refs)))
            failed.append(repo)
            continue
        unique = sorted(set(allpaths))
        if not unique:
            print("%-40s EMPTY (%d refs, 0 files)" % (repo, len(refs)))
            empty.append(repo)
        else:
            print("%-40s HOLDS %d files (%d refs)" % (repo, len(unique), len(refs)))
            for p in unique[:12]:
                print("      %s" % p)
            if len(unique) > 12:
                print("      ... %d more" % (len(unique) - 12))
            nonempty.append(repo)

    print()
    print("empty %d, holds content %d, unreadable %d"
          % (len(empty), len(nonempty), len(failed)))
    if nonempty:
        print("HOLDS CONTENT, do not delete: %s" % ", ".join(nonempty))
    if failed:
        print("UNREADABLE, do not delete: %s" % ", ".join(failed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
