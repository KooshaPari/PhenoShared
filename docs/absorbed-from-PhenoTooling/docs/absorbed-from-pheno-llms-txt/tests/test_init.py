"""Tests for pheno-llms-txt init_llms entrypoint (V6 PR-3)."""

from __future__ import annotations

from pathlib import Path

import pheno_llms_txt as m


def test_init_llms_writes_file(tmp_path: Path) -> None:
    result = m.init_llms(tmp_path)
    assert result["ok"] is True, result
    out = Path(result["llms_txt"])
    assert out.exists()
    assert out.parent == tmp_path


def test_init_llms_missing_dir(tmp_path: Path) -> None:
    result = m.init_llms(tmp_path / "does-not-exist")
    assert result["ok"] is False
    assert "does not exist" in result["error"]


def test_init_llms_idempotent(tmp_path: Path) -> None:
    m.init_llms(tmp_path)
    result = m.init_llms(tmp_path)
    assert result["ok"] is True
    assert Path(result["llms_txt"]).exists()
