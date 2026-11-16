#!/usr/bin/env python3
"""Is the registry's absorbed tree complete against the live repository?

A repository is only safe to delete when its files exist somewhere else. For the
three `delete-eligible` repos that "somewhere else" is
`PhenoRegistry/repos/<name>/tree/`, so this compares that subtree against the live
repository's default branch by git blob id - which is a content hash, so equality
per path means every byte arrived.

The registry tree is reached by walking three tree objects (root -> repos ->
<name> -> tree) rather than requesting a recursive listing of an 8.8 GB
repository, which times out.

Usage:
    python registry_coverage.py <repo> [repo ...]
"""
import json
import subprocess
import sys

OWNER = "KooshaPari"
REGISTRY = "PhenoRegistry"


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def api(path):
    code, out, err = sh(["gh", "api", path])
    if code != 0:
        return None
    return json.loads(out)


def find_entry(tree_sha, name):
    """Entry (name, sha, type) inside one tree level. No recursion."""
    d = api("repos/%s/%s/git/trees/%s" % (OWNER, REGISTRY, tree_sha))
    if not d:
        return None
    for e in d.get("tree", []):
        if e["path"] == name:
            return e
    return None


def registry_tree(repo):
    d = api("repos/%s/%s/commits/main" % (OWNER, REGISTRY))
    if not d:
        return None, "cannot read registry main"
    root = d["commit"]["tree"]["sha"]
    e_repos = find_entry(root, "repos")
    if not e_repos:
        return None, "no repos/ in the registry"
    e_name = find_entry(e_repos["sha"], repo)
    if not e_name:
        return None, "no repos/%s/" % repo
    e_tree = find_entry(e_name["sha"], "tree")
    if not e_tree:
        return None, "repos/%s/ has no tree/" % repo
    d = api("repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, REGISTRY, e_tree["sha"]))
    if not d:
        return None, "cannot read the content tree"
    if d.get("truncated"):
        return None, "content tree listing truncated"
    return {e["path"]: e["sha"] for e in d["tree"] if e.get("type") == "blob"}, None


def live_tree(repo):
    d = api("repos/%s/%s" % (OWNER, repo))
    if not d:
        return None, "cannot read the repository"
    ref = d["default_branch"]
    d = api("repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, repo, ref))
    if not d:
        return None, "cannot read the branch tree"
    if d.get("truncated"):
        return None, "branch tree listing truncated"
    return {e["path"]: e["sha"] for e in d["tree"] if e.get("type") == "blob"}, ref


def main():
    repos = sys.argv[1:]
    if not repos:
        print(__doc__)
        return 2

    for repo in repos:
        print("=== %s ===" % repo)
        reg, err = registry_tree(repo)
        if reg is None:
            print("  registry: %s" % err)
            print()
            continue
        live, ref = live_tree(repo)
        if live is None:
            print("  live %s" % ref)
            print()
            continue

        common = set(reg) & set(live)
        same = [p for p in common if reg[p] == live[p]]
        diff = [p for p in common if reg[p] != live[p]]
        missed = sorted(set(live) - set(reg))
        extra = sorted(set(reg) - set(live))

        print("  live @%s: %d files" % (ref, len(live)))
        print("  registry tree: %d files" % len(reg))
        print("  identical per path : %d" % len(same))
        print("  different content  : %d" % len(diff))
        print("  in live, not in reg: %d" % len(missed))
        print("  in reg, not in live: %d" % len(extra))
        if diff:
            for p in diff[:8]:
                print("      differs: %s" % p)
        if missed:
            for p in missed[:12]:
                print("      missing: %s" % p)
            if len(missed) > 12:
                print("      ... %d more" % (len(missed) - 12))
        if not missed and not diff:
            print("  VERDICT: the registry tree covers the repository exactly")
        elif not missed:
            print("  VERDICT: every path is present; %d differ in content" % len(diff))
        else:
            print("  VERDICT: NOT covered - deleting would lose %d files" % len(missed))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
