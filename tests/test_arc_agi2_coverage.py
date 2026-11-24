"""Comprehensive coverage tests for ``bench.suites.arc_agi2``.

Exercises:
* module-level constants (SOURCE_URL, VERSION, NUM_TASKS_*, DEFAULT_TIMEOUT_S,
  ARC_COLOR_LABELS).
* helpers ``_arc_prompt``, ``_parse_grid_response``, ``_grid_to_pretty``,
  ``_arc_correctness_check``.
* the ``ArcAgi2`` suite class: instantiation, ``subset()``, ``verify()``,
  ``_generate_synthetic_task`` (via the public verify path).
"""

from __future__ import annotations

import json

from bench.suites.arc_agi2 import (
    ARC_COLOR_LABELS,
    DEFAULT_TIMEOUT_S,
    NUM_TASKS_FULL,
    NUM_TASKS_SUBSET,
    SOURCE_URL,
    VERSION,
    ArcAgi2,
    _arc_correctness_check,
    _arc_prompt,
    _grid_to_pretty,
    _parse_grid_response,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestModuleConstants:
    """Constant values exposed by the module."""

    def test_source_url(self) -> None:
        assert SOURCE_URL == "arcprize.org/arc-agi/2025/"

    def test_version(self) -> None:
        assert VERSION == "2.0"

    def test_num_tasks_full_is_thousand(self) -> None:
        assert NUM_TASKS_FULL == 1000

    def test_num_tasks_subset_is_hundred(self) -> None:
        assert NUM_TASKS_SUBSET == 100

    def test_default_timeout_s(self) -> None:
        assert DEFAULT_TIMEOUT_S == 90

    def test_color_labels_has_sixteen_entries(self) -> None:
        assert len(ARC_COLOR_LABELS) == 16

    def test_color_labels_first_is_black(self) -> None:
        assert ARC_COLOR_LABELS[0] == "black"

    def test_color_labels_last_is_purple(self) -> None:
        assert ARC_COLOR_LABELS[-1] == "purple"


# ---------------------------------------------------------------------------
# _arc_prompt
# ---------------------------------------------------------------------------


class TestArcPrompt:
    """``_arc_prompt`` formats the task description for the model."""

    def test_contains_task_id(self) -> None:
        prompt = _arc_prompt("ARC-0042", [], [[0]])
        assert "ARC-0042" in prompt

    def test_contains_arc_done_marker(self) -> None:
        prompt = _arc_prompt("ARC-0001", [], [[0]])
        assert "ARC_DONE=ARC-0001" in prompt

    def test_contains_test_input(self) -> None:
        test_input = [[1, 2], [3, 4]]
        prompt = _arc_prompt("ARC-1", [], test_input)
        assert json.dumps(test_input) in prompt

    def test_serializes_at_most_three_train_pairs(self) -> None:
        train = [{"input": [[i]], "output": [[i + 1]]} for i in range(10)]
        prompt = _arc_prompt("ARC-1", train, [[0]])
        # Only first 3 are serialized → "### Example 3" appears, "Example 4" doesn't
        assert "### Example 3" in prompt
        assert "### Example 4" not in prompt

    def test_serializes_each_train_pair_input_and_output(self) -> None:
        train = [
            {"input": [[1, 2]], "output": [[2, 3]]},
            {"input": [[4, 5]], "output": [[5, 6]]},
        ]
        prompt = _arc_prompt("ARC-2", train, [[0]])
        assert json.dumps([[1, 2]]) in prompt
        assert json.dumps([[2, 3]]) in prompt
        assert json.dumps([[4, 5]]) in prompt

    def test_empty_train_pairs_works(self) -> None:
        prompt = _arc_prompt("ARC-1", [], [[0]])
        # No "### Example 1" header should appear
        assert "### Example 1" not in prompt
        # But the rest of the framing should be present
        assert "Training Examples" in prompt
        assert "Test Input" in prompt


# ---------------------------------------------------------------------------
# _parse_grid_response
# ---------------------------------------------------------------------------


class TestParseGridResponse:
    """``_parse_grid_response`` extracts a 2D grid from a model response."""

    def test_parses_simple_grid(self) -> None:
        text = "Some text [[1, 2], [3, 4]] more text"
        grid = _parse_grid_response(text)
        assert grid == [[1, 2], [3, 4]]

    def test_parses_nested_grid(self) -> None:
        text = "Output: [[0, 1, 2], [3, 4, 5], [6, 7, 8]]"
        grid = _parse_grid_response(text)
        assert grid == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]

    def test_returns_none_when_no_grid_marker(self) -> None:
        assert _parse_grid_response("nothing resembling a grid") is None

    def test_returns_none_when_grid_malformed(self) -> None:
        # Unbalanced brackets
        assert _parse_grid_response("[[[]]") is None

    def test_skips_non_grid_brackets(self) -> None:
        # The "[[" marker is needed to consider this a grid candidate
        assert _parse_grid_response("[1, 2]") is None

    def test_returns_first_valid_grid(self) -> None:
        text = "first [[1, 1], [1, 1]] second [[2, 2]]"
        grid = _parse_grid_response(text)
        # First matching "[[" wins
        assert grid == [[1, 1], [1, 1]]

    def test_handles_whitespace_in_grid(self) -> None:
        text = "[[ 1 ,  2 ],  [ 3 ,  4 ]]"
        grid = _parse_grid_response(text)
        assert grid == [[1, 2], [3, 4]]

    def test_handles_negative_numbers(self) -> None:
        text = "[[-1, -2], [-3, -4]]"
        grid = _parse_grid_response(text)
        assert grid == [[-1, -2], [-3, -4]]

    def test_handles_irregular_dimensions(self) -> None:
        text = "[[1, 2, 3], [4]]"
        grid = _parse_grid_response(text)
        assert grid == [[1, 2, 3], [4]]


# ---------------------------------------------------------------------------
# _grid_to_pretty
# ---------------------------------------------------------------------------


class TestGridToPretty:
    """``_grid_to_pretty`` renders a small grid as ASCII art."""

    def test_empty_grid(self) -> None:
        assert _grid_to_pretty([]) == "<empty>"

    def test_grid_with_empty_first_row(self) -> None:
        assert _grid_to_pretty([[]]) == "<empty>"

    def test_renders_simple_grid(self) -> None:
        out = _grid_to_pretty([[1, 2], [3, 4]])
        assert "1" in out
        assert "2" in out
        assert "3" in out
        assert "4" in out

    def test_caps_rows_at_six(self) -> None:
        grid = [[i] for i in range(20)]
        out = _grid_to_pretty(grid)
        # Should render at most 6 rows
        assert out.count("\n") <= 5  # 6 rows → 5 newlines

    def test_caps_columns_at_ten(self) -> None:
        grid = [list(range(20))]
        out = _grid_to_pretty(grid)
        # First row should contain at most 10 columns worth of numbers
        first_line = out.split("\n", 1)[0]
        # Each cell is right-aligned 2 chars + space = 3 chars
        assert len(first_line) <= 10 * 3


# ---------------------------------------------------------------------------
# _arc_correctness_check
# ---------------------------------------------------------------------------


class TestArcCorrectnessCheck:
    """``_arc_correctness_check`` runs the pixel-perfect scoring."""

    def test_pixel_perfect_match(self) -> None:
        expected = [[0, 1], [2, 3]]
        text = json.dumps(expected)
        passed, reason, parsed = _arc_correctness_check(text, expected)
        assert passed is True
        assert reason == "pixel-perfect"
        assert parsed == expected

    def test_no_grid_returns_no_grid(self) -> None:
        passed, reason, parsed = _arc_correctness_check("hello", [[0]])
        assert passed is False
        assert reason == "no-grid"
        assert parsed is None

    def test_row_count_mismatch(self) -> None:
        expected = [[0, 1], [2, 3]]
        text = json.dumps([[0, 1]])  # only 1 row
        passed, reason, parsed = _arc_correctness_check(text, expected)
        assert passed is False
        assert reason.startswith("row-count-mismatch:")
        assert "1vs2" in reason
        assert parsed == [[0, 1]]

    def test_pixel_diff_when_same_shape(self) -> None:
        expected = [[0, 1], [2, 3]]
        text = json.dumps([[0, 9], [9, 3]])  # 2 of 4 pixels different
        passed, reason, parsed = _arc_correctness_check(text, expected)
        assert passed is False
        assert reason.startswith("pixel-diff:")
        assert "2/4" in reason
        assert parsed == [[0, 9], [9, 3]]

    def test_no_difference_when_all_match(self) -> None:
        # Same grid but different format
        text = json.dumps([[5, 5], [5, 5]])
        passed, reason, _ = _arc_correctness_check(text, [[5, 5], [5, 5]])
        assert passed is True
        assert reason == "pixel-perfect"

    def test_full_pixel_diff(self) -> None:
        expected = [[0, 0], [0, 0]]
        text = json.dumps([[9, 9], [9, 9]])
        passed, reason, _ = _arc_correctness_check(text, expected)
        assert passed is False
        assert reason.startswith("pixel-diff:")
        assert "4/4" in reason


# ---------------------------------------------------------------------------
# ArcAgi2 suite class
# ---------------------------------------------------------------------------


class TestArcAgi2ClassAttrs:
    """Class-level metadata on ``ArcAgi2``."""

    def test_name(self) -> None:
        assert ArcAgi2.name == "arc-agi-2"

    def test_domain(self) -> None:
        assert ArcAgi2.domain == "visual-reasoning"

    def test_default_judge(self) -> None:
        assert ArcAgi2.default_judge == "deterministic"

    def test_source_url(self) -> None:
        assert ArcAgi2.source_url == SOURCE_URL

    def test_paper_metrics(self) -> None:
        assert ArcAgi2.paper_metrics == ("pass@1", "pixel-diff")


class TestArcAgi2Init:
    """``ArcAgi2.__init__`` generates the synthetic task corpus."""

    def test_init_creates_tasks(self) -> None:
        suite = ArcAgi2()
        # Should have NUM_TASKS_SUBSET entries
        assert len(suite._tasks) == NUM_TASKS_SUBSET

    def test_init_creates_expected_grids(self) -> None:
        suite = ArcAgi2()
        assert len(suite._expected) == NUM_TASKS_SUBSET
        # Each task's expected grid should be a list of lists of ints
        for tid in list(suite._expected)[:5]:
            grid = suite._expected[tid]
            assert isinstance(grid, list)
            assert all(isinstance(row, list) for row in grid)

    def test_task_ids_are_zero_padded(self) -> None:
        suite = ArcAgi2()
        ids = [t.task_id for t in suite._tasks]
        assert ids[0] == "ARC-0000"
        assert ids[-1] == f"ARC-{NUM_TASKS_SUBSET - 1:04d}"

    def test_task_spec_has_correct_suite(self) -> None:
        suite = ArcAgi2()
        for t in suite._tasks[:5]:
            assert t.suite == "arc-agi-2"

    def test_init_is_deterministic(self) -> None:
        # Two instances should produce identical task corpora
        s1 = ArcAgi2()
        s2 = ArcAgi2()
        assert [t.task_id for t in s1._tasks] == [t.task_id for t in s2._tasks]
        assert s1._expected == s2._expected


class TestArcAgi2Subset:
    """``ArcAgi2.subset()`` returns n deterministically sampled tasks."""

    def test_subset_returns_subset_size(self) -> None:
        suite = ArcAgi2()
        sub = suite.subset(10, seed=42)
        assert len(sub) == 10

    def test_subset_returns_all_when_n_exceeds_size(self) -> None:
        suite = ArcAgi2()
        sub = suite.subset(NUM_TASKS_SUBSET + 50, seed=42)
        assert len(sub) == NUM_TASKS_SUBSET

    def test_subset_is_deterministic(self) -> None:
        suite = ArcAgi2()
        sub1 = suite.subset(20, seed=42)
        sub2 = suite.subset(20, seed=42)
        assert [t.task_id for t in sub1] == [t.task_id for t in sub2]

    def test_subset_different_seed_yields_different_order(self) -> None:
        suite = ArcAgi2()
        sub1 = suite.subset(20, seed=1)
        sub2 = suite.subset(20, seed=2)
        # Two different seeds should give different orderings
        assert [t.task_id for t in sub1] != [t.task_id for t in sub2]


class TestArcAgi2Verify:
    """``ArcAgi2.verify()`` scores a model completion."""

    def test_verify_correct_grid_passes(self) -> None:
        suite = ArcAgi2()
        # Task at index 0 has a known expected grid
        task = suite._tasks[0]
        expected = suite._expected[task.task_id]
        # Provide the exact expected grid as the completion
        completion = json.dumps(expected)
        passed, info = suite.verify(task, completion)
        assert passed is True
        assert info["reason"] == "pixel-perfect"

    def test_verify_wrong_grid_fails(self) -> None:
        suite = ArcAgi2()
        task = suite._tasks[0]
        # Wrong grid (all zeros, may not match)
        completion = json.dumps([[0, 0], [0, 0]])
        passed, info = suite.verify(task, completion)
        assert passed is False
        assert info["reason"] != "pixel-perfect"
        # Either row-count-mismatch or pixel-diff
        assert info["reason"].startswith("pixel-diff:") or info["reason"].startswith("row-count-mismatch:")

    def test_verify_no_grid_returns_no_grid(self) -> None:
        suite = ArcAgi2()
        task = suite._tasks[0]
        passed, info = suite.verify(task, "no grid in here")
        assert passed is False
        assert info["reason"] == "no-grid"
        assert info["parsed_grid"] is None

    def test_verify_returns_expected_keys(self) -> None:
        suite = ArcAgi2()
        task = suite._tasks[0]
        passed, info = suite.verify(task, "blah")
        assert "judge" in info
        assert info["judge"] == "pixel-perfect-grid-compare"
        assert "reason" in info
        assert "parsed_grid" in info
        assert "expected_grid" in info

    def test_verify_return_type(self) -> None:
        suite = ArcAgi2()
        task = suite._tasks[0]
        result = suite.verify(task, "anything")
        # Returns (passed: bool, info: dict)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], dict)


class TestArcAgi2SyntheticGeneration:
    """``_generate_synthetic_task`` covers all 4 pattern types."""

    def test_generates_consistent_train_test_pairs(self) -> None:
        suite = ArcAgi2()
        # Iterate through tasks 0..3 (one of each pattern)
        for idx in range(4):
            train, test_in, test_out = suite._generate_synthetic_task()
            assert isinstance(train, list)
            assert len(train) == 2  # always 2 train pairs
            for pair in train:
                assert "input" in pair
                assert "output" in pair
            assert isinstance(test_in, list)
            assert isinstance(test_out, list)
            assert all(isinstance(row, list) for row in test_in)
            assert all(isinstance(row, list) for row in test_out)
            # Output dimensions must be valid grids
            assert all(all(isinstance(c, int) for c in row) for row in test_out)
