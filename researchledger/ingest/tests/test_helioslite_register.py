"""helioslite register-only characterization.

helioslite is a fork installed but unused on this workstation; the migrator
intentionally performs a no-op except for a `sources` row insert.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path

import pytest

ANALYSIS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ANALYSIS))


@pytest.fixture
def helioslite_migrator(tmp_path, monkeypatch):
    """Patch DEFAULT constants so the script touches tmp_path only.

    helioslite's main() takes no argv and uses module-level DB_PATH /
    HELIOSLITE_DIR constants. Put both at sibling paths under tmp_path so
    they don't collide with the research_db fixture path.
    """
    sys.path.insert(0, str(ANALYSIS))
    mod = importlib.import_module("helioslite_migrate_to_research")
    hl_db = tmp_path / "helioslite_research_ledger.sqlite"
    hl_dir = tmp_path / "helioslite_home"
    hl_dir.mkdir()
    monkeypatch.setattr(mod, "DB_PATH", hl_db)
    monkeypatch.setattr(mod, "HELIOSLITE_DIR", hl_dir)
    return mod


def test_helioslite_registers_source_row_no_migrated_tables(
    tmp_path, research_db, helioslite_migrator
):
    """Run the script against a real tmp research_ledger.

    Initialize the DB at helioslite's path (a sibling of research_db) so
    both fixtures coexist under tmp_path without colliding.
    """
    from research_ledger_init import init as init_research_ledger
    init_research_ledger(helioslite_migrator.DB_PATH)

    rc = helioslite_migrator.main()
    # helioslite's main() doesn't explicitly return; rc is None on success.

    conn = sqlite3.connect(helioslite_migrator.DB_PATH)
    try:
        # Source row registered with kind=helioslite.
        row = conn.execute(
            "SELECT kind, base_path FROM sources WHERE kind='helioslite'"
        ).fetchone()
        assert row is not None, "helioslite source row not registered"
        assert row[0] == "helioslite"
        assert row[1] is not None

        # No migrated_helioslite_* tables — helioslite is a no-op.
        names = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert not any(n.startswith("migrated_helioslite") for n in names), \
            f"unexpected migrated_helioslite tables: {names}"

        # No items or attachments touched.
        n_items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        n_att = conn.execute("SELECT COUNT(*) FROM attachments").fetchone()[0]
        assert n_items == 0 and n_att == 0
    finally:
        conn.close()