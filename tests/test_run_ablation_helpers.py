"""Tests for bench.matrix.run_ablation_helpers.

Exercises compute_verified_pass_at_1, _utc_now, _git_head, _task_ids,
_prompt_for, _sort_json, _sha256_hex, _cell_to_task_result,
build_cells_payload, verifier_available, verifier_judge_for_cell, and
the REPO_ROOT constant.

Target: 80%+ coverage (baseline 39.3%).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

from bench.matrix.run_ablation_helpers import (
    REPO_ROOT,
    _cell_to_task_result,
    _git_head,
    _prompt_for,
    _sha256_hex,
    _sort_json,
    _task_ids,
    _utc_now,
    build_cells_payload,
    compute_verified_pass_at_1,
    verifier_available,
    verifier_judge_for_cell,
)

# ---------------------------------------------------------------------------
# Mock AblationResult
# ---------------------------------------------------------------------------


@dataclass
class MockResult:
    """Minimal AblationResult stand-in for build_cells_payload tests."""

    run_id: str = "test-run"
    cells: list = field(default_factory=list)
    started_at: str = "2026-01-01T00:00:00Z"
    stopped_at: str = "2026-01-01T00:00:01Z"
    dry_run: bool = True
    model_id: str = "mock"
    suites: list = field(default_factory=list)
    variants: list = field(default_factory=list)
    tasks_per_suite: int = 2


# ---------------------------------------------------------------------------
# compute_verified_pass_at_1
# ---------------------------------------------------------------------------


class TestComputeVerifiedPassAt1:
    """Tests for compute_verified_pass_at_1()."""

    def test_empty_list_returns_zero(self) -> None:
        """An empty list should return 0.0."""
        assert compute_verified_pass_at_1([]) == 0.0

    def test_cells_without_key_default_to_zero(self) -> None:
        """Cells lacking verified_pass_at_1 default to 0.0."""
        cells = [{"ok": True}, {"ok": False}]
        assert compute_verified_pass_at_1(cells) == 0.0

    def test_mixed_cells(self) -> None:
        """Mix of cells with and without the key averages correctly."""
        cells = [
            {"verified_pass_at_1": 1.0},
            {"ok": True},  # defaults to 0.0
            {"verified_pass_at_1": 0.5},
        ]
        expected = round((1.0 + 0.0 + 0.5) / 3, 4)
        assert compute_verified_pass_at_1(cells) == expected

    def test_all_cells_with_values(self) -> None:
        """All cells carry verified_pass_at_1."""
        cells = [
            {"verified_pass_at_1": 1.0},
            {"verified_pass_at_1": 1.0},
            {"verified_pass_at_1": 0.0},
        ]
        expected = round((1.0 + 1.0 + 0.0) / 3, 4)
        assert compute_verified_pass_at_1(cells) == expected

    def test_single_cell(self) -> None:
        """Single cell returns its own value."""
        cells = [{"verified_pass_at_1": 0.75}]
        assert compute_verified_pass_at_1(cells) == 0.75

    def test_string_numeric_value(self) -> None:
        """String numeric values are cast to float."""
        cells = [{"verified_pass_at_1": "0.6"}]
        assert compute_verified_pass_at_1(cells) == 0.6


# ---------------------------------------------------------------------------
# _utc_now
# ---------------------------------------------------------------------------


class TestUtcNow:
    """Tests for _utc_now()."""

    def test_format(self) -> None:
        """Should return ISO format string ending with Z."""
        result = _utc_now()
        assert result.endswith("Z")
        # Should match YYYY-MM-DDTHH:MM:SSZ
        assert len(result) == 20
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == "T"
        assert result[13] == ":"
        assert result[16] == ":"

    def test_returns_string(self) -> None:
        """Return type must be str."""
        assert isinstance(_utc_now(), str)


# ---------------------------------------------------------------------------
# _git_head
# ---------------------------------------------------------------------------


class TestGitHead:
    """Tests for _git_head()."""

    @patch("bench.matrix.run_ablation_helpers.subprocess.check_output")
    def test_success(self, mock_check: object) -> None:
        """Returns stripped hash on success."""
        mock_check.return_value = "abc123def456\n"  # type: ignore[union-attr]
        assert _git_head() == "abc123def456"

    @patch(
        "bench.matrix.run_ablation_helpers.subprocess.check_output",
        side_effect=subprocess.CalledProcessError(1, "git"),
    )
    def test_called_process_error(self, _mock: object) -> None:
        """Returns 'unknown' on CalledProcessError."""
        assert _git_head() == "unknown"

    @patch(
        "bench.matrix.run_ablation_helpers.subprocess.check_output",
        side_effect=FileNotFoundError,
    )
    def test_file_not_found(self, _mock: object) -> None:
        """Returns 'unknown' when git is not installed."""
        assert _git_head() == "unknown"


# ---------------------------------------------------------------------------
# _task_ids
# ---------------------------------------------------------------------------


class TestTaskIds:
    """Tests for _task_ids()."""

    def test_basic_format(self) -> None:
        """IDs follow suite-task-NNN pattern."""
        ids = _task_ids("arithmetic", 3)
        assert ids == ["arithmetic-task-000", "arithmetic-task-001", "arithmetic-task-002"]

    def test_zero_returns_empty(self) -> None:
        """n=0 returns an empty list."""
        assert _task_ids("any", 0) == []

    def test_single(self) -> None:
        """n=1 returns one item."""
        ids = _task_ids("suite", 1)
        assert len(ids) == 1
        assert ids[0] == "suite-task-000"


# ---------------------------------------------------------------------------
# _prompt_for
# ---------------------------------------------------------------------------


class TestPromptFor:
    """Tests for _prompt_for()."""

    def test_format(self) -> None:
        """Prompt contains suite, task_id, and question."""
        prompt = _prompt_for("math", "math-task-000")
        assert "[math]" in prompt
        assert "math-task-000" in prompt
        assert "2+2" in prompt


# ---------------------------------------------------------------------------
# _sort_json
# ---------------------------------------------------------------------------


class TestSortJson:
    """Tests for _sort_json()."""

    def test_dict_keys_sorted(self) -> None:
        """Dict keys appear in sorted order."""
        obj = {"z": 1, "a": 2, "m": 3}
        result = _sort_json(obj)
        assert list(result.keys()) == ["a", "m", "z"]

    def test_list_preserved(self) -> None:
        """Lists are recursively sorted but order is preserved."""
        obj = [3, 1, 2]
        result = _sort_json(obj)
        # Lists maintain their order but elements are processed recursively
        assert result == [3, 1, 2]

    def test_nested_structures(self) -> None:
        """Nested dicts inside lists get sorted too."""
        obj = {"b": [{"z": 1, "a": 2}], "a": 10}
        result = _sort_json(obj)
        assert list(result.keys()) == ["a", "b"]
        assert list(result["b"][0].keys()) == ["a", "z"]

    def test_primitives_unchanged(self) -> None:
        """Primitives pass through unchanged."""
        assert _sort_json(42) == 42
        assert _sort_json("hello") == "hello"
        assert _sort_json(3.14) == 3.14
        assert _sort_json(True) is True
        assert _sort_json(None) is None


# ---------------------------------------------------------------------------
# _sha256_hex
# ---------------------------------------------------------------------------


class TestSha256Hex:
    """Tests for _sha256_hex()."""

    def test_deterministic(self) -> None:
        """Same input always produces the same hash."""
        obj = {"key": "value", "nested": {"a": 1}}
        assert _sha256_hex(obj) == _sha256_hex(obj)

    def test_varies_with_input(self) -> None:
        """Different inputs produce different hashes."""
        assert _sha256_hex({"a": 1}) != _sha256_hex({"b": 1})

    def test_is_hex_string(self) -> None:
        """Output is a lowercase hex string of length 64."""
        h = _sha256_hex({"test": True})
        assert isinstance(h, str)
        assert len(h) == 64
        # All characters must be valid hex
        int(h, 16)

    def test_key_order_independence(self) -> None:
        """Dict key order should not affect the hash (sorted internally)."""
        a = _sha256_hex({"z": 1, "a": 2})
        b = _sha256_hex({"a": 2, "z": 1})
        assert a == b


# ---------------------------------------------------------------------------
# _cell_to_task_result
# ---------------------------------------------------------------------------


class TestCellToTaskResult:
    """Tests for _cell_to_task_result()."""

    def test_ok_cell(self) -> None:
        """Cell with ok=True produces status='ok'."""
        cell = {"ok": True, "task_id": "t1", "wall_clock_s": 1.5}
        result = _cell_to_task_result(cell)
        assert result["status"] == "ok"
        assert result["task_id"] == "t1"
        assert result["wall_clock_s"] == 1.5
        assert result["judge"] == "deterministic"

    def test_fail_cell(self) -> None:
        """Cell with ok=False produces status='wrong'."""
        cell = {"ok": False, "task_id": "t2"}
        result = _cell_to_task_result(cell)
        assert result["status"] == "wrong"

    def test_with_gen_ok(self) -> None:
        """Cell carrying gen_ok overrides pass_at_1 and evidence fields."""
        cell = {
            "ok": True,
            "task_id": "t3",
            "gen_ok": 1.0,
            "pass_at_1": 0.9,
            "verified_pass_at_1": 0.85,
            "evidence_label": "verified",
        }
        result = _cell_to_task_result(cell)
        ap = result["additionalProperties"]
        assert ap["gen_ok"] == 1.0
        assert ap["pass_at_1"] == 0.9
        assert ap["verified_pass_at_1"] == 0.85
        assert ap["evidence_label"] == "verified"

    def test_uses_suite_task_key(self) -> None:
        """suite_task_key takes precedence over task_id."""
        cell = {"ok": True, "suite_task_key": "sk-1", "task_id": "tid-2"}
        result = _cell_to_task_result(cell)
        assert result["task_id"] == "sk-1"

    def test_defaults_without_suite_task_key(self) -> None:
        """Falls back to task_id when suite_task_key is absent."""
        cell = {"ok": True, "task_id": "fallback-id"}
        result = _cell_to_task_result(cell)
        assert result["task_id"] == "fallback-id"

    def test_empty_cell_defaults(self) -> None:
        """Minimal cell uses all defaults."""
        cell: dict = {}
        result = _cell_to_task_result(cell)
        assert result["status"] == "wrong"
        assert result["task_id"] == ""
        assert result["wall_clock_s"] == 0.0
        assert result["tokens_in"] == 0
        assert result["tokens_out"] == 0
        assert result["additionalProperties"]["synthetic"] is False

    def test_harbor_reward_cell(self) -> None:
        """Cell with harbor_reward gets verified evidence."""
        cell = {"ok": True, "task_id": "t4", "harbor_reward": 0.9}
        result = _cell_to_task_result(cell)
        ap = result["additionalProperties"]
        assert ap["verified_pass_at_1"] == 0.9
        assert ap["evidence_label"] == "verified"

    def test_token_fields_mapped(self) -> None:
        """tokens_read/tokens_created map to tokens_in/tokens_out."""
        cell = {"ok": True, "tokens_read": 100, "tokens_created": 50}
        result = _cell_to_task_result(cell)
        assert result["tokens_in"] == 100
        assert result["tokens_out"] == 50

    def test_synthetic_flag(self) -> None:
        """synthetic flag is forwarded."""
        cell = {"ok": True, "synthetic": True}
        result = _cell_to_task_result(cell)
        assert result["additionalProperties"]["synthetic"] is True


# ---------------------------------------------------------------------------
# build_cells_payload
# ---------------------------------------------------------------------------


class TestBuildCellsPayload:
    """Tests for build_cells_payload()."""

    def test_structure(self) -> None:
        """Payload contains all required top-level keys."""
        result = MockResult(
            variants=["v1"],
            cells=[
                {"variant": "v1", "ok": True, "task_id": "t1"},
                {"variant": "v1", "ok": False, "task_id": "t2"},
            ],
            suites=["arithmetic"],
        )
        payload = build_cells_payload(result)
        assert payload["run_id"] == "test-run"
        assert payload["dry_run"] is True
        assert payload["model_id"] == "mock"
        assert payload["variants"] == ["v1"]
        assert payload["suites"] == ["arithmetic"]
        assert "summary" in payload
        assert "cells" in payload
        assert payload["cells"] == result.cells

    def test_by_variant_summary(self) -> None:
        """by_variant section aggregates per-variant stats."""
        result = MockResult(
            variants=["fast", "slow"],
            cells=[
                {"variant": "fast", "ok": True, "task_id": "t1"},
                {"variant": "fast", "ok": True, "task_id": "t2"},
                {"variant": "slow", "ok": False, "task_id": "t3"},
            ],
        )
        payload = build_cells_payload(result)
        bv = payload["summary"]["by_variant"]
        assert bv["fast"]["n_cells"] == 2
        assert bv["fast"]["ok_count"] == 2
        assert bv["slow"]["n_cells"] == 1
        assert bv["slow"]["ok_count"] == 0

    def test_gen_ok_mean_computed(self) -> None:
        """gen_ok_mean is computed when cells carry gen_ok."""
        result = MockResult(
            variants=["v1"],
            cells=[
                {"variant": "v1", "ok": True, "gen_ok": 1.0},
                {"variant": "v1", "ok": True, "gen_ok": 0.5},
            ],
        )
        payload = build_cells_payload(result)
        bv = payload["summary"]["by_variant"]["v1"]
        assert bv["gen_ok_mean"] == round((1.0 + 0.5) / 2, 4)
        assert bv["pass_at_1"] == bv["gen_ok_mean"]

    def test_gen_ok_mean_zero_without_gen_ok(self) -> None:
        """gen_ok_mean defaults to 0.0 when no gen_ok fields present."""
        result = MockResult(
            variants=["v1"],
            cells=[
                {"variant": "v1", "ok": True},
                {"variant": "v1", "ok": False},
            ],
        )
        payload = build_cells_payload(result)
        bv = payload["summary"]["by_variant"]["v1"]
        assert bv["gen_ok_mean"] == 0.0

    def test_empty_variants(self) -> None:
        """Empty variant list produces empty by_variant dict."""
        result = MockResult(variants=[], cells=[])
        payload = build_cells_payload(result)
        assert payload["summary"]["by_variant"] == {}

    def test_meta_model(self) -> None:
        """summary.meta.model matches model_id."""
        result = MockResult(model_id="gpt-4o", variants=[])
        payload = build_cells_payload(result)
        assert payload["summary"]["meta"]["model"] == "gpt-4o"


# ---------------------------------------------------------------------------
# verifier_available
# ---------------------------------------------------------------------------


class TestVerifierAvailable:
    """Tests for verifier_available()."""

    def test_returns_bool(self) -> None:
        """Must return a boolean value."""
        assert isinstance(verifier_available(), bool)


# ---------------------------------------------------------------------------
# verifier_judge_for_cell
# ---------------------------------------------------------------------------


class TestVerifierJudgeForCell:
    """Tests for verifier_judge_for_cell()."""

    def test_ok_cell(self) -> None:
        """ok=True cell returns gen_ok=1.0."""
        cell = {"ok": True}
        result = verifier_judge_for_cell(cell)
        assert result["gen_ok"] == 1.0
        assert result["evidence_label"] == "reported"

    def test_with_harbor_reward(self) -> None:
        """Cell with harbor_reward gets verified evidence."""
        cell = {"ok": True, "harbor_reward": 0.8}
        result = verifier_judge_for_cell(cell)
        assert result["verified_pass_at_1"] == 0.8
        assert result["evidence_label"] == "verified"

    def test_dry_run_cell_no_harbor(self) -> None:
        """Dry-run cell without harbor_reward keeps verified_pass_at_1 at 0.0."""
        cell = {"ok": False}
        result = verifier_judge_for_cell(cell)
        assert result["verified_pass_at_1"] == 0.0
        assert result["gen_ok"] == 0.0
        assert result["evidence_label"] == "reported"

    def test_returns_dict_with_expected_keys(self) -> None:
        """Returned dict always has the four contract keys."""
        result = verifier_judge_for_cell({"ok": True})
        for key in ("gen_ok", "pass_at_1", "verified_pass_at_1", "evidence_label"):
            assert key in result


# ---------------------------------------------------------------------------
# REPO_ROOT
# ---------------------------------------------------------------------------


class TestRepoRoot:
    """Tests for REPO_ROOT constant."""

    def test_is_path(self) -> None:
        """REPO_ROOT must be a Path instance."""
        assert isinstance(REPO_ROOT, Path)

    def test_points_to_project_root(self) -> None:
        """REPO_ROOT should contain bench/ directory."""
        assert (REPO_ROOT / "bench").is_dir()
