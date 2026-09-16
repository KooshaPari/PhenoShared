"""Tests for eval/tbench_v21.py — coverage-focused.

Covers _utc_run_id, build_manifest, write_manifest, and execute.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ======================================================================
# 1. _utc_run_id
# ======================================================================


class TestUtcRunId:
    def test_format(self) -> None:
        from eval.tbench_v21 import _utc_run_id

        rid = _utc_run_id()
        # Should end with _ and 8 hex chars
        assert "_" in rid
        parts = rid.split("_")
        assert len(parts) >= 2
        # The last part should be 8 hex chars
        assert len(parts[-1]) == 8
        assert all(c in "0123456789abcdef" for c in parts[-1])

    def test_unique(self) -> None:
        from eval.tbench_v21 import _utc_run_id

        ids = {_utc_run_id() for _ in range(50)}
        # At least some should be unique (uuid ensures this)
        assert len(ids) > 1


# ======================================================================
# 2. build_manifest
# ======================================================================


class TestBuildManifest:
    @patch("eval.tbench_v21.require_local_alias")
    def test_basic_manifest_2_0(self, mock_require: MagicMock) -> None:
        from eval.tbench_v21 import build_manifest

        manifest = build_manifest(model_alias="test-alias", subset="full", dry_run=True)
        assert manifest["schema_version"] == 1
        assert manifest["suite"] == "terminal-bench@2.0"
        assert manifest["suite_version"] == "2.0"
        assert manifest["model_alias"] == "test-alias"
        assert manifest["subset"] == "full"
        assert manifest["run_mode"] == "dry_run"
        assert manifest["scoreable"] is False
        assert manifest["review_required"] is True
        assert manifest["verification_status"] == "not_run"
        mock_require.assert_called_once_with("test-alias")

    @patch("eval.tbench_v21.require_local_alias")
    def test_basic_manifest_2_1(self, mock_require: MagicMock) -> None:
        from eval.tbench_v21 import build_manifest

        manifest = build_manifest(
            model_alias="test-alias",
            subset="full",
            dry_run=False,
            suite="terminal-bench@2.1",
        )
        assert manifest["suite"] == "terminal-bench@2.1"
        assert manifest["suite_version"] == "2.1"
        assert manifest["run_mode"] == "execute"
        assert manifest["tbench_21_status"] == "missing"

    @patch("eval.tbench_v21.require_local_alias")
    def test_unsupported_suite_raises(self, mock_require: MagicMock) -> None:
        from eval.tbench_v21 import build_manifest

        with pytest.raises(ValueError, match="unsupported Terminal-Bench suite"):
            build_manifest(
                model_alias="test-alias",
                subset="full",
                dry_run=True,
                suite="terminal-bench@3.0",
            )

    @patch("eval.tbench_v21.require_local_alias")
    def test_integrity_flags(self, mock_require: MagicMock) -> None:
        from eval.tbench_v21 import build_manifest

        manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
        integrity = manifest["integrity"]
        assert integrity["local_only"] is True
        assert integrity["cloud_evals_disabled"] is True
        assert integrity["no_training_on_eval_tasks"] is True
        assert integrity["single_attempt_only"] is True

    @patch("eval.tbench_v21.require_local_alias")
    def test_provider_cost_zero(self, mock_require: MagicMock) -> None:
        from eval.tbench_v21 import build_manifest

        manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
        assert manifest["provider_cost_usd"] == 0

    @patch("eval.tbench_v21.require_local_alias")
    def test_n_attempts_one(self, mock_require: MagicMock) -> None:
        from eval.tbench_v21 import build_manifest

        manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
        assert manifest["n_attempts"] == 1

    @patch("eval.tbench_v21.require_local_alias")
    def test_route_is_local(self, mock_require: MagicMock) -> None:
        from eval.tbench_v21 import build_manifest

        manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
        assert manifest["route"] == "local_pheno_serve"

    @patch("eval.tbench_v21.require_local_alias")
    def test_created_at_present(self, mock_require: MagicMock) -> None:
        from eval.tbench_v21 import build_manifest

        manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
        assert "created_at" in manifest
        assert "T" in manifest["created_at"]  # ISO-8601

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_artifact_manifest_2_0_acquired(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        # Write acquired file at the correct path: PHENO_ROOT/state/harbor_terminal_bench_2_0_artifacts.json
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        acquired_file = state_dir / "harbor_terminal_bench_2_0_artifacts.json"
        acquired_file.write_text(json.dumps({"task_count": 89}), encoding="utf-8")

        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
            assert manifest["suite_status"] == "dataset_acquired_verifier_unverified"
            assert manifest["task_artifact_manifest"] is not None

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_no_artifact_manifest_2_0(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        # No acquired file exists
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
            assert manifest["suite_status"] == "availability_unverified"
            assert manifest["task_artifact_manifest"] is None

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_artifact_manifest_2_1_with_valid_acquired(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        tb21_file = tmp_path / "state" / "tbench21_source_acquisition_complete_20260801.json"
        tb21_file.parent.mkdir(parents=True)
        tb21_file.write_text(
            json.dumps({
                "status": "source_acquired_pinned",
                "git_head": "abc123",
                "source_path": str(source_dir),
                "task_count": 10,
            }),
            encoding="utf-8",
        )
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(
                model_alias="x",
                subset="full",
                dry_run=True,
                suite="terminal-bench@2.1",
            )
            assert manifest["tbench_21_status"] == "available"
            assert manifest["task_artifact_manifest"] is not None

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_artifact_manifest_2_1_missing_source(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        tb21_file = tmp_path / "state" / "tbench21_source_acquisition_complete_20260801.json"
        tb21_file.parent.mkdir(parents=True)
        tb21_file.write_text(
            json.dumps({
                "status": "source_acquired_pinned",
                "git_head": "abc123",
                "source_path": "/nonexistent/path",
                "task_count": 10,
            }),
            encoding="utf-8",
        )
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(
                model_alias="x",
                subset="full",
                dry_run=True,
                suite="terminal-bench@2.1",
            )
            assert manifest["tbench_21_status"] == "missing"

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_artifact_manifest_2_1_missing_task_count(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        tb21_file = tmp_path / "state" / "tbench21_source_acquisition_complete_20260801.json"
        tb21_file.parent.mkdir(parents=True)
        tb21_file.write_text(
            json.dumps({
                "status": "source_acquired_pinned",
                "git_head": "abc123",
                "source_path": str(source_dir),
                "task_count": 0,
            }),
            encoding="utf-8",
        )
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(
                model_alias="x",
                subset="full",
                dry_run=True,
                suite="terminal-bench@2.1",
            )
            assert manifest["tbench_21_status"] == "missing"

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_subset_manifest_valid(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        subset_file = tmp_path / "subset.json"
        subset_file.write_text(
            json.dumps({
                "suite": "terminal-bench@2.0",
                "task_ids": ["task-a", "task-b"],
                "subset_manifest_sha256": "abc123hash",
            }),
            encoding="utf-8",
        )
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(
                model_alias="x",
                subset="custom",
                dry_run=True,
                subset_manifest=subset_file,
            )
            assert manifest["task_count"] == 2
            assert manifest["task_names"] == ["task-a", "task-b"]
            assert manifest["subset_manifest_sha256"] == "abc123hash"
            assert manifest["subset_manifest"] == str(subset_file)

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_subset_manifest_suite_mismatch(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        subset_file = tmp_path / "subset.json"
        subset_file.write_text(
            json.dumps({
                "suite": "terminal-bench@3.0",
                "task_ids": ["task-a"],
                "subset_manifest_sha256": "hash",
            }),
            encoding="utf-8",
        )
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            with pytest.raises(ValueError, match="subset manifest suite does not match"):
                build_manifest(
                    model_alias="x",
                    subset="custom",
                    dry_run=True,
                    subset_manifest=subset_file,
                )

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_subset_manifest_missing_task_ids(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        subset_file = tmp_path / "subset.json"
        subset_file.write_text(
            json.dumps({
                "suite": "terminal-bench@2.0",
                "task_ids": [],
                "subset_manifest_sha256": "hash",
            }),
            encoding="utf-8",
        )
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            with pytest.raises(ValueError, match="subset manifest must contain task_ids"):
                build_manifest(
                    model_alias="x",
                    subset="custom",
                    dry_run=True,
                    subset_manifest=subset_file,
                )

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_subset_manifest_missing_sha(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        subset_file = tmp_path / "subset.json"
        subset_file.write_text(
            json.dumps({
                "suite": "terminal-bench@2.0",
                "task_ids": ["task-a"],
            }),
            encoding="utf-8",
        )
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            with pytest.raises(ValueError, match="subset manifest must contain task_ids"):
                build_manifest(
                    model_alias="x",
                    subset="custom",
                    dry_run=True,
                    subset_manifest=subset_file,
                )

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_task_count_from_artifact(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        acquired_file = state_dir / "harbor_terminal_bench_2_0_artifacts.json"
        acquired_file.write_text(json.dumps({"task_count": 42}), encoding="utf-8")
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
            assert manifest["task_count"] == 42

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_task_count_default_89(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(
                model_alias="x",
                subset="full",
                dry_run=True,
                suite="terminal-bench@2.0",
            )
            assert manifest["task_count"] == 89

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_task_count_none_for_2_1_no_artifact(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(
                model_alias="x",
                subset="full",
                dry_run=True,
                suite="terminal-bench@2.1",
            )
            assert manifest["task_count"] is None

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_task_artifact_root_from_acquired(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        acquired_file = state_dir / "harbor_terminal_bench_2_0_artifacts.json"
        acquired_file.write_text(
            json.dumps({"task_count": 89, "local_root": "/some/root"}),
            encoding="utf-8",
        )
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
            assert manifest["task_artifact_root"] == "/some/root"

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_task_manifest_sha256_from_acquired(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        acquired_file = state_dir / "harbor_terminal_bench_2_0_artifacts.json"
        acquired_file.write_text(
            json.dumps({
                "task_count": 89,
                "task_manifest_sha256": "abcdef123456",
            }),
            encoding="utf-8",
        )
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
            assert manifest["task_manifest_sha256"] == "abcdef123456"

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_task_manifest_sha256_fallback_manifest_sha256(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        acquired_file = state_dir / "harbor_terminal_bench_2_0_artifacts.json"
        acquired_file.write_text(
            json.dumps({
                "task_count": 89,
                "manifest_sha256": "fallback_hash",
            }),
            encoding="utf-8",
        )
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
            assert manifest["task_manifest_sha256"] == "fallback_hash"

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_tbench_21_status_not_requested(
        self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path
    ) -> None:
        from eval.tbench_v21 import build_manifest

        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path):
            manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
            assert manifest["tbench_21_status"] == "not_requested"

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_base_url_from_env(self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path) -> None:
        from eval.tbench_v21 import build_manifest

        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path), \
             patch.dict(os.environ, {"PHENO_SERVE_BASE_URL": "http://custom:9999/v1"}):
            manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
            assert manifest["base_url"] == "http://custom:9999/v1"

    @patch("eval.tbench_v21.require_local_alias")
    @patch("eval.tbench_v21.PHENO_ROOT")
    def test_base_url_default(self, mock_root: MagicMock, mock_require: MagicMock, tmp_path: Path) -> None:
        from eval.tbench_v21 import build_manifest

        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path), \
             patch.dict(os.environ, {}, clear=False):
            env = os.environ.copy()
            env.pop("PHENO_SERVE_BASE_URL", None)
            with patch("os.environ", env):
                manifest = build_manifest(model_alias="x", subset="full", dry_run=True)
                assert manifest["base_url"] == "http://127.0.0.1:21080/v1"


# ======================================================================
# 3. write_manifest
# ======================================================================


class TestWriteManifest:
    def test_write_manifest_default_root(self, tmp_path: Path) -> None:
        from eval.tbench_v21 import write_manifest

        manifest = {"suite_version": "2.0", "model_alias": "test"}
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path), \
             patch("eval.tbench_v21._utc_run_id", return_value="20260101T000000Z_abc12345"):
            result = write_manifest(manifest)
            assert result.exists()
            assert result.suffix == ".json"
            loaded = json.loads(result.read_text(encoding="utf-8"))
            assert loaded["suite_version"] == "2.0"

    def test_write_manifest_custom_root(self, tmp_path: Path) -> None:
        from eval.tbench_v21 import write_manifest

        manifest = {"suite_version": "2.1", "model_alias": "test"}
        custom_root = tmp_path / "custom_output"
        with patch("eval.tbench_v21._utc_run_id", return_value="run123"):
            result = write_manifest(manifest, root=custom_root)
            assert result.exists()
            assert str(custom_root) in str(result)

    def test_write_manifest_version_dir(self, tmp_path: Path) -> None:
        from eval.tbench_v21 import write_manifest

        manifest = {"suite_version": "2.1"}
        with patch("eval.tbench_v21.PHENO_ROOT", tmp_path), \
             patch("eval.tbench_v21._utc_run_id", return_value="run456"):
            result = write_manifest(manifest)
            # suite_version "2.1" → "21" directory
            assert "21" in str(result)

    def test_write_manifest_creates_parents(self, tmp_path: Path) -> None:
        from eval.tbench_v21 import write_manifest

        manifest = {"suite_version": "2.0"}
        custom_root = tmp_path / "a" / "b" / "c"
        with patch("eval.tbench_v21._utc_run_id", return_value="run789"):
            result = write_manifest(manifest, root=custom_root)
            assert result.exists()


# ======================================================================
# 4. execute
# ======================================================================


class TestExecute:
    @patch("eval.tbench_v21.subprocess.run")
    @patch("eval.tbench_v21.require_runtime_alias")
    @patch("eval.tbench_v21.local_env")
    @patch("eval.tbench_v21.PHENO_ROOT")
    @patch("eval.tbench_v21.CONFIG_DIR")
    def test_execute_basic(
        self,
        mock_cfg: MagicMock,
        mock_root: MagicMock,
        mock_local_env: MagicMock,
        mock_runtime: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        from eval.tbench_v21 import execute

        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_local_env.return_value = {}
        mock_cfg.__truediv__ = MagicMock(return_value=Path("/tmp/harbor.yaml"))
        manifest = {
            "model_alias": "test-model",
            "suite": "terminal-bench@2.0",
            "base_url": "http://127.0.0.1:21080/v1",
            "task_names": [],
            "task_artifact_root": None,
        }
        output_dir = Path("/tmp/output")
        result = execute(manifest, output_dir)
        assert result == 0
        mock_runtime.assert_called_once_with("test-model")

    @patch("eval.tbench_v21.subprocess.run")
    @patch("eval.tbench_v21.require_runtime_alias")
    @patch("eval.tbench_v21.local_env")
    @patch("eval.tbench_v21.PHENO_ROOT")
    @patch("eval.tbench_v21.CONFIG_DIR")
    def test_execute_with_task_names(
        self,
        mock_cfg: MagicMock,
        mock_root: MagicMock,
        mock_local_env: MagicMock,
        mock_runtime: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        from eval.tbench_v21 import execute

        mock_subprocess.return_value = MagicMock(returncode=1)
        mock_local_env.return_value = {}
        mock_cfg.__truediv__ = MagicMock(return_value=Path("/tmp/harbor.yaml"))
        manifest = {
            "model_alias": "m1",
            "suite": "terminal-bench@2.0",
            "base_url": "http://127.0.0.1:21080/v1",
            "task_names": ["task-a", "task-b"],
            "task_artifact_root": None,
        }
        result = execute(manifest, Path("/tmp/output"))
        assert result == 1
        # Verify --include-task-name was passed
        call_args = mock_subprocess.call_args
        cmd = call_args[0][0]
        assert "--include-task-name" in cmd
        assert "task-a" in cmd
        assert "task-b" in cmd

    @patch("eval.tbench_v21.subprocess.run")
    @patch("eval.tbench_v21.require_runtime_alias")
    @patch("eval.tbench_v21.local_env")
    @patch("eval.tbench_v21.PHENO_ROOT")
    @patch("eval.tbench_v21.CONFIG_DIR")
    def test_execute_with_artifact_root(
        self,
        mock_cfg: MagicMock,
        mock_root: MagicMock,
        mock_local_env: MagicMock,
        mock_runtime: MagicMock,
        mock_subprocess: MagicMock,
        tmp_path: Path,
    ) -> None:
        from eval.tbench_v21 import execute

        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_local_env.return_value = {}
        mock_cfg.__truediv__ = MagicMock(return_value=Path("/tmp/harbor.yaml"))
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        manifest = {
            "model_alias": "m1",
            "suite": "terminal-bench@2.0",
            "base_url": "http://127.0.0.1:21080/v1",
            "task_names": [],
            "task_artifact_root": str(source_dir),
        }
        execute(manifest, Path("/tmp/output"))
        call_args = mock_subprocess.call_args
        cmd = call_args[0][0]
        assert "-p" in cmd

    @patch("eval.tbench_v21.subprocess.run")
    @patch("eval.tbench_v21.require_runtime_alias")
    @patch("eval.tbench_v21.local_env")
    @patch("eval.tbench_v21.PHENO_ROOT")
    @patch("eval.tbench_v21.CONFIG_DIR")
    def test_execute_2_1_requires_root(
        self,
        mock_cfg: MagicMock,
        mock_root: MagicMock,
        mock_local_env: MagicMock,
        mock_runtime: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        from eval.tbench_v21 import execute

        mock_local_env.return_value = {}
        mock_cfg.__truediv__ = MagicMock(return_value=Path("/tmp/harbor.yaml"))
        manifest = {
            "model_alias": "m1",
            "suite": "terminal-bench@2.1",
            "base_url": "http://127.0.0.1:21080/v1",
            "task_names": [],
            "task_artifact_root": "/nonexistent/path",
        }
        with pytest.raises(ValueError, match="pinned local task root"):
            execute(manifest, Path("/tmp/output"))

    @patch("eval.tbench_v21.subprocess.run")
    @patch("eval.tbench_v21.require_runtime_alias")
    @patch("eval.tbench_v21.local_env")
    @patch("eval.tbench_v21.PHENO_ROOT")
    @patch("eval.tbench_v21.CONFIG_DIR")
    def test_execute_2_1_no_root_fallback_refused(
        self,
        mock_cfg: MagicMock,
        mock_root: MagicMock,
        mock_local_env: MagicMock,
        mock_runtime: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        from eval.tbench_v21 import execute

        mock_local_env.return_value = {}
        mock_cfg.__truediv__ = MagicMock(return_value=Path("/tmp/harbor.yaml"))
        manifest = {
            "model_alias": "m1",
            "suite": "terminal-bench@2.1",
            "base_url": "http://127.0.0.1:21080/v1",
            "task_names": [],
            "task_artifact_root": None,
        }
        with pytest.raises(ValueError, match="pinned local task root"):
            execute(manifest, Path("/tmp/output"))

    @patch("eval.tbench_v21.subprocess.run")
    @patch("eval.tbench_v21.require_runtime_alias")
    @patch("eval.tbench_v21.local_env")
    @patch("eval.tbench_v21.PHENO_ROOT")
    @patch("eval.tbench_v21.CONFIG_DIR")
    def test_execute_podman_compat(
        self,
        mock_cfg: MagicMock,
        mock_root: MagicMock,
        mock_local_env: MagicMock,
        mock_runtime: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        from eval.tbench_v21 import execute

        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_local_env.return_value = {}
        mock_cfg.__truediv__ = MagicMock(return_value=Path("/tmp/harbor.yaml"))
        manifest = {
            "model_alias": "m1",
            "suite": "terminal-bench@2.0",
            "base_url": "http://127.0.0.1:21080/v1",
            "task_names": [],
        }
        with patch.dict(os.environ, {"PHENO_HARBOR_PODMAN_COMPAT": "1"}):
            execute(manifest, Path("/tmp/output"))
            call_args = mock_subprocess.call_args
            cmd = call_args[0][0]
            # First element should be sys.executable, not "harbor"
            assert cmd[0] != "harbor"

    @patch("eval.tbench_v21.subprocess.run")
    @patch("eval.tbench_v21.require_runtime_alias")
    @patch("eval.tbench_v21.local_env")
    @patch("eval.tbench_v21.PHENO_ROOT")
    @patch("eval.tbench_v21.CONFIG_DIR")
    def test_execute_uses_d_flag_without_artifact(
        self,
        mock_cfg: MagicMock,
        mock_root: MagicMock,
        mock_local_env: MagicMock,
        mock_runtime: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        from eval.tbench_v21 import execute

        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_local_env.return_value = {}
        mock_cfg.__truediv__ = MagicMock(return_value=Path("/tmp/harbor.yaml"))
        manifest = {
            "model_alias": "m1",
            "suite": "terminal-bench@2.0",
            "base_url": "http://127.0.0.1:21080/v1",
            "task_names": [],
            "task_artifact_root": None,
        }
        execute(manifest, Path("/tmp/output"))
        call_args = mock_subprocess.call_args
        cmd = call_args[0][0]
        assert "-d" in cmd
        assert "terminal-bench@2.0" in cmd
