"""Tests for pheno-prompt-test assertions and helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from phenotype_py_extras.prompt_test import (
    LLMResponse,
    PromptCase,
    assert_in_text,
    assert_matches_pattern,
    assert_json_valid,
    compute_similarity,
    find_prompt_cases,
    register_case,
)


def test_assert_in_text_pass():
    assert_in_text("hello world", ["hello", "world"])


def test_assert_in_text_fail():
    with pytest.raises(AssertionError):
        assert_in_text("hello world", ["hello", "missing"])


def test_assert_matches_pattern_pass():
    assert_matches_pattern("user-12345", r"^user-\d+$")


def test_assert_matches_pattern_fail():
    with pytest.raises(AssertionError):
        assert_matches_pattern("user-abc", r"^user-\d+$")


def test_assert_json_valid_pass():
    assert_json_valid('{"a": 1, "b": [1, 2]}')


def test_assert_json_valid_fail():
    with pytest.raises(AssertionError):
        assert_json_valid('{"a": 1, b: 2}')


def test_compute_similarity_identical():
    s = compute_similarity("hello world", "hello world")
    assert s == 1.0


def test_compute_similarity_disjoint():
    s = compute_similarity("foo", "bar")
    assert s == 0.0


def test_compute_similarity_overlap():
    s = compute_similarity("the quick brown fox", "the slow brown dog")
    assert 0.30 <= s <= 0.36


def test_find_prompt_cases(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "case_a.prompt").write_text("name: a\nprompt: |\n  hello\n")
    (prompts_dir / "case_b.prompt").write_text("name: b\nprompt: |\n  world\n")
    (prompts_dir / "readme.txt").write_text("ignore me")

    cases = find_prompt_cases(prompts_dir)
    assert len(cases) == 2
    assert {c.name for c in cases} == {"a", "b"}


def test_prompt_case_dataclass():
    case = PromptCase(name="x", prompt="hi", expected="hi", min_similarity=0.9)
    assert case.name == "x"
    assert case.prompt == "hi"
    assert case.min_similarity == 0.9


def test_register_case():
    case = PromptCase(name="y", prompt="ping", expected="pong")
    register_case(case)
