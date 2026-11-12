#!/usr/bin/env python3
"""Publish a restore index for the preserved refs inside the registry.

Refs under `refs/preserved/` hold the full history of absorbed repositories,
but GitHub's UI never shows them: they are invisible unless you already know
the name. That makes them useless as a recovery path for anyone who was not
present when they were pushed. This generates `repos/RESTORE.md` from the live
ref list, so the index cannot drift from reality.

    python scripts/publish_restore_index.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

OWNER = "KooshaPari"
REGISTRY = "PhenoRegistry"


def sh(args, stdin=None):
    p = subprocess.run(args, input=stdin, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def build_index() -> str:
    code, out, err = sh(["gh", "api", "repos/%s/%s/git/matching-refs/preserved"
                         % (OWNER, REGISTRY)])
    if code != 0:
        raise SystemExit("cannot list preserved refs: %s" % err[:200])
    refs = [r["ref"] for r in json.loads(out)]

    # Group by repository, then by kind, so the index reads as a directory.
    groups: dict[str, dict[str, list[str]]] = {}
    for ref in refs:
        rest = ref[len("refs/preserved/"):]
        repo, _, tail = rest.partition("/")
        kind, _, name = tail.partition("/")
        groups.setdefault(repo, {}).setdefault(kind, []).append(name)

    lines = [
        "# Restoring preserved history",
        "",
        "Repositories absorbed into PhenoShared or this registry had their full",
        "git history preserved before deletion. A bundle cannot hold a history",
        "larger than 100 MB, because GitHub rejects any file over that size, so",
        "history is stored as real git refs under `refs/preserved/<repo>/`.",
        "",
        "These refs do not appear anywhere in the GitHub interface. This index is",
        "generated from the live ref list, so it always matches what is stored.",
        "",
        "## Restoring a repository",
        "",
        "```",
        "git clone --mirror https://github.com/%s/%s.git restored.git" % (OWNER, REGISTRY),
        "cd restored.git",
        "git fetch origin '+refs/preserved/<repo>/*:refs/heads/*'",
        "```",
        "",
        "The branches and tags of that repository are now local refs and can be",
        "inspected or pushed to a new remote.",
        "",
        "## What is preserved",
        "",
        "| Repository | Branches | Tags |",
        "|---|---:|---:|",
    ]
    for repo in sorted(groups):
        heads = groups[repo].get("heads", [])
        tags = groups[repo].get("tags", [])
        lines.append("| `%s` | %d | %d |" % (repo, len(heads), len(tags)))

    lines += ["", "## Branch detail", ""]
    for repo in sorted(groups):
        lines.append("### `%s`" % repo)
        lines.append("")
        for kind in sorted(groups[repo]):
            for name in sorted(groups[repo][kind]):
                lines.append("- `%s/%s`" % (kind, name))
        lines.append("")

    lines += [
        "## Not covered here",
        "",
        "Repositories whose content was exported as a patch series are recorded in",
        "`absorption/<repo>/patches/` in PhenoShared, not here. Their diff was",
        "verified to apply to the named upstream base commit and to reproduce the",
        "fork tree exactly.",
        "",
    ]
    return "\n".join(lines)


def publish(content: str) -> str:
    tmp = tempfile.mkdtemp(prefix="restore-index-")
    clone = os.path.join(tmp, "registry")
    code, _, err = sh(["gh", "repo", "clone", "%s/%s" % (OWNER, REGISTRY), clone,
                       "--", "--filter=blob:none", "--no-checkout"])
    if code != 0:
        raise SystemExit("cannot clone registry: %s" % err[:200])

    src = os.path.join(tmp, "RESTORE.md")
    with open(src, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)

    def g(*a):
        c, o, e = sh(["git", "-C", clone] + list(a))
        return c, o.strip(), e.strip()

    c, blob, e = g("hash-object", "-w", src)
    if c != 0:
        raise SystemExit("hash-object failed: %s" % e[:200])
    c, _, e = g("fetch", "-q", "origin", "main")
    if c != 0:
        raise SystemExit("fetch failed: %s" % e[:200])
    g("read-tree", "FETCH_HEAD")
    c, _, e = g("update-index", "--add", "--cacheinfo", "100644,%s,repos/RESTORE.md" % blob)
    if c != 0:
        raise SystemExit("update-index failed: %s" % e[:200])
    _, tree, _ = g("write-tree")
    c, commit, e = g("commit-tree", tree, "-p", "FETCH_HEAD",
                     "-m", "docs(registry): publish an index of preserved histories")
    if c != 0:
        raise SystemExit("commit-tree failed: %s" % e[:200])
    c, _, e = g("push", "origin", "%s:main" % commit)
    if c != 0:
        raise SystemExit("push failed: %s" % e[:200])
    return commit[:12]


if __name__ == "__main__":
    text = build_index()
    print("index bytes:", len(text))
    print("published:", publish(text))
    sys.exit(0)
