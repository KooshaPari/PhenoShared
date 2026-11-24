"""Direct unit tests for scripts.reconciliation_preflight_checks_security_remote.

Verifies the operator-pinned remote snapshot integrity boundary:

* snapshot size is bounded;
* snapshot body parses as canonical JSON with no duplicate keys;
* schema version and required field set match exactly;
* branch graph and default-ref point to operator-expected SHAs.

The orchestrator covers happy-path scenarios; these tests are
defense-in-depth for the negative paths so the trust anchor on the
remote snapshot cannot silently regress.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

import scripts.reconciliation_preflight as preflight

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


BASE_SHA = "1" * 40
LOCAL_SHA = "2" * 40
LIVE_SHA = "3" * 40
FEATURE_SHA = "4" * 40
REPOSITORY = "example/pheno"


def _build_inputs(remote_path: Path, tmp_path: Path) -> preflight.PreflightInputs:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(exist_ok=True)
    packet = tmp_path / "packet"
    packet.mkdir(exist_ok=True)
    return preflight.PreflightInputs(
        repo_root=repo_root,
        packet=packet,
        packet_checksum_manifest_sha256="a" * 64,
        remote_snapshot=remote_path,
        remote_snapshot_sha256=hashlib.sha256(remote_path.read_bytes()).hexdigest(),
        expected_repository=REPOSITORY,
        expected_default_branch="main",
        expected_base_sha=BASE_SHA,
        expected_local_sha=LOCAL_SHA,
        expected_live_sha=LIVE_SHA,
        expected_branches=(("main", LIVE_SHA), ("feat/kernel", FEATURE_SHA)),
    )


def _write_snapshot(
    snapshot_path: Path,
    payload: dict[str, object],
    *,
    add_newline: bool = True,
) -> None:
    raw = preflight._canonical_bytes(payload)
    if add_newline:
        raw += b"\n"
    snapshot_path.write_bytes(raw)


def _valid_snapshot() -> dict[str, object]:
    return {
        "schema_version": preflight.REMOTE_SCHEMA_VERSION,
        "captured_at_utc": "2026-07-15T03:41:35Z",
        "repository": {
            "full_name": REPOSITORY,
            "private": True,
            "archived": False,
            "default_branch": "main",
        },
        "base_sha": BASE_SHA,
        "local_sha": LOCAL_SHA,
        "live_sha": LIVE_SHA,
        "branches": [
            {"name": "feat/kernel", "sha": FEATURE_SHA},
            {"name": "main", "sha": LIVE_SHA},
        ],
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_verify_remote_snapshot_accepts_valid_payload(tmp_path: Path) -> None:
    snapshot = tmp_path / "remote.json"
    _write_snapshot(snapshot, _valid_snapshot())
    inputs = _build_inputs(snapshot, tmp_path)
    report = preflight._verify_remote_snapshot(inputs)
    assert report["verified"] is True
    assert report["branch_count"] == 2
    assert report["live_sha"] == LIVE_SHA
    assert report["network_used"] is False


# ---------------------------------------------------------------------------
# Size bound
# ---------------------------------------------------------------------------


def test_verify_remote_snapshot_rejects_oversized(tmp_path: Path) -> None:
    snapshot = tmp_path / "remote.json"
    _write_snapshot(snapshot, _valid_snapshot())
    inputs = _build_inputs(snapshot, tmp_path)
    # Force the cap below the actual file size to trip the bound.
    with patch.object(preflight, "_REMOTE_SNAPSHOT_MAX_BYTES", 16):
        with pytest.raises(preflight.PreflightError) as excinfo:
            preflight._verify_remote_snapshot(inputs)
    assert excinfo.value.code == "REMOTE_SNAPSHOT_TOO_LARGE"


# ---------------------------------------------------------------------------
# JSON / structural integrity
# ---------------------------------------------------------------------------


def test_verify_remote_snapshot_rejects_malformed_json(tmp_path: Path) -> None:
    snapshot = tmp_path / "remote.json"
    snapshot.write_bytes(b"{not really json,,,}")
    inputs = _build_inputs(snapshot, tmp_path)
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_remote_snapshot(inputs)
    assert excinfo.value.code in {"REMOTE_SNAPSHOT_INVALID", "REMOTE_SNAPSHOT_DIGEST_MISMATCH"}


def test_verify_remote_snapshot_rejects_non_object_top_level(tmp_path: Path) -> None:
    snapshot = tmp_path / "remote.json"
    snapshot.write_bytes(b'[1, 2, 3]\n')
    # Re-stamp the inputs because we wrote the file directly.
    raw = snapshot.read_bytes()
    inputs = preflight.PreflightInputs(
        repo_root=tmp_path / "repo",
        packet=tmp_path / "packet",
        packet_checksum_manifest_sha256="a" * 64,
        remote_snapshot=snapshot,
        remote_snapshot_sha256=hashlib.sha256(raw).hexdigest(),
        expected_repository=REPOSITORY,
        expected_default_branch="main",
        expected_base_sha=BASE_SHA,
        expected_local_sha=LOCAL_SHA,
        expected_live_sha=LIVE_SHA,
        expected_branches=(("main", LIVE_SHA),),
    )
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_remote_snapshot(inputs)
    assert excinfo.value.code == "REMOTE_SNAPSHOT_INVALID"


def test_verify_remote_snapshot_rejects_duplicate_top_level_key(tmp_path: Path) -> None:
    snapshot = tmp_path / "remote.json"
    # Build the duplicate by repeating a top-level field.
    valid = _valid_snapshot()
    raw = preflight._canonical_bytes(valid) + b"\n"
    needle = f'"live_sha":"{LIVE_SHA}"'
    assert needle.encode() in raw
    tampered = raw.replace(
        needle.encode(), needle.encode() + b"," + needle.encode(), 1
    )
    snapshot.write_bytes(tampered)
    inputs = _build_inputs(snapshot, tmp_path)
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_remote_snapshot(inputs)
    assert excinfo.value.code == "REMOTE_SNAPSHOT_DUPLICATE_KEY"


# ---------------------------------------------------------------------------
# Schema drift
# ---------------------------------------------------------------------------


def test_verify_remote_snapshot_rejects_unknown_top_level_field(tmp_path: Path) -> None:
    snapshot = tmp_path / "remote.json"
    payload = _valid_snapshot()
    payload["unexpected_field"] = "nope"  # type: ignore[assignment]
    _write_snapshot(snapshot, payload)
    inputs = _build_inputs(snapshot, tmp_path)
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_remote_snapshot(inputs)
    assert excinfo.value.code == "REMOTE_SNAPSHOT_FIELDS_INVALID"


def test_verify_remote_snapshot_rejects_missing_repository_field(tmp_path: Path) -> None:
    snapshot = tmp_path / "remote.json"
    payload = _valid_snapshot()
    repository = payload["repository"]
    assert isinstance(repository, dict)
    del repository["default_branch"]
    _write_snapshot(snapshot, payload)
    inputs = _build_inputs(snapshot, tmp_path)
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_remote_snapshot(inputs)
    assert excinfo.value.code == "REMOTE_REPOSITORY_FIELDS_INVALID"


def test_verify_remote_snapshot_rejects_wrong_schema_version(tmp_path: Path) -> None:
    snapshot = tmp_path / "remote.json"
    payload = _valid_snapshot()
    payload["schema_version"] = "wrong.schema"
    _write_snapshot(snapshot, payload)
    inputs = _build_inputs(snapshot, tmp_path)
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_remote_snapshot(inputs)
    assert excinfo.value.code == "REMOTE_SNAPSHOT_INVALID"


def test_verify_remote_snapshot_rejects_missing_required_sha(tmp_path: Path) -> None:
    snapshot = tmp_path / "remote.json"
    payload = _valid_snapshot()
    # Drop a SHA entirely (still produces canonical JSON, still under
    # the byte budget, but the field set will not match the contract).
    payload["local_sha"] = None
    _write_snapshot(snapshot, payload)
    inputs = _build_inputs(snapshot, tmp_path)
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_remote_snapshot(inputs)
    assert excinfo.value.code in {
        "REMOTE_SNAPSHOT_INVALID",
        "REMOTE_GRAPH_MISMATCH",
    }


def test_verify_remote_snapshot_rejects_branch_set_mismatch(tmp_path: Path) -> None:
    snapshot = tmp_path / "remote.json"
    payload = _valid_snapshot()
    payload["branches"] = [{"name": "main", "sha": LIVE_SHA}]
    _write_snapshot(snapshot, payload)
    inputs = _build_inputs(snapshot, tmp_path)
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_remote_snapshot(inputs)
    assert excinfo.value.code == "REMOTE_BRANCH_SET_MISMATCH"


def test_verify_remote_snapshot_rejects_invalid_default_ref(tmp_path: Path) -> None:
    snapshot = tmp_path / "remote.json"
    payload = _valid_snapshot()
    # main's SHA does not match the expected live_sha.
    for entry in payload["branches"]:
        assert isinstance(entry, dict)
        if entry.get("name") == "main":
            entry["sha"] = "9" * 40
    _write_snapshot(snapshot, payload)
    inputs = _build_inputs(snapshot, tmp_path)
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_remote_snapshot(inputs)
    assert excinfo.value.code in {
        "REMOTE_DEFAULT_REF_MISMATCH",
        "REMOTE_BRANCH_SET_MISMATCH",
    }
