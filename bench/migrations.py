"""pheno-harness L14 — migration framework for bench suites.

Lightweight forward + backward migration runner. Reads `migrations/*.json` in
lexicographic order, applies pending ones, and records applied versions in
the `_bench_migrations` table inside the bench results database.

Each migration file is a JSON object with:
    {
        "version":   "0001_initial",
        "up":        "SQL or list of SQL statements to apply",
        "down":      "SQL or list of SQL statements to revert (optional)",
        "note":      "free-form description"
    }

Usage:
    from bench.migrations import apply_migrations, status, rollback

    apply_migrations(conn)              # apply all pending
    status(conn)                        # show what's applied / pending
    rollback(conn, version="0002_seed") # revert a specific version
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
TRACKING_TABLE = "_bench_migrations"


@dataclass(frozen=True)
class Migration:
    version: str
    up_sql: list[str]
    down_sql: list[str]
    note: str
    path: Path

    @classmethod
    def from_file(cls, path: Path) -> Migration:
        data = json.loads(path.read_text(encoding="utf-8"))
        up = data["up"]
        up_sql = up if isinstance(up, list) else [up]
        down = data.get("down", [])
        down_sql = down if isinstance(down, list) else [down]
        return cls(
            version=data["version"],
            up_sql=up_sql,
            down_sql=down_sql,
            note=data.get("note", ""),
            path=path,
        )


def _normalize(stmts: Iterable[str]) -> list[str]:
    """Split a SQL string on `;` boundaries, ignoring empty pieces."""
    out: list[str] = []
    for stmt in stmts:
        for piece in stmt.split(";"):
            piece = piece.strip()
            if piece:
                out.append(piece)
    return out


def ensure_tracking(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
            version   TEXT PRIMARY KEY,
            applied_at INTEGER NOT NULL,
            note      TEXT
        )
        """
    )
    conn.commit()


def discover_migrations() -> list[Migration]:
    if not MIGRATIONS_DIR.exists():
        return []
    out: list[Migration] = []
    for f in sorted(MIGRATIONS_DIR.glob("*.json")):
        try:
            out.append(Migration.from_file(f))
        except (json.JSONDecodeError, KeyError) as exc:
            raise RuntimeError(f"Invalid migration {f}: {exc}") from exc
    return out


def applied_versions(conn: sqlite3.Connection) -> set[str]:
    ensure_tracking(conn)
    rows = conn.execute(f"SELECT version FROM {TRACKING_TABLE}").fetchall()  # nosec B608 — TRACKING_TABLE is a module-level constant, not user input
    return {r[0] for r in rows}


def apply_migrations(conn: sqlite3.Connection) -> list[Migration]:
    """Apply all pending migrations in order. Returns the list applied."""
    ensure_tracking(conn)
    already = applied_versions(conn)
    applied: list[Migration] = []
    for mig in discover_migrations():
        if mig.version in already:
            continue
        for stmt in _normalize(mig.up_sql):
            conn.execute(stmt)
        conn.execute(
            f"INSERT OR REPLACE INTO {TRACKING_TABLE} (version, applied_at, note) VALUES (?, strftime('%s','now'), ?)",  # nosec B608 — TRACKING_TABLE is a module-level constant, not user input
            (mig.version, mig.note),
        )
        conn.commit()
        applied.append(mig)
    return applied


def rollback(conn: sqlite3.Connection, version: str) -> Migration:
    """Revert a single migration by version. Caller is responsible for ordering."""
    ensure_tracking(conn)
    target: Migration | None = None
    for mig in discover_migrations():
        if mig.version == version:
            target = mig
            break
    if target is None:
        raise LookupError(f"unknown migration version: {version}")
    if not target.down_sql:
        raise ValueError(f"migration {version} has no down_sql")
    for stmt in _normalize(target.down_sql):
        conn.execute(stmt)
    conn.execute(f"DELETE FROM {TRACKING_TABLE} WHERE version = ?", (version,))  # nosec B608 — TRACKING_TABLE is a module-level constant, not user input
    conn.commit()
    return target


def status(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """Return [(version, state, note), ...] sorted by version."""
    ensure_tracking(conn)
    already = applied_versions(conn)
    rows = []
    for mig in discover_migrations():
        state = "applied" if mig.version in already else "pending"
        rows.append((mig.version, state, mig.note))
    return rows


__all__ = [
    "Migration",
    "apply_migrations",
    "rollback",
    "status",
    "ensure_tracking",
    "discover_migrations",
    "applied_versions",
]
