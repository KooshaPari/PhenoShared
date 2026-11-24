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
    strict = "--strict" in sys.argv
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

        # `refs/pull/<n>/merge` is a synthetic merge commit GitHub generates and
        # regenerates whenever the base branch moves. Its sha is not content: it
        # changes when unrelated work lands on main. Comparing it produces
        # perpetual false failures, so it is reported separately and never
        # counted as a real mismatch.
        merge_only = [k for k in differ
                      if k.startswith("pull/") and k.endswith("/merge")]
        differ = [k for k in differ if k not in merge_only]

        # A freshly recreated repository (0 KB, one empty commit, refs pushed by
        # a restore) legitimately holds less than the snapshot. Extra refs in
        # the registry are also by design now that stale refs are quarantined
        # under refs/superseded/ rather than deleted. Neither is a fault.
        # What counts as a fault depends on the question being asked.
        #
        # A ref the source has and the registry does not is always a fault: the
        # snapshot does not cover the source, so deleting the source would lose
        # it. That is `missing`.
        #
        # A ref whose tip differs is usually just progress. These repositories
        # are still being developed, so `main` advances and branches move; a
        # snapshot taken yesterday will not equal today's source, and demanding
        # equality would report every live repository as broken forever. That is
        # `differ`, reported but not fatal unless --strict is given, which is the
        # mode to use immediately before authorising a deletion.
        real = bool(missing) or (strict and bool(differ))

        if not real:
            note = ""
            if extra:
                note += "  (+%d registry-only)" % len(extra)
            if merge_only:
                note += "  (%d merge-ref)" % len(merge_only)
            print("%-46s OK  %d refs%s" % (repo, len(src), note))
            ok += 1
        else:
            print("%-46s FAIL  src=%d reg=%d  missing=%d extra=%d differ=%d"
                  % (repo, len(src), len(reg), len(missing), len(extra), len(differ)))
            for k in missing[:5]:
                print("      MISSING %s" % k)
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
