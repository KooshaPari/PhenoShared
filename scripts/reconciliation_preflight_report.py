"""Report generation and orchestration for repository reconciliation preflight.

This module contains the main preflight orchestration logic that coordinates
individual checks and assembles the final report document.
"""

from __future__ import annotations

import json
import tarfile
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from scripts.reconciliation_preflight_check import (
    CurrentSnapshot,
    PreflightError,
    PreflightInputs,
    _capture_current_state,
    _delta_total,
    _validate_sha,
    _verify_local_graph,
    _verify_packet,
    _verify_remote_snapshot,
)


def run_preflight(
    raw_inputs: PreflightInputs,
    *,
    sleeper: Callable[[float], None] = time.sleep,
    snapshotter: Callable[
        [Path, Mapping[str, tuple[int, str]], set[str], Mapping[str, set[str]]],
        CurrentSnapshot,
    ] = _capture_current_state,
) -> dict[str, Any]:
    from scripts.reconciliation_preflight_check import _base_report

    report = _base_report()
    try:
        if raw_inputs.repo_root.is_symlink():
            raise PreflightError(
                "REPOSITORY_PATH_UNSAFE",
                "local repository path must not be a symbolic link",
            )
        if raw_inputs.packet.is_symlink():
            raise PreflightError(
                "PACKET_PATH_UNSAFE",
                "preservation packet path must not be a symbolic link",
            )
        if raw_inputs.remote_snapshot.is_symlink():
            raise PreflightError(
                "REMOTE_SNAPSHOT_PATH_UNSAFE",
                "remote snapshot path must not be a symbolic link",
            )
        inputs = PreflightInputs(
            repo_root=raw_inputs.repo_root.resolve(strict=True),
            packet=raw_inputs.packet.resolve(strict=True),
            packet_checksum_manifest_sha256=(
                raw_inputs.packet_checksum_manifest_sha256.lower()
            ),
            remote_snapshot=raw_inputs.remote_snapshot.resolve(strict=True),
            remote_snapshot_sha256=raw_inputs.remote_snapshot_sha256.lower(),
            expected_repository=raw_inputs.expected_repository,
            expected_default_branch=raw_inputs.expected_default_branch,
            expected_base_sha=_validate_sha(raw_inputs.expected_base_sha),
            expected_local_sha=_validate_sha(raw_inputs.expected_local_sha),
            expected_live_sha=_validate_sha(raw_inputs.expected_live_sha),
            expected_branches=raw_inputs.expected_branches,
            quiescence_delay_ms=raw_inputs.quiescence_delay_ms,
        )
        if not inputs.repo_root.is_dir() or not (inputs.repo_root / ".git").is_dir():
            raise PreflightError("REPOSITORY_INVALID", "local repository is invalid")
        if not 0 <= inputs.quiescence_delay_ms <= 10_000:
            raise PreflightError(
                "QUIESCENCE_DELAY_INVALID", "quiescence delay is outside the safe bound"
            )
        report["checks"]["remote_snapshot"] = _verify_remote_snapshot(inputs)
        packet_report, captured, exclusions, captured_categories = _verify_packet(
            inputs
        )
        report["checks"]["packet"] = packet_report
        report["checks"]["local_graph"] = _verify_local_graph(inputs)
        first = snapshotter(inputs.repo_root, captured, exclusions, captured_categories)
        sleeper(inputs.quiescence_delay_ms / 1000)
        second = snapshotter(
            inputs.repo_root, captured, exclusions, captured_categories
        )
        quiescent = (
            first.fingerprint == second.fingerprint
            and first.race_count == 0
            and second.race_count == 0
        )
        report["checks"]["quiescence"] = {
            "samples": 2,
            "stable": quiescent,
            "first_fingerprint": first.fingerprint,
            "second_fingerprint": second.fingerprint,
            "raced_files": first.race_count + second.race_count,
        }
        report["checks"]["current_delta"] = {
            "categories": second.categories,
            "captured_payload": second.captured_payload,
            "git_controls": second.git_controls,
            "git_objects": second.git_objects,
            "changed_or_new_total": _delta_total(second),
        }
        if second.local_head != inputs.expected_local_sha:
            raise PreflightError(
                "LOCAL_HEAD_MOVED", "local HEAD moved during preflight"
            )
        if not quiescent:
            report["decision"] = "NOT_QUIESCENT"
        elif _delta_total(second) > 0:
            report["decision"] = "NEEDS_FRESH_DELTA_CAPTURE"
        else:
            report["decision"] = "READY_FOR_DISPOSABLE_CLONE_REVIEW"
            report["ok"] = True
    except PreflightError as exc:
        report["errors"].append({"code": exc.code, "message": exc.safe_message})
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, tarfile.TarError):
        report["errors"].append(
            {
                "code": "INTERNAL_CHECK_FAILED",
                "message": "a bounded preflight check failed",
            }
        )
    return report
