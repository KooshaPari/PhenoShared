#!/usr/bin/env python3
"""Portable regression corpus for the Codex guard source installer."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "guards" / "install-codex-repo-delete-guard.sh"
SOURCE_GUARD = REPO_ROOT / "guards" / "codex-repo-delete-guard.sh"
CORPUS = REPO_ROOT / "tests" / "test_codex_repo_delete_guard.py"


def run(*args: str, expected: int = 0, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        ["/bin/bash", str(INSTALLER), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
        env=environment,
        check=False,
    )
    if completed.returncode != expected:
        output = (completed.stdout + completed.stderr).decode("utf-8", errors="replace")
        raise AssertionError(f"{args}: expected exit {expected}, got {completed.returncode}; output={output!r}")
    return completed


def manifest_path(output: bytes) -> Path:
    match = re.search(rb"^MANIFEST=(.+)$", output, flags=re.MULTILINE)
    if not match:
        raise AssertionError(f"install did not report a manifest: {output!r}")
    return Path(match.group(1).decode("utf-8"))


def target_for(root: Path) -> Path:
    parent = root / ".codex" / "bin"
    parent.mkdir(parents=True)
    return parent / "codex-repo-delete-guard.sh"


def assert_mode(path: Path, expected: int) -> None:
    actual = stat.S_IMODE(path.stat().st_mode)
    if actual != expected:
        raise AssertionError(f"{path}: expected mode {expected:o}, got {actual:o}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="codex-guard-installer-") as temporary:
        root = Path(temporary)
        target = target_for(root)
        original = b"#!/usr/bin/env bash\nprintf '%s\\n' old-guard\n"
        target.write_bytes(original)
        target.chmod(0o700)

        dry_run = run("--target-root", str(root))
        if b"DRY-RUN" not in dry_run.stdout or target.read_bytes() != original:
            raise AssertionError("default invocation must report dry run and preserve target")
        assert_mode(target, 0o700)

        copied_bundle = root / "mismatch-bundle"
        copied_guards = copied_bundle / "guards"
        copied_tests = copied_bundle / "tests"
        copied_guards.mkdir(parents=True)
        copied_tests.mkdir()
        copied_installer = copied_guards / INSTALLER.name
        copied_guard = copied_guards / SOURCE_GUARD.name
        shutil.copy2(INSTALLER, copied_installer)
        shutil.copy2(SOURCE_GUARD, copied_guard)
        shutil.copy2(CORPUS, copied_tests / CORPUS.name)
        with copied_guard.open("ab") as handle:
            handle.write(b"# mismatch fixture\n")
        mismatch = subprocess.run(
            ["/bin/bash", str(copied_installer), "--install", "--target-root", str(root)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
        )
        if mismatch.returncode != 1 or b"source SHA-256 mismatch" not in mismatch.stderr:
            raise AssertionError("mutated source must be refused before target mutation")
        if target.read_bytes() != original:
            raise AssertionError("SHA mismatch changed the target")

        installed = run("--install", "--target-root", str(root))
        manifest = manifest_path(installed.stdout)
        if not manifest.is_file() or target.read_bytes() != SOURCE_GUARD.read_bytes():
            raise AssertionError("install must create manifest and atomically replace target")
        assert_mode(target, 0o755)
        manifest_text = manifest.read_text()
        if (
            f"target={target}" not in manifest_text
            or "original_existed=1" not in manifest_text
            or "backup_sha256=" not in manifest_text
            or "backup_mode=700" not in manifest_text
        ):
            raise AssertionError("manifest is missing target/original state")
        backup_match = re.search(r"^backup=(.+)$", manifest_text, flags=re.MULTILINE)
        if not backup_match:
            raise AssertionError("manifest is missing backup path")
        backup = Path(backup_match.group(1))
        if backup.read_bytes() != original:
            raise AssertionError("backup content does not preserve original guard")
        assert_mode(backup, 0o700)

        installed_corpus = subprocess.run(
            [sys.executable, str(CORPUS)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            env={**os.environ, "CODEX_REPO_DELETE_GUARD": str(target)},
            check=False,
        )
        if installed_corpus.returncode != 0:
            raise AssertionError(f"installed corpus failed: {(installed_corpus.stdout + installed_corpus.stderr)!r}")

        backup.write_bytes(b"tampered backup\n")
        backup.chmod(0o700)
        tampered_rollback = run("--rollback", str(manifest), expected=1)
        if b"recorded backup changed since install" not in tampered_rollback.stderr:
            raise AssertionError("rollback must refuse a tampered backup")
        if target.read_bytes() != SOURCE_GUARD.read_bytes():
            raise AssertionError("refused rollback changed installed target")
        backup.write_bytes(original)
        backup.chmod(0o700)

        run("--rollback", str(manifest))
        if target.read_bytes() != original:
            raise AssertionError("rollback did not restore only the recorded original")
        assert_mode(target, 0o700)

    print("PASS codex-repo-delete-guard installer corpus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
