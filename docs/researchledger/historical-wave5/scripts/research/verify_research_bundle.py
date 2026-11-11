#!/usr/bin/env python3
"""Verify a derived research package without running its source material.

Integrity is not truth, review completeness, or experiment reproduction.
This checker rejects the previously delivered three-file status stub.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

MANIFEST = "BUNDLE-MANIFEST.json"
REQUIRED = frozenset({
    "README.md",
    "docs/corpora/emergent-garden/data/youtube-channel-inventory-v1.json",
    "docs/corpora/emergent-garden/data/wave-4-source-reviews.json",
    "docs/corpora/emergent-garden/research/WAVE-4-METHODS-REVIEW.md",
    "docs/corpora/emergent-garden/research/WAVE-4-EXECUTION-CHECKPOINT.md",
    "scripts/research/verify_research_bundle.py",
    "validation/wave-4-tests.txt",
})
MAX_FILES = 10000
MAX_BYTES = 100_000_000


def verify(root: Path, required: frozenset[str] = REQUIRED) -> dict:
    """Return all bounded validation failures; never execute imported content."""
    root = root.resolve()
    findings: list[str] = []
    manifest = root / MANIFEST
    if not manifest.is_file() or manifest.is_symlink():
        return {"passed": False, "checked_files": 0, "findings": ["MANIFEST_MISSING_OR_SYMLINK"]}
    if manifest.stat().st_size > 2_000_000:
        return {"passed": False, "checked_files": 0, "findings": ["MANIFEST_TOO_LARGE"]}
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"passed": False, "checked_files": 0, "findings": ["MANIFEST_UNREADABLE"]}
    rows = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows or len(rows) > MAX_FILES:
        return {"passed": False, "checked_files": 0, "findings": ["MANIFEST_ENTRIES_INVALID"]}
    listed: set[str] = set()
    checked, total = 0, 0
    for row in rows:
        if not isinstance(row, dict):
            findings.append("ENTRY_INVALID")
            continue
        name, expected, size = row.get("path"), row.get("sha256"), row.get("bytes")
        if (not isinstance(name, str) or not name or "\\" in name
                or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
                or str(PurePosixPath(name)) != name or name == MANIFEST):
            findings.append("PATH_INVALID")
            continue
        if name in listed:
            findings.append("DUPLICATE_PATH:" + name)
            continue
        listed.add(name)
        if (not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected)
                or not isinstance(size, int) or isinstance(size, bool) or size < 0):
            findings.append("HASH_OR_SIZE_INVALID:" + name)
            continue
        path = root / name
        if any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
            findings.append("SYMLINK_REFUSED:" + name)
            continue
        if not path.resolve().is_relative_to(root) or not path.is_file():
            findings.append("MISSING_OR_ESCAPING_FILE:" + name)
            continue
        actual_size = path.stat().st_size
        total += actual_size
        if total > MAX_BYTES:
            findings.append("SIZE_BUDGET_EXCEEDED")
            break
        if actual_size != size:
            findings.append("SIZE_MISMATCH:" + name)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            findings.append("HASH_MISMATCH:" + name)
        if path.suffix == ".json":
            try:
                json.loads(raw)
            except (ValueError, UnicodeError):
                findings.append("INVALID_JSON:" + name)
        checked += 1
    actual = {str(p.relative_to(root)) for p in root.rglob("*")
              if (p.is_file() or p.is_symlink()) and p != manifest
              and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    findings.extend("UNLISTED_FILE:" + name for name in sorted(actual - listed))
    findings.extend("REQUIRED_FILE_MISSING:" + name for name in sorted(required - listed))
    return {"passed": not findings, "checked_files": checked, "checked_bytes": total,
            "findings": findings,
            "limits": "Verifies package bytes and required artifacts, not source truth or full campaign completion."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    result = verify(args.root)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
