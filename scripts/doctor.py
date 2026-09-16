#!/usr/bin/env python3
"""Emit a deterministic, read-only local environment report.

The doctor is an observation command, not an execution preflight.  It reads
repository metadata, checks local Python/package/config availability, and
never launches a model, contacts a service, invokes a GPU tool, or writes a
file.  A non-zero exit code means a required local prerequisite is missing.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "pheno-harness-doctor-v1"
REQUIRED_CONFIGS = (
    "config/eval_pillars.yaml",
    "config/fleet_readiness.yaml",
    "config/evidence_registry.yaml",
)


def _git(*args: str) -> str | None:
    """Read one git value without mutating the repository."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    return result.stdout.strip()


def _package_status(name: str) -> dict[str, Any]:
    """Report importability only; do not import or initialize packages."""
    return {
        "importable": importlib.util.find_spec(name) is not None,
    }


def build_report() -> dict[str, Any]:
    """Build a JSON-safe report from local, read-only observations."""
    config_report = {path: (ROOT / path).is_file() for path in REQUIRED_CONFIGS}
    required_ok = all(config_report.values())
    git_sha = _git("rev-parse", "HEAD")
    branch = _git("branch", "--show-current")
    porcelain = _git("status", "--porcelain")
    git_available = git_sha is not None and branch is not None and porcelain is not None
    dirty_entries = len(porcelain.splitlines()) if porcelain else 0
    checks = {
        "git_metadata": git_available,
        "required_configs": required_ok,
        "python": sys.version_info >= (3, 12),
        "pytest": _package_status("pytest")["importable"],
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "repo": "pheno-harness",
        "root": str(ROOT),
        "state": "ready" if all(checks.values()) else "blocked",
        "checks": checks,
        "git": {
            "sha": git_sha,
            "branch": branch,
            "dirty_entries": dirty_entries,
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "packages": {
            "yaml": _package_status("yaml"),
            "pytest": _package_status("pytest"),
            "harbor": _package_status("harbor"),
        },
        "required_configs": config_report,
        "execution": {
            "model_launched": False,
            "gpu_probed": False,
            "network_contacted": False,
            "files_written": False,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only local pheno-harness environment report"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero when any required local check is blocked",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report()
    print(json.dumps(report, sort_keys=True, indent=2))
    return 1 if args.strict and report["state"] != "ready" else 0


if __name__ == "__main__":
    raise SystemExit(main())
