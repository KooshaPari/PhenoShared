#!/usr/bin/env python3
"""Who created the repositories that appeared on 2026-11-14?

GitHub does not expose a repo's creator through the API, and the org audit log is
an enterprise feature here (404). What is available is the commit identity on the
import commits, plus the repo metadata. That is enough to tell a human push from
a scripted one, and to see whether the identity differs from the one used for
normal work.
"""
import json
import subprocess
import sys

OWNER = "KooshaPari"

REPOS = ["BytePort", "audit-snapshot-pheno", "audit-snapshot-tooling",
         "dagrun", "harness-ops", "zz-aa-dep-AirLock", "pheno"]


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def main():
    for repo in REPOS:
        print("=== %s ===" % repo)
        code, out, err = sh(["gh", "api", "repos/%s/%s" % (OWNER, repo)])
        if code != 0:
            print("  no repo")
            continue
        d = json.loads(out)
        print("  created   %s" % d.get("created_at"))
        print("  pushed    %s" % d.get("pushed_at"))
        print("  owner     %s" % (d.get("owner") or {}).get("login"))
        print("  desc      %s" % (d.get("description") or "")[:70])

        code, out, err = sh(["gh", "api",
                             "repos/%s/%s/commits?per_page=1" % (OWNER, repo)])
        if code == 0:
            commits = json.loads(out)
            if commits:
                c = commits[0]["commit"]
                print("  author    %s <%s>" % (c["author"]["name"], c["author"]["email"]))
                print("  committed %s" % c["committer"]["date"])
                print("  message   %s" % c["message"].splitlines()[0][:70])
        else:
            print("  no commits")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
