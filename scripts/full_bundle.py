#!/usr/bin/env python3
"""Create a verified full-history bundle of a repository.

`git bundle create --all` captures every ref namespace - branches, tags, and the
refs/pull, refs/keep, refs/archive and refs/sources that real repositories in
this account carry. That matters: in this account `refs/pull` alone runs to over
a thousand refs on some repositories, and a commit reachable only from one of
those is invisible to a heads-plus-tags capture.

The bundle is verified before it is stored, and the verification is a real
round-trip: the bundle is cloned into a scratch directory and its ref list is
compared against the source. A bundle that cannot restore the graph is not a
backup.

    python scripts/full_bundle.py HeliosLite --store
    python scripts/full_bundle.py HeliosCLI HeliosLite --store
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

OWNER_DEFAULT = "KooshaPari"
REGISTRY_DEFAULT = "PhenoRegistry"


def sh(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def ref_map(repo: str) -> dict[str, str]:
    code, out, err = sh(["git", "-C", repo, "for-each-ref",
                         "--format=%(refname) %(objectname)"])
    if code != 0:
        raise RuntimeError("for-each-ref failed: %s" % err.strip()[:200])
    return dict(line.split(" ", 1) for line in out.splitlines() if " " in line)


def build(repo: str, owner: str, workdir: str) -> tuple[bool, str, str | None]:
    """Mirror, bundle, and round-trip verify. Returns (ok, detail, bundle path)."""
    mirror = os.path.join(workdir, "%s.git" % repo)
    code, _, err = sh(["git", "clone", "--mirror", "--quiet",
                       "https://github.com/%s/%s.git" % (owner, repo), mirror])
    if code != 0:
        return False, "mirror clone failed: %s" % err.strip()[:150], None

    source = ref_map(mirror)
    spaces: dict[str, int] = {}
    for name in source:
        if name.startswith("refs/"):
            ns = name[len("refs/"):].split("/")[0]
            spaces[ns] = spaces.get(ns, 0) + 1

    bundle = os.path.join(workdir, "%s.bundle" % repo)
    code, _, err = sh(["git", "-C", mirror, "bundle", "create", bundle, "--all"])
    if code != 0:
        return False, "bundle create failed: %s" % err.strip()[:150], None
    code, _, err = sh(["git", "-C", mirror, "bundle", "verify", bundle])
    if code != 0:
        return False, "bundle verify failed: %s" % err.strip()[:150], None

    # Round trip: a bundle that will not clone back is not a backup.
    check = os.path.join(workdir, "%s.check" % repo)
    code, _, err = sh(["git", "clone", "--quiet", "--mirror", bundle, check])
    if code != 0:
        return False, "bundle does not clone back: %s" % err.strip()[:150], None
    restored = ref_map(check)
    if restored != source:
        missing = sorted(set(source) - set(restored))
        differing = sorted(k for k in set(source) & set(restored) if source[k] != restored[k])
        return False, ("round-trip mismatch: %d missing, %d differing"
                       % (len(missing), len(differing))), None

    size = os.path.getsize(bundle)
    _, count, _ = sh(["git", "-C", mirror, "rev-list", "--all", "--count"])
    detail = ("%d refs across %d namespaces (%s), %s commits, %.1f MB, round-trip exact"
              % (len(source), len(spaces),
                 ", ".join("%s=%d" % (k, v) for k, v in sorted(spaces.items())),
                 count.strip(), size / 1048576.0))
    return True, detail, bundle


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repos", nargs="+")
    ap.add_argument("--owner", default=OWNER_DEFAULT)
    ap.add_argument("--registry", default=REGISTRY_DEFAULT)
    ap.add_argument("--store", action="store_true",
                    help="push the bundle to <registry>/repos/<repo>/history/")
    args = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    workdir = tempfile.mkdtemp(prefix="fullbundle-")
    failures = 0
    for repo in args.repos:
        ok, detail, path = build(repo, args.owner, workdir)
        print("== %s" % repo)
        if not ok:
            print("   FAILED  %s" % detail)
            failures += 1
            continue
        print("   bundled %s" % detail)
        if args.store:
            import prepare_deletion as pd
            with open(path, "rb") as fh:
                data = fh.read()
            ok, ref = pd.store_file(args.registry, args.owner, repo, "history",
                                    "%s.bundle" % repo, data)
            if not ok:
                print("   FAILED  store: %s" % ref)
                failures += 1
                continue
            print("   stored  %s" % ref)
        else:
            print("   not stored (pass --store), left at %s" % path)

    print()
    print("bundled %d, failed %d" % (len(args.repos) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
