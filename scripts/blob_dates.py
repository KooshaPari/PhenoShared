#!/usr/bin/env python3
"""Is the snapshot's version of a file newer or older than the live repo's?

A blob that exists in the snapshot but nowhere in the live history is divergent
content. That alone does not say which side is more recent, and restoring the
wrong direction silently reverts work.

Two dates per path settle most of it:

  snapshot commit date      when the import was created
  live last-changed date    the most recent commit touching that path

If live last changed a path before the snapshot was taken, the snapshot may hold
newer work. If live changed it after, the live version is at least as recent,
and restoring the snapshot would be a regression.

Usage:
    python blob_dates.py <snapshot> <live> [path ...]
"""
import json
import subprocess
import sys

OWNER = "KooshaPari"

PATHS = [
    "open-sse/executors/userAgentHeader.ts",
    "open-sse/executors/reasoningEffortMaps.ts",
    "open-sse/executors/vertexMedia.ts",
    "open-sse/handlers/chatCore/getUpstreamErrorIdentifier.ts",
    "open-sse/services/autoCombo/speedRanking.ts",
    "scripts/sre/oncall-rotation.mjs",
    "scripts/sre/redact-logs.mjs",
    "src/app/api/compression/replay/route.ts",
    "src/lib/skills/containerProvider.ts",
    "tests/unit/vertex-media.test.ts",
]


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def snapshot_date(repo):
    code, out, err = sh(["gh", "api", "repos/%s/%s/commits?per_page=1" % (OWNER, repo),
                         "--jq", '.[0] | "\\(.commit.committer.date) \\(.commit.message | split("\\n")[0])"'])
    if code != 0:
        return "unknown", ""
    line = out.strip()
    date, _, msg = line.partition(" ")
    return date, msg


def live_last_change(repo, path):
    quoted = path.replace("(", "%28").replace(")", "%29")
    code, out, err = sh(["gh", "api",
                         "repos/%s/%s/commits?path=%s&per_page=1" % (OWNER, repo, quoted),
                         "--jq", '.[0] | "\\(.commit.committer.date) \\(.sha[0:8])"'])
    if code != 0 or not out.strip() or out.strip() == "null":
        return "none", ""
    date, _, sha = out.strip().partition(" ")
    return date, sha


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    snap, live = sys.argv[1], sys.argv[2]
    paths = sys.argv[3:] or PATHS

    sdate, smsg = snapshot_date(snap)
    print("snapshot %s committed %s" % (snap, sdate))
    if smsg:
        print("  %s" % smsg[:90])
    print()
    print("%-52s %-22s %-10s %s" % ("path", "live last changed", "sha", "reading"))
    print("-" * 110)
    older = newer = unknown = 0
    for path in paths:
        ldate, lsha = live_last_change(live, path)
        if ldate == "none":
            reading = "live never had this path"
            unknown += 1
        elif ldate[:10] > sdate[:10]:
            reading = "live CHANGED AFTER the snapshot"
            newer += 1
        else:
            reading = "live last changed BEFORE the snapshot"
            older += 1
        print("%-52s %-22s %-10s %s" % (path[:52], ldate, lsha, reading))
    print()
    print("live newer than snapshot: %d   live older: %d   indeterminate: %d"
          % (newer, older, unknown))
    return 0


if __name__ == "__main__":
    sys.exit(main())
