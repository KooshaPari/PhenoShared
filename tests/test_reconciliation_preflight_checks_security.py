"""Direct unit tests for scripts.reconciliation_preflight_checks_security.

Focuses on the security-critical primitives exercised by the
reconciliation preflight orchestrator:

* ``_safe_relative_path`` rejects hostile relative paths (absolute, parent
  traversal, null bytes, backslashes, empty/dot segments).
* ``_packet_path`` rejects packet files that escape the packet root via
  ``..`` segments, symlinks, or other traversal tricks.
* ``_verify_checksums`` enforces the SHA-256 trust anchor and the packet
  byte budget.

The orchestrator covers happy-path scenarios; these tests are
defense-in-depth for the negative paths so that the security boundary
cannot silently regress.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import scripts.reconciliation_preflight as preflight

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_symlink(source: Path, target: Path) -> bool:
    """Create ``source -> target`` symlink. Returns False on Windows when
    the developer mode / SeCreateSymbolicLinkPrivilege is unavailable.
    """
    try:
        source.symlink_to(target)
        return True
    except (OSError, NotImplementedError):
        return False


def _write_packet_files(packet: Path) -> dict[str, bytes]:
    """Materialize the seven required packet files plus a correct
    SHA256SUMS.txt manifest. Returns ``{relative: bytes}``.
    """
    files: dict[str, bytes] = {
        "HEAD.txt": b"0" * 40 + b"\n",
        "ignored.txt": b"ignored-sample.txt\n",
        "local-only.bundle": b"# v2 git bundle header\n",
        "pheno-harness-full.tar.gz": b"placeholder-tarball-bytes",
        "source-files.after.cjson": json.dumps([]).encode("utf-8"),
        "source-files.before.cjson": json.dumps([]).encode("utf-8"),
        "untracked.txt": b"untracked-sample.txt\n",
    }
    for relative, payload in files.items():
        (packet / relative).write_bytes(payload)
    manifest_lines = [
        f"{hashlib.sha256(payload).hexdigest()} *{relative}"
        for relative, payload in files.items()
    ]
    (packet / "SHA256SUMS.txt").write_text(
        "\n".join(manifest_lines) + "\n", encoding="utf-8"
    )
    return files


# ---------------------------------------------------------------------------
# _safe_relative_path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "/etc/passwd",
        "/",
        "/foo/bar",
    ],
)
def test_safe_relative_path_rejects_absolute_posix(value: str) -> None:
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._safe_relative_path(value)
    assert excinfo.value.code == "UNSAFE_PACKET_PATH"


@pytest.mark.parametrize(
    "value",
    [
        r"C:\Windows",
        r"..\Windows",
        "subdir\\evil",
    ],
)
def test_safe_relative_path_rejects_backslash_and_windows(value: str) -> None:
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._safe_relative_path(value)
    assert excinfo.value.code == "UNSAFE_PACKET_PATH"


@pytest.mark.parametrize(
    "value",
    [
        "../etc/passwd",
        "..",
        "foo/../bar",
        "foo/..",
        "foo\x00bar",
    ],
)
def test_safe_relative_path_rejects_traversal_and_null(value: str) -> None:
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._safe_relative_path(value)
    assert excinfo.value.code == "UNSAFE_PACKET_PATH"


def test_safe_relative_path_rejects_empty() -> None:
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._safe_relative_path("")
    assert excinfo.value.code == "UNSAFE_PACKET_PATH"


@pytest.mark.parametrize(
    "value",
    [
        "HEAD.txt",
        "nested/file.txt",
        "deeply/nested/path/to/file.bin",
    ],
)
def test_safe_relative_path_accepts_valid_relative(value: str) -> None:
    assert preflight._safe_relative_path(value) == value


# ---------------------------------------------------------------------------
# _packet_path
# ---------------------------------------------------------------------------


def test_packet_path_accepts_valid_relative_file(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    (packet / "HEAD.txt").write_text("payload", encoding="utf-8")
    resolved = preflight._packet_path(packet, "HEAD.txt")
    assert resolved == (packet / "HEAD.txt").resolve()


def test_packet_path_rejects_parent_traversal(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    (packet / "HEAD.txt").write_text("payload", encoding="utf-8")
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._packet_path(packet, "/../etc/passwd")
    assert excinfo.value.code == "UNSAFE_PACKET_PATH"


def test_packet_path_rejects_symlink_pointing_outside_root(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"target content")
    if not _safe_symlink(packet / "link.txt", outside):
        pytest.skip("symbolic links unavailable on this platform/privilege")
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._packet_path(packet, "link.txt")
    assert excinfo.value.code == "UNSAFE_PACKET_PATH"


def test_packet_path_rejects_missing_file(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    # ``_packet_path`` raises ``FileNotFoundError`` (an ``OSError``) on a
    # missing file. The higher-level ``_read_packet_file`` translates it
    # into a ``PACKET_FILE_MISSING`` PreflightError; verify both layers.
    with pytest.raises(FileNotFoundError):
        preflight._packet_path(packet, "does-not-exist.txt")
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._read_packet_file(
            packet, "does-not-exist.txt", preflight._PACKET_FILE_MAX_BYTES
        )
    assert excinfo.value.code == "PACKET_FILE_MISSING"


# ---------------------------------------------------------------------------
# _verify_checksums
# ---------------------------------------------------------------------------


def _make_valid_packet(packet: Path) -> str:
    _write_packet_files(packet)
    manifest_bytes = (packet / "SHA256SUMS.txt").read_bytes()
    return hashlib.sha256(manifest_bytes).hexdigest()


def test_verify_checksums_accepts_valid_manifest(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    manifest_sha = _make_valid_packet(packet)
    entries, files, report = preflight._verify_checksums(packet, manifest_sha)
    assert set(entries) == set(files)
    assert "HEAD.txt" in entries
    assert report["manifest_sha256"] == manifest_sha
    assert report["mismatched"] == 0
    assert report["missing"] == 0


def test_verify_checksums_rejects_mismatched_sha256(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    _make_valid_packet(packet)
    wrong_sha = "0" * 64
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_checksums(packet, wrong_sha)
    assert excinfo.value.code == "CHECKSUM_MANIFEST_DIGEST_MISMATCH"


def test_verify_checksums_rejects_invalid_sha_format(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    _make_valid_packet(packet)
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_checksums(packet, "not-a-real-sha")
    assert excinfo.value.code == "CHECKSUM_MANIFEST_DIGEST_INVALID"


def test_verify_checksums_rejects_missing_manifest(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_checksums(packet, "a" * 64)
    assert excinfo.value.code == "CHECKSUM_MANIFEST_MISSING"


def test_verify_checksums_rejects_payload_checksum_mismatch(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    _make_valid_packet(packet)
    (packet / "HEAD.txt").write_bytes(b"tampered\n")
    manifest_sha = hashlib.sha256(
        (packet / "SHA256SUMS.txt").read_bytes()
    ).hexdigest()
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_checksums(packet, manifest_sha)
    assert excinfo.value.code == "CHECKSUM_MISMATCH"


def test_verify_checksums_rejects_packet_total_too_large(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    _make_valid_packet(packet)
    manifest_size = (packet / "SHA256SUMS.txt").stat().st_size
    with patch.object(preflight, "_PACKET_TOTAL_MAX_BYTES", manifest_size + 1):
        with pytest.raises(preflight.PreflightError) as excinfo:
            preflight._verify_checksums(packet, hashlib.sha256(
                (packet / "SHA256SUMS.txt").read_bytes()
            ).hexdigest())
    assert excinfo.value.code == "PACKET_TOTAL_TOO_LARGE"


def test_verify_checksums_rejects_packet_file_too_large(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    _write_packet_files(packet)
    # Patch the per-file cap to 0 so any non-empty entry trips it.
    with patch.object(preflight, "_PACKET_FILE_MAX_BYTES", 0):
        with pytest.raises(preflight.PreflightError) as excinfo:
            preflight._verify_checksums(packet, hashlib.sha256(
                (packet / "SHA256SUMS.txt").read_bytes()
            ).hexdigest())
    assert excinfo.value.code == "PACKET_FILE_TOO_LARGE"


def test_verify_checksums_rejects_missing_required_entries(tmp_path: Path) -> None:
    packet = tmp_path / "packet"
    packet.mkdir()
    files = _write_packet_files(packet)
    # Drop the HEAD.txt entry from the manifest.
    files.pop("HEAD.txt")
    manifest_lines = [
        f"{hashlib.sha256(payload).hexdigest()} *{relative}"
        for relative, payload in files.items()
    ]
    (packet / "SHA256SUMS.txt").write_text(
        "\n".join(manifest_lines) + "\n", encoding="utf-8"
    )
    manifest_sha = hashlib.sha256(
        (packet / "SHA256SUMS.txt").read_bytes()
    ).hexdigest()
    with pytest.raises(preflight.PreflightError) as excinfo:
        preflight._verify_checksums(packet, manifest_sha)
    assert excinfo.value.code == "CHECKSUM_COVERAGE_INCOMPLETE"
