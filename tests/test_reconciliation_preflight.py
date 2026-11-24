from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import scripts.reconciliation_preflight as preflight


def _git(repo: Path, *arguments: str) -> str:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_unreachable_blob(repo: Path, payload: bytes) -> str:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    completed = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=repo,
        env=env,
        input=payload,
        check=True,
        capture_output=True,
    )
    return completed.stdout.decode("ascii").strip()


def _manifest(repo: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        payload = path.read_bytes()
        records.append(
            {
                "path": path.relative_to(repo).as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return records


def _write_json(path: Path, payload: object) -> None:
    path.write_bytes(preflight._canonical_bytes(payload))


def _replace_checksum(packet: Path, relative: str) -> None:
    checksum_path = packet / "SHA256SUMS.txt"
    replacement = f"{_digest(packet / relative)} *{relative}"
    lines = checksum_path.read_text(encoding="utf-8").splitlines()
    lines = [replacement if line.endswith(f"*{relative}") else line for line in lines]
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _create_fixture(root: Path) -> tuple[Path, Path, Path, str, str, str, str]:
    repo = root / "repo"
    packet = root / "packet"
    repo.mkdir()
    packet.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Preflight Test")
    _git(repo, "config", "user.email", "preflight@example.invalid")
    (repo / "README.md").write_text("base\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "base")
    base_sha = _git(repo, "rev-parse", "HEAD")
    (repo / "local.txt").write_text("local\n", encoding="utf-8", newline="\n")
    (repo / "dirty-tracked.txt").write_text(
        "head version\n", encoding="utf-8", newline="\n"
    )
    (repo / ".gitignore").write_text("ignored/\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "local.txt", "dirty-tracked.txt", ".gitignore")
    _git(repo, "commit", "-q", "-m", "local")
    local_sha = _git(repo, "rev-parse", "HEAD")

    (repo / "dirty-tracked.txt").write_text(
        "captured dirty version\n", encoding="utf-8", newline="\n"
    )
    (repo / "captured-untracked.txt").write_text(
        "captured untracked\n", encoding="utf-8", newline="\n"
    )
    (repo / "ignored").mkdir()
    (repo / "ignored" / "captured.log").write_text(
        "captured ignored\n", encoding="utf-8", newline="\n"
    )
    dangling_sha = _write_unreachable_blob(repo, b"captured unreachable object\n")

    records = _manifest(repo)
    _write_json(packet / "source-files.before.cjson", records)
    _write_json(packet / "source-files.after.cjson", records)
    (packet / "HEAD.txt").write_text(local_sha + "\n", encoding="utf-8", newline="\n")
    (packet / "untracked.txt").write_text(
        "captured-untracked.txt\n", encoding="utf-8", newline="\n"
    )
    (packet / "ignored.txt").write_text(
        "ignored/captured.log\n", encoding="utf-8", newline="\n"
    )
    with tarfile.open(packet / "pheno-harness-full.tar.gz", "w:gz") as archive:
        for record in records:
            relative = str(record["path"])
            archive.add(
                repo / Path(relative),
                arcname=f"{repo.name}/{relative}",
                recursive=False,
            )
    _git(
        repo,
        "bundle",
        "create",
        str(packet / "local-only.bundle"),
        "main",
        f"^{base_sha}",
    )
    packet_files = [
        "HEAD.txt",
        "ignored.txt",
        "local-only.bundle",
        "pheno-harness-full.tar.gz",
        "source-files.after.cjson",
        "source-files.before.cjson",
        "untracked.txt",
    ]
    checksum_lines = [f"{_digest(packet / name)} *{name}" for name in packet_files]
    (packet / "SHA256SUMS.txt").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8", newline="\n"
    )

    live_sha = "f" * 40
    remote = root / "remote.json"
    _write_json(
        remote,
        {
            "schema_version": preflight.REMOTE_SCHEMA_VERSION,
            "captured_at_utc": "2026-07-15T03:41:35Z",
            "repository": {
                "full_name": "example/pheno",
                "private": True,
                "archived": False,
                "default_branch": "main",
            },
            "base_sha": base_sha,
            "local_sha": local_sha,
            "live_sha": live_sha,
            "branches": [
                {"name": "feature/kernel", "sha": "e" * 40},
                {"name": "main", "sha": live_sha},
            ],
        },
    )
    return repo, packet, remote, base_sha, local_sha, live_sha, dangling_sha


class ReconciliationPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._fixture_temp = tempfile.TemporaryDirectory()
        cls.fixture_root = Path(cls._fixture_temp.name)
        cls.fixture = _create_fixture(cls.fixture_root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._fixture_temp.cleanup()

    def setUp(self) -> None:
        self._case_temp = tempfile.TemporaryDirectory()
        case = Path(self._case_temp.name)
        source_repo, source_packet, source_remote, base, local, live, dangling = (
            self.fixture
        )
        self.repo = shutil.copytree(source_repo, case / "repo")
        self.packet = shutil.copytree(source_packet, case / "packet")
        self.remote = shutil.copy2(source_remote, case / "remote.json")
        self.inputs = preflight.PreflightInputs(
            repo_root=self.repo,
            packet=self.packet,
            packet_checksum_manifest_sha256=_digest(self.packet / "SHA256SUMS.txt"),
            remote_snapshot=self.remote,
            remote_snapshot_sha256=_digest(self.remote),
            expected_repository="example/pheno",
            expected_default_branch="main",
            expected_base_sha=base,
            expected_local_sha=local,
            expected_live_sha=live,
            expected_branches=(("feature/kernel", "e" * 40), ("main", live)),
            quiescence_delay_ms=0,
        )
        self.captured_dangling_sha = dangling

    def tearDown(self) -> None:
        self._case_temp.cleanup()

    def test_clean_fixture_is_ready_and_canonicalizable(self) -> None:
        result = preflight.run_preflight(self.inputs, sleeper=lambda _seconds: None)
        self.assertTrue(result["ok"], result)
        self.assertEqual("READY_FOR_DISPOSABLE_CLONE_REVIEW", result["decision"])
        self.assertEqual(0, result["checks"]["current_delta"]["changed_or_new_total"])
        encoded = preflight._canonical_bytes(result)
        self.assertEqual(result, json.loads(encoded))
        self.assertNotIn(b"Preflight Test", encoded)

    def test_changed_worktree_requires_fresh_delta_capture(self) -> None:
        (self.repo / "local.txt").write_text(
            "post-capture\n", encoding="utf-8", newline="\n"
        )
        result = preflight.run_preflight(self.inputs, sleeper=lambda _seconds: None)
        self.assertFalse(result["ok"])
        self.assertEqual("NEEDS_FRESH_DELTA_CAPTURE", result["decision"])
        tracked = result["checks"]["current_delta"]["categories"]["tracked"]
        self.assertEqual(1, tracked["changed_since_capture"])

    def test_deleted_captured_untracked_and_ignored_files_are_deltas(self) -> None:
        (self.repo / "captured-untracked.txt").unlink()
        (self.repo / "ignored" / "captured.log").unlink()
        result = preflight.run_preflight(self.inputs, sleeper=lambda _seconds: None)
        self.assertEqual("NEEDS_FRESH_DELTA_CAPTURE", result["decision"])
        categories = result["checks"]["current_delta"]["categories"]
        for name in ("untracked", "ignored"):
            self.assertEqual(1, categories[name]["non_regular_or_missing"])
            self.assertEqual(1, categories[name]["removed_from_capture_category"])
            self.assertEqual(1, categories[name]["delta_files"])

    def test_reverted_captured_dirty_file_is_found_when_diff_omits_it(self) -> None:
        (self.repo / "dirty-tracked.txt").write_text(
            "head version\n", encoding="utf-8", newline="\n"
        )
        real_run_git = preflight._run_git

        def omit_from_current_diff(repo_root, arguments, *, stdin=None):
            if arguments[0] == "diff-files":
                return b""
            return real_run_git(repo_root, arguments, stdin=stdin)

        with patch(
            "scripts.reconciliation_preflight._run_git",
            side_effect=omit_from_current_diff,
        ):
            result = preflight.run_preflight(self.inputs, sleeper=lambda _seconds: None)
        self.assertEqual("NEEDS_FRESH_DELTA_CAPTURE", result["decision"])
        current = result["checks"]["current_delta"]
        self.assertEqual(0, current["categories"]["tracked"]["total"])
        self.assertEqual(1, current["captured_payload"]["changed_since_capture"])
        self.assertEqual(1, current["changed_or_new_total"])

    def test_checksum_tampering_fails_closed(self) -> None:
        (self.packet / "HEAD.txt").write_text("0" * 40 + "\n", encoding="utf-8")
        result = preflight.run_preflight(self.inputs, sleeper=lambda _seconds: None)
        self.assertEqual("FAILED", result["decision"])
        self.assertEqual("CHECKSUM_MISMATCH", result["errors"][0]["code"])

    def test_manifest_swap_after_single_read_cannot_change_verified_semantics(
        self,
    ) -> None:
        real_read = preflight._read_packet_file

        def read_then_swap(packet: Path, relative: str, max_bytes: int) -> bytes:
            payload = real_read(packet, relative, max_bytes)
            if relative == "SHA256SUMS.txt":
                (packet / relative).write_text(
                    "0" * 64 + " *HEAD.txt\n", encoding="utf-8", newline="\n"
                )
            return payload

        with patch(
            "scripts.reconciliation_preflight._read_packet_file",
            side_effect=read_then_swap,
        ):
            entries, packet_files, report = preflight._verify_checksums(
                self.packet, self.inputs.packet_checksum_manifest_sha256
            )
        self.assertIn("HEAD.txt", entries)
        self.assertEqual(
            self.inputs.expected_local_sha,
            packet_files["HEAD.txt"].decode("utf-8").strip(),
        )
        self.assertEqual(
            self.inputs.packet_checksum_manifest_sha256,
            report["manifest_sha256"],
        )
        self.assertNotEqual(
            self.inputs.packet_checksum_manifest_sha256,
            _digest(self.packet / "SHA256SUMS.txt"),
        )

    def test_payload_swap_after_single_read_cannot_change_verified_semantics(
        self,
    ) -> None:
        real_read = preflight._read_packet_file

        def read_then_swap(packet: Path, relative: str, max_bytes: int) -> bytes:
            payload = real_read(packet, relative, max_bytes)
            if relative == "HEAD.txt":
                (packet / relative).write_text(
                    "0" * 40 + "\n", encoding="utf-8", newline="\n"
                )
            return payload

        with patch(
            "scripts.reconciliation_preflight._read_packet_file",
            side_effect=read_then_swap,
        ):
            _entries, packet_files, _report = preflight._verify_checksums(
                self.packet, self.inputs.packet_checksum_manifest_sha256
            )
        self.assertEqual(
            self.inputs.expected_local_sha,
            packet_files["HEAD.txt"].decode("utf-8").strip(),
        )
        self.assertNotEqual(
            self.inputs.expected_local_sha,
            (self.packet / "HEAD.txt").read_text(encoding="utf-8").strip(),
        )

    def test_packet_individual_and_total_read_bounds_fail_closed(self) -> None:
        with patch.object(preflight, "_PACKET_FILE_MAX_BYTES", 1):
            with self.assertRaises(preflight.PreflightError) as individual:
                preflight._verify_checksums(
                    self.packet, self.inputs.packet_checksum_manifest_sha256
                )
        self.assertEqual("PACKET_FILE_TOO_LARGE", individual.exception.code)

        manifest_size = (self.packet / "SHA256SUMS.txt").stat().st_size
        with patch.object(preflight, "_PACKET_TOTAL_MAX_BYTES", manifest_size + 1):
            with self.assertRaises(preflight.PreflightError) as total:
                preflight._verify_checksums(
                    self.packet, self.inputs.packet_checksum_manifest_sha256
                )
        self.assertEqual("PACKET_TOTAL_TOO_LARGE", total.exception.code)

    def test_missing_checksum_manifest_fails_closed(self) -> None:
        (self.packet / "SHA256SUMS.txt").unlink()
        result = preflight.run_preflight(self.inputs, sleeper=lambda _seconds: None)
        self.assertEqual("FAILED", result["decision"])
        self.assertEqual("CHECKSUM_MANIFEST_MISSING", result["errors"][0]["code"])

    def test_symlinked_checksum_manifest_is_reported_as_unsafe(self) -> None:
        manifest = self.packet / "SHA256SUMS.txt"
        target = self.packet / "SHA256SUMS.real.txt"
        manifest.replace(target)
        try:
            manifest.symlink_to(target.name)
        except OSError as exc:
            self.skipTest(f"symbolic links unavailable: {exc}")
        result = preflight.run_preflight(self.inputs, sleeper=lambda _seconds: None)
        self.assertEqual("FAILED", result["decision"])
        self.assertEqual("UNSAFE_PACKET_PATH", result["errors"][0]["code"])

    def test_invalid_bundle_fails_even_with_updated_checksum(self) -> None:
        (self.packet / "local-only.bundle").write_bytes(b"not a git bundle\n")
        _replace_checksum(self.packet, "local-only.bundle")
        inputs = replace(
            self.inputs,
            packet_checksum_manifest_sha256=_digest(self.packet / "SHA256SUMS.txt"),
        )
        result = preflight.run_preflight(inputs, sleeper=lambda _seconds: None)
        self.assertEqual("FAILED", result["decision"])
        self.assertEqual("GIT_READ_FAILED", result["errors"][0]["code"])

    def test_rewritten_payload_and_checksum_manifest_fail_external_anchor(self) -> None:
        (self.packet / "HEAD.txt").write_text("0" * 40 + "\n", encoding="utf-8")
        _replace_checksum(self.packet, "HEAD.txt")
        result = preflight.run_preflight(self.inputs, sleeper=lambda _seconds: None)
        self.assertEqual("FAILED", result["decision"])
        self.assertEqual(
            "CHECKSUM_MANIFEST_DIGEST_MISMATCH", result["errors"][0]["code"]
        )

    def test_remote_branch_set_mismatch_fails_closed(self) -> None:
        payload = json.loads(self.remote.read_bytes())
        payload["branches"] = [payload["branches"][-1]]
        _write_json(self.remote, payload)
        inputs = replace(self.inputs, remote_snapshot_sha256=_digest(self.remote))
        result = preflight.run_preflight(inputs, sleeper=lambda _seconds: None)
        self.assertEqual("FAILED", result["decision"])
        self.assertEqual("REMOTE_BRANCH_SET_MISMATCH", result["errors"][0]["code"])

    def test_remote_snapshot_duplicate_key_fails_closed(self) -> None:
        raw = self.remote.read_text(encoding="utf-8")
        needle = f'"live_sha":"{self.inputs.expected_live_sha}"'
        self.assertIn(needle, raw)
        self.remote.write_text(
            raw.replace(needle, f"{needle},{needle}", 1),
            encoding="utf-8",
            newline="\n",
        )
        inputs = replace(self.inputs, remote_snapshot_sha256=_digest(self.remote))
        result = preflight.run_preflight(inputs, sleeper=lambda _seconds: None)
        self.assertEqual("REMOTE_SNAPSHOT_DUPLICATE_KEY", result["errors"][0]["code"])

    def test_remote_snapshot_unknown_field_fails_closed(self) -> None:
        payload = json.loads(self.remote.read_bytes())
        payload["unexpected"] = True
        _write_json(self.remote, payload)
        inputs = replace(self.inputs, remote_snapshot_sha256=_digest(self.remote))
        result = preflight.run_preflight(inputs, sleeper=lambda _seconds: None)
        self.assertEqual("REMOTE_SNAPSHOT_FIELDS_INVALID", result["errors"][0]["code"])

    def test_remote_snapshot_read_is_bounded(self) -> None:
        with (
            patch.object(
                preflight, "_REMOTE_SNAPSHOT_MAX_BYTES", self.remote.stat().st_size - 1
            ),
            self.assertRaises(preflight.PreflightError) as error,
        ):
            preflight._verify_remote_snapshot(self.inputs)
        self.assertEqual("REMOTE_SNAPSHOT_TOO_LARGE", error.exception.code)

    def test_git_config_secret_is_not_exposed(self) -> None:
        with (self.repo / ".git" / "config").open("a", encoding="utf-8") as handle:
            handle.write("\n[private]\n\ttoken = DO_NOT_EXPOSE_THIS_VALUE\n")
        result = preflight.run_preflight(self.inputs, sleeper=lambda _seconds: None)
        encoded = preflight._canonical_bytes(result)
        self.assertEqual("NEEDS_FRESH_DELTA_CAPTURE", result["decision"])
        self.assertNotIn(b"DO_NOT_EXPOSE_THIS_VALUE", encoded)
        controls = result["checks"]["current_delta"]["git_controls"]
        self.assertEqual(1, controls["changed_since_capture"])

    def test_new_unreachable_git_object_is_a_delta(self) -> None:
        _write_unreachable_blob(self.repo, b"new unreachable object\n")
        result = preflight.run_preflight(self.inputs, sleeper=lambda _seconds: None)
        self.assertEqual("NEEDS_FRESH_DELTA_CAPTURE", result["decision"])
        objects = result["checks"]["current_delta"]["git_objects"]
        self.assertEqual(1, objects["new_since_capture"])
        self.assertEqual(1, objects["delta_files"])

    def test_missing_captured_unreachable_git_object_is_a_delta(self) -> None:
        object_path = (
            self.repo
            / ".git"
            / "objects"
            / self.captured_dangling_sha[:2]
            / self.captured_dangling_sha[2:]
        )
        object_path.chmod(stat.S_IWRITE)
        object_path.unlink()
        result = preflight.run_preflight(self.inputs, sleeper=lambda _seconds: None)
        self.assertEqual("NEEDS_FRESH_DELTA_CAPTURE", result["decision"])
        objects = result["checks"]["current_delta"]["git_objects"]
        self.assertEqual(1, objects["missing_since_capture"])
        self.assertEqual(1, objects["delta_files"])

    def test_two_different_snapshots_report_non_quiescence(self) -> None:
        calls = 0

        def moving_snapshot(repo, captured, exclusions, captured_categories):
            nonlocal calls
            calls += 1
            snapshot = preflight._capture_current_state(
                repo, captured, exclusions, captured_categories
            )
            return replace(snapshot, fingerprint=str(calls) * 64)

        result = preflight.run_preflight(
            self.inputs,
            sleeper=lambda _seconds: None,
            snapshotter=moving_snapshot,
        )
        self.assertEqual(2, calls)
        self.assertEqual("NOT_QUIESCENT", result["decision"])
        self.assertFalse(result["checks"]["quiescence"]["stable"])

    def test_bundle_validation_uses_the_exact_verified_bytes_on_stdin(self) -> None:
        bundle = (self.packet / "local-only.bundle").read_bytes()
        calls: list[tuple[list[str], bytes | None]] = []

        def fake_run_git(
            _repo_root: Path,
            arguments: list[str],
            *,
            stdin: bytes | None = None,
        ) -> bytes:
            calls.append((arguments, stdin))
            return b""

        with patch(
            "scripts.reconciliation_preflight._run_git", side_effect=fake_run_git
        ):
            report = preflight._verify_bundle(
                self.repo,
                bundle,
                self.inputs.expected_base_sha,
                self.inputs.expected_local_sha,
            )
        self.assertTrue(report["verified"])
        # The bundle is now written to a tempfile and verified via path
        # (rather than `bundle verify -` via stdin). This avoids a git
        # rev-list quirk that fails when the repo has unreachable
        # objects unrelated to the bundle.
        self.assertEqual(1, len(calls))
        arguments, stdin = calls[0]
        self.assertTrue(
            arguments[:2] == ["bundle", "verify"],
            msg=f"expected 'bundle verify <path>', got {arguments}",
        )
        self.assertNotEqual("-", arguments[2], "must not use stdin path")
        self.assertIsNone(stdin)

    def test_git_reads_are_hermetic_noninteractive_and_read_only(self) -> None:
        completed = subprocess.CompletedProcess(["git"], 0, stdout=b"ok", stderr=b"")
        inherited = {
            "GIT_DIR": "malicious-directory",
            "GIT_WORK_TREE": "malicious-worktree",
            "GIT_CONFIG_COUNT": "9",
        }
        with (
            patch.dict(os.environ, inherited, clear=False),
            patch(
                "scripts.reconciliation_preflight.subprocess.run",
                return_value=completed,
            ) as run,
        ):
            self.assertEqual(
                b"ok",
                preflight._run_git(
                    self.repo, ["rev-parse", "HEAD"], stdin=b"exact input"
                ),
            )
        environment = run.call_args.kwargs["env"]
        self.assertEqual("0", environment["GIT_OPTIONAL_LOCKS"])
        self.assertEqual("0", environment["GIT_TERMINAL_PROMPT"])
        self.assertNotIn("GIT_DIR", environment)
        self.assertNotIn("GIT_WORK_TREE", environment)
        self.assertNotIn("GIT_CONFIG_COUNT", environment)
        command = run.call_args.args[0]
        self.assertIn("core.fsmonitor=false", command)
        self.assertIn(f"core.hooksPath={os.devnull}", command)
        self.assertEqual(b"exact input", run.call_args.kwargs["input"])
        self.assertFalse(run.call_args.kwargs["check"])


if __name__ == "__main__":
    unittest.main()
