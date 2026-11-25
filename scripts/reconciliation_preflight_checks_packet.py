"""Packet and bundle verification for repository reconciliation preflight."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from scripts.reconciliation_preflight_check import (
    PreflightError,
    PreflightInputs,
    _validate_sha,
)
from scripts.reconciliation_preflight_checks_security import (
    _BUNDLE_HEADER_MAX_BYTES,
    _load_capture_manifest,
    _load_path_inventory,
    _load_recorded_exclusions,
    _verify_checksums,
    _verify_tar,
)


def _bundle_header(payload: bytes) -> tuple[set[str], dict[str, str]]:
    handle = io.BytesIO(payload)
    header = bytearray()
    while len(header) <= _BUNDLE_HEADER_MAX_BYTES:
        line = handle.readline(_BUNDLE_HEADER_MAX_BYTES - len(header) + 1)
        if not line:
            break
        if line in {b"\n", b"\r\n"}:
            break
        header.extend(line)
    if len(header) > _BUNDLE_HEADER_MAX_BYTES:
        raise PreflightError("BUNDLE_INVALID", "local preservation bundle is invalid")
    try:
        lines = bytes(header).decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise PreflightError(
            "BUNDLE_INVALID", "local preservation bundle is invalid"
        ) from exc
    if not lines or not lines[0].startswith("# v"):
        raise PreflightError("BUNDLE_INVALID", "local preservation bundle is invalid")
    prerequisites: set[str] = set()
    heads: dict[str, str] = {}
    for line in lines[1:]:
        if line.startswith("-"):
            token = line[1:].split(" ", 1)[0].lower()
            prerequisites.add(_validate_sha(token, code="BUNDLE_INVALID"))
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2:
            raise PreflightError(
                "BUNDLE_INVALID", "local preservation bundle is invalid"
            )
        sha, ref = parts
        if ref in heads:
            raise PreflightError(
                "BUNDLE_INVALID", "local preservation bundle is invalid"
            )
        heads[ref] = _validate_sha(sha, code="BUNDLE_INVALID")
    return prerequisites, heads


def _verify_bundle(
    repo_root: Path,
    bundle: bytes,
    expected_base_sha: str,
    expected_local_sha: str,
) -> dict[str, Any]:
    # Import from the public re-export module so monkey-patching tests
    # that target ``scripts.reconciliation_preflight._run_git`` apply.
    # Note: we verify the bundle via a tempfile rather than stdin (`-`).
    # Git's `bundle verify -` uses rev-list internally and can fail with
    # "some prerequisite commits exist in the object store, but are not
    # connected to the repository's history" when the repo has any
    # unreachable objects — even though those objects aren't required by
    # the bundle. Writing to a tempfile avoids the spurious failure.
    import tempfile

    from scripts.reconciliation_preflight import _run_git

    with tempfile.NamedTemporaryFile(suffix=".bundle", delete=False) as tmp:
        tmp.write(bundle)
        tmp_path = Path(tmp.name)
    try:
        _run_git(repo_root, ["bundle", "verify", str(tmp_path)])
    finally:
        tmp_path.unlink(missing_ok=True)
    prerequisites, listed = _bundle_header(bundle)
    if expected_local_sha not in listed.values():
        raise PreflightError(
            "BUNDLE_LOCAL_SHA_MISMATCH",
            "local bundle does not preserve the expected local tip",
        )
    if expected_base_sha not in prerequisites:
        raise PreflightError(
            "BUNDLE_BASE_SHA_MISMATCH",
            "local bundle does not require the expected base",
        )
    return {
        "verified": True,
        "heads": len(listed),
        "prerequisites": len(prerequisites),
        "preserves_expected_local": True,
        "requires_expected_base": True,
    }


def _verify_packet(
    inputs: PreflightInputs,
) -> tuple[
    dict[str, Any],
    dict[str, tuple[int, str]],
    set[str],
    dict[str, set[str]],
]:

    packet = inputs.packet.resolve(strict=True)
    checksums, packet_files, checksum_report = _verify_checksums(
        packet, inputs.packet_checksum_manifest_sha256
    )
    before = _load_capture_manifest(packet_files["source-files.before.cjson"])
    after = _load_capture_manifest(packet_files["source-files.after.cjson"])
    if before != after:
        raise PreflightError(
            "CAPTURE_NOT_STABLE",
            "capture manifests disagree before and after preservation",
        )
    exclusions = _load_recorded_exclusions(packet_files, checksums)
    captured_categories = {
        "untracked": _load_path_inventory(packet_files["untracked.txt"]),
        "ignored": _load_path_inventory(packet_files["ignored.txt"]),
    }
    if captured_categories["untracked"] & captured_categories["ignored"]:
        raise PreflightError(
            "CAPTURE_PATH_INVENTORY_INVALID", "capture path inventory is invalid"
        )
    covered_paths = before.keys() | exclusions
    if any(not paths <= covered_paths for paths in captured_categories.values()):
        raise PreflightError(
            "CAPTURE_PATH_INVENTORY_UNCOVERED",
            "capture path inventory is not covered by preservation",
        )
    tar_report = _verify_tar(
        packet_files["pheno-harness-full.tar.gz"], inputs.repo_root.name, before
    )
    bundle_report = _verify_bundle(
        inputs.repo_root,
        packet_files["local-only.bundle"],
        inputs.expected_base_sha,
        inputs.expected_local_sha,
    )
    try:
        head_text = packet_files["HEAD.txt"].decode("utf-8").strip().lower()
    except UnicodeError as exc:
        raise PreflightError(
            "CAPTURE_HEAD_INVALID", "captured HEAD is invalid"
        ) from exc
    if head_text != inputs.expected_local_sha:
        raise PreflightError(
            "CAPTURE_HEAD_MISMATCH",
            "captured HEAD does not match the expected local tip",
        )
    return (
        {
            "verified": True,
            "checksums": checksum_report,
            "capture_manifest_files": len(before),
            "capture_manifests_identical": True,
            "captured_ignored_paths": len(captured_categories["ignored"]),
            "captured_untracked_paths": len(captured_categories["untracked"]),
            "recorded_exclusions": len(exclusions),
            "tar": tar_report,
            "bundle": bundle_report,
        },
        before,
        exclusions,
        captured_categories,
    )
