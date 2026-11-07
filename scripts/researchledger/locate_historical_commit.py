#!/usr/bin/env python3
"""Locate an exact ResearchLedger commit in local Git stores without mutation.

Search directory roots supplied by the operator (desktop/worktree/backups).
Never contacts GitHub, checks out branches, creates refs, or reads secrets.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

TARGET = "8822aa14baef2a964288076645edcc493c338688"
SKIP_DIRS = {"node_modules", "target", ".venv", "venv", "dist", "build",
             ".next", ".cache", "__pycache__", ".cargo-target"}


def repositories(root: Path, max_depth: int = 6, max_candidates: int = 2000):
    if not root.exists() or root.is_symlink() or not root.is_dir():
        return
    found = 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        here = Path(parent)
        depth = len(here.relative_to(root).parts)
        if ".git" in dirs or ".git" in files:
            yield here
            found += 1
            dirs[:] = []
        elif "HEAD" in files and "objects" in dirs:
            yield here
            found += 1
            dirs[:] = []
        elif depth >= max_depth:
            dirs[:] = []
        else:
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS
                       and not (here / d).is_symlink()]
        if found >= max_candidates:
            return


def inspect(path: Path, target: str) -> dict:
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "cat-file", "-t", target],
            capture_output=True, text=True, timeout=8, check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"path": str(path), "state": "INSPECTION_UNAVAILABLE"}
    return {"path": str(path), "state": (
        "EXACT_COMMIT_PRESENT" if proc.returncode == 0 and proc.stdout.strip() == "commit"
        else "GIT_OBJECT_MISSING"
    )}


def locate(roots: list[Path], target: str = TARGET,
           max_depth: int = 6, max_candidates: int = 2000) -> dict:
    if len(target) != 40 or any(x not in "0123456789abcdef" for x in target):
        raise ValueError("INVALID_COMMIT_HASH")
    scanned = []
    seen = set()
    for root in roots:
        for repo in repositories(root, max_depth=max_depth, max_candidates=max_candidates):
            real = repo.resolve()
            if real in seen:
                continue
            seen.add(real)
            scanned.append(inspect(repo, target))
            if len(scanned) >= max_candidates:
                break
        if len(scanned) >= max_candidates:
            break
    matches = [r for r in scanned if r["state"] == "EXACT_COMMIT_PRESENT"]
    return {
        "schema": "researchledger-local-git-recovery-v1",
        "target_commit": target,
        "roots": [str(x) for x in roots],
        "repositories_checked": len(scanned),
        "matches": matches,
        "state": "EXACT_COMMIT_FOUND" if matches else "NOT_FOUND_IN_INSPECTED_ROOTS",
        "exhaustive": False,
        "not_performed": ["network_fetch", "git_checkout", "branch_write", "restoration"],
        "scanned": scanned,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", required=True, type=Path)
    parser.add_argument("--commit", default=TARGET)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--max-candidates", type=int, default=2000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = locate(args.root, args.commit,
                    max_depth=max(0, args.max_depth),
                    max_candidates=max(1, args.max_candidates))
    serialized = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)
    else:
        print(serialized)


if __name__ == "__main__":
    main()
