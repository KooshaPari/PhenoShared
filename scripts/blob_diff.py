#!/usr/bin/env python3
"""Show a readable diff between a snapshot blob and the live repo's version.

The 41 divergent OmniRoute files cannot be ordered by hash or by date. What can
be read is the content: a snapshot newer than the live tree tends to *add*
imports, options and tests; an older one tends to lack things the live tree has.
This prints a bounded unified diff per file so that judgement can be made on the
actual text rather than on inference.

Usage:
    python blob_diff.py <snapshot> <live> [path ...]
"""
import base64
import difflib
import json
import subprocess
import sys

OWNER = "KooshaPari"

PATHS = [
    "scripts/sre/redact-logs.mjs",
    "open-sse/services/autoCombo/speedRanking.ts",
    "tests/unit/provider-onboarding-href.test.ts",
    "open-sse/executors/userAgentHeader.ts",
]

MAX_LINES = 40


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def tree_map(repo):
    code, out, err = sh(["gh", "api", "repos/%s/%s" % (OWNER, repo), "--jq", ".default_branch"])
    ref = out.strip()
    code, out, err = sh(["gh", "api",
                         "repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, repo, ref)])
    d = json.loads(out)
    return {e["path"]: e["sha"] for e in d["tree"] if e.get("type") == "blob"}


def blob_text(repo, sha):
    code, out, err = sh(["gh", "api", "repos/%s/%s/git/blobs/%s" % (OWNER, repo, sha)])
    if code != 0:
        return None
    d = json.loads(out)
    if d.get("encoding") != "base64":
        return None
    raw = base64.b64decode(d["content"])
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    snap, live = sys.argv[1], sys.argv[2]
    paths = sys.argv[3:] or PATHS

    a = tree_map(snap)
    b = tree_map(live)

    for path in paths:
        sa, sb = a.get(path), b.get(path)
        if not sa or not sb:
            print("=== %s === (missing on one side)" % path)
            continue
        ta, tb = blob_text(snap, sa), blob_text(live, sb)
        if ta is None or tb is None:
            print("=== %s === (binary or unreadable)" % path)
            continue
        la, lb = ta.splitlines(), tb.splitlines()
        added = sum(1 for l in difflib.unified_diff(la, lb, n=0)
                    if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in difflib.unified_diff(la, lb, n=0)
                      if l.startswith("-") and not l.startswith("---"))
        print("=== %s ===" % path)
        print("    snapshot %d lines, live %d lines"
              % (len(la), len(lb)))
        print("    going snapshot -> live: %d lines added, %d removed"
              % (added, removed))
        diff = list(difflib.unified_diff(la, lb, fromfile="snapshot",
                                         tofile="live", lineterm="", n=2))
        for line in diff[:MAX_LINES]:
            print("    %s" % line[:160])
        if len(diff) > MAX_LINES:
            print("    ... %d more diff lines" % (len(diff) - MAX_LINES))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
