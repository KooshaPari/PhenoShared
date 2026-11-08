"""Tests for pheno-prompt-test init_prompt_test entrypoint (V6 PR-4)."""

from __future__ import annotations

from pathlib import Path

import pheno_prompt_test as m


def test_init_prompt_test_creates_layout(tmp_path: Path) -> None:
    result = m.init_prompt_test(tmp_path)
    assert result["ok"] is True, result
    prompts = Path(result["prompts_dir"])
    assert prompts.exists()
    assert prompts.is_dir()
    assert (prompts / "README.md").exists()


def test_init_prompt_test_idempotent(tmp_path: Path) -> None:
    m.init_prompt_test(tmp_path)
    result = m.init_prompt_test(tmp_path)
    assert result["ok"] is True
    # README written only once (idempotent).
    assert (Path(result["prompts_dir"]) / "README.md").exists()


def test_init_prompt_test_missing_dir(tmp_path: Path) -> None:
    result = m.init_prompt_test(tmp_path / "nope")
    assert result["ok"] is False
