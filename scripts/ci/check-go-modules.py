#!/usr/bin/env python3
"""Verify every Go module in the tree is explicitly declared or ignored.

The Go CI job gates the modules listed in go.modules.txt. This check makes
that list authoritative: a go.mod that appears anywhere in the tree but is
neither listed nor covered by an ignore rule fails the build.

Without it, a vendored snapshot under _archived/ or absorption/ can enter the
module set unnoticed. Those snapshots carry replace directives pointing at
worktrees that no longer exist, so building them fails for reasons unrelated
to the change under test.

Usage:
    python3 scripts/ci/check-go-modules.py [--root .]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ALLOWLIST = "go.modules.txt"

# Paths whose go.mod files are deliberately not gated. Each exclusion is
# documented with its reason in docs/go-modules-excluded.md.
#
#   _archived/, absorption/  absorbed or archived snapshots; their go.mod
#                            files carry replace directives pointing at
#                            worktrees and vendored trees that no longer exist
#   crates/hexa-kit/        embedded templates, not build targets
#   crates/policystack/     wrapper fixtures
IGNORE_PREFIXES = (
    "_archived/",
    "absorption/",
    ".archive/",
    "node_modules/",
    "vendor/",
    "crates/hexa-kit/",
    "crates/policystack/",
)

# Module paths excluded for a documented reason. These are live paths, not
# prefixes, so each one needs its own entry. The reason for each is recorded
# in docs/go-modules-excluded.md.
IGNORED_MODULES = frozenset(
    {
        # Absorbed snapshot: upstreams deleted, cmd/ missing, needs templ generate.
        "hfscope",
        # Integration-test fixture workspaces.
        "servers/external/mcpforge/integrationtests/workspaces/go",
        # Duplicate copies of agileplus/pheno-cli (same module path, missing
        # internal/hooks/scripts/ so they fail go vet).
        "crates/agile-plus/pheno-cli",
        "crates/hexa-kit/agileplus/pheno-cli",
        # Broken, each needs a real fix before it can be gated:
        #   unknown command "bootstrap"; templates_test expects 5, finds 39
        "agents/phenoagent/pheno-cli-go",
        # Needs Go >= 1.26.7 and has 152 gofmt violations.
        "crates/argis-extensions",
        # Incomplete vendored shim: undefined schemas.ChatMessageRole.
        "crates/argis-extensions/bifrost/core",
        # TestDiagnostics/CleanFile fails after 41s.
        "servers/external/mcpforge",
        # go vet does not complete within 300s; heavy dependency tree.
        "servers/external/ops-mcp",
    }
)

SKIP_DIRS = {".git", "node_modules", "vendor", "target", "pheno-wtrees"}


def parse_allowlist(path: Path) -> set[str]:
    """Return the module directories declared in the allowlist."""
    entries: set[str] = set()
    if not path.is_file():
        return entries
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entries.add(line.rstrip("/"))
    return entries


def find_modules(root: Path) -> list[str]:
    """Return every directory containing a go.mod, relative to root.

    Paths ignored by git are skipped: test harnesses often write a go.mod
    into a scratch workspace, and those are not modules of this repository.
    """
    found: list[str] = []
    for go_mod in root.rglob("go.mod"):
        parts = go_mod.relative_to(root).parts
        if any(part in SKIP_DIRS for part in parts):
            continue
        if is_git_ignored(root, go_mod):
            continue
        found.append(str(go_mod.parent.relative_to(root)))
    return sorted(found)


def is_git_ignored(root: Path, path: Path) -> bool:
    """Report whether git ignores the given path."""
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def is_ignored(rel: str) -> bool:
    """Report whether a module path is covered by an ignore rule."""
    if rel in IGNORED_MODULES:
        return True
    return any(rel.startswith(prefix) for prefix in IGNORE_PREFIXES)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    allowlist_path = root / ALLOWLIST
    allowed = parse_allowlist(allowlist_path)

    if not allowed:
        print(f"error: {ALLOWLIST} is missing or empty", file=sys.stderr)
        return 1

    problems: list[str] = []

    for module in sorted(allowed):
        if not (root / module / "go.mod").is_file():
            problems.append(f"{ALLOWLIST}: {module} is listed but has no go.mod")

    for module in find_modules(root):
        if module in allowed:
            continue
        if is_ignored(module):
            continue
        problems.append(
            f"stray go.mod: {module} is not in {ALLOWLIST}. "
            "Add it if it is a live module, or move it under an ignored path "
            "if it is a vendored snapshot."
        )

    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        print(f"\n{len(problems)} Go module declaration problem(s).", file=sys.stderr)
        return 1

    print(f"Go modules OK: {len(allowed)} declared, no strays.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
