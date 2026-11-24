#!/usr/bin/env python3
"""Absorb a private repo into the private registry, proven complete (v2).

V2 FIXES
1. Scratch directory fail-loud: KCODE_SCRATCH_DIR (or the default agent scratch
   root) must exist as a directory. No silent fallback to the system temp dir.
   This prevents a large clone from landing on C: by accident.
2. Parameterised push target: --push-branch and --recover-branch. The tree
   commit is first pushed to a throwaway recovery ref and verified, then to the
   destination branch. This keeps stranded objects recoverable after a race.
3. Preserve work on failure: no cleanup on failure, always print the absolute
   workdir path. Cleanup is opt-in only on overall success via --clean.
4. Bounded destination push retry: on non-fast-forward, fetch once then push
   once more. No force, no rebase, no further retries.
5. LFS pre-flight: inspect only blobs under 300 bytes from `git ls-tree -r -l`,
   count exact LFS pointer headers, and require --allow-lfs-pointers when any
   are found. This avoids uploading 80 MB before GitHub rejects GH008.
6. Exit-code discipline: every subprocess call is checked, with command,
   return code, stdout, and stderr in failures.
7. Denominated report: always include paths in tree, files written, withheld,
   excluded, refs, commits, and LFS pointer count. Counts come from objects
   actually written/routed, not filename patterns.

Private ops repositories are data, not code, so they belong in PhenoRegistry
rather than PhenoShared. Each one is absorbed as two things:

  repos/<repo>/tree/     the working tree, readable and browsable
  refs/preserved/<repo>/ every branch and tag, full history

The completeness proof is exact rather than sampled: git object ids are content
hashes, so comparing the source tree's blob ids against the pushed tree's blob
ids proves every file arrived byte for byte. Nothing is deleted here; the
script prints DELETE-AUTHORISED only when the comparison passes.

    python scripts/absorb_private_v2.py nexus host-ops

Re-running it for a repo that was already absorbed refreshes the registry's
snapshot to the source's current default branch; it is not append-only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

OWNER_DEFAULT = "KooshaPari"
REGISTRY_DEFAULT = "PhenoRegistry"
RECOVER_BRANCH_DEFAULT = "refs/heads/recover/{repo}-{sha8}"
LFS_POINTER_HEADER = "version https://git-lfs.github.com/spec/v1"
LFS_SCAN_SIZE_LIMIT = 300


class CommandError(RuntimeError):
    """A subprocess exited non-zero, with enough context to diagnose it."""


def _snippet(text: str, limit: int = 500) -> str:
    compact = " ".join((text or "").split())
    return compact[:limit]


def sh(args, cwd=None):
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True)
    except OSError as exc:
        raise CommandError("cannot run %s: %s" % (" ".join(args), exc)) from exc
    return (
        p.returncode,
        p.stdout.decode("utf-8", "replace"),
        p.stderr.decode("utf-8", "replace"),
    )


def checked_sh(args, cwd=None, label=None):
    """Run a command and raise CommandError on any non-zero return code."""
    code, out, err = sh(args, cwd=cwd)
    if code != 0:
        command = label or " ".join(args)
        raise CommandError(
            "%s failed (exit %d): stdout=%s stderr=%s"
            % (command, code, _snippet(out), _snippet(err))
        )
    return out, err


def git(repo, *args):
    return sh(["git", "-C", repo] + list(args))


def checked_git(repo, *args):
    return checked_sh(["git", "-C", repo] + list(args))


def must(repo, *args):
    out, _ = checked_git(repo, *args)
    return out.strip()


def ls_tree_entries(repo: str, treeish: str) -> list[tuple[str, str, str, str, str]]:
    """Return (mode, kind, sha, size, path) for every entry in a tree."""
    out = must(repo, "ls-tree", "-r", "-l", "--full-tree", treeish)
    entries = []
    for line in out.splitlines():
        meta, sep, path = line.partition("\t")
        if not sep:
            continue
        parts = meta.split()
        if len(parts) != 4:
            raise CommandError(
                "unexpected git ls-tree output for %r: %s" % (path, _snippet(meta))
            )
        mode, kind, sha, size = parts
        entries.append((mode, kind, sha, size, path))
    return entries


def ls_blobs(repo: str, treeish: str) -> dict[str, str]:
    """Map path -> blob sha for every file in a tree."""
    entries = ls_tree_entries(repo, treeish)
    return {path: sha for _, kind, sha, _, path in entries if kind == "blob"}


def scan_lfs_pointers(
    repo: str, commit: str
) -> tuple[list[tuple[str, str]], list[str]]:
    """Find exact LFS pointers among small blobs in a commit's tree.

    `git ls-tree -r -l` provides the blob size. Only blobs under 300 bytes are
    read; large blobs are never cat-file'd. A pointer is accepted only when the
    first line exactly matches the LFS spec header.
    """
    small_blobs = [
        (path, sha)
        for _, kind, sha, size, path in ls_tree_entries(repo, commit)
        if kind == "blob" and size.isdigit() and int(size) < LFS_SCAN_SIZE_LIMIT
    ]
    pointers: list[tuple[str, str]] = []
    errors: list[str] = []
    for path, sha in small_blobs:
        code, out, err = git(repo, "cat-file", "blob", sha)
        if code != 0:
            errors.append(
                "git cat-file blob %s for %s failed (exit %d): %s"
                % (sha, path, code, _snippet(err))
            )
            continue
        first_line = out.split("\n", 1)[0].rstrip("\r")
        if first_line == LFS_POINTER_HEADER:
            pointers.append((path, sha))
    return pointers, errors


def counts_report(counts: dict[str, int]) -> str:
    """Render a single report line with every count and its denominator."""
    return (
        "paths-in-tree=%(paths)d files-written=%(written)d/%(source)d "
        "withheld=%(withheld)d excluded=%(excluded)d refs=%(refs)d "
        "commits=%(commits)d lfs-pointers=%(lfs)d"
        % counts
    )


def recover_ref_for(repo: str, commit: str, template: str) -> str:
    """Build a full recovery ref name for one repository.

    The template accepts {repo}, {sha}, and {sha8}. A bare name is placed
    under refs/heads/. Multiple repos should include {repo} or {sha8}.
    """
    try:
        ref = template.format(repo=repo, sha=commit, sha8=commit[:8])
    except (KeyError, IndexError, ValueError) as exc:
        raise CommandError("invalid --recover-branch template: %s" % exc) from exc
    if ".." in ref or ref.endswith("/") or any(c.isspace() for c in ref):
        raise CommandError("invalid --recover-branch template: unsafe ref %r" % ref)
    return ref if ref.startswith("refs/") else "refs/heads/" + ref


def push_destination(registry_clone: str, commit: str, dest: str):
    """Push commit to dest, with at most one non-fast-forward recovery retry.

    Returns (ok, detail, retried). The caller owns workdir reporting on failure.
    """
    code, out, err = git(registry_clone, "push", "-q", "origin", "%s:%s" % (commit, dest))
    combined = "%s\n%s" % (out, err)
    if code == 0:
        return True, "", False

    if not re.search(
        r"non-fast-forward|fetch first|rejected", combined, re.I
    ) or not re.search(r"rejected|failed to push|non-fast-forward", combined, re.I):
        return False, (
            "destination push failed (exit %d): %s" % (code, _snippet(combined))
        ), False

    # Exactly one fetch, then exactly one retry push. Never force, never rebase.
    retry_ref = "refs/absorb-retry/%s" % re.sub(r"[^A-Za-z0-9._-]+", "-", dest)
    code, out, err = git(
        registry_clone, "fetch", "-q", "origin", "%s:%s" % (dest, retry_ref)
    )
    if code != 0:
        return False, (
            "destination push was rejected and the single recovery fetch failed "
            "(exit %d): %s" % (code, _snippet("%s\n%s" % (out, err)))
        ), True

    code, out, err = git(registry_clone, "push", "-q", "origin", "%s:%s" % (commit, dest))
    if code != 0:
        return False, (
            "destination push failed again after one fetch (exit %d): %s"
            % (code, _snippet("%s\n%s" % (out, err)))
        ), True
    return True, "", True


def absorb(
    registry_clone: str,
    url_registry: str,
    owner: str,
    repo: str,
    workdir: str,
    push_branch: str,
    recover_branch: str,
    allow_lfs_pointers: bool,
) -> tuple[bool, str, dict[str, int] | None]:
    """Absorb one repository. Counts are returned even for reported failures."""
    counts = {
        "paths": 0,
        "written": 0,
        "source": 0,
        "withheld": 0,
        "excluded": -1,
        "refs": 0,
        "commits": 0,
        "lfs": -1,
    }
    mirror = os.path.join(workdir, "%s.git" % repo)

    code, out, err = sh(
        ["gh", "repo", "clone", "%s/%s" % (owner, repo), mirror, "--", "--mirror"]
    )
    if code != 0:
        counts["source"] = -1
        return False, (
            "mirror clone failed (exit %d): %s" % (code, _snippet(err))
        ), counts

    code, out, err = sh(["gh", "api", "repos/%s/%s" % (owner, repo)])
    if code != 0:
        counts["source"] = -1
        return False, (
            "cannot read repo metadata (exit %d): %s" % (code, _snippet(err))
        ), counts
    # Not `symbolic-ref HEAD`: for a fork, `gh repo clone` points HEAD at the
    # *upstream* default branch rather than the fork's own, which would absorb
    # the wrong branch's content.
    try:
        branch = json.loads(out).get("default_branch") or "main"
    except (ValueError, TypeError) as exc:
        return False, ("cannot parse repo metadata: %s" % exc), counts
    try:
        source_tree = must(mirror, "rev-parse", "%s^{tree}" % branch)
    except CommandError as exc:
        return False, str(exc), counts

    # Prepare refs: registry state, source content, source history.
    try:
        checked_git(
            registry_clone, "fetch", "-q", "origin", "main:refs/reg/main"
        )
        checked_git(
            registry_clone, "fetch", "-q", mirror, "%s:refs/src/%s" % (branch, repo)
        )
        checked_git(
            registry_clone,
            "fetch",
            "-q",
            mirror,
            "+refs/heads/*:refs/hist/%s/heads/*" % repo,
            "+refs/tags/*:refs/hist/%s/tags/*" % repo,
        )
    except CommandError as exc:
        return False, "fetch failed: %s" % exc, counts

    # Graft the whole source tree under repos/<repo>/tree in one commit, keeping
    # the registry's own content intact. read-tree --prefix deliberately avoids
    # git add and therefore preserves the original .gitignore behaviour.
    prefix = "repos/%s/tree/" % repo
    repo_root = "repos/%s/" % repo
    try:
        checked_git(registry_clone, "read-tree", "refs/reg/main")
        # A repo absorbed on an earlier pass already has its old snapshot at this
        # prefix, and `read-tree --prefix` refuses to write over any path that is
        # already in the index. Dropping the stale snapshot from the index first
        # keeps a second run a refresh instead of a hard failure.
        checked_git(
            registry_clone,
            "rm",
            "-r",
            "-q",
            "-f",
            "--cached",
            "--ignore-unmatch",
            prefix.rstrip("/"),
        )
        checked_git(
            registry_clone,
            "read-tree",
            "--prefix=" + prefix,
            "refs/src/%s^{tree}" % repo,
        )
        tree = must(registry_clone, "write-tree")
        commit = must(
            registry_clone,
            "commit-tree",
            tree,
            "-p",
            "refs/reg/main",
            "-m",
            "chore(absorb): %s tree and history" % repo,
        )
    except CommandError as exc:
        return False, "tree construction failed: %s" % exc, counts

    try:
        all_entries = ls_tree_entries(registry_clone, commit)
    except CommandError as exc:
        return False, "cannot count tree paths: %s" % exc, counts
    counts["paths"] = len(all_entries)

    # LFS pre-flight: inspect only small blobs, before any push.
    try:
        pointers, lfs_errors = scan_lfs_pointers(registry_clone, commit)
    except CommandError as exc:
        return False, "LFS pre-flight failed: %s" % exc, counts
    if lfs_errors:
        return False, "LFS pre-flight failed: %s" % "; ".join(lfs_errors), counts
    counts["lfs"] = len(pointers)
    if pointers and not allow_lfs_pointers:
        preview = ", ".join(path for path, _ in pointers[:5])
        return False, (
            "LFS pre-flight found %d pointer(s), including: %s; "
            "re-run with --allow-lfs-pointers to proceed"
            % (len(pointers), preview)
        ), counts
    if pointers:
        preview = ", ".join(path for path, _ in pointers[:5])
        print("   WARNING LFS pointers=%d first=%s" % (len(pointers), preview))

    # Push new objects to a throwaway ref first, then verify it before touching
    # the destination branch. This keeps stranded objects recoverable.
    recover_ref = recover_ref_for(repo, commit, recover_branch)
    try:
        checked_git(
            registry_clone, "push", "-q", "origin", "%s:%s" % (commit, recover_ref)
        )
    except CommandError as exc:
        return False, "recovery push failed: %s" % exc, counts
    try:
        out, _ = checked_git(
            registry_clone, "ls-remote", "--exit-code", "origin", recover_ref
        )
    except CommandError as exc:
        return False, "recovery push verification failed: %s" % exc, counts
    if commit not in out:
        return False, (
            "recovery push verification failed: %s does not contain %s"
            % (recover_ref, commit)
        ), counts

    ok, detail, retried = push_destination(registry_clone, commit, push_branch)
    if not ok:
        return False, detail, counts

    try:
        checked_git(
            registry_clone,
            "push",
            "-q",
            "origin",
            "+refs/hist/%s/*:refs/preserved/%s/*" % (repo, repo),
        )
    except CommandError as exc:
        return False, "push history failed: %s" % exc, counts

    # Verify by reading back from the registry what we actually pushed. Retried
    # because the ref update can lose the race with the push that just landed
    # and fail with "cannot lock ref ... unable to resolve reference", which is
    # a transient local condition, not evidence that the absorption failed.
    # The retry fetch above is explicit and bounded; only this verification
    # fetch is retried up to three times, matching the original's workaround.
    last_fetch_error = ""
    for attempt in range(3):
        try:
            checked_git(
                registry_clone,
                "fetch",
                "-q",
                "origin",
                "%s:refs/reg/main" % push_branch,
            )
            last_fetch_error = ""
            break
        except CommandError as exc:
            last_fetch_error = str(exc)
        if attempt < 2:
            time.sleep(2)
    if last_fetch_error:
        return False, "re-fetch failed after 3 attempts: %s" % last_fetch_error, counts

    try:
        pushed = ls_blobs(registry_clone, "refs/reg/main")
        want = ls_blobs(mirror, source_tree)
    except CommandError as exc:
        return False, "verification blob listing failed: %s" % exc, counts

    got = {p[len(prefix) :]: sha for p, sha in pushed.items() if p.startswith(prefix)}
    counts["written"] = len(got)
    counts["source"] = len(want)

    if got != want:
        missing = sorted(set(want) - set(got))
        extra = sorted(set(got) - set(want))
        differ = sorted(p for p in set(want) & set(got) if want[p] != got[p])
        update_counts(counts, pushed, prefix, repo_root, want, got)
        return False, (
            "tree mismatch: %d missing, %d extra, %d differing"
            % (len(missing), len(extra), len(differ))
        ), counts

    try:
        heads = must(
            registry_clone, "ls-remote", url_registry, "refs/preserved/%s/*" % repo
        )
        nrefs = len([l for l in heads.splitlines() if l.strip()])
        ncommits = int(must(mirror, "rev-list", "--all", "--count"))
    except (CommandError, ValueError) as exc:
        return False, "verification count failed: %s" % exc, counts
    counts["refs"] = nrefs
    counts["commits"] = ncommits
    update_counts(counts, pushed, prefix, repo_root, want, got)

    suffix = " (after one retry)" if retried else ""
    return True, "pushed to %s%s" % (push_branch, suffix), counts


def update_counts(
    counts: dict[str, int],
    pushed: dict[str, str],
    prefix: str,
    repo_root: str,
    want: dict[str, str],
    got: dict[str, str],
) -> None:
    """Derive written/withheld/excluded counts from objects actually present."""
    direct_paths = {
        p[len(repo_root) :]
        for p in pushed
        if p.startswith(repo_root) and not p.startswith(prefix)
    }
    withheld = set(want) & direct_paths
    written = set(got) | withheld
    counts["written"] = len(written)
    counts["withheld"] = len(withheld)
    counts["excluded"] = len(set(want) - written)


def cleanup_workdir(workdir: str) -> str:
    try:
        shutil.rmtree(workdir)
    except OSError as exc:
        return "cleanup failed for %s: %s" % (workdir, exc)
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repos", nargs="+")
    ap.add_argument("--owner", default=OWNER_DEFAULT)
    ap.add_argument("--registry", default=REGISTRY_DEFAULT)
    ap.add_argument(
        "--push-branch",
        default="main",
        help="destination branch for the tree commit (default: main)",
    )
    ap.add_argument(
        "--recover-branch",
        default=RECOVER_BRANCH_DEFAULT,
        help=(
            "throwaway recovery ref template; supports {repo}, {sha8}, and "
            "{sha} (default: refs/heads/recover/{repo}-{sha8}); bare names "
            "are placed under refs/heads/"
        ),
    )
    ap.add_argument(
        "--allow-lfs-pointers",
        action="store_true",
        help="allow pushes containing detected Git LFS pointers (default: refuse)",
    )
    ap.add_argument(
        "--clean",
        action="store_true",
        help="remove the workdir only after every repo succeeds (default: keep)",
    )
    args = ap.parse_args()

    # Scratch belongs under a declared scratch root. A configured scratch path
    # that is missing is an error, never a reason to fall back to system temp.
    scratch = os.environ.get("KCODE_SCRATCH_DIR") or os.path.expanduser("~/Agents/scratch")
    if not os.path.isdir(scratch):
        print(
            "ERROR scratch directory does not exist or is not a directory: %s\n"
            "Set KCODE_SCRATCH_DIR to an existing directory. Refusing to fall "
            "back to the system temp directory." % scratch,
            file=sys.stderr,
        )
        return 2

    workdir: str | None = None
    failures = 0
    successful_repos = 0
    from_main = False
    try:
        from_main = True
        workdir = tempfile.mkdtemp(prefix="absorb-private-", dir=scratch)
        registry_clone = os.path.join(workdir, "registry")
        url_registry = "https://github.com/%s/%s.git" % (args.owner, args.registry)

        # A full clone, not a blobless one. Pushing a *refresh* of an
        # already-absorbed repo makes pack-objects delta the new blobs against
        # the snapshot already at repos/<repo>/tree/, and a --filter=blob:none
        # clone does not have those old blobs. Each one then becomes its own
        # lazy fetch: a measured 10+ minutes of single-object round trips with
        # no progress. The registry is ~450 MB, so cloning it whole is cheaper.
        code, out, err = sh(
            [
                "gh",
                "repo",
                "clone",
                "%s/%s" % (args.owner, args.registry),
                registry_clone,
                "--",
                "--no-checkout",
            ]
        )
        if code != 0:
            failures = len(args.repos)
            print(
                "cannot clone registry (exit %d): %s\nWORKDIR %s"
                % (code, _snippet("%s\n%s" % (out, err)), os.path.abspath(workdir))
            )
            return 2

        for repo in args.repos:
            ok, detail, counts = absorb(
                registry_clone,
                url_registry,
                args.owner,
                repo,
                workdir,
                args.push_branch,
                args.recover_branch,
                args.allow_lfs_pointers,
            )
            print("== %s" % repo)
            report = counts_report(counts)
            print("   counts %s" % report)
            if ok:
                successful_repos += 1
                print("   absorbed  %s" % detail)
                print("   DELETE-AUTHORISED %s" % repo)
            else:
                print("   REFUSED   %s" % detail)
                print("   WORKDIR   %s" % os.path.abspath(workdir))
                failures += 1

        print()
        print("absorbed %d, blocked %d" % (len(args.repos) - failures, failures))
        return 1 if failures else 0
    except BaseException:
        if from_main and workdir:
            print("   WORKDIR   %s" % os.path.abspath(workdir))
        raise
    finally:
        # A workdir is removed only on overall success and with explicit --clean.
        # Any failure keeps it and its absolute path has already been printed.
        if (
            workdir
            and failures == 0
            and successful_repos == len(args.repos)
            and args.clean
            and os.path.isdir(workdir)
        ):
            cleanup_error = cleanup_workdir(workdir)
            if cleanup_error:
                print("   WARNING   %s" % cleanup_error)


if __name__ == "__main__":
    sys.exit(main())
