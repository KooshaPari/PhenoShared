"""Research-ledger corpus tooling.

The research ledger is a single SQLite corpus. Many ingest pipelines write to it,
and the two ways it has been damaged were both silent:

1. **Path drift** (2026-11-10): `CANONICAL` pointed at a path that no longer
   existed, so the write guard was comparing every target against a dead
   address and protecting nothing.
2. **Symlink swap** (2026-10-15): a symlink planted on the canonical path
   redirected writes away from the real file.

`corpus_guard` is the one gate every writer calls before opening the corpus.
It is deliberately a hard stop (`SystemExit`), not a warning.

Public API lives in :mod:`researchledger.corpus_guard`.
"""

from .corpus_guard import (
    ALLOW_ENV,
    ALLOW_FLAG,
    CANONICAL,
    CANONICAL_ENV,
    RETIRED_CANONICALS,
    SEALED_ARCHIVE_DIR,
    SEALED_BACKUP,
    SEALED_ENV,
    assert_corpus_sane,
    guard_write_target,
)

__all__ = [
    "ALLOW_ENV",
    "ALLOW_FLAG",
    "CANONICAL",
    "CANONICAL_ENV",
    "RETIRED_CANONICALS",
    "SEALED_ARCHIVE_DIR",
    "SEALED_BACKUP",
    "SEALED_ENV",
    "assert_corpus_sane",
    "guard_write_target",
]
