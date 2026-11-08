"""Tests for pheno-worklog-schema."""

import json
import sys
import warnings
from datetime import date
from pathlib import Path

import pytest

from pheno_worklog_schema import (
    WorklogEntry,
    validate_row,
    parse_worklog,
    to_jsonl,
    stats,
    add_entry,
    EXPECTED_COLUMNS,
    COLUMN_NAMES,
)

PYTHON_AVAILABLE = sys.version_info >= (3, 10)
pytestmark = pytest.mark.skipif(not PYTHON_AVAILABLE, reason="requires Python 3.10+")


def test_worklog_entry_valid():
    e = WorklogEntry(
        task_id="V4-1.1.1",
        date="2026-06-11",
        repo="thegent",
        category="L1-Stabilize",
        title="Merge L1_TRIAGE",
        commit_sha="8a5611420",
        pr_number=1099,
        status="merged",
        author="koosha",
        notes="First L1 deliverable",
    )
    assert e.task_id == "V4-1.1.1"
    assert e.commit_sha == "8a5611420"


def test_worklog_entry_optional_fields():
    e = WorklogEntry(task_id="X", date="2026-06-11", title="x")
    assert e.commit_sha is None
    assert e.pr_number is None
    assert e.notes == ""


def test_validate_row_valid():
    cols = [
        "V4-1.1.1", "2026-06-11", "thegent", "L1-Stabilize",
        "Merge L1_TRIAGE", "8a5611420", "1099", "merged", "koosha", "First L1",
    ]
    assert validate_row(cols) == []


def test_validate_row_wrong_count():
    cols = ["V4-1.1.1", "2026-06-11"]
    errors = validate_row(cols)
    assert any("10" in e for e in errors)


def test_validate_row_bad_date():
    cols = [
        "V4-1.1.1", "not-a-date", "thegent", "L1",
        "title", "sha", "1", "merged", "koosha", "note",
    ]
    errors = validate_row(cols)
    assert any("date" in e.lower() for e in errors)


def test_validate_row_bad_status():
    cols = [
        "V4-1.1.1", "2026-06-11", "thegent", "L1",
        "title", "sha", "1", "BOGUS", "koosha", "note",
    ]
    errors = validate_row(cols)
    assert any("status" in e.lower() for e in errors)


def test_parse_worklog_table():
    md = """# WORKLOG

Some intro text.

| task_id | date | repo | category | title | commit_sha | pr_number | status | author | notes |
|---------|------|------|----------|-------|------------|-----------|--------|--------|-------|
| V4-1.1.1 | 2026-06-11 | thegent | L1 | Merge L1_TRIAGE | 8a5611420 | 1099 | merged | koosha | First L1 |
| V4-1.1.2 | 2026-06-11 | thegent | L1 | WORKLOG entry | 3730df65b | 1100 | merged | koosha | Second L1 |

Trailing text.
"""
    entries = parse_worklog(md)
    assert len(entries) == 2
    assert entries[0].task_id == "V4-1.1.1"
    assert entries[1].commit_sha == "3730df65b"


def test_parse_worklog_unspaced_v2_1_header():
    """Regression: parse_worklog must accept the no-space header style.

    The migration script ``migrate_v2_to_v2_1.py`` produces both spaced
    (``| task_id | ...``) and unspaced (``|task_id|...``) header styles
    depending on its ``sep_with_spaces`` toggle. The previous literal
    string check ``"| task_id" in text.lower()`` was too strict and
    rejected the unspaced variant, causing the substrate's own
    WORKLOG.md (which the migration script writes without spaces) to
    parse to 0 entries. This test pins the unspaced variant down so
    the bug never recurs.
    """
    md = """|task_id|date|repo|category|title|commit_sha|pr_number|status|author|device|notes|
|---|---|---|---|---|---|---|---|---|---|---|
|V4-1.1.1|2026-06-11|thegent|L1|Merge L1_TRIAGE|8a5611420|1099|merged|koosha|macbook|First L1|
|V4-1.1.2|2026-06-11|thegent|L1|WORKLOG entry|3730df65b|1100|merged|koosha|macbook|Second L1|
"""
    entries = parse_worklog(md)
    assert len(entries) == 2
    assert entries[0].task_id == "V4-1.1.1"
    assert entries[0].device == "macbook"
    assert entries[1].commit_sha == "3730df65b"
    assert entries[1].device == "macbook"


def test_parse_worklog_unspaced_v2_0_legacy_header():
    """Regression: parse_worklog accepts the no-space v2.0 (10-col) header too.

    Mirrors test_parse_worklog_unspaced_v2_1_header for the 10-col
    legacy form (no `device` column). After parsing, ``device`` is "".
    """
    md = """|task_id|date|repo|category|title|commit_sha|pr_number|status|author|notes|
|---|---|---|---|---|---|---|---|---|---|
|V4-1.1.1|2026-06-11|thegent|L1|First L1|8a5611420|1099|merged|koosha|First L1|
"""
    entries = parse_worklog(md)
    assert len(entries) == 1
    assert entries[0].task_id == "V4-1.1.1"
    assert entries[0].device == ""  # v2.0 legacy → empty device


def test_parse_worklog_v20_deprecation_warning():
    """Ensure a DeprecationWarning is emitted when parsing v2.0 (10-col) format.

    The v2.0 format lacks the ``device`` column required by v2.1.
    Deprecation deadline: 2026-06-22 per ADR-025.
    """
    md = """|task_id|date|repo|category|title|commit_sha|pr_number|status|author|notes|
|---|---|---|---|---|---|---|---|---|---|
|V4-1.1.1|2026-06-11|thegent|L1|First L1|8a5611420|1099|merged|koosha|First L1|
"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        entries = parse_worklog(md)
        assert len(entries) == 1
        # Should have at least one DeprecationWarning about v2.0
        deprecations = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecations) >= 1, (
            f"Expected at least one DeprecationWarning for v2.0 format, "
            f"got {len(deprecations)} warnings: {[str(x.message) for x in w]}"
        )
        assert "v2.0" in str(deprecations[0].message).lower()


def test_parse_worklog_empty():
    assert parse_worklog("# Just a header") == []


def test_to_jsonl_roundtrip():
    e = WorklogEntry(
        task_id="V4-1.1.1",
        date="2026-06-11",
        repo="thegent",
        category="L1",
        title="test",
        commit_sha="abc",
        status="merged",
    )
    line = to_jsonl([e])[0]
    parsed = json.loads(line)
    assert parsed["task_id"] == "V4-1.1.1"
    assert parsed["commit_sha"] == "abc"


def test_stats_empty():
    s = stats([])
    assert s["total"] == 0
    assert s["by_status"] == {}
    assert s["by_repo"] == {}


def test_stats_with_entries():
    entries = [
        WorklogEntry(task_id="A", date="2026-06-11", repo="r1", category="L1", title="x", status="merged"),
        WorklogEntry(task_id="B", date="2026-06-11", repo="r1", category="L1", title="y", status="merged"),
        WorklogEntry(task_id="C", date="2026-06-12", repo="r2", category="L2", title="z", status="open"),
    ]
    s = stats(entries)
    assert s["total"] == 3
    assert s["by_status"]["merged"] == 2
    assert s["by_status"]["open"] == 1
    assert s["by_repo"]["r1"] == 2
    assert s["by_repo"]["r2"] == 1


def test_add_entry_to_existing(tmp_path):
    md_file = tmp_path / "WORKLOG.md"
    md_file.write_text(
        "# WORKLOG\n\n"
        "| task_id | date | repo | category | title | commit_sha | pr_number | status | author | notes |\n"
        "|---------|------|------|----------|-------|------------|-----------|--------|--------|-------|\n"
        "| A | 2026-06-11 | r | L1 | first | sha1 | 1 | merged | k | n |\n"
    )
    new_entry = WorklogEntry(
        task_id="B", date="2026-06-11", repo="r",
        category="L1", title="second", commit_sha="sha2",
        status="merged",
    )
    updated = add_entry(md_file, new_entry)
    assert "first" in updated
    assert "second" in updated
    # Count table rows
    assert updated.count("| A |") == 1
    assert updated.count("| B |") == 1


def test_column_definitions_consistent():
    """EXPECTED_COLUMNS and COLUMN_NAMES must agree."""
    assert len(EXPECTED_COLUMNS) == len(COLUMN_NAMES)
    assert set(EXPECTED_COLUMNS) == set(COLUMN_NAMES)


def test_self_worklog_validates():
    """The repo's own WORKLOG.md should validate against the schema.

    Pins down two invariants:

    1. ``parse_worklog(WORKLOG.md)`` must yield at least one entry.
       A previous bug — the parser's literal-string format check
       ``if "| task_id" in text.lower()`` — silently returned 0
       entries for the substrate's own no-space WORKLOG.md. The test
       loop body never executed, the assertion never fired, and the
       test passed vacuously. This guard catches that bug class.

    2. Every parsed entry must validate cleanly via ``validate_row``.
       A 10-col v2.0 row is allowed (per ADR-025 backward-compat) and
       is padded with an empty ``device`` cell.
    """
    own = Path(__file__).resolve().parent.parent / "WORKLOG.md"
    if own.exists():
        text = own.read_text()
        entries = parse_worklog(text)
        assert len(entries) > 0, (
            f"WORKLOG.md parsed to 0 entries — the v2.1 parser likely "
            f"rejected the header style. Inspect the header row and "
            f"the parser's _is_v2_header_line() helper."
        )
        for e in entries:
            # Normalize date to ISO string (V2 row validator expects str)
            date_str = e.date if isinstance(e.date, str) else e.date.isoformat()
            row = [
                e.task_id, date_str, e.repo, e.category, e.title,
                e.commit_sha or "", str(e.pr_number) if e.pr_number else "",
                e.status, e.author, e.notes,
            ]
            errors = validate_row(row)
            assert errors == [], f"row {e.task_id} failed: {errors}"
