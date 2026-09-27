#!/usr/bin/env python3
"""Reproducible codebase atlas generator for PhenoShared.

Deterministic and offline: Python 3 standard library only, no network, no
`cargo build`. The git index (`git ls-files`) is the source of truth, so build
output and untracked files never enter the inventory.

Writes four artifacts into docs/atlas/codebase/:

    INVENTORY.md   per-package inventory (every tracked Cargo.toml directory)
    FILES.md       per-file inventory and the file-size gate violation lists
    HYGIENE.md     repository-rule violations and absorbed debris
    README.md      how to re-run, and what each artifact means

Usage:
    python3 scripts/atlas/generate.py
    python3 scripts/atlas/generate.py --check
    python3 scripts/atlas/generate.py --stdout INVENTORY.md
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from atlaslib import gitio, hygiene, packages, render, render_hygiene, scan  # noqa: E402
from atlaslib.definitions import (  # noqa: E402
    ARTIFACTS,
    LIMIT_HARD,
    LIMIT_TARGET,
    OUT_DIR_REL,
)
from atlaslib.readme_text import README  # noqa: E402


def build(root: str):
    """Collect everything, then render. Pure computation; writes nothing."""
    _, revision = gitio.revision(root)
    paths = gitio.tracked_paths(root)
    files = scan.scan_all(root, paths)
    manifests, _ = packages.build_packages(root, paths)
    dates = gitio.commit_dates(root)
    rows, unowned, _ = packages.aggregate(root, manifests, paths, files, dates)
    findings = hygiene.collect(root, files, manifests)

    member_rows = [r for r in rows if r["is_member"]]
    totals = {
        "packages": len(rows),
        "members": len(member_rows),
        "files": len(paths),
        "loc": sum(rec["loc"] for rec in files.values()),
        "rs_files": sum(1 for p in paths if p.endswith(".rs")),
        "rust_loc": sum(rec["loc"] for p, rec in files.items() if p.endswith(".rs")),
        "tests": sum(rec["tests"] for rec in files.values()),
        "member_loc": sum(r["loc"] for r in member_rows),
    }
    artifacts = {
        "INVENTORY.md": render.render_inventory(revision, rows, unowned, totals, manifests),
        "FILES.md": render.render_files(revision, files, findings),
        "HYGIENE.md": render_hygiene.render(revision, files, findings, manifests),
        "README.md": README,
    }
    return revision, paths, files, manifests, findings, totals, artifacts


def normalize(text: str) -> str:
    return text.replace("\n", "\n").rstrip("\n") + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", help="repository root (default: git toplevel)")
    parser.add_argument("--out-dir", help=f"output directory (default: {os.path.join(*OUT_DIR_REL)})")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if the committed artifacts are stale")
    parser.add_argument("--stdout", choices=ARTIFACTS, metavar="ARTIFACT",
                        help="print one artifact to stdout and write nothing")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    root = gitio.repo_root(args.repo_root)
    out_dir = os.path.join(root, args.out_dir or os.path.join(*OUT_DIR_REL))
    revision, paths, files, manifests, findings, totals, artifacts = build(root)

    if args.stdout:
        sys.stdout.write(normalize(artifacts[args.stdout]))
        return 0

    if args.check:
        stale = []
        for name in ARTIFACTS:
            try:
                with open(os.path.join(out_dir, name), encoding="utf-8") as handle:
                    if handle.read() != normalize(artifacts[name]):
                        stale.append(name)
            except OSError:
                stale.append(name + " (missing)")
        if stale:
            print("stale artifacts at " + os.path.relpath(out_dir, root) + ": "
                  + ", ".join(stale), file=sys.stderr)
            return 1
        print("atlas artifacts are up to date")
        return 0

    os.makedirs(out_dir, exist_ok=True)
    for name in ARTIFACTS:
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
            handle.write(normalize(artifacts[name]))

    if not args.quiet:
        print(f"wrote {len(ARTIFACTS)} artifacts to {os.path.relpath(out_dir, root)}")
        print(f"  revision {revision}: {totals['files']} tracked files, "
              f"{totals['packages']} packages ({totals['members']} workspace members), "
              f"{totals['rust_loc']} Rust LOC")
        print(f"  gate: {len(findings['over_target'])} files >{LIMIT_TARGET}, "
              f"{len(findings['over_hard'])} files >{LIMIT_HARD}; "
              f"{len(findings['zero_byte'])} zero-byte; "
              f"{len(findings['redacted'])} files with the redaction marker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
