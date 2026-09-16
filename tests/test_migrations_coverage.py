"""Comprehensive coverage tests for ``bench.migrations``.

Exercises the migration framework's pure-function helpers
(``_normalize``, ``Migration.from_file``, ``ensure_tracking``,
``discover_migrations``, ``applied_versions``, ``apply_migrations``,
``rollback``, ``status``) plus dataclass behaviour. Tests use an
isolated sqlite3 database and a temporary ``migrations`` directory so
they never touch the project's real migrations or DB.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

import bench.migrations as bench_migrations
from bench.migrations import (
    MIGRATIONS_DIR,
    TRACKING_TABLE,
    Migration,
    _normalize,
    applied_versions,
    apply_migrations,
    discover_migrations,
    ensure_tracking,
    rollback,
    status,
)

# ---------------------------------------------------------------------------
# Local fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_migrations_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide an isolated migrations directory via monkey-patching."""
    monkeypatch.setattr(bench_migrations, "MIGRATIONS_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def connection(tmp_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Open a fresh sqlite3 connection that the test owns."""
    db = tmp_path / "migrations.db"
    conn = sqlite3.connect(str(db))
    yield conn
    conn.close()


def _write_migration(dir_path: Path, name: str, payload: dict[str, Any]) -> Path:
    path = dir_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Migration dataclass + from_file
# ---------------------------------------------------------------------------


class TestMigrationDataclass:
    """Migration dataclass instantiation + from_file parsing."""

    def test_construction_with_required_fields(self) -> None:
        mig = Migration(
            version="0001_x",
            up_sql=["CREATE TABLE foo (x INT)"],
            down_sql=["DROP TABLE foo"],
            note="init",
            path=Path("/tmp/x.json"),
        )
        assert mig.version == "0001_x"
        assert mig.up_sql == ["CREATE TABLE foo (x INT)"]
        assert mig.down_sql == ["DROP TABLE foo"]
        assert mig.note == "init"
        assert mig.path == Path("/tmp/x.json")

    def test_from_file_string_up(self, tmp_path: Path) -> None:
        path = _write_migration(
            tmp_path,
            "0001_init.json",
            {
                "version": "0001_init",
                "up": "CREATE TABLE t(x INT)",
                "down": "DROP TABLE t",
                "note": "single-string-up",
            },
        )
        mig = Migration.from_file(path)
        assert mig.version == "0001_init"
        assert mig.up_sql == ["CREATE TABLE t(x INT)"]
        assert mig.down_sql == ["DROP TABLE t"]
        assert mig.note == "single-string-up"
        assert mig.path == path

    def test_from_file_list_up(self, tmp_path: Path) -> None:
        path = _write_migration(
            tmp_path,
            "0002_seed.json",
            {
                "version": "0002_seed",
                "up": ["CREATE TABLE a(x INT)", "CREATE TABLE b(x INT)"],
                "down": ["DROP TABLE a", "DROP TABLE b"],
                "note": "list-up",
            },
        )
        mig = Migration.from_file(path)
        assert len(mig.up_sql) == 2
        assert mig.up_sql[0] == "CREATE TABLE a(x INT)"

    def test_from_file_missing_down_defaults_to_empty(self, tmp_path: Path) -> None:
        path = _write_migration(
            tmp_path,
            "0003_no_down.json",
            {
                "version": "0003_no_down",
                "up": ["CREATE TABLE c(x INT)"],
                "note": "no-down",
            },
        )
        mig = Migration.from_file(path)
        assert mig.down_sql == []

    def test_from_file_missing_note_defaults_to_empty(self, tmp_path: Path) -> None:
        path = _write_migration(
            tmp_path,
            "0004_no_note.json",
            {
                "version": "0004_no_note",
                "up": "CREATE TABLE d(x INT)",
            },
        )
        mig = Migration.from_file(path)
        assert mig.note == ""

    def test_from_file_single_string_down(self, tmp_path: Path) -> None:
        path = _write_migration(
            tmp_path,
            "0005_strdown.json",
            {
                "version": "0005_strdown",
                "up": "CREATE TABLE e(x INT)",
                "down": "DROP TABLE e",
            },
        )
        mig = Migration.from_file(path)
        assert mig.down_sql == ["DROP TABLE e"]

    def test_from_file_raises_keyerror_for_missing_version(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"up": "CREATE TABLE x(x INT)"}), encoding="utf-8")
        with pytest.raises(KeyError):
            Migration.from_file(path)

    def test_from_file_raises_jsond_error_for_invalid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.json"
        path.write_text("not-json{", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            Migration.from_file(path)

    def test_migration_is_frozen(self, tmp_path: Path) -> None:
        mig = Migration(
            version="v1",
            up_sql=["x"],
            down_sql=["y"],
            note="",
            path=tmp_path / "x.json",
        )
        with pytest.raises(Exception):
            mig.version = "v2"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# _normalize helper
# ---------------------------------------------------------------------------


class TestNormalize:
    """``_normalize`` splits SQL on ';' boundaries."""

    def test_single_statement(self) -> None:
        out = _normalize(["CREATE TABLE a(x INT)"])
        assert out == ["CREATE TABLE a(x INT)"]

    def test_multiple_statements_split_by_semicolon(self) -> None:
        out = _normalize(
            ["CREATE TABLE a(x INT); CREATE TABLE b(x INT); CREATE TABLE c(x INT)"]
        )
        assert out == [
            "CREATE TABLE a(x INT)",
            "CREATE TABLE b(x INT)",
            "CREATE TABLE c(x INT)",
        ]

    def test_whitespace_only_pieces_dropped(self) -> None:
        out = _normalize(["CREATE TABLE a(x INT); ; ; CREATE TABLE b(x INT)"])
        assert out == ["CREATE TABLE a(x INT)", "CREATE TABLE b(x INT)"]

    def test_leading_and_trailing_whitespace_stripped(self) -> None:
        out = _normalize(["   CREATE TABLE a(x INT)   "])
        assert out == ["CREATE TABLE a(x INT)"]

    def test_empty_iterable(self) -> None:
        assert _normalize([]) == []

    def test_statements_separated_by_only_whitespace(self) -> None:
        out = _normalize(["CREATE TABLE a(x INT)"])
        # No semicolon → kept as one statement (no trailing semicolon trimmed)
        assert out == ["CREATE TABLE a(x INT)"]

    def test_multiple_inputs_concatenated(self) -> None:
        out = _normalize(
            [
                "CREATE TABLE a(x INT)",
                "CREATE TABLE b(x INT); CREATE TABLE c(x INT)",
            ]
        )
        assert out == [
            "CREATE TABLE a(x INT)",
            "CREATE TABLE b(x INT)",
            "CREATE TABLE c(x INT)",
        ]


# ---------------------------------------------------------------------------
# discover_migrations
# ---------------------------------------------------------------------------


class TestDiscoverMigrations:
    """``discover_migrations`` walks the MIGRATIONS_DIR for ``*.json``."""

    def test_returns_empty_list_when_dir_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing = tmp_path / "does_not_exist"
        monkeypatch.setattr(bench_migrations, "MIGRATIONS_DIR", missing)
        assert discover_migrations() == []

    def test_returns_empty_list_when_dir_empty(self, fake_migrations_dir: Path) -> None:
        assert discover_migrations() == []

    def test_discovers_json_files_in_lexicographic_order(
        self, fake_migrations_dir: Path
    ) -> None:
        # Write in reverse order; result should still be sorted.
        _write_migration(
            fake_migrations_dir,
            "0003_three.json",
            {"version": "0003_three", "up": "CREATE TABLE c(x INT)", "note": "3"},
        )
        _write_migration(
            fake_migrations_dir,
            "0001_one.json",
            {"version": "0001_one", "up": "CREATE TABLE a(x INT)", "note": "1"},
        )
        _write_migration(
            fake_migrations_dir,
            "0002_two.json",
            {"version": "0002_two", "up": "CREATE TABLE b(x INT)", "note": "2"},
        )
        migs = discover_migrations()
        assert [m.version for m in migs] == ["0001_one", "0002_two", "0003_three"]

    def test_ignores_non_json_files(self, fake_migrations_dir: Path) -> None:
        _write_migration(
            fake_migrations_dir,
            "0001_real.json",
            {"version": "0001_real", "up": "CREATE TABLE a(x INT)"},
        )
        # Files that should be ignored
        (fake_migrations_dir / "README.md").write_text("hello", encoding="utf-8")
        (fake_migrations_dir / "0001_real.txt").write_text("not json", encoding="utf-8")
        migs = discover_migrations()
        assert len(migs) == 1
        assert migs[0].version == "0001_real"

    def test_invalid_migration_raises_runtime_error(
        self, fake_migrations_dir: Path
    ) -> None:
        bad = fake_migrations_dir / "0001_bad.json"
        bad.write_text("not-json{", encoding="utf-8")
        with pytest.raises(RuntimeError, match="Invalid migration"):
            discover_migrations()

    def test_missing_required_key_raises_runtime_error(
        self, fake_migrations_dir: Path
    ) -> None:
        bad = fake_migrations_dir / "0001_bad.json"
        bad.write_text(json.dumps({"note": "missing up and version"}), encoding="utf-8")
        with pytest.raises(RuntimeError, match="Invalid migration"):
            discover_migrations()


# ---------------------------------------------------------------------------
# ensure_tracking + applied_versions
# ---------------------------------------------------------------------------


class TestEnsureTrackingAndAppliedVersions:
    """Tests for ``ensure_tracking`` + ``applied_versions``."""

    def test_ensure_tracking_creates_table(self, connection: sqlite3.Connection) -> None:
        ensure_tracking(connection)
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (TRACKING_TABLE,),
        ).fetchone()
        assert row is not None
        assert row[0] == TRACKING_TABLE

    def test_ensure_tracking_is_idempotent(
        self, connection: sqlite3.Connection
    ) -> None:
        ensure_tracking(connection)
        # Should not raise on a second call.
        ensure_tracking(connection)
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (TRACKING_TABLE,),
        ).fetchone()
        assert row is not None

    def test_applied_versions_returns_empty_when_nothing_applied(
        self, connection: sqlite3.Connection
    ) -> None:
        assert applied_versions(connection) == set()

    def test_applied_versions_returns_seeded_set(
        self, connection: sqlite3.Connection
    ) -> None:
        ensure_tracking(connection)
        connection.execute(
            f"INSERT INTO {TRACKING_TABLE} (version, applied_at, note) VALUES (?, ?, ?)",
            ("0001_seed", 1_700_000_000, "seeded"),
        )
        connection.commit()
        assert applied_versions(connection) == {"0001_seed"}


# ---------------------------------------------------------------------------
# apply_migrations + status
# ---------------------------------------------------------------------------


class TestApplyMigrations:
    """``apply_migrations`` end-to-end with a fake migration directory."""

    def test_apply_all_pending(self, connection: sqlite3.Connection,
                                fake_migrations_dir: Path) -> None:
        _write_migration(
            fake_migrations_dir,
            "0001_init.json",
            {
                "version": "0001_init",
                "up": "CREATE TABLE foo (id INTEGER PRIMARY KEY, name TEXT)",
                "down": "DROP TABLE foo",
                "note": "init-foo",
            },
        )
        applied = apply_migrations(connection)
        assert len(applied) == 1
        assert applied[0].version == "0001_init"
        # Side effect: the table should exist in the DB
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='foo'"
        ).fetchone()
        assert row is not None
        # And the tracking table should have one entry
        assert applied_versions(connection) == {"0001_init"}

    def test_apply_is_idempotent(self, connection: sqlite3.Connection,
                                  fake_migrations_dir: Path) -> None:
        _write_migration(
            fake_migrations_dir,
            "0001_init.json",
            {"version": "0001_init", "up": "CREATE TABLE a(x INT)", "note": "a"},
        )
        first = apply_migrations(connection)
        second = apply_migrations(connection)
        assert len(first) == 1
        assert second == []

    def test_apply_records_note_and_applied_at(
        self, connection: sqlite3.Connection, fake_migrations_dir: Path
    ) -> None:
        _write_migration(
            fake_migrations_dir,
            "0001_init.json",
            {"version": "0001_init", "up": "CREATE TABLE a(x INT)", "note": "the note"},
        )
        apply_migrations(connection)
        row = connection.execute(
            f"SELECT version, note, applied_at FROM {TRACKING_TABLE}"
        ).fetchone()
        assert row is not None
        version, note, applied_at = row
        assert version == "0001_init"
        assert note == "the note"
        assert applied_at > 0  # strftime('%s','now')

    def test_apply_returns_in_sorted_order(
        self, connection: sqlite3.Connection, fake_migrations_dir: Path
    ) -> None:
        _write_migration(
            fake_migrations_dir,
            "0003_three.json",
            {"version": "0003_three", "up": "CREATE TABLE c(x INT)"},
        )
        _write_migration(
            fake_migrations_dir,
            "0001_one.json",
            {"version": "0001_one", "up": "CREATE TABLE a(x INT)"},
        )
        _write_migration(
            fake_migrations_dir,
            "0002_two.json",
            {"version": "0002_two", "up": "CREATE TABLE b(x INT)"},
        )
        applied = apply_migrations(connection)
        assert [m.version for m in applied] == ["0001_one", "0002_two", "0003_three"]

    def test_apply_normalises_semicolon_separated_statements(
        self, connection: sqlite3.Connection, fake_migrations_dir: Path
    ) -> None:
        _write_migration(
            fake_migrations_dir,
            "0001_init.json",
            {
                "version": "0001_init",
                "up": (
                    "CREATE TABLE a(x INT);"
                    " CREATE TABLE b(x INT);"
                    " CREATE TABLE c(x INT)"
                ),
                "note": "multi",
            },
        )
        apply_migrations(connection)
        for t in ("a", "b", "c"):
            row = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (t,),
            ).fetchone()
            assert row is not None

    def test_status_reports_pending_and_applied(
        self, connection: sqlite3.Connection, fake_migrations_dir: Path
    ) -> None:
        _write_migration(
            fake_migrations_dir,
            "0001_init.json",
            {"version": "0001_init", "up": "CREATE TABLE a(x INT)", "note": "first"},
        )
        _write_migration(
            fake_migrations_dir,
            "0002_two.json",
            {"version": "0002_two", "up": "CREATE TABLE b(x INT)", "note": "second"},
        )
        # Mark 0001 as already applied
        ensure_tracking(connection)
        connection.execute(
            f"INSERT INTO {TRACKING_TABLE} (version, applied_at, note) VALUES (?, ?, ?)",
            ("0001_init", 1_700_000_000, "first"),
        )
        connection.commit()

        rows = status(connection)
        # Expect (version, state, note)
        by_version = {r[0]: r for r in rows}
        assert by_version["0001_init"][1] == "applied"
        assert by_version["0002_two"][1] == "pending"
        assert by_version["0001_init"][2] == "first"
        assert by_version["0002_two"][2] == "second"
        # Output is sorted by version
        assert [r[0] for r in rows] == sorted(r[0] for r in rows)


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------


class TestRollback:
    """``rollback`` reverts a single migration by version."""

    def test_rollback_runs_down_and_removes_row(
        self, connection: sqlite3.Connection, fake_migrations_dir: Path
    ) -> None:
        _write_migration(
            fake_migrations_dir,
            "0001_init.json",
            {
                "version": "0001_init",
                "up": "CREATE TABLE foo (id INT)",
                "down": "DROP TABLE foo",
                "note": "init",
            },
        )
        apply_migrations(connection)
        # Sanity: the table exists
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='foo'"
            ).fetchone()
            is not None
        )

        target = rollback(connection, "0001_init")
        assert target.version == "0001_init"
        # After rollback, table should be gone and tracking row removed
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='foo'"
            ).fetchone()
            is None
        )
        assert "0001_init" not in applied_versions(connection)

    def test_rollback_unknown_version_raises_lookup_error(
        self, connection: sqlite3.Connection, fake_migrations_dir: Path
    ) -> None:
        with pytest.raises(LookupError, match="unknown migration version"):
            rollback(connection, "9999_missing")

    def test_rollback_no_down_sql_raises_value_error(
        self, connection: sqlite3.Connection, fake_migrations_dir: Path
    ) -> None:
        _write_migration(
            fake_migrations_dir,
            "0001_no_down.json",
            {"version": "0001_no_down", "up": "CREATE TABLE x(x INT)", "note": "nd"},
        )
        with pytest.raises(ValueError, match="no down_sql"):
            rollback(connection, "0001_no_down")

    def test_rollback_returns_target_migration(
        self, connection: sqlite3.Connection, fake_migrations_dir: Path
    ) -> None:
        _write_migration(
            fake_migrations_dir,
            "0001_init.json",
            {
                "version": "0001_init",
                "up": "CREATE TABLE a(x INT)",
                "down": "DROP TABLE a",
                "note": "first",
            },
        )
        apply_migrations(connection)
        target = rollback(connection, "0001_init")
        assert isinstance(target, Migration)
        assert target.version == "0001_init"
        assert target.down_sql == ["DROP TABLE a"]
        assert target.note == "first"


# ---------------------------------------------------------------------------
# module-level constants
# ---------------------------------------------------------------------------


class TestModuleConstants:
    """The TRACKING_TABLE constant is non-empty and stable."""

    def test_tracking_table_is_non_empty_string(self) -> None:
        assert isinstance(TRACKING_TABLE, str)
        assert len(TRACKING_TABLE) > 0

    def test_migrations_dir_is_path(self) -> None:
        assert isinstance(MIGRATIONS_DIR, Path)


# ---------------------------------------------------------------------------
# End-to-end: apply + status + rollback + re-apply
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """Full lifecycle: apply → status → rollback → re-apply."""

    def test_full_lifecycle(self, connection: sqlite3.Connection,
                             fake_migrations_dir: Path) -> None:
        _write_migration(
            fake_migrations_dir,
            "0001_init.json",
            {
                "version": "0001_init",
                "up": "CREATE TABLE t1 (id INTEGER)",
                "down": "DROP TABLE t1",
                "note": "first",
            },
        )
        _write_migration(
            fake_migrations_dir,
            "0002_seed.json",
            {
                "version": "0002_seed",
                "up": "CREATE TABLE t2 (id INTEGER)",
                "down": "DROP TABLE t2",
                "note": "second",
            },
        )

        # Apply both
        applied = apply_migrations(connection)
        assert {m.version for m in applied} == {"0001_init", "0002_seed"}
        # Both tables exist
        for t in ("t1", "t2"):
            assert (
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (t,),
                ).fetchone()
                is not None
            )

        # Status reflects everything applied
        states = {r[0]: r[1] for r in status(connection)}
        assert states == {"0001_init": "applied", "0002_seed": "applied"}

        # Re-apply: nothing pending
        assert apply_migrations(connection) == []

        # Rollback one
        rollback(connection, "0002_seed")
        assert "0002_seed" not in applied_versions(connection)
        assert "0001_init" in applied_versions(connection)
        # t2 should be gone, t1 still present
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='t2'"
            ).fetchone()
            is None
        )
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='t1'"
            ).fetchone()
            is not None
        )

        # Re-applying now picks up the rolled-back migration again
        reapplied = apply_migrations(connection)
        assert [m.version for m in reapplied] == ["0002_seed"]
        assert "0002_seed" in applied_versions(connection)
