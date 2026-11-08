#!/usr/bin/env python3
"""Resolve the cargo packages affected by a set of changed files.

The local hooks should validate the code a change actually touches, not the
whole workspace. A workspace-wide `cargo clippy -D warnings` fails on lint debt
in crates the change never touched, which makes the hook block unrelated work
and duplicates the CI hard gate (.github/workflows/quality-gate.yml -> make
check) that already runs on the pull request.

Usage:
    python3 .lefthook/changed_packages.py <file> [<file> ...]

Prints one `-p <package>` selector per line, so the output can be piped
straight into cargo:

    python3 .lefthook/changed_packages.py $(git diff --name-only) | xargs cargo check

Prints nothing when no changed file belongs to a workspace package.
Paths are resolved relative to the repository root.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(out.stdout.strip())


def workspace_manifests(root: Path) -> dict[str, str]:
    """Map package directory -> package name for every workspace member."""
    out = subprocess.run(
        ["cargo", "metadata", "--no-deps", "--format-version", "1"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(out.stdout)
    manifests: dict[str, str] = {}
    for package in data.get("packages", []):
        manifest = package.get("manifest_path")
        if manifest:
            manifests[str(Path(manifest).parent.resolve())] = package["name"]
    return manifests


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: changed_packages.py <file> [...]", file=sys.stderr)
        return 2

    root = repo_root()
    try:
        manifests = workspace_manifests(root)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"changed_packages: could not read cargo metadata: {exc}", file=sys.stderr)
        return 1

    # Longest manifest path first so nested crates win over their parent.
    ordered = sorted(manifests.items(), key=lambda item: len(item[0]), reverse=True)

    names: list[str] = []
    for raw in argv[1:]:
        path = Path(raw)
        if not path.is_absolute():
            path = root / path
        try:
            resolved = path.resolve()
        except OSError:
            continue
        for manifest_dir, name in ordered:
            if resolved.is_relative_to(manifest_dir):
                if name not in names:
                    names.append(name)
                break

    for name in names:
        # Emit a ready-to-use cargo argument fragment. The selectors must come
        # BEFORE cargo's `--` separator: everything after it is forwarded to
        # the compiler, which rejects `--package` with
        # "Unrecognized option: 'package'".
        print(f"--package {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
