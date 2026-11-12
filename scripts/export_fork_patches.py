#!/usr/bin/env python3
"""Export a fork's local-only commits as a reviewable patch series.

The `zz-aa-dep-*` repos look like dependency pins but each carries real work:
between 4 and 242 commits authored here, patching a third-party project. A
patch series is the right container for that. It is readable in review, it
applies cleanly onto the upstream the base commit names, and it does not
require keeping gigabytes of upstream history to understand one local change.

The base is the merge-base against the upstream branch, so every exported
patch is a change this fork made and not something upstream wrote.

    python scripts/export_fork_patches.py zz-aa-dep-TurboQuant
"""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import tempfile

OWNER_DEFAULT = "KooshaPari"
OUT_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "absorption")


def sh(args):
    p = subprocess.run(args, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def git(repo, *args):
    return sh(["git", "-C", repo] + list(args))


def api(path):
    p = subprocess.run(["gh", "api", path], capture_output=True)
    if p.returncode != 0:
        return None
    return json.loads(p.stdout.decode("utf-8", "replace"))


def export(repo: str, owner: str, workdir: str, outroot: str) -> tuple[bool, str]:
    info = api("repos/%s/%s" % (owner, repo))
    if not info:
        return False, "cannot read repo metadata"

    mirror = os.path.join(workdir, "%s.git" % repo)
    code, _, err = sh(["gh", "repo", "clone", "%s/%s" % (owner, repo), mirror, "--", "--mirror"])
    if code != 0:
        return False, "mirror clone failed: %s" % err.strip()[:150]

    code, out, _ = git(mirror, "symbolic-ref", "--short", "HEAD")
    branch = out.strip() or "main"

    parent = (info.get("parent") or {}).get("full_name")
    if not parent:
        return False, "not a fork; nothing to diff against"
    parent_branch = (info["parent"].get("default_branch")) or "main"
    parent_url = "https://github.com/%s.git" % parent

    code, _, err = git(mirror, "fetch", "-q", parent_url,
                       "+%s:refs/upstream/base" % parent_branch)
    if code != 0:
        return False, "cannot fetch upstream %s: %s" % (parent, err.strip()[:120])

    code, base, err = git(mirror, "merge-base", "refs/upstream/base", branch)
    base = base.strip()
    if code != 0 or not base:
        return False, "no merge base with upstream: %s" % err.strip()[:120]

    code, ahead, _ = git(mirror, "rev-list", "--count", "%s..%s" % (base, branch))
    n = int(ahead.strip() or 0)
    if n == 0:
        return False, "no local commits; nothing unique to export"

    outdir = os.path.join(workdir, "patches", repo)
    os.makedirs(outdir, exist_ok=True)
    # --binary keeps image and other non-text changes intact; a text-only patch
    # series would silently drop them and look complete while being lossy.
    code, _, err = git(mirror, "format-patch", "--binary", "--full-index",
                       "-o", outdir, "%s..%s" % (base, branch))
    if code != 0:
        return False, "format-patch failed: %s" % err.strip()[:150]

    files = sorted(f for f in os.listdir(outdir) if f.endswith(".patch"))
    if len(files) != n:
        return False, "patch count %d != commit count %d" % (len(files), n)

    manifest = [
        "# %s" % repo,
        "",
        "Local patches against `%s` (%s)." % (parent, parent_branch),
        "",
        "- base commit: `%s` (merge-base with upstream)" % base,
        "- local commits: %d" % n,
        "- exported: %d patch files" % len(files),
        "",
        "## Applying",
        "",
        "Clone upstream at the base commit, then apply in order:",
        "",
        "```",
        "git clone https://github.com/%s.git" % parent,
        "git checkout %s" % base,
        "git am /path/to/these/patches/*.patch",
        "```",
    ]
    io.open(os.path.join(outdir, "MANIFEST.md"), "w", encoding="utf-8").write(
        "\n".join(manifest) + "\n")

    dest = os.path.join(outroot, repo, "patches")
    total = 0
    for f in files + ["MANIFEST.md"]:
        with open(os.path.join(outdir, f), "rb") as fh:
            data = fh.read()
        total += len(data)
        target = os.path.join(dest, f)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as fh:
            fh.write(data)

    return True, "%d patches, %.1f KB, base %s" % (len(files), total / 1024.0, base[:10])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repos", nargs="+")
    ap.add_argument("--owner", default=OWNER_DEFAULT)
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()

    workdir = tempfile.mkdtemp(prefix="forkpatch-")
    failures = 0
    for repo in args.repos:
        ok, detail = export(repo, args.owner, workdir, args.out)
        print("== %s" % repo)
        if ok:
            print("   exported  %s" % detail)
        else:
            print("   SKIP      %s" % detail)
            failures += 1
    print()
    print("exported %d, skipped %d" % (len(args.repos) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
