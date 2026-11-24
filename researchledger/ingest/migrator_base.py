"""migrator_base.py — shared scaffolding for the 12 *_migrate_to_research.py scripts.

WHY THIS EXISTS
---------------
The four 2026-10 tool-name regressions (JSON STRING vs JSON ARRAY) were all
caused by duplicated per-builder code paths. The migrator side carried the
same shape of duplication: every script had its own copy of the
``guard_write_target`` + ``sqlite3.connect`` + sources-table INSERT. A defect
in any one of them was a defect in twelve files. This module is the
single place those patterns live now.

WHAT IT PROVIDES
----------------
* ``add_common_args(parser, *, db_required, db_default)`` — installs the
  standard ``--db`` / ``--allow-canonical`` pair on an ArgumentParser. The
  help text is identical to the per-migrator original so ``--help`` output
  is unchanged.

* ``guard_and_connect(db_path, allow_canonical, *, timeout=60,
  row_factory=None, pragmas=None)`` — performs the load-bearing
  ``guard_write_target`` + ``sqlite3.connect`` sequence in the exact order
  every migrator used: guard FIRST, then connect. The guard is what stops a
  writer from opening the canonical corpus, so its position is not a style
  choice; it is a safety property. Returns the open connection; the caller
  is responsible for ``close()``.

* ``register_source(conn, *, kind, base_path, byte_size, captured_at,
  schema_version="v1.0", notes="")`` - inserts a row into the ``sources``
  table (guarded by WHERE NOT EXISTS, so one row per ``kind``) and returns
  the row id. The column list and order match the pre-refactor inline
  INSERTs.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
* It does not standardize error messages. They are user-facing and may not
  change.
* It does not force a particular pragma set on the connection. Some
  migrators deliberately leave the journal mode alone; adding
  ``PRAGMA journal_mode = WAL`` to a script that did not have it would
  create ``-wal`` / ``-shm`` sidecar files and change observable behaviour.
  Callers pass ``pragmas=[...]`` only when they want them.
* It does not normalize the ``main()`` signature. Some migrators take
  ``argv``; some read ``sys.argv`` directly. Preserving that is part of
  the contract with the characterization tests.
* It does not unify per-source flags (``--src``, ``--raw-dir``,
  ``--sessions-dir``, ``--since``, ``--only``, ``--dry-run``, ``--session``,
  ``--research``). Those vary by source and are documented per migrator.
"""
from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path

# The corpus guard is shared code: PhenoShared/researchledger/corpus_guard.py
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from researchledger import corpus_guard  # noqa: E402
from researchledger.corpus_guard import guard_write_target  # noqa: E402

#: Default path to the canonical research_ledger corpus. Mirrors
#: ``corpus_guard.CANONICAL`` so the help text references the right file.
CANONICAL_RESEARCH_LEDGER = Path.home() / "Exports" / "analysis" / "research_ledger.sqlite"


def add_common_args(
    parser: argparse.ArgumentParser,
    *,
    db_required: bool = True,
    db_default: Path | None = None,
) -> None:
    """Install ``--db`` and ``--allow-canonical`` on ``parser``.

    ``db_required`` and ``db_default`` reproduce the per-migrator
    originals. Most migrators pass ``db_required=True`` with no default;
    a few (e.g. helioslite) pass ``db_required=False, db_default=CANONICAL_…``.
    Help text is byte-identical to the pre-refactor output for the standard
    cases.
    """
    if db_default is None and not db_required:
        db_default = CANONICAL_RESEARCH_LEDGER
    if db_required:
        db_help = (
            "Path to research_ledger.sqlite to write into "
            "(REQUIRED; no default — see corpus_guard.py)"
        )
    else:
        db_help = (
            "Path to research_ledger.sqlite to write into "
            "(defaults to module DB_PATH; see corpus_guard.py)"
        )
    parser.add_argument("--db", type=Path, required=db_required, default=db_default, help=db_help)
    parser.add_argument(
        "--allow-canonical", action="store_true",
        help="Permit writing the canonical corpus (dangerous).",
    )


def guard_and_connect(
    db_path: str | Path,
    allow_canonical: bool,
    *,
    timeout: int = 60,
    row_factory: type | None = None,
    pragmas: list[str] | None = None,
) -> sqlite3.Connection:
    """Call ``guard_write_target`` then ``sqlite3.connect`` in that order.

    The guard MUST be first. If the guard refuses the path, the connection
    is never opened, so the corpus cannot be silently touched. This is the
    reason the helper exists: a copy-paste of these two lines is a place
    where the order can drift; the helper makes drift impossible.

    ``pragmas`` is an opt-in list like ``["journal_mode = WAL",
    "foreign_keys = ON"]``. Pass it only when the migrator actually used
    those pragmas before the refactor.
    """
    guard_write_target(str(db_path), allow_canonical=allow_canonical)
    conn = sqlite3.connect(str(db_path), timeout=timeout)
    if row_factory is not None:
        conn.row_factory = row_factory
    for pragma in pragmas or ():
        conn.execute(f"PRAGMA {pragma}")
    return conn


def write_with_retry(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple = (),
    *,
    attempts: int = 10,
    base_delay: float = 0.5,
) -> sqlite3.Cursor:
    """Run a write statement, retrying while the corpus is locked.

    Another migrator (or a WAL checkpoint) can hold the corpus write lock,
    and SQLite then raises ``database is locked``. The per-row
    ``except Exception`` handlers in the migrators used to swallow that and
    move on, so a lock collision turned into a zero-row run that still exited
    0 -- which is how a source ends up empty in ``items`` with no error
    recorded anywhere.

    Retry with backoff instead, and let the final failure propagate so the
    caller can count it and fail loudly.
    """
    last: sqlite3.OperationalError | None = None
    for attempt in range(attempts):
        try:
            return conn.execute(sql, params)
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if "locked" not in message and "busy" not in message:
                raise
            last = exc
            time.sleep(base_delay * (attempt + 1))
    if last is not None:
        raise last
    raise sqlite3.OperationalError("write failed")


def register_source(
    conn: sqlite3.Connection,
    *,
    kind: str,
    base_path: str,
    byte_size: int,
    captured_at: str,
    schema_version: str = "v1.0",
    notes: str = "",
) -> int:
    """Insert one row into ``sources`` for this ``kind`` and return its id.

    If a row with this ``kind`` already exists, its id is returned and no
    INSERT happens. Idempotency is enforced with ``WHERE NOT EXISTS`` rather
    than ``INSERT OR IGNORE``: the ``sources`` table has no UNIQUE constraint
    on ``kind``, so ``INSERT OR IGNORE`` would happily insert a duplicate.
    The column list and order match the pre-refactor inline INSERTs used by
    every migrator.
    """
    # The real sources table (per research_ledger_init core.py) has
    # ``id INTEGER PRIMARY KEY`` and a CHECK constraint on ``kind`` but NO
    # UNIQUE constraint on ``kind``. INSERT OR IGNORE on a no-unique column
    # does NOT short-circuit duplicates — it happily inserts a second row.
    # The pre-refactor per-migrator code used a check-then-INSERT pattern for
    # exactly this reason (and the jcode W9 auto-increment dup bug is what
    # made the check-then-INSERT discipline mandatory). We use WHERE NOT
    # EXISTS to reproduce that single-row-per-kind contract.
    conn.execute(
        """
        INSERT INTO sources (
            kind, base_path, captured_at, byte_size, schema_version, notes
        )
        SELECT ?, ?, ?, ?, ?, ?
        WHERE NOT EXISTS (SELECT 1 FROM sources WHERE kind = ?)
        """,
        (kind, base_path, captured_at, byte_size, schema_version, notes, kind),
    )
    row = conn.execute("SELECT id FROM sources WHERE kind = ?", (kind,)).fetchone()
    return row[0]
