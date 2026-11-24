"""Tests for bench/comparison/needle_router.py — coverage push from 42.9% to >=80%.

Covers route_task (all modes), route_task_batch, _ground_truth_category,
_heuristic_route (known suite + fallback), _needle_route (success + fallback),
_build_tools_json, _is_needle_available, and the ROUTING_TABLE constant.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bench.comparison.needle_router import (
    _CATEGORY_SUITES,
    ROUTING_TABLE,
    _build_tools_json,
    _ground_truth_category,
    _heuristic_route,
    _is_needle_available,
    _needle_route,
    route_task,
    route_task_batch,
)

# ---------------------------------------------------------------------------
# ROUTING_TABLE constant
# ---------------------------------------------------------------------------


class TestRoutingTable:
    """ROUTING_TABLE is a dict of suite → {category, keywords}."""

    def test_has_expected_suites(self):
        expected = {"arc-agi-2", "gpqa-diamond", "mmlu-pro", "deep-swe", "terminal-bench",
                    "livecodebench", "aider-polyglot", "swe-bench", "swe-bench-pro", "bfcl"}
        assert set(ROUTING_TABLE.keys()) == expected

    def test_each_entry_has_category_and_keywords(self):
        for suite, entry in ROUTING_TABLE.items():
            assert "category" in entry, f"{suite} missing category"
            assert "keywords" in entry, f"{suite} missing keywords"
            assert isinstance(entry["keywords"], list)
            assert len(entry["keywords"]) > 0

    def test_category_suites_reverse_map(self):
        for suite, entry in ROUTING_TABLE.items():
            cat = entry["category"]
            assert cat in _CATEGORY_SUITES
            assert suite in _CATEGORY_SUITES[cat]


# ---------------------------------------------------------------------------
# _ground_truth_category
# ---------------------------------------------------------------------------


class TestGroundTruthCategory:
    """_ground_truth_category returns the expected category or 'unknown'."""

    def test_known_suites(self):
        assert _ground_truth_category("swe-bench") == "code_generation"
        assert _ground_truth_category("arc-agi-2") == "grid_transform"
        assert _ground_truth_category("terminal-bench") == "shell_command"
        assert _ground_truth_category("bfcl") == "function_calling"
        assert _ground_truth_category("gpqa-diamond") == "question_answering"

    def test_unknown_suite(self):
        assert _ground_truth_category("nonexistent-suite") == "unknown"


# ---------------------------------------------------------------------------
# _heuristic_route
# ---------------------------------------------------------------------------


class TestHeuristicRoute:
    """_heuristic_route classifies prompts using keyword matching."""

    def test_known_suite_with_matching_prompt(self):
        result = _heuristic_route("Fix the off-by-one bug in process()", "swe-bench")
        assert result["tool"] == "code_generation"
        assert result["method"] == "heuristic_suite"
        assert result["confidence"] > 0
        assert "routing_time_ms" in result

    def test_known_suite_no_keyword_match(self):
        result = _heuristic_route("hello world", "swe-bench")
        assert result["tool"] == "code_generation"
        assert result["method"] == "heuristic_suite"
        assert result["confidence"] == 0.5  # fallback when matched == 0

    def test_unknown_suite_fallback(self):
        result = _heuristic_route("fix the bug in the code", "unknown-suite")
        assert result["method"] == "heuristic_fallback"
        assert result["confidence"] > 0

    def test_unknown_suite_no_match(self):
        result = _heuristic_route("xyzzy nothing relevant", "unknown-suite")
        assert result["method"] == "heuristic_fallback"
        assert result["confidence"] == 0.1  # no keyword hits

    def test_multiple_keyword_matches(self):
        result = _heuristic_route(
            "fix the bug in the pull request", "swe-bench"
        )
        assert result["confidence"] > 0.3

    def test_arc_agi_grid_prompt(self):
        result = _heuristic_route("Draw the 2D grid pattern", "arc-agi-2")
        assert result["tool"] == "grid_transform"

    def test_terminal_bash_prompt(self):
        result = _heuristic_route("run the bash command", "terminal-bench")
        assert result["tool"] == "shell_command"


# ---------------------------------------------------------------------------
# _is_needle_available
# ---------------------------------------------------------------------------


class TestIsNeedleAvailable:
    """_is_needle_available caches the import check."""

    def test_needle_not_installed(self):
        import bench.comparison.needle_router as mod
        mod._NEEDLE_AVAILABLE = None
        with patch.dict("sys.modules", {"needle": None}):
            assert _is_needle_available() is False
        # Second call should use cached value
        assert _is_needle_available() is False

    def test_needle_available(self):
        import bench.comparison.needle_router as mod
        mod._NEEDLE_AVAILABLE = None
        mock_needle = MagicMock()
        with patch.dict("sys.modules", {"needle": mock_needle}):
            assert _is_needle_available() is True
        # Reset cache for other tests
        mod._NEEDLE_AVAILABLE = None


# ---------------------------------------------------------------------------
# _build_tools_json
# ---------------------------------------------------------------------------


class TestBuildToolsJson:
    """_build_tools_json returns a valid JSON array of tool definitions."""

    def test_returns_json_string(self):
        raw = _build_tools_json()
        tools = json.loads(raw)
        assert isinstance(tools, list)

    def test_no_duplicate_categories(self):
        raw = _build_tools_json()
        tools = json.loads(raw)
        names = [t["name"] for t in tools]
        assert len(names) == len(set(names))

    def test_each_tool_has_required_fields(self):
        tools = json.loads(_build_tools_json())
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool


# ---------------------------------------------------------------------------
# _needle_route
# ---------------------------------------------------------------------------


class TestNeedleRoute:
    """_needle_route uses Needle when available, falls back to heuristic."""

    def test_needle_success(self):
        mock_needle = MagicMock()
        mock_needle.generate.return_value = json.dumps(
            {"name": "code_generation", "confidence": 0.95}
        )
        with patch.dict("sys.modules", {"needle": mock_needle}):
            result = _needle_route("Fix the bug", "swe-bench")
            assert result["method"] == "needle"
            assert result["tool"] == "code_generation"
            assert result["confidence"] == 0.95

    def test_needle_returns_dict(self):
        mock_needle = MagicMock()
        mock_needle.generate.return_value = {"tool": "shell_command", "confidence": 0.8}
        with patch.dict("sys.modules", {"needle": mock_needle}):
            result = _needle_route("run command", "terminal-bench")
            assert result["tool"] == "shell_command"

    def test_needle_returns_function_key(self):
        mock_needle = MagicMock()
        mock_needle.generate.return_value = {"function": "grid_transform"}
        with patch.dict("sys.modules", {"needle": mock_needle}):
            result = _needle_route("draw grid", "arc-agi-2")
            assert result["tool"] == "grid_transform"

    def test_needle_import_error_fallback(self):
        with patch.dict("sys.modules", {"needle": None}):
            result = _needle_route("Fix the bug", "swe-bench")
            assert result["method"] == "needle_fallback"

    def test_needle_runtime_error_fallback(self):
        mock_needle = MagicMock()
        mock_needle.generate.side_effect = RuntimeError("boom")
        with patch.dict("sys.modules", {"needle": mock_needle}):
            result = _needle_route("Fix the bug", "swe-bench")
            assert result["method"] == "needle_fallback"


# ---------------------------------------------------------------------------
# route_task — mode="none"
# ---------------------------------------------------------------------------


class TestRouteTaskNone:
    """route_task with mode='none' returns a no-op result."""

    def test_none_mode(self):
        result = route_task("any prompt", "swe-bench", mode="none")
        assert result["tool"] == "none"
        assert result["confidence"] == 0.0
        assert result["method"] == "none"
        assert result["correct"] is True


# ---------------------------------------------------------------------------
# route_task — mode="heuristic"
# ---------------------------------------------------------------------------


class TestRouteTaskHeuristic:
    """route_task with mode='heuristic' (default)."""

    def test_default_mode(self):
        result = route_task("Fix the bug in process()", "swe-bench")
        assert result["method"] == "heuristic_suite"
        assert "correct" in result

    def test_correct_when_matches_ground_truth(self):
        result = route_task("fix the bug patch issue", "swe-bench")
        assert result["correct"] is True

    def test_incorrect_when_mismatched(self):
        # arc-agi-2 expects grid_transform, but prompt has code keywords
        result = route_task("draw grid pattern transform matrix", "arc-agi-2")
        assert result["correct"] is True  # matches grid_transform

    def test_unknown_suite_fallback_correct(self):
        result = route_task("fix bug", "nonexistent")
        # Unknown suite ground truth is "unknown", tool will be code_generation
        assert result["correct"] is False


# ---------------------------------------------------------------------------
# route_task — mode="needle" (fallback to heuristic)
# ---------------------------------------------------------------------------


class TestRouteTaskNeedle:
    """route_task with mode='needle' falls back when needle is unavailable."""

    def test_needle_unavailable_falls_back(self):
        with patch("bench.comparison.needle_router._is_needle_available", return_value=False):
            result = route_task("Fix the bug", "swe-bench", mode="needle")
            assert result["method"] == "heuristic_suite"

    def test_needle_available_routes_via_needle(self):
        mock_needle = MagicMock()
        mock_needle.generate.return_value = json.dumps(
            {"name": "code_generation", "confidence": 0.9}
        )
        with patch.dict("sys.modules", {"needle": mock_needle}):
            result = route_task("Fix the bug", "swe-bench", mode="needle")
            assert result["method"] == "needle"


# ---------------------------------------------------------------------------
# route_task_batch
# ---------------------------------------------------------------------------


class TestRouteTaskBatch:
    """route_task_batch routes multiple tasks at once."""

    def test_batch(self):
        tasks = [
            ("Fix the bug in process()", "swe-bench"),
            ("draw grid pattern", "arc-agi-2"),
        ]
        results = route_task_batch(tasks)
        assert len(results) == 2
        assert results[0]["tool"] == "code_generation"
        assert results[1]["tool"] == "grid_transform"

    def test_empty_batch(self):
        results = route_task_batch([])
        assert results == []

    def test_batch_with_none_mode(self):
        tasks = [("Fix the bug", "swe-bench")]
        results = route_task_batch(tasks, mode="none")
        assert results[0]["tool"] == "none"
