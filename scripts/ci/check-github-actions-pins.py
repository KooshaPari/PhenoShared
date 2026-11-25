#!/usr/bin/env python3
"""Verify GitHub Actions workflow references are pinned to immutable SHAs."""

from __future__ import annotations

import re
import sys
from pathlib import Path


PINNED_REF = re.compile(r"^[0-9a-fA-F]{40}$")
USES_LINE = re.compile(r"^\s*uses:\s*([^\s#]+)")
SKIP_DIRS = {".git", "node_modules", "target", "pheno-wtrees"}


def workflow_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob(".github"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        workflows = path / "workflows"
        if workflows.is_dir():
            files.extend(sorted(workflows.glob("*.yml")))
            files.extend(sorted(workflows.glob("*.yaml")))
    return sorted(files)


def is_local_reference(reference: str) -> bool:
    return reference.startswith("./") or reference.startswith("../")


def is_pinned_reference(reference: str) -> bool:
    if is_local_reference(reference):
        return True
    if "@" not in reference:
        return False
    ref = reference.rsplit("@", 1)[1]
    return bool(PINNED_REF.fullmatch(ref))


def main() -> int:
    root = Path.cwd()
    violations: list[tuple[Path, int, str]] = []

    for workflow in workflow_files(root):
        for line_number, line in enumerate(workflow.read_text().splitlines(), start=1):
            match = USES_LINE.match(line)
            if not match:
                continue
            reference = match.group(1).strip('"\'')
            if not is_pinned_reference(reference):
                violations.append((workflow, line_number, reference))

    if violations:
        print("Unpinned GitHub Actions references found:")
        for workflow, line_number, reference in violations:
            print(f"{workflow}:{line_number}: {reference}")
        return 1

    print(f"All GitHub Actions uses references are pinned in {len(workflow_files(root))} workflows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
