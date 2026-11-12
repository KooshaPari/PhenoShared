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


def git_bytes(repo, *args):
    """Run git and return stdout as raw bytes.

    Diffs are not guaranteed to be text: they carry file content verbatim, so
    decoding them would replace every non-UTF-8 byte and silently produce a
    patch that no longer reproduces its source.
    """
    p = subprocess.run(["git", "-C", repo] + list(args), capture_output=True)
    if p.returncode != 0:
        raise RuntimeError("git %s failed: %s"
                           % (" ".join(args), p.stderr.decode("utf-8", "replace").strip()[:200]))
    return p.stdout


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

    # Not `symbolic-ref HEAD`: `gh repo clone` on a fork sets HEAD to the
    # *upstream* default branch (master here) while the fork's own work is on
    # main, so HEAD would silently pick the wrong branch.
    branch = info.get("default_branch") or "main"

    parent = (info.get("parent") or {}).get("full_name")
    if not parent:
        return False, "not a fork; nothing to diff against"
    parent_branch = (info["parent"].get("default_branch")) or "main"

    # Ask the API where the two histories part. Fetching the upstream clone
    # instead would mean downloading some of the largest repos on GitHub
    # (unsloth is 7000+ commits behind) to learn one commit id, and the fork's
    # own object store already contains that commit because it is an ancestor.
    cmp_ = api("repos/%s/%s/compare/%s:%s...%s"
               % (owner, repo, parent.split("/")[0], parent_branch, branch))
    if not cmp_ or not cmp_.get("merge_base_commit"):
        return False, "cannot determine merge base against %s" % parent
    base = cmp_["merge_base_commit"]["sha"]

    code, _, _ = git(mirror, "cat-file", "-e", "%s^{commit}" % base)
    if code != 0:
        return False, "base %s absent from the fork" % base[:10]
    code, _, _ = git(mirror, "merge-base", "--is-ancestor", base, branch)
    if code != 0:
        return False, "base %s is not an ancestor of %s" % (base[:10], branch)

    code, ahead, _ = git(mirror, "rev-list", "--count", "%s..%s" % (base, branch))
    n = int(ahead.strip() or 0)
    if n == 0:
        return False, "no local commits; nothing unique to export"

    check = os.path.join(workdir, "check-%s" % repo)
    want_tree = git(mirror, "rev-parse", "%s^{tree}" % branch)[1].strip()

    def fresh_checkout() -> str:
        git(mirror, "worktree", "remove", "--force", check)
        code, _, err = git(mirror, "worktree", "add", "--detach", check, base)
        if code != 0:
            raise RuntimeError("cannot check out base %s: %s" % (base[:10], err.strip()[:120]))
        return check

    def worktree_tree() -> str:
        # git apply only touches the worktree, so HEAD still points at the base.
        # Building the tree from the worktree is the only way to see what the
        # patch actually produced. -f so files the diff adds are staged even if
        # the repository ignores them.
        git(check, "add", "-A", "-f")
        return git(check, "write-tree")[1].strip()

    outdir = os.path.join(workdir, "out", repo)
    os.makedirs(outdir, exist_ok=True)

    # The combined diff is the authoritative artifact. It is one base-to-fork
    # tree diff, so commit ordering and merge commits cannot make it
    # inapplicable the way they can for a per-commit series.
    combined = os.path.join(outdir, "%s-combined.diff" % repo)
    with open(combined, "wb") as fh:
        fh.write(git_bytes(mirror, "diff", "--binary", "--full-index", base, branch))
    if os.path.getsize(combined) == 0:
        return False, "combined diff is empty"

    try:
        fresh_checkout()
    except RuntimeError as exc:
        return False, str(exc)
    code, out, err = sh(["git", "-C", check, "apply", "--binary", combined])
    if code != 0:
        git(mirror, "worktree", "remove", "--force", check)
        return False, "combined diff did not apply: %s" % (err or out).strip()[:150]
    got_tree = worktree_tree()
    if got_tree != want_tree:
        diff_list = git(mirror, "diff-tree", "-r", "--no-commit-id", got_tree, want_tree)[1]
        n_paths = len(diff_list.splitlines())
        git(mirror, "worktree", "remove", "--force", check)
        return False, ("combined diff did not reproduce the fork tree "
                       "(got %s, want %s, %d paths differ)"
                       % (got_tree[:10], want_tree[:10], n_paths))

    # The per-commit series is far nicer to review, but it only survives when
    # the history is linear and every patch applies. Publish it only after the
    # same tree check passes, so a broken series is never mistaken for the
    # complete record.
    nmerge = int(git(mirror, "rev-list", "--count", "--merges",
                     "%s..%s" % (base, branch))[1].strip() or 0)
    sdir = os.path.join(workdir, "series", repo)
    os.makedirs(sdir, exist_ok=True)
    git(mirror, "format-patch", "--binary", "--full-index", "-o", sdir,
        "%s..%s" % (base, branch))
    files = sorted(f for f in os.listdir(sdir) if f.endswith(".patch"))

    series_ok = False
    note = ""
    if len(files) == n - nmerge and files:
        try:
            fresh_checkout()
        except RuntimeError as exc:
            return False, str(exc)
        code, out, err = sh(["git", "-C", check, "am", "--whitespace=nowarn"] +
                            [os.path.join(sdir, f) for f in files])
        if code == 0 and worktree_tree() == want_tree:
            for f in files:
                with open(os.path.join(sdir, f), "rb") as src, \
                        open(os.path.join(outdir, f), "wb") as dst:
                    dst.write(src.read())
            series_ok = True
        else:
            subprocess.run(["git", "-C", check, "am", "--abort"], capture_output=True)
        git(mirror, "worktree", "remove", "--force", check)

    if not series_ok:
        files = []
        note = ("\nThe per-commit series could not be reproduced cleanly (%d commits, "
                "%d merge commits), so it is not published; the combined diff above "
                "is the authoritative record and its application was verified.\n"
                % (n, nmerge))

    manifest = [
        "# %s" % repo,
        "",
        "Local changes against `%s` (%s)." % (parent, parent_branch),
        "",
        "- base commit: `%s` (merge-base with upstream)" % base,
        "- local commits: %d (%d merges)" % (n, nmerge),
        "- combined diff: `%s` (verified: applies to the base and reproduces the fork tree)"
        % os.path.basename(combined),
        "- per-commit series: %s" % ("%d patches, verified" % len(files) if series_ok
                                     else "not published"),
        "",
        "## Applying",
        "",
        "```",
        "git clone https://github.com/%s.git" % parent,
        "git checkout %s" % base,
        "git apply --binary %s" % os.path.basename(combined),
        "```",
    ]
    if series_ok:
        manifest += ["", "Or replay the commits individually:", "", "```",
                     "git am *.patch", "```"]
    io.open(os.path.join(outdir, "MANIFEST.md"), "w", encoding="utf-8").write(
        "\n".join(manifest) + note + "\n")

    dest = os.path.join(outroot, repo, "patches")
    total = 0
    for f in files + ["MANIFEST.md", os.path.basename(combined)]:
        with open(os.path.join(outdir, f), "rb") as fh:
            data = fh.read()
        total += len(data)
        target = os.path.join(dest, f)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as fh:
            fh.write(data)

    return True, "%d patches, %.1f KB, %s, tree verified" % (
        len(files), total / 1024.0,
        "series" if series_ok else "combined diff only")


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

