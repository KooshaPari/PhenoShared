"""Direct unit tests for scripts.reconciliation_preflight_checks_packet.

Verifies the preservation packet boundary:

* required packet files are all present and SHA-256 verified;
* capture manifest files are byte-equal before and after capture;
* the tar archive matches the manifest content;
* the local-only bundle includes the expected local tip and requires
  the expected base;
* HEAD.txt matches the expected local SHA.

The orchestrator covers happy-path scenarios; these tests are
defense-in-depth for the negative paths and the corner cases that the
end-to-end fixture doesn't exercise (byte budget overflow, capture
manifest disagreement, HEAD.txt mismatch).
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest

import scripts.reconciliation_preflight as preflight

# ---------------------------------------------------------------------------
# Git / fixture helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *arguments: str, input: bytes | None = None) -> bytes:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        input=input,
    )
    return completed.stdout


def _git_text(repo: Path, *arguments: str) -> str:
    return _git(repo, *arguments).decode().strip()


def _write_capture_record(path: Path, payload: bytes) -> dict[str, object]:
    return {
        "path": path.relative_to(path.parents[1]).as_posix(),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _build_inputs(
    repo_root: Path,
    packet: Path,
    *,
    base_sha: str,
    local_sha: str,
    live_sha: str = "f" * 40,
    feature_sha: str = "e" * 40,
) -> preflight.PreflightInputs:
    return preflight.PreflightInputs(
        repo_root=repo_root,
        packet=packet,
        packet_checksum_manifest_sha256="0" * 64,  # overwritten by caller
        remote_snapshot=repo_root / "remote.json",
        remote_snapshot_sha256="0" * 64,
        expected_repository="example/pheno",
        expected_default_branch="main",
        expected_base_sha=base_sha,
        expected_local_sha=local_sha,
        expected_live_sha=live_sha,
        expected_branches=(("feature/kernel", feature_sha), ("main", live_sha)),
        quiescence_delay_ms=0,
    )


def _create_minimal_packet(
    repo_root: Path,
    packet: Path,
) -> tuple[str, str, list[dict[str, object]]]:
    """Create a real Git repo + a matching preservation packet.

    Returns ``(base_sha, local_sha, records)`` where ``records`` is the
    capture manifest used to write both before/after .cjson files and
    the tar archive.
    """
    repo_root.mkdir()
    packet.mkdir()
    _git(repo_root, "init", "-q", "-b", "main")
    _git(repo_root, "config", "user.name", "Packet Test")
    _git(repo_root, "config", "user.email", "packet@example.invalid")
    (repo_root / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo_root, "add", "README.md")
    _git(repo_root, "commit", "-q", "-m", "base")
    base_sha = _git_text(repo_root, "rev-parse", "HEAD")

    (repo_root / "local.txt").write_text("local\n", encoding="utf-8")
    _git(repo_root, "add", "local.txt")
    _git(repo_root, "commit", "-q", "-m", "local")
    local_sha = _git_text(repo_root, "rev-parse", "HEAD")

    records: list[dict[str, object]] = []
    for relative in ("README.md", "local.txt"):
        full = repo_root / relative
        records.append(
            {
                "path": relative,
                "bytes": full.stat().st_size,
                "sha256": hashlib.sha256(full.read_bytes()).hexdigest(),
            }
        )

    (packet / "HEAD.txt").write_bytes(local_sha.encode() + b"\n")
    (packet / "untracked.txt").write_bytes(b"")
    (packet / "ignored.txt").write_bytes(b"")
    (packet / "source-files.before.cjson").write_bytes(
        preflight._canonical_bytes(records)
    )
    (packet / "source-files.after.cjson").write_bytes(
        preflight._canonical_bytes(records)
    )

    with tarfile.open(packet / "pheno-harness-full.tar.gz", "w:gz") as archive:
        for record in records:
            relative = str(record["path"])
            archive.add(
                repo_root / relative,
                arcname=f"{repo_root.name}/{relative}",
                recursive=False,
            )
    _git(
        repo_root,
        "bundle",
        "create",
        str(packet / "local-only.bundle"),
        "main",
        f"^{base_sha}",
    )

    manifest_lines: list[str] = []
    for relative in (
        "HEAD.txt",
        "ignored.txt",
        "local-only.bundle",
        "pheno-harness-full.tar.gz",
        "source-files.after.cjson",
        "source-files.before.cjson",
        "untracked.txt",
    ):
        full = packet / relative
        manifest_lines.append(
            f"{hashlib.sha256(full.read_bytes()).hexdigest()} *{relative}"
        )
    (packet / "SHA256SUMS.txt").write_text(
        "\n".join(manifest_lines) + "\n", encoding="utf-8"
    )
    return base_sha, local_sha, records


# ---------------------------------------------------------------------------
# Missing required files
# ---------------------------------------------------------------------------


def test_verify_packet_rejects_missing_required_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    packet = tmp_path / "packet"
    base_sha, local_sha, _records = _create_minimal_packet(repo_root, packet)
    inputs = _build_inputs(repo_root, packet, base_sha=base_sha, local_sha=local_sha)

    # Delete HEAD.txt (a required file) and re-stamp the manifest so the
    # SHA on the trust anchor matches the (still-present) SHA256SUMS.txt.
    (packet / "HEAD.txt").unlink()
    manifest_lines = [
        f"{hashlib.sha256((packet / name).read_bytes()).hexdigest()} *{name}"
        for name in (
            "ignored.txt",
            "local-only.bundle",
            "pheno-harness-full.tar.gz",
            "source-files.after.cjson",
            "source-files.before.cjson",
            "untracked.txt",
        )
    ]
    (packet / "SHA256SUMS.txt").write_text(
        "\n".join(manifest_lines) + "\n", encoding="utf-8"
    )
    manifest_sha = hashlib.sha256(
        (packet / "SHA256SUMS.txt").read_bytes()
    ).hexdigest()
    inputs = preflight.PreflightInputs(
        **{**inputs.__dict__, "packet_checksum_manifest_sha256": manifest_sha}
    )

    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_packet(inputs)
    # The orchestrator's first failure is the manifest coverage check:
    # the missing file isn't listed in the checksum manifest.
    assert excinfo.value.code in {
        "CHECKSUM_COVERAGE_INCOMPLETE",
        "PACKET_FILE_MISSING",
    }


# ---------------------------------------------------------------------------
# Byte budget exceeded
# ---------------------------------------------------------------------------


def test_verify_packet_rejects_total_byte_budget_exceeded(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    packet = tmp_path / "packet"
    base_sha, local_sha, _records = _create_minimal_packet(repo_root, packet)
    inputs = _build_inputs(repo_root, packet, base_sha=base_sha, local_sha=local_sha)
    manifest_sha = hashlib.sha256(
        (packet / "SHA256SUMS.txt").read_bytes()
    ).hexdigest()
    inputs = preflight.PreflightInputs(
        **{**inputs.__dict__, "packet_checksum_manifest_sha256": manifest_sha}
    )

    manifest_size = (packet / "SHA256SUMS.txt").stat().st_size
    with patch.object(preflight, "_PACKET_TOTAL_MAX_BYTES", manifest_size + 1):
        with pytest.raises(preflight.PreflightError) as excinfo:
            preflight._verify_packet(inputs)
    assert excinfo.value.code == "PACKET_TOTAL_TOO_LARGE"


# ---------------------------------------------------------------------------
# Capture file integrity (sha256 matches)
# ---------------------------------------------------------------------------


def test_verify_packet_rejects_tampered_capture_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    packet = tmp_path / "packet"
    base_sha, local_sha, _records = _create_minimal_packet(repo_root, packet)
    inputs = _build_inputs(repo_root, packet, base_sha=base_sha, local_sha=local_sha)

    # Tamper with HEAD.txt — checksum is now wrong but trust anchor still
    # matches the (unchanged) manifest file.
    (packet / "HEAD.txt").write_bytes(b"0" * 40 + b"\n")
    manifest_sha = hashlib.sha256(
        (packet / "SHA256SUMS.txt").read_bytes()
    ).hexdigest()
    inputs = preflight.PreflightInputs(
        **{**inputs.__dict__, "packet_checksum_manifest_sha256": manifest_sha}
    )

    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_packet(inputs)
    assert excinfo.value.code == "CHECKSUM_MISMATCH"


def test_verify_packet_rejects_capture_manifest_disagreement(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    packet = tmp_path / "packet"
    base_sha, local_sha, _records = _create_minimal_packet(repo_root, packet)
    inputs = _build_inputs(repo_root, packet, base_sha=base_sha, local_sha=local_sha)

    # Make the after-manifest disagree with the before-manifest. The
    # checksum manifest still matches both files because we recompute it.
    tampered_records = _records + [
        {"path": "extra.txt", "bytes": 0, "sha256": hashlib.sha256(b"").hexdigest()}
    ]
    (packet / "source-files.after.cjson").write_bytes(
        preflight._canonical_bytes(tampered_records)
    )
    manifest_lines = [
        f"{hashlib.sha256((packet / name).read_bytes()).hexdigest()} *{name}"
        for name in (
            "HEAD.txt",
            "ignored.txt",
            "local-only.bundle",
            "pheno-harness-full.tar.gz",
            "source-files.after.cjson",
            "source-files.before.cjson",
            "untracked.txt",
        )
    ]
    (packet / "SHA256SUMS.txt").write_text(
        "\n".join(manifest_lines) + "\n", encoding="utf-8"
    )
    manifest_sha = hashlib.sha256(
        (packet / "SHA256SUMS.txt").read_bytes()
    ).hexdigest()
    inputs = preflight.PreflightInputs(
        **{**inputs.__dict__, "packet_checksum_manifest_sha256": manifest_sha}
    )

    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_packet(inputs)
    assert excinfo.value.code == "CAPTURE_NOT_STABLE"


def test_verify_packet_rejects_head_mismatch(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    packet = tmp_path / "packet"
    base_sha, local_sha, _records = _create_minimal_packet(repo_root, packet)
    # Build inputs with an expected_local_sha that disagrees with HEAD.txt.
    inputs = _build_inputs(
        repo_root,
        packet,
        base_sha=base_sha,
        local_sha="0" * 40,
    )
    manifest_sha = hashlib.sha256(
        (packet / "SHA256SUMS.txt").read_bytes()
    ).hexdigest()
    inputs = preflight.PreflightInputs(
        **{**inputs.__dict__, "packet_checksum_manifest_sha256": manifest_sha}
    )

    # The bundle check runs before HEAD.txt is decoded, so the bundle
    # raises first when ``expected_local_sha`` disagrees with the real
    # tip. Either error code is an acceptable rejection of the mismatch.
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_packet(inputs)
    assert excinfo.value.code in {
        "CAPTURE_HEAD_MISMATCH",
        "BUNDLE_LOCAL_SHA_MISMATCH",
    }


def test_verify_packet_head_mismatch_is_detected_when_bundle_passes(
    tmp_path: Path,
) -> None:
    """When ``expected_local_sha`` matches the bundle tip but HEAD.txt is
    rewritten, the ``CAPTURE_HEAD_MISMATCH`` check fires after the bundle
    verification succeeds.
    """
    repo_root = tmp_path / "repo"
    packet = tmp_path / "packet"
    base_sha, local_sha, _records = _create_minimal_packet(repo_root, packet)
    inputs = _build_inputs(
        repo_root,
        packet,
        base_sha=base_sha,
        local_sha=local_sha,
    )
    manifest_sha = hashlib.sha256(
        (packet / "SHA256SUMS.txt").read_bytes()
    ).hexdigest()
    inputs = preflight.PreflightInputs(
        **{**inputs.__dict__, "packet_checksum_manifest_sha256": manifest_sha}
    )

    # Rewrite HEAD.txt so its content disagrees with the expected tip.
    (packet / "HEAD.txt").write_bytes(b"f" * 40 + b"\n")
    manifest_lines = [
        f"{hashlib.sha256((packet / name).read_bytes()).hexdigest()} *{name}"
        for name in (
            "HEAD.txt",
            "ignored.txt",
            "local-only.bundle",
            "pheno-harness-full.tar.gz",
            "source-files.after.cjson",
            "source-files.before.cjson",
            "untracked.txt",
        )
    ]
    (packet / "SHA256SUMS.txt").write_text(
        "\n".join(manifest_lines) + "\n", encoding="utf-8"
    )
    manifest_sha = hashlib.sha256(
        (packet / "SHA256SUMS.txt").read_bytes()
    ).hexdigest()
    inputs = preflight.PreflightInputs(
        **{**inputs.__dict__, "packet_checksum_manifest_sha256": manifest_sha}
    )

    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_packet(inputs)
    assert excinfo.value.code == "CAPTURE_HEAD_MISMATCH"


# ---------------------------------------------------------------------------
# Valid packet (happy path)
# ---------------------------------------------------------------------------


def test_verify_packet_accepts_valid_packet(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    packet = tmp_path / "packet"
    base_sha, local_sha, _records = _create_minimal_packet(repo_root, packet)
    inputs = _build_inputs(repo_root, packet, base_sha=base_sha, local_sha=local_sha)
    manifest_sha = hashlib.sha256(
        (packet / "SHA256SUMS.txt").read_bytes()
    ).hexdigest()
    inputs = preflight.PreflightInputs(
        **{**inputs.__dict__, "packet_checksum_manifest_sha256": manifest_sha}
    )

    report, captured, exclusions, captured_categories = preflight._verify_packet(
        inputs
    )
    assert report["verified"] is True
    assert report["checksums"]["manifest_sha256"] == manifest_sha
    assert report["capture_manifests_identical"] is True
    assert report["bundle"]["verified"] is True
    assert report["bundle"]["preserves_expected_local"] is True
    assert report["bundle"]["requires_expected_base"] is True
    assert report["tar"]["files"] == len(captured)
    # The untracked / ignored inventories are empty in this fixture.
    assert captured_categories["untracked"] == set()
    assert captured_categories["ignored"] == set()
    assert exclusions == set()
