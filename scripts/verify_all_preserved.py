#!/usr/bin/env python3
"""Verify every preserved ref namespace against its live source.

Two questions per repo, both answered from the server rather than from a local
checkout:

  1. Does the registry hold every ref the source holds, at the same tip?
  2. Does the registry hold anything the source does not (a leftover from an
     earlier push, which would misrepresent the repo)?

A local fetch is deliberately not used. Windows is case-insensitive, and a repo
with `release-preview-H1` alongside `release-preview-h1` cannot be materialised
there at all; git aborts the fetch and the check reports a false failure. That
exact bug made `claude-remember` look 1 ref short when it was complete.

Usage:
    python verify_all_preserved.py            # every preserved namespace
    python verify_all_preserved.py --deleted  # only namespaces with no live repo
"""
import json
import subprocess
import sys

OWNER = "KooshaPari"
REGISTRY = "PhenoRegistry"


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def ls_remote(url, pattern=None):
    args = ["git", "ls-remote", "--refs", url]
    if pattern:
        args.append(pattern)
    code, out, err = sh(args)
    if code != 0:
        raise RuntimeError("ls-remote %s failed: %s" % (url, err.strip()[:200]))
    refs = {}
    for line in out.splitlines():
        if "\t" not in line:
            continue
        sha, _, name = line.partition("\t")
        refs[name] = sha
    return refs


def preserved_namespaces():
    reg = ls_remote("https://github.com/%s/%s.git" % (OWNER, REGISTRY))
    repos = set()
    for name in reg:
        parts = name.split("/")
        if len(parts) >= 5 and parts[1] == "preserved":
            repos.add(parts[2])
    return sorted(repos)


def live_repos():
    code, out, err = sh(["gh", "repo", "list", OWNER, "--limit", "300",
                         "--json", "name"])
    if code != 0:
        raise RuntimeError("gh repo list failed: %s" % err.strip()[:200])
    return {x["name"] for x in json.loads(out)}


def main():
    deleted_only = "--deleted" in sys.argv
    live = live_repos()
    names = preserved_namespaces()

    ok, bad, gone = 0, 0, 0
    failures = []
    for repo in names:
        if deleted_only and repo in live:
            continue
        try:
            src = ls_remote("https://github.com/%s/%s.git" % (OWNER, repo))
        except RuntimeError as exc:
            # A 404 here means the source is deleted, which is the expected
            # end state; the registry is then the only copy and there is
            # nothing to compare against.
            if "404" in str(exc) or "not found" in str(exc).lower() or "Repository not found" in str(exc):
                print("%-46s source gone (registry is sole copy)" % repo)
                gone += 1
                continue
            print("%-46s SOURCE ERROR %s" % (repo, str(exc)[:90]))
            bad += 1
            failures.append(repo)
            continue

        prefix = "refs/preserved/%s/" % repo
        reg = {k[len(prefix):]: v
               for k, v in ls_remote("https://github.com/%s/%s.git" % (OWNER, REGISTRY),
                                     "refs/preserved/%s/*" % repo).items()
               if k.startswith(prefix)}
        src = {k[len("refs/"):]: v for k, v in src.items() if k.startswith("refs/")}

        missing = sorted(set(src) - set(reg))
        extra = sorted(set(reg) - set(src))
        differ = sorted(k for k in set(src) & set(reg) if src[k] != reg[k])

        if not (missing or extra or differ):
            print("%-46s OK  %d refs" % (repo, len(src)))
            ok += 1
        else:
            print("%-46s FAIL  src=%d reg=%d  missing=%d extra=%d differ=%d"
                  % (repo, len(src), len(reg), len(missing), len(extra), len(differ)))
            for k in missing[:5]:
                print("      MISSING %s" % k)
            for k in extra[:5]:
                print("      EXTRA   %s" % k)
            for k in differ[:5]:
                print("      DIFFER  %s" % k)
            bad += 1
            failures.append(repo)

    print()
    print("verified %d, failed %d, source gone %d" % (ok, bad, gone))
    if failures:
        print("failed: %s" % ", ".join(failures))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
