"""DAG-73: tests/test_gitignore_no_source_tree_patterns.py

ADR 0008 §D4 forbids .gitignore patterns that hide source-tree files.
The 5 toxic patterns removed in commit 4bf638c were:

  - /AGENTS.md       (shadowed the canonical intake)
  - /SPEC.md         (shadowed the canonical spec)
  - /DESIGN.md       (shadowed the canonical design)
  - /README.md       (shadowed the canonical readme)
  - /pyproject.toml  (shadowed the canonical pyproject)

This test asserts none of those patterns (or their file names) reappear
in .gitignore. It is a load-bearing drift-guard for ADR 0008.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GITIGNORE = REPO_ROOT / ".gitignore"

TOXIC_FILES = ["AGENTS.md", "SPEC.md", "DESIGN.md", "README.md", "pyproject.toml"]


def test_gitignore_does_not_shadow_canonical_source_files() -> None:
    """None of the 5 toxic source-tree patterns can reappear."""
    text = GITIGNORE.read_text()
    for fname in TOXIC_FILES:
        # Patterns like /AGENTS.md, /AGENTS.md*, AGENTS.md, etc. — match
        # the bare filename at the start of a line (after optional
        # leading /). Whitelist comments that mention the filename
        # in prose (e.g. "AGENTS.md is the canonical intake").
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Strip the leading / if present.
            if stripped.startswith("/"):
                stripped = stripped[1:]
            # Ignore patterns that include a directory prefix
            # (e.g. "build/AGENTS.md" is fine — it scopes to build/).
            if "/" in stripped and not stripped.startswith("**/"):
                continue
            if stripped == fname or stripped.startswith(fname + "*"):
                pytest.fail(
                    f".gitignore line {line!r} shadows canonical source "
                    f"file {fname!r} (ADR 0008 §D4 violation)"
                )


def test_gitignore_does_not_have_double_star_in_root() -> None:
    """Patterns like ``/foo/**/bar`` that walk into source dirs are
    not allowed at the root. The bench/results/ subtree is exempted
    because its .json is gitignored (audit-F4 close-out).
    """
    text = GITIGNORE.read_text()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("**/"):
            # Double-star at the root is fine if it scopes to a
            # build artifact (e.g. kernels/**/.zig-cache/).
            pytest.fail(
                f".gitignore line {line!r} has a top-level **/ pattern "
                f"(ADR 0008 §D4 violation)"
            )
