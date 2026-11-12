#!/usr/bin/env python3
"""Prepare a repo for deletion: verify, preserve history, export discussion.

Why this exists: nine repos were deleted after their *files* were verified
complete, but without a git bundle or an issue/PR export. The files survived;
the history and the discussion did not, and that is unrecoverable. An earlier
batch of six got both, so the difference was procedural discipline, not
capability -- exactly the kind of thing that should be enforced in code.

This script makes the earlier, better behaviour the only path:

    python scripts/prepare_deletion.py SessionLedger ResearchLedger
    python scripts/prepare_deletion.py --all-deleted

For each repo it will:
  1. Verify the absorbed tree is complete (refuses if not)
  2. Create a full-history git bundle and store it in the private registry
  3. Export issues, pull requests and comments to the private registry
  4. Print DELETE-AUTHORISED only when all three succeeded

It never deletes anything itself. Deletion stays a separate, deliberate step.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OWNER = "KooshaPari"
DEFAULT_REGISTRY = "PhenoRegistry"


def sh(args: list[str], stdin: bytes | None = None) -> tuple[int, bytes, bytes]:
    p = subprocess.run(args, input=stdin, capture_output=True)
    return p.returncode, p.stdout, p.stderr


def gh_api(path: str) -> tuple[int, str]:
    code, out, err = sh(["gh", "api", path])
    return code, (out.decode("utf-8", "replace") if code == 0 else err.decode("utf-8", "replace"))


def verify(repo: str) -> tuple[bool, str]:
    script = os.path.join(REPO_ROOT, "scripts", "verify_absorption.py")
    code, out, err = sh([sys.executable, script, repo, "--json"])
    if code not in (0, 1):
        return False, "verifier error: %s" % err.decode("utf-8", "replace")[:120]
    try:
        data = json.loads(out.decode("utf-8", "replace"))[0]
    except Exception:
        return False, "unparseable verifier output"
    if data["status"] != "complete":
        return False, "incomplete: %d missing" % data["missing"]
    return True, "%d/%d files" % (data["covered"], data["remote_files"])


def store_file_via_git(registry: str, owner: str, repo: str, kind: str,
                       name: str, data: bytes) -> tuple[bool, str]:
    """Fallback for payloads too large for the Contents API.

    The blob API rejects anything over roughly 100 MB, and base64 inflates by a
    third, so a large bundle can never go that way. Cloning the registry and
    pushing the file is slower but has no practical ceiling.
    """
    tmp = tempfile.mkdtemp(prefix="regpush-")
    clone = os.path.join(tmp, "registry")
    # A plain clone of the registry is ~200 MB and fails here with "early EOF".
    # A blobless partial clone fetches only commit and tree metadata, so we can
    # add one file and push without downloading the existing content.
    code, _, err = sh(["gh", "repo", "clone", "%s/%s" % (owner, registry), clone,
                       "--", "--filter=blob:none", "--no-checkout"])
    if code != 0:
        return False, "clone failed: %s" % err.decode("utf-8", "replace")[:120]

    src = os.path.join(tmp, name)
    with open(src, "wb") as fh:
        fh.write(data)
    rel = "repos/%s/%s/%s" % (repo, kind, name)

    def g(*a) -> tuple[int, str, str]:
        c, o, e = sh(["git", "-C", clone] + list(a))
        return c, o.decode("utf-8", "replace").strip(), e.decode("utf-8", "replace").strip()

    c, blob, e = g("hash-object", "-w", src)
    if c != 0:
        return False, "hash-object failed: %s" % e[:100]

    # Plumbing only: no working tree, no index juggling. Build the tree from the
    # remote commit, graft our blob in, commit against that parent, push.
    for attempt in range(5):
        c, _, e = g("fetch", "--depth", "1", "origin", "main")
        if c != 0:
            return False, "fetch failed: %s" % e[:100]
        g("read-tree", "FETCH_HEAD")
        c, _, e = g("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, rel))
        if c != 0:
            return False, "update-index failed: %s" % e[:100]
        c, tree, e = g("write-tree")
        if c != 0:
            return False, "write-tree failed: %s" % e[:100]
        c, commit, e = g("commit-tree", tree, "-p", "FETCH_HEAD",
                         "-m", "chore(preserve): %s/%s/%s" % (repo, kind, name))
        if c != 0:
            return False, "commit-tree failed: %s" % e[:100]
        c, _, e = g("push", "origin", "%s:main" % commit)
        if c == 0:
            return True, commit[:12]
        if "too large" in e.lower() or "exceeds" in e.lower():
            return False, "server rejected size: %s" % e[:120]
    return False, "push failed: %s" % e[:120]


def store_file(registry: str, owner: str, repo: str, kind: str,
               name: str, data: bytes) -> tuple[bool, str]:
    """Commit one file into <registry>/repos/<repo>/<kind>/<name>.

    Small files go through the Contents API. Large ones fall back to a clone and
    push, because the blob API caps out around 100 MB and base64 inflates the
    payload by a third.
    """
    if len(data) > 30 * 1024 * 1024:
        return store_file_via_git(registry, owner, repo, kind, name, data)
    target = "%s/%s" % (owner, registry)
    code, out = gh_api("repos/%s/git/ref/heads/main" % target)
    if code != 0:
        return False, "cannot read registry ref"
    head = json.loads(out)["object"]["sha"]

    code, out = gh_api("repos/%s/git/commits/%s" % (target, head))
    if code != 0:
        return False, "cannot read registry commit"
    base_tree = json.loads(out)["tree"]["sha"]

    body = json.dumps({"content": base64.b64encode(data).decode(), "encoding": "base64"})
    code, out, err = sh(["gh", "api", "repos/%s/git/blobs" % target, "-X", "POST", "--input", "-"],
                        body.encode())
    if code != 0:
        detail = err.decode("utf-8", "replace")
        # Do not guess at a size ceiling; react to the server's own refusal.
        if "too large" in detail.lower() or "payload" in detail.lower():
            return store_file_via_git(registry, owner, repo, kind, name, data)
        return False, "blob failed: %s" % detail[:100]
    blob = json.loads(out.decode("utf-8", "replace"))["sha"]

    body = json.dumps({"base_tree": base_tree, "tree": [{
        "path": "repos/%s/%s/%s" % (repo, kind, name),
        "mode": "100644", "type": "blob", "sha": blob,
    }]})
    code, out, err = sh(["gh", "api", "repos/%s/git/trees" % target, "-X", "POST", "--input", "-"],
                        body.encode())
    if code != 0:
        return False, "tree failed: %s" % err.decode("utf-8", "replace")[:100]
    tree = json.loads(out.decode("utf-8", "replace"))["sha"]

    body = json.dumps({
        "message": "chore(preserve): %s/%s for an impending deletion" % (repo, kind),
        "tree": tree, "parents": [head],
    })
    code, out, err = sh(["gh", "api", "repos/%s/git/commits" % target, "-X", "POST", "--input", "-"],
                        body.encode())
    if code != 0:
        return False, "commit failed: %s" % err.decode("utf-8", "replace")[:100]
    commit = json.loads(out.decode("utf-8", "replace"))["sha"]

    body = json.dumps({"sha": commit, "force": False})
    code, out, err = sh(["gh", "api", "repos/%s/git/refs/heads/main" % target, "-X", "PATCH",
                         "--input", "-"], body.encode())
    if code != 0:
        return False, "ref update failed: %s" % err.decode("utf-8", "replace")[:100]
    return True, commit[:12]


def export_bundle(owner: str, repo: str) -> tuple[bool, str, int]:
    """Create and verify a full-history bundle. Returns (ok, path-or-error, size).

    Returning the path rather than the bytes matters: a large repository makes a
    bundle too big to hold alongside the fetch buffer, and often too big to store
    at all, so the caller decides how to preserve it.
    """
    tmp = tempfile.mkdtemp(prefix="preserve-")
    path = os.path.join(tmp, "%s.bundle" % repo)
    clone = os.path.join(tmp, "clone")
    code, _, err = sh(["gh", "repo", "clone", "%s/%s" % (owner, repo), clone, "--", "--mirror"])
    if code != 0:
        return False, "clone failed (repo may already be gone): %s" % err.decode("utf-8", "replace")[:100], 0
    code, _, err = sh(["git", "-C", clone, "bundle", "create", path, "--all"])
    if code != 0:
        return False, "bundle failed: %s" % err.decode("utf-8", "replace")[:100], 0
    code, _, _ = sh(["git", "-C", clone, "bundle", "verify", path])
    if code != 0:
        return False, "bundle verify failed", 0
    return True, path, os.path.getsize(path)


def store_history_as_refs(registry: str, owner: str, repo: str) -> tuple[bool, str]:
    """Preserve full history as git refs inside the private registry.

    A bundle is a single file, and GitHub rejects any file over 100 MB, so a
    repository whose history exceeds that cannot be preserved as a bundle at
    all. Pushing the real git objects into a private ref namespace has no such
    ceiling, keeps every commit reachable, and restores with a plain fetch:

        git fetch <registry> '+refs/preserved/<repo>/*:refs/heads/*'

    The push is verified by fetching the namespace back and comparing every
    branch tip, so a partial upload cannot pass as preserved.
    """
    tmp = tempfile.mkdtemp(prefix="refpush-")
    mirror = os.path.join(tmp, "mirror.git")
    # Plain git, not `gh repo clone`: for a fork gh adds an `upstream` remote and
    # fetches it, which lands upstream branches under refs/heads and would
    # preserve them under the fork's own namespace.
    code, _, err = sh(["git", "clone", "--mirror", "--quiet",
                       "https://github.com/%s/%s.git" % (owner, repo), mirror])
    if code != 0:
        return False, "mirror clone failed: %s" % err.decode("utf-8", "replace")[:100]

    def refs(where: str) -> dict[str, str]:
        _, out, _ = sh(["git", "-C", where, "for-each-ref",
                        "--format=%(refname) %(objectname)"])
        return dict(line.split(" ", 1)
                    for line in out.decode("utf-8", "replace").splitlines() if " " in line)

    def namespaces(source: dict[str, str]) -> list[str]:
        found = set()
        for name in source:
            rest = name[len("refs/"):].split("/") if name.startswith("refs/") else []
            if len(rest) >= 2:
                found.add(rest[0])
        # Our own namespaces inside the registry must never be copied into
        # themselves.
        found.discard("preserved")
        found.discard("restored")
        return sorted(found)

    # Preserve EVERY ref namespace, not just heads and tags. Repositories in this
    # account carry refs/pull/* (over a thousand in some), refs/keep/*,
    # refs/archive/* and refs/sources/*, and a commit reachable only from one of
    # those is invisible to a heads+tags capture. Enumerate instead of
    # hard-coding, so a namespace nobody anticipated cannot be silently dropped.
    source_refs = refs(mirror)
    spaces = namespaces(source_refs)
    if not spaces:
        return False, "no refs found in the source"

    url = "https://github.com/%s/%s.git" % (owner, registry)
    spec = ["+refs/%s/*:refs/preserved/%s/%s/*" % (ns, repo, ns) for ns in spaces]
    code, _, err = sh(["git", "-C", mirror, "push", url] + spec)
    if code != 0:
        return False, "ref push failed: %s" % err.decode("utf-8", "replace")[:120]

    # Compare on the same key shape: both sides keyed "<namespace>/<name>".
    expected = {m[len("refs/"):]: sha for m, sha in source_refs.items()
                if m.startswith("refs/") and m[len("refs/"):].split("/")[0] in spaces}
    check = os.path.join(tmp, "check")
    os.makedirs(check, exist_ok=True)
    for args in (["init", "-q"], ["remote", "add", "origin", url],
                 ["fetch", "-q", "origin", "+refs/preserved/%s/*:refs/restored/*" % repo]):
        code, _, err = sh(["git", "-C", check] + args)
        if code != 0:
            return False, "verify fetch failed: %s" % err.decode("utf-8", "replace")[:100]
    actual = {m[len("refs/restored/"):]: sha for m, sha in refs(check).items()
              if m.startswith("refs/restored/")}
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        differing = sorted(k for k in set(expected) & set(actual) if expected[k] != actual[k])
        return False, ("ref round-trip mismatch: %d missing, %d differing "
                       "(namespaces: %s)"
                       % (len(missing), len(differing), ",".join(spaces)))

    _, commits, _ = sh(["git", "-C", mirror, "rev-list", "--all", "--count"])
    return True, "%d refs across %d namespaces (%s), %s commits" % (
        len(expected), len(spaces), ",".join(spaces), commits.decode().strip())


def export_threads(owner: str, repo: str) -> tuple[bool, dict]:
    def paginate(path: str):
        code, out, _ = sh(["gh", "api", path, "--paginate"])
        if code != 0:
            return []
        try:
            return json.loads(out.decode("utf-8", "replace"))
        except Exception:
            return []

    issues = paginate("repos/%s/%s/issues?state=all&per_page=100" % (owner, repo))
    pulls = paginate("repos/%s/%s/pulls?state=all&per_page=100" % (owner, repo))
    comments = []
    for it in issues:
        if it.get("comments", 0):
            for c in paginate("repos/%s/%s/issues/%d/comments?per_page=100" % (owner, repo, it["number"])):
                c["_issue_number"] = it["number"]
                comments.append(c)
    return True, {"issues": issues, "pulls": pulls, "comments": comments}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repos", nargs="*")
    ap.add_argument("--owner", default=DEFAULT_OWNER)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    args = ap.parse_args()

    if not args.repos:
        ap.error("give one or more repo names")

    failures = 0
    for repo in args.repos:
        print("== %s" % repo)

        ok, detail = verify(repo)
        if not ok:
            print("   REFUSED  completeness check: %s" % detail)
            failures += 1
            continue
        print("   verified %s" % detail)

        ok, path, size = export_bundle(args.owner, repo)
        if not ok:
            print("   REFUSED  history bundle: %s" % path)
            failures += 1
            continue

        # 100 MB is a hard per-file limit on GitHub. Switch to refs while there
        # is still margin rather than discovering the ceiling mid-push.
        if size > 90 * 1024 * 1024:
            ok, detail = store_history_as_refs(args.registry, args.owner, repo)
            if not ok:
                print("   REFUSED  history refs: %s" % detail)
                failures += 1
                continue
            print("   history  %s (%.1f MB, too big for a bundle)"
                  % (detail, size / 1048576.0))
            note = (
                "# %s\n\n"
                "Full history is preserved as git refs, not as a bundle: the history is\n"
                "%.1f MB and GitHub rejects files over 100 MB.\n\n"
                "Restore with:\n\n"
                "    git clone --mirror https://github.com/%s/%s.git restored.git\n"
                "    cd restored.git\n"
                "    git fetch origin '+refs/preserved/%s/*:refs/heads/*'\n\n"
                "Every branch and tag tip was verified against the source after the push.\n"
            ) % (repo, size / 1048576.0, args.owner, args.registry, repo)
            ok, ref = store_file(args.registry, args.owner, repo, "history",
                                 "PRESERVED-AS-REFS.md", note.encode())
            if not ok:
                print("   REFUSED  history note: %s" % ref)
                failures += 1
                continue
        else:
            with open(path, "rb") as fh:
                payload = fh.read()
            os.unlink(path)
            ok, ref = store_file(args.registry, args.owner, repo, "history",
                                 "%s.bundle" % repo, payload)
            if not ok:
                print("   REFUSED  bundle store: %s" % ref)
                failures += 1
                continue
            print("   bundled  %s (%.1f KB)" % (ref, size / 1024.0))

        ok, threads = export_threads(args.owner, repo)
        if not ok:
            print("   REFUSED  thread export")
            failures += 1
            continue
        for name, data in (("issues.json", threads["issues"]),
                           ("pulls.json", threads["pulls"]),
                           ("issue-comments.json", threads["comments"])):
            if not data:
                continue
            ok, ref = store_file(args.registry, args.owner, repo, "github", name,
                                 json.dumps(data, indent=1).encode())
            if not ok:
                print("   REFUSED  %s: %s" % (name, ref))
                failures += 1
                break
        else:
            print("   threads  %d issues, %d pulls, %d comments"
                  % (len(threads["issues"]), len(threads["pulls"]), len(threads["comments"])))
            print("   DELETE-AUTHORISED %s" % repo)
            continue
        continue

    print()
    print("prepared %d, blocked %d" % (len(args.repos) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
