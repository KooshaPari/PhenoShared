#!/usr/bin/env python3
"""Quick OmniRoute DB schema inspector."""

import sqlite3
from pathlib import Path

DB = Path.home() / ".omniroute" / "storage.sqlite"


def main() -> None:
    conn = sqlite3.connect(DB)
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]
    print("tables:", len(tables))
    for t in (
        "call_logs",
        "compression_analytics",
        "routing_decisions",
        "middleware_hooks",
    ):
        if t in tables:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})").fetchall()]
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # nosec B608 — local sqlite introspection, no user input, reviewed false positive
            print(f"{t}: {n} rows, cols={cols}")
    conn.close()


if __name__ == "__main__":
    main()
