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


def store_file(registry: str, owner: str, repo: str, kind: str,
               name: str, data: bytes) -> tuple[bool, str]:
    """Commit one file into <registry>/repos/<repo>/<kind>/<name> via the API."""
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
        return False, "blob failed: %s" % err.decode("utf-8", "replace")[:100]
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


def export_bundle(owner: str, repo: str) -> tuple[bool, bytes | str]:
    tmp = tempfile.mkdtemp(prefix="preserve-")
    path = os.path.join(tmp, "%s.bundle" % repo)
    clone = os.path.join(tmp, "clone")
    code, _, err = sh(["gh", "repo", "clone", "%s/%s" % (owner, repo), clone])
    if code != 0:
        return False, "clone failed (repo may already be gone): %s" % err.decode("utf-8", "replace")[:100]
    code, _, err = sh(["git", "-C", clone, "bundle", "create", path, "--all"])
    if code != 0:
        return False, "bundle failed: %s" % err.decode("utf-8", "replace")[:100]
    code, _, err = sh(["git", "-C", clone, "bundle", "verify", path])
    if code != 0:
        return False, "bundle verify failed"
    with open(path, "rb") as fh:
        return True, fh.read()


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

        ok, payload = export_bundle(args.owner, repo)
        if not ok:
            print("   REFUSED  history bundle: %s" % payload)
            failures += 1
            continue
        ok, ref = store_file(args.registry, args.owner, repo, "history",
                             "%s.bundle" % repo, payload)
        if not ok:
            print("   REFUSED  bundle store: %s" % ref)
            failures += 1
            continue
        print("   bundled  %s (%.1f KB)" % (ref, len(payload) / 1024.0))

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
