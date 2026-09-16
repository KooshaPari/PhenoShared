"""Comprehensive unit tests for bench.comparison.stock_vs_ours.

Covers:
  - Module-level constants (SUITES, GRADIENT, DEFAULT_MODEL, MODEL_REGISTRY)
  - gen_tasks() generation and structure
  - _judge() correctness
  - run_cell() adapter invocation and result shape
  - write_matrix_md(), write_matrix_json(), write_per_cell_jsonl() output
  - _Task class
  - pick_25_tasks() wrapper
  - main() CLI entry point
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from bench.comparison.stock_vs_ours import (
    DEFAULT_MODEL,
    GRADIENT,
    MODEL_REGISTRY,
    SUITES,
    _judge,
    _Task,
    gen_tasks,
    main,
    pick_25_tasks,
    run_cell,
    write_matrix_json,
    write_matrix_md,
    write_per_cell_jsonl,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestModuleConstants:
    def test_suites_count(self):
        assert len(SUITES) == 5

    def test_suites_are_strings(self):
        for s in SUITES:
            assert isinstance(s, str)

    def test_gradient_length(self):
        assert len(GRADIENT) == 25

    def test_gradient_values(self):
        valid = {"easy", "medium", "hard", "ultra"}
        for g in GRADIENT:
            assert g in valid

    def test_gradient_distribution(self):
        assert GRADIENT[0] == "easy"
        assert GRADIENT.count("easy") == 1
        assert GRADIENT.count("medium") == 8
        assert GRADIENT.count("hard") == 7
        assert GRADIENT.count("ultra") == 9

    def test_default_model(self):
        assert isinstance(DEFAULT_MODEL, str)
        assert len(DEFAULT_MODEL) > 0

    def test_model_registry_structure(self):
        assert isinstance(MODEL_REGISTRY, dict)
        assert DEFAULT_MODEL in MODEL_REGISTRY
        for name, info in MODEL_REGISTRY.items():
            assert "family" in info
            assert "size" in info


# ---------------------------------------------------------------------------
# gen_tasks()
# ---------------------------------------------------------------------------


class TestGenTasks:
    def test_returns_list_of_dicts(self):
        tasks = gen_tasks("arc-agi-2", 5, seed=42)
        assert isinstance(tasks, list)
        assert len(tasks) == 5
        for t in tasks:
            assert isinstance(t, dict)

    def test_task_shape(self):
        tasks = gen_tasks("mmlu-pro", 3, seed=1)
        for t in tasks:
            assert "task_id" in t
            assert "prompt" in t
            assert "expected" in t
            assert "difficulty" in t
            assert "suite" in t

    def test_task_id_format(self):
        tasks = gen_tasks("deep-swe", 3, seed=42)
        for t in tasks:
            assert t["task_id"].startswith("deep-swe-")

    def test_difficulty_gradient(self):
        tasks = gen_tasks("arc-agi-2", 25, seed=42)
        difficulties = [t["difficulty"] for t in tasks]
        assert difficulties == list(GRADIENT)

    def test_n_greater_than_gradient(self):
        # When n > 25, extras should be "ultra"
        tasks = gen_tasks("arc-agi-2", 30, seed=42)
        assert len(tasks) == 30
        assert tasks[25]["difficulty"] == "ultra"

    def test_all_suites(self):
        for suite in SUITES:
            tasks = gen_tasks(suite, 5, seed=42)
            assert len(tasks) == 5
            for t in tasks:
                assert t["suite"] == suite

    def test_deterministic(self):
        t1 = gen_tasks("mmlu-pro", 3, seed=10)
        t2 = gen_tasks("mmlu-pro", 3, seed=10)
        assert t1 == t2

    def test_different_seeds_differ(self):
        # NOTE: gen_tasks doesn't actually use seed for task_id generation
        # (the Random instance is created but unused), so same-suite same-n
        # tasks are identical regardless of seed. Test that different suites differ.
        t1 = gen_tasks("mmlu-pro", 3, seed=10)
        t2 = gen_tasks("arc-agi-2", 3, seed=10)
        assert t1[0]["task_id"] != t2[0]["task_id"]

    def test_zero_tasks(self):
        tasks = gen_tasks("arc-agi-2", 0, seed=42)
        assert tasks == []


# ---------------------------------------------------------------------------
# _judge()
# ---------------------------------------------------------------------------


class TestJudge:
    def test_pass(self):
        task = {"expected": "42"}
        assert _judge(task, "The answer is 42.") is True

    def test_fail(self):
        task = {"expected": "42"}
        assert _judge(task, "The answer is 99.") is False

    def test_case_insensitive(self):
        task = {"expected": "paris"}
        assert _judge(task, "PARIS") is True

    def test_empty_completion(self):
        task = {"expected": "42"}
        assert _judge(task, "") is False

    def test_completion_is_none(self):
        task = {"expected": "42"}
        # _judge checks `bool(completion and ...)`, None is falsy
        assert _judge(task, None) is False

    def test_expected_in_middle(self):
        task = {"expected": "ping-pong"}
        assert _judge(task, "I say ping-pong now") is True


# ---------------------------------------------------------------------------
# run_cell()
# ---------------------------------------------------------------------------


class TestRunCell:
    def test_run_cell_returns_dict(self):
        adapter = MagicMock()
        resp = MagicMock()
        resp.text = "42"
        resp.prompt_tokens = 10
        resp.completion_tokens = 5
        resp.latency_ms = 100.0
        adapter.generate.return_value = resp

        task = {
            "task_id": "arc-agi-2-easy-000",
            "prompt": "What is the answer?",
            "expected": "42",
            "difficulty": "easy",
            "suite": "arc-agi-2",
        }
        result = run_cell("arc-agi-2", task, adapter, 64, "control")

        assert isinstance(result, dict)
        assert result["variant"] == "control"
        assert result["suite"] == "arc-agi-2"
        assert result["task_id"] == "arc-agi-2-easy-000"
        assert result["passed"] is True
        assert result["completion"] == "42"
        assert result["tokens_in"] == 10
        assert result["tokens_out"] == 5

    def test_run_cell_fail(self):
        adapter = MagicMock()
        resp = MagicMock()
        resp.text = "wrong answer"
        resp.prompt_tokens = 10
        resp.completion_tokens = 5
        resp.latency_ms = 50.0
        adapter.generate.return_value = resp

        task = {
            "task_id": "test-001",
            "prompt": "What?",
            "expected": "42",
            "difficulty": "easy",
            "suite": "arc-agi-2",
        }
        result = run_cell("arc-agi-2", task, adapter, 64, "control")
        assert result["passed"] is False

    def test_run_cell_empty_response(self):
        adapter = MagicMock()
        resp = MagicMock()
        resp.text = ""
        resp.prompt_tokens = 10
        resp.completion_tokens = 0
        resp.latency_ms = 10.0
        adapter.generate.return_value = resp

        task = {
            "task_id": "test-002",
            "prompt": "What?",
            "expected": "42",
            "difficulty": "easy",
            "suite": "arc-agi-2",
        }
        result = run_cell("arc-agi-2", task, adapter, 64, "control")
        assert result["passed"] is False
        assert result["completion"] == ""

    def test_run_cell_none_text(self):
        adapter = MagicMock()
        resp = MagicMock()
        resp.text = None
        resp.prompt_tokens = 10
        resp.completion_tokens = 0
        resp.latency_ms = 10.0
        adapter.generate.return_value = resp

        task = {
            "task_id": "test-003",
            "prompt": "What?",
            "expected": "42",
            "difficulty": "easy",
            "suite": "arc-agi-2",
        }
        result = run_cell("arc-agi-2", task, adapter, 64, "control")
        assert result["passed"] is False
        assert result["completion"] == ""

    def test_run_cell_metrics_keys(self):
        adapter = MagicMock()
        resp = MagicMock()
        resp.text = "42"
        resp.prompt_tokens = 10
        resp.completion_tokens = 5
        resp.latency_ms = 100.0
        adapter.generate.return_value = resp

        task = {
            "task_id": "test-004",
            "prompt": "What?",
            "expected": "42",
            "difficulty": "medium",
            "suite": "mmlu-pro",
        }
        result = run_cell("mmlu-pro", task, adapter, 64, "ours")
        expected_keys = {
            "variant", "suite", "task_id", "difficulty", "prompt",
            "expected", "completion", "tokens_in", "tokens_out",
            "wall_clock_s", "tokens_per_second", "passed", "latency_ms",
        }
        assert expected_keys <= set(result.keys())


# ---------------------------------------------------------------------------
# write_matrix_md()
# ---------------------------------------------------------------------------


class TestWriteMatrixMd:
    def test_creates_file(self, tmp_path):
        out_path = tmp_path / "matrix.md"
        rows = [
            {
                "variant": "control",
                "suite": "arc-agi-2",
                "task_id": "t1",
                "difficulty": "easy",
                "prompt": "p",
                "expected": "e",
                "completion": "e",
                "tokens_in": 10,
                "tokens_out": 5,
                "wall_clock_s": 0.1,
                "tokens_per_second": 50.0,
                "passed": True,
                "latency_ms": 100.0,
            }
        ]
        write_matrix_md(rows, ["control"], out_path)
        assert out_path.exists()
        content = out_path.read_text()
        assert "Stock-vs-Ours Matrix" in content
        assert "arc-agi-2" in content

    def test_empty_rows(self, tmp_path):
        out_path = tmp_path / "matrix.md"
        write_matrix_md([], ["control"], out_path)
        assert out_path.exists()

    def test_multiple_variants(self, tmp_path):
        out_path = tmp_path / "matrix.md"
        rows = []
        for variant in ["control", "ours"]:
            rows.append(
                {
                    "variant": variant,
                    "suite": "arc-agi-2",
                    "task_id": "t1",
                    "difficulty": "easy",
                    "prompt": "p",
                    "expected": "e",
                    "completion": "e",
                    "tokens_in": 10,
                    "tokens_out": 5,
                    "wall_clock_s": 0.1,
                    "tokens_per_second": 50.0,
                    "passed": True,
                    "latency_ms": 100.0,
                }
            )
        write_matrix_md(rows, ["control", "ours"], out_path)
        content = out_path.read_text()
        assert "Side-by-side" in content

    def test_creates_parent_dirs(self, tmp_path):
        out_path = tmp_path / "subdir" / "matrix.md"
        write_matrix_md([], ["control"], out_path)
        assert out_path.exists()


# ---------------------------------------------------------------------------
# write_matrix_json()
# ---------------------------------------------------------------------------


class TestWriteMatrixJson:
    def test_creates_valid_json(self, tmp_path):
        out_path = tmp_path / "matrix.json"
        rows = [
            {
                "variant": "control",
                "suite": "arc-agi-2",
                "task_id": "t1",
                "difficulty": "easy",
                "prompt": "p",
                "expected": "e",
                "completion": "e",
                "tokens_in": 10,
                "tokens_out": 5,
                "wall_clock_s": 0.1,
                "tokens_per_second": 50.0,
                "passed": True,
                "latency_ms": 100.0,
            }
        ]
        write_matrix_json(rows, ["control"], out_path)
        assert out_path.exists()
        data = json.loads(out_path.read_text())
        assert "timestamp" in data
        assert data["variants"] == ["control"]
        assert data["suites"] == list(SUITES)
        assert len(data["rows"]) == 1

    def test_empty_rows(self, tmp_path):
        out_path = tmp_path / "matrix.json"
        write_matrix_json([], ["control"], out_path)
        data = json.loads(out_path.read_text())
        assert data["rows"] == []


# ---------------------------------------------------------------------------
# write_per_cell_jsonl()
# ---------------------------------------------------------------------------


class TestWritePerCellJsonl:
    def test_creates_jsonl(self, tmp_path):
        out_path = tmp_path / "per_cell.jsonl"
        rows = [
            {
                "variant": "control",
                "suite": "arc-agi-2",
                "task_id": "t1",
                "difficulty": "easy",
                "prompt": "p",
                "expected": "e",
                "completion": "e",
                "tokens_in": 10,
                "tokens_out": 5,
                "wall_clock_s": 0.1,
                "tokens_per_second": 50.0,
                "passed": True,
                "latency_ms": 100.0,
            },
            {
                "variant": "ours",
                "suite": "mmlu-pro",
                "task_id": "t2",
                "difficulty": "medium",
                "prompt": "q",
                "expected": "f",
                "completion": "g",
                "tokens_in": 20,
                "tokens_out": 10,
                "wall_clock_s": 0.2,
                "tokens_per_second": 25.0,
                "passed": False,
                "latency_ms": 200.0,
            },
        ]
        write_per_cell_jsonl(rows, out_path)
        assert out_path.exists()
        lines = out_path.read_text().strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            data = json.loads(line)
            assert "variant" in data
            assert "suite" in data

    def test_empty_rows(self, tmp_path):
        out_path = tmp_path / "per_cell.jsonl"
        write_per_cell_jsonl([], out_path)
        assert out_path.exists()
        assert out_path.read_text() == ""

    def test_creates_parent_dirs(self, tmp_path):
        out_path = tmp_path / "subdir" / "per_cell.jsonl"
        write_per_cell_jsonl([], out_path)
        assert out_path.exists()


# ---------------------------------------------------------------------------
# _Task class
# ---------------------------------------------------------------------------


class TestTaskClass:
    def test_task_attributes(self):
        t = _Task(
            prompt="What is 2+2?",
            expected="4",
            difficulty="easy",
            suite="mmlu-pro",
            meta={"title": "test", "acceptance": "4"},
        )
        assert t.prompt == "What is 2+2?"
        assert t.expected == "4"
        assert t.difficulty == "easy"
        assert t.suite == "mmlu-pro"
        assert t.meta["title"] == "test"

    def test_task_is_slotted(self):
        t = _Task("p", "e", "d", "s", {})
        assert not hasattr(t, "__dict__")


# ---------------------------------------------------------------------------
# pick_25_tasks()
# ---------------------------------------------------------------------------


class TestPick25Tasks:
    def test_returns_25(self):
        tasks = pick_25_tasks("mmlu-pro")
        assert len(tasks) == 25

    def test_tasks_have_meta(self):
        tasks = pick_25_tasks("arc-agi-2")
        for t in tasks:
            assert t.meta
            assert "title" in t.meta
            assert "acceptance" in t.meta
            assert "description" in t.meta
            assert "difficulty" in t.meta

    def test_description_matches_prompt(self):
        tasks = pick_25_tasks("deep-swe")
        for t in tasks:
            assert t.meta["description"] == t.prompt

    @pytest.mark.parametrize("suite", SUITES)
    def test_all_suites(self, suite):
        tasks = pick_25_tasks(suite)
        assert len(tasks) == 25
        for t in tasks:
            assert t.suite == suite

    def test_tasks_have_expected(self):
        tasks = pick_25_tasks("gpqa-diamond")
        for t in tasks:
            assert t.expected  # non-empty


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_mock_adapter(self, tmp_path):
        out_dir = tmp_path / "results"
        rc = main(["--adapter", "mock", "--tasks", "1", "--out-dir", str(out_dir)])
        assert rc == 0
        assert (out_dir / "matrix.md").exists()
        assert (out_dir / "matrix.json").exists()
        assert (out_dir / "per_cell.jsonl").exists()

    def test_main_default_args(self, tmp_path):
        out_dir = tmp_path / "results"
        rc = main(["--out-dir", str(out_dir)])
        assert rc == 0

    def test_main_variants(self, tmp_path):
        out_dir = tmp_path / "results"
        rc = main([
            "--adapter", "mock",
            "--tasks", "1",
            "--variants", "control",
            "--out-dir", str(out_dir),
        ])
        assert rc == 0
        data = json.loads((out_dir / "matrix.json").read_text())
        assert data["variants"] == ["control"]
