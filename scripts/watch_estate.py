#!/usr/bin/env python3
"""Detect repository creation and deletion by diffing the estate over time.

The process that recreated sixteen repositories on 2026-11-14 could not be
identified from GitHub (the org audit log is enterprise-only here) or from the
machine (no scheduled task, no persistent script, no process whose command line
matched). It acts inline from an agent session, so it leaves nothing behind after
the command returns.

Chasing it further is low-yield. Making it visible is not: this records the full
repository list with sizes, diffs it against the previous record, and reports what
appeared or disappeared with the time window in which it happened. Run it from a
watcher or by hand and the next burst is attributable to an interval even when the
actor is not.

Usage:
    python watch_estate.py            # diff against the last snapshot and update it
    python watch_estate.py --show     # diff only, do not update
"""
import json
import os
import subprocess
import sys
import time

OWNER = "KooshaPari"
STATE = r"C:\Users\koosh\PhenoShared\docs\absorption-ledger\estate-snapshot.json"

# Names that are expected to exist and never be deleted.
PROTECTED = {"PhenoShared", "PhenoRegistry"}


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def current():
    code, out, err = sh(["gh", "repo", "list", OWNER, "--limit", "500",
                         "--json", "name,isPrivate,diskUsage,createdAt"])
    if code != 0:
        raise SystemExit("gh repo list failed: %s" % err[:200])
    return {x["name"]: {"priv": x["isPrivate"], "kb": x["diskUsage"],
                        "created": x["createdAt"]}
            for x in json.loads(out)}


def load():
    if not os.path.isfile(STATE):
        return None
    try:
        with open(STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def main():
    show_only = "--show" in sys.argv
    now = current()
    prev = load()

    print("repositories now: %d" % len(now))

    if prev is None:
        print("no previous snapshot; recording a baseline")
        prev_repos = {}
    else:
        prev_repos = prev.get("repos", {})
        stamp = prev.get("captured", "unknown")
        print("previous snapshot: %s (%d repos)" % (stamp, len(prev_repos)))

    added = sorted(set(now) - set(prev_repos))
    removed = sorted(set(prev_repos) - set(now))
    resized = sorted(n for n in set(now) & set(prev_repos)
                     if now[n]["kb"] != prev_repos[n].get("kb"))

    print()
    if added:
        print("ADDED since the last snapshot: %d" % len(added))
        for n in added:
            print("   + %-46s %8.1f MB  created %s"
                  % (n, now[n]["kb"] / 1024.0, now[n]["created"][:19]))
    if removed:
        print("REMOVED since the last snapshot: %d" % len(removed))
        for n in removed:
            flag = "  <-- PROTECTED, investigate" if n in PROTECTED else ""
            print("   - %-46s%s" % (n, flag))
    if resized:
        print("CHANGED SIZE: %d" % len(resized))
        for n in resized:
            print("   ~ %-46s %8.1f -> %8.1f MB"
                  % (n, prev_repos[n].get("kb", 0) / 1024.0, now[n]["kb"] / 1024.0))
    if not (added or removed or resized):
        print("no change")

    if not show_only:
        payload = {
            "captured": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "count": len(now),
            "repos": now,
        }
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1, sort_keys=True)
        print()
        print("snapshot written to %s" % STATE)

    return 0


if __name__ == "__main__":
    sys.exit(main())
