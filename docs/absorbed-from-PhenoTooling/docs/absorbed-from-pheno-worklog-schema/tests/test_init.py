"""Tests for pheno-worklog-schema init_worklog entrypoint (V6 PR-6)."""

from __future__ import annotations

from pathlib import Path

import pheno_worklog_schema as m


def test_init_worklog_creates_file(tmp_path: Path) -> None:
    result = m.init_worklog(tmp_path)
    assert result["ok"] is True, result
    wl = Path(result["worklog"])
    assert wl.exists()
    text = wl.read_text(encoding="utf-8")
    assert text.startswith("# WORKLOG")
    # All canonical column names are present in the header row.
    for col in m.COLUMN_NAMES:
        assert col in text


def test_init_worklog_idempotent(tmp_path: Path) -> None:
    m.init_worklog(tmp_path)
    result = m.init_worklog(tmp_path)
    assert result["ok"] is True
    assert result["already_present"] is True


def test_init_worklog_missing_dir(tmp_path: Path) -> None:
    result = m.init_worklog(tmp_path / "nope")
    assert result["ok"] is False
