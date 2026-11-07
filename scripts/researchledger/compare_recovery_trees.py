#!/usr/bin/env python3
"""Compare recovered newer ResearchLedger files with a checksummed historical fallback.

This tool never writes into either source tree. A missing newer checkout is an
explicit unresolved blocker, not permission to promote an older corpus.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def inspect_relative(root: Path) -> dict[str, dict]:
    if not root.is_dir():
        raise FileNotFoundError("SOURCE_TREE_UNAVAILABLE")
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("SYMLINK_IN_SOURCE_TREE")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in ("PRESERVATION-MANIFEST.json", "RECOVERY-RECEIPT.json"):
            continue
        data = path.read_bytes()
        result[relative] = {"sha256": sha(data), "bytes": len(data)}
    return result

def compare(historical: Path, newer: Path) -> dict:
    old = inspect_relative(historical)
    recent = inspect_relative(newer)
    rows = []
    for path in sorted(set(old) | set(recent)):
        if path not in old:
            state = "NEWER_ONLY"
        elif path not in recent:
            state = "HISTORICAL_ONLY_UNRESOLVED"
        elif old[path]["sha256"] == recent[path]["sha256"]:
            state = "BYTE_IDENTICAL"
        else:
            state = "CONFLICT_NEEDS_THREE_WAY_REVIEW"
        rows.append({"path": path, "state": state,
                     "historical": old.get(path), "newer": recent.get(path)})
    counts = {s: sum(r["state"] == s for r in rows) for s in
              ("BYTE_IDENTICAL", "NEWER_ONLY", "HISTORICAL_ONLY_UNRESOLVED",
               "CONFLICT_NEEDS_THREE_WAY_REVIEW")}
    return {
        "schema": "researchledger-source-reconciliation-v1",
        "source_a": "verified_Wave_5_historical",
        "source_b": "operator_supplied_newer_source",
        "counts": counts,
        "review_required": counts["HISTORICAL_ONLY_UNRESOLVED"] + counts["CONFLICT_NEEDS_THREE_WAY_REVIEW"] > 0,
        "safe_to_auto_merge": False,
        "meaning": "Byte comparison; not a release, source validity, or provenance verification",
        "files": rows,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-root", required=True, type=Path)
    parser.add_argument("--newer-root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.historical_root, args.newer_root)
    except (FileNotFoundError, ValueError) as error:
        print(json.dumps({"state": "BLOCKED", "reason": str(error)}))
        return 2
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
