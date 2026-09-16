#!/usr/bin/env python3
"""Read-only, fail-closed preflight for repository reconciliation.

The command consumes an operator-pinned remote snapshot. It never contacts a
remote and never invokes a mutating Git command. Its only output is one
canonical JSON document on stdout.
"""

from __future__ import annotations

import argparse
import subprocess  # noqa: F401 - re-exported for monkey-patching tests
import sys
from collections.abc import Sequence
from pathlib import Path

from scripts.reconciliation_preflight_check import (  # noqa: F401
    _BUNDLE_HEADER_MAX_BYTES,
    _CAPTURE_FILE_MAX_BYTES,
    _CAPTURE_TOTAL_MAX_BYTES,
    _CHECKSUM_MANIFEST_MAX_BYTES,
    _CHECKSUM_RE,
    _PACKET_FILE_MAX_BYTES,
    _PACKET_TOTAL_MAX_BYTES,
    _REMOTE_SNAPSHOT_MAX_BYTES,
    _REQUIRED_PACKET_FILES,
    _SHA256_RE,
    _SHA_RE,
    _STATIC_GIT_CONTROL_PATHS,
    REMOTE_SCHEMA_VERSION,
    SCHEMA_VERSION,
    CurrentSnapshot,
    FileState,
    PreflightError,
    PreflightInputs,
    _base_report,
    _bundle_header,
    _canonical_bytes,
    _capture_current_state,
    _captured_payload_report,
    _category_report,
    _current_git_control_paths,
    _current_git_object_paths,
    _decode_nul_paths,
    _decode_unmerged_paths,
    _delta_total,
    _expected_branch_map,
    _file_state,
    _git_control_report,
    _git_object_report,
    _hash_file,
    _load_capture_manifest,
    _load_path_inventory,
    _load_recorded_exclusions,
    _normalize_tar_path,
    _packet_path,
    _read_packet_file,
    _read_regular_file_once,
    _remote_object,
    _require_exact_keys,
    _run_git,
    _safe_relative_path,
    _sha256_bytes,
    _valid_branch_name,
    _validate_sha,
    _verify_bundle,
    _verify_checksums,
    _verify_local_graph,
    _verify_packet,
    _verify_remote_snapshot,
    _verify_tar,
)
from scripts.reconciliation_preflight_report import run_preflight  # noqa: F401


def _parse_expected_branch(value: str) -> tuple[str, str]:
    name, separator, sha = value.rpartition("=")
    if not separator:
        raise argparse.ArgumentTypeError("expected NAME=SHA")
    return name, sha.lower()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--packet-checksum-manifest-sha256", required=True)
    parser.add_argument("--remote-snapshot", type=Path, required=True)
    parser.add_argument("--remote-snapshot-sha256", required=True)
    parser.add_argument("--expected-repository", required=True)
    parser.add_argument("--expected-default-branch", default="main")
    parser.add_argument("--expected-base-sha", required=True)
    parser.add_argument("--expected-local-sha", required=True)
    parser.add_argument("--expected-live-sha", required=True)
    parser.add_argument(
        "--expected-branch",
        type=_parse_expected_branch,
        action="append",
        required=True,
        dest="expected_branches",
        metavar="NAME=SHA",
    )
    parser.add_argument("--quiescence-delay-ms", type=int, default=250)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    namespace = _parser().parse_args(argv)
    inputs = PreflightInputs(
        repo_root=namespace.repo_root,
        packet=namespace.packet,
        packet_checksum_manifest_sha256=namespace.packet_checksum_manifest_sha256,
        remote_snapshot=namespace.remote_snapshot,
        remote_snapshot_sha256=namespace.remote_snapshot_sha256,
        expected_repository=namespace.expected_repository,
        expected_default_branch=namespace.expected_default_branch,
        expected_base_sha=namespace.expected_base_sha,
        expected_local_sha=namespace.expected_local_sha,
        expected_live_sha=namespace.expected_live_sha,
        expected_branches=tuple(namespace.expected_branches),
        quiescence_delay_ms=namespace.quiescence_delay_ms,
    )
    result = run_preflight(inputs)
    sys.stdout.buffer.write(_canonical_bytes(result) + b"\n")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
