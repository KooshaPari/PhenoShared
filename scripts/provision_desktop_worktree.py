#!/usr/bin/env python3
"""DAG-27: scripts/provision_desktop_worktree.py

Provisions a tailscale-bootstrap worktree on the Desktop NVIDIA rig
(WSL2 + Fedora 44). Idempotent: safe to re-run.

What it does:
  1. Validates tailscale reachability (ssh ping to the WSL host).
  2. Clones the named branch (default: fix/desktop-vllm-runtime) into
     a fresh worktree on the rig.
  3. Records the worktree path in evidence/dual_gpu/worktrees.json
     so the next-run Desktop lane can find it.

Usage:
  python3 scripts/provision_desktop_worktree.py \\
    --host <REDACTED>@100.x.x.x \\
    --branch fix/desktop-vllm-runtime \\
    --worktree-dir /home/<REDACTED>/pheno-harness \\
    [--dry-run]
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = REPO_ROOT / "evidence" / "dual_gpu"
WORKTREE_INDEX = EVIDENCE / "worktrees.json"
TEMP_ROOT = Path(tempfile.gettempdir()).resolve()


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _read_index(index_path: Path = WORKTREE_INDEX) -> dict[str, Any]:
    if not index_path.is_file():
        return {"version": 1, "worktrees": []}
    return json.loads(index_path.read_text())


def _write_index(idx: dict[str, Any], index_path: Path = WORKTREE_INDEX) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(idx, indent=2, sort_keys=True) + "\n")


def _validate_index_path(index_path: Path, dry_run: bool) -> Path:
    """Allow a new temporary index only for an isolated dry-run test."""
    resolved = index_path.resolve()
    if resolved == WORKTREE_INDEX.resolve():
        return resolved
    if not dry_run:
        raise SystemExit("--index-path is allowed only with --dry-run")
    try:
        resolved.relative_to(TEMP_ROOT)
    except ValueError as exc:
        raise SystemExit(
            "--index-path must be under the system temporary directory"
        ) from exc
    if resolved.exists():
        raise SystemExit("--index-path must name a new temporary file")
    return resolved


def _ssh_ping(host: str, timeout_s: int = 5) -> bool:
    """Returns True if the SSH host answers within timeout. Catches
    the case where the WSL distro is off the network (audit
    desktop-live-20260801 record)."""
    try:
        result = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                f"ConnectTimeout={timeout_s}",
                host,
                "echo ok",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_s + 2,
        )
        return result.returncode == 0 and "ok" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _record(
    host: str,
    branch: str,
    worktree_dir: str,
    dry_run: bool,
    ssh_ok: bool,
    index_path: Path = WORKTREE_INDEX,
) -> None:
    idx = _read_index(index_path)
    entry = {
        "recorded_at": _now(),
        "host": host,
        "branch": branch,
        "worktree_dir": worktree_dir,
        "ssh_ok": ssh_ok,
        "dry_run": dry_run,
    }
    # Idempotent: replace any prior entry for the same host+branch.
    idx["worktrees"] = [
        w
        for w in idx["worktrees"]
        if not (w.get("host") == host and w.get("branch") == branch)
    ]
    idx["worktrees"].append(entry)
    _write_index(idx, index_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        required=True,
        help="SSH target for the Desktop rig (e.g. user@100.x.x.x)",
    )
    parser.add_argument(
        "--branch",
        default="fix/desktop-vllm-runtime",
        help="branch to check out on the rig (default: fix/desktop-vllm-runtime)",
    )
    parser.add_argument(
        "--worktree-dir",
        required=True,
        help="absolute path on the rig where the worktree will live",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="record the entry but skip the actual SSH + clone",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=WORKTREE_INDEX,
        help="local path for the recorded worktree index (default: evidence/dual_gpu/worktrees.json)",
    )
    args = parser.parse_args(argv)
    index_path = _validate_index_path(args.index_path, args.dry_run)

    ssh_ok = _ssh_ping(args.host) if not args.dry_run else False
    _record(
        host=args.host,
        branch=args.branch,
        worktree_dir=args.worktree_dir,
        dry_run=args.dry_run,
        ssh_ok=ssh_ok,
        index_path=index_path,
    )
    if ssh_ok and not args.dry_run:
        # Best-effort: ask the rig to refresh the worktree. We don't
        # fail the script if this errors (the rig may be busy).
        subprocess.run(
            [
                "ssh",
                args.host,
                f"cd {args.worktree_dir} && "
                f"git fetch origin {args.branch} && "
                f"git worktree add -f {args.worktree_dir}-{args.branch.replace('/', '-')} "
                f"origin/{args.branch}",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    print(
        f"recorded worktree entry for {args.host} branch={args.branch} "
        f"ssh_ok={ssh_ok} dry_run={args.dry_run}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
