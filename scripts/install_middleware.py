#!/usr/bin/env python3
"""Install Pheno middleware hooks into OmniRoute via REST API or direct SQLite."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pheno.paths import OMNIROUTE_DB, OMNIROUTE_URL, PHENO_ROOT

HOOKS: list[dict[str, Any]] = [
    {
        "name": "pheno-context-caps",
        "description": "Enforce role context/output caps; block uncapped cloud giants >32k",
        "priority": 50,
        "scope": {"type": "global"},
        "file": PHENO_ROOT / "middleware" / "pheno-context-caps.js",
    },
    {
        "name": "pheno-routing-logger",
        "description": "Attach routing metadata for RL / routing_decisions pipeline",
        "priority": 60,
        "scope": {"type": "global"},
        "file": PHENO_ROOT / "middleware" / "pheno-routing-logger.js",
    },
]


def install_sqlite(db: Path) -> None:
    conn = sqlite3.connect(db)
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    for h in HOOKS:
        code = h["file"].read_text(encoding="utf-8")
        scope_type = h["scope"]["type"]
        combo_id = h["scope"].get("comboId")
        conn.execute(
            """
            INSERT INTO middleware_hooks (
                name, description, priority, scope_type, combo_id, enabled, code,
                created_at, updated_at, run_count, last_error
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, 0, NULL)
            ON CONFLICT(name) DO UPDATE SET
                description=excluded.description,
                priority=excluded.priority,
                scope_type=excluded.scope_type,
                combo_id=excluded.combo_id,
                enabled=1,
                code=excluded.code,
                updated_at=excluded.updated_at
            """,
            (
                h["name"],
                h["description"],
                h["priority"],
                scope_type,
                combo_id,
                code,
                now,
                now,
            ),
        )
        print(f"SQLite: installed hook {h['name']}")
    conn.commit()
    conn.close()


def install_api(base_url: str) -> bool:
    ok = True
    for h in HOOKS:
        code = h["file"].read_text(encoding="utf-8")
        payload = {
            "name": h["name"],
            "description": h["description"],
            "priority": h["priority"],
            "scope": h["scope"],
            "code": code,
        }
        r = requests.post(
            f"{base_url.rstrip('/')}/api/middleware/hooks", json=payload, timeout=30
        )
        if r.status_code == 409:
            r = requests.put(
                f"{base_url.rstrip('/')}/api/middleware/hooks/{h['name']}",
                json=cast(dict[str, Any], {
                    "code": code,
                    "description": h["description"],
                    "priority": h["priority"],
                    "enabled": True,
                }),
                timeout=30,
            )
        if r.status_code not in (200, 201):
            print(f"API: failed {h['name']}: {r.status_code} {r.text[:200]}")
            ok = False
        else:
            print(f"API: installed hook {h['name']}")
    return ok


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, default=OMNIROUTE_DB)
    p.add_argument("--url", default=OMNIROUTE_URL)
    p.add_argument("--mode", choices=["sqlite", "api", "both"], default="both")
    args = p.parse_args()
    if args.mode in ("sqlite", "both"):
        install_sqlite(args.db)
    if args.mode in ("api", "both"):
        if not install_api(args.url):
            print(
                "API install failed (auth?). SQLite install may still work after OmniRoute restart."
            )


if __name__ == "__main__":
    main()
