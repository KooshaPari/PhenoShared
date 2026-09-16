#!/usr/bin/env python3
"""Backfill and sync routing_decisions from call_logs (OmniRoute v3.8.18 gap)."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import OMNIROUTE_DB, STATE_DIR

STATE_FILE = STATE_DIR / "routing_sync.json"


def _infer_task_type(row: sqlite3.Row) -> str:
    path = (row["path"] or "").lower()
    model = (row["model"] or row["requested_model"] or "").lower()
    if "embed" in path:
        return "embed"
    if "codex" in model or "codex" in (row["provider"] or "").lower():
        return "code"
    if "opus" in model or "claude" in (row["provider"] or "").lower():
        return "reasoning"
    if (row["tokens_in"] or 0) > 32768:
        return "long_context"
    return "chat"


def _call_log_to_decision(row: sqlite3.Row) -> tuple:
    factors = {
        "tokens_in": row["tokens_in"],
        "tokens_out": row["tokens_out"],
        "tokens_cache_read": row["tokens_cache_read"],
        "combo_name": row["combo_name"],
        "status": row["status"],
        "pheno_source": "call_logs_sync",
    }
    success = 1 if (row["status"] or 0) < 400 else 0
    return (
        str(row["id"]),
        _infer_task_type(row),
        row["combo_name"] or "Main",
        row["provider"],
        row["model"] or row["requested_model"],
        None,
        json.dumps(factors),
        0,
        success,
        int(row["duration"] or 0),
        None,
        "pheno_sync",
        row["timestamp"],
    )


INSERT_SQL = """
INSERT OR IGNORE INTO routing_decisions (
    request_id, task_type, combo_id, provider_selected, model_selected,
    score, factors_json, fallbacks_triggered, success, latency_ms, cost,
    source, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def backfill(conn: sqlite3.Connection, batch: int = 500) -> int:
    existing = {
        r[0]
        for r in conn.execute(
            "SELECT request_id FROM routing_decisions WHERE source = 'pheno_sync'"
        )
    }
    cur = conn.execute("""
        SELECT id, timestamp, path, status, model, requested_model, provider,
               combo_name, duration, tokens_in, tokens_out, tokens_cache_read
        FROM call_logs ORDER BY id ASC
    """)
    n = 0
    batch_rows = []
    for row in cur:
        rid = str(row["id"])
        if rid in existing:
            continue
        batch_rows.append(_call_log_to_decision(row))
        if len(batch_rows) >= batch:
            conn.executemany(INSERT_SQL, batch_rows)
            conn.commit()
            n += len(batch_rows)
            batch_rows = []
    if batch_rows:
        conn.executemany(INSERT_SQL, batch_rows)
        conn.commit()
        n += len(batch_rows)
    return n


def sync_new(conn: sqlite3.Connection, last_id: int) -> tuple[int, int]:
    cur = conn.execute(
        """
        SELECT id, timestamp, path, status, model, requested_model, provider,
               combo_name, duration, tokens_in, tokens_out, tokens_cache_read
        FROM call_logs WHERE id > ? ORDER BY id ASC
    """,
        (last_id,),
    )
    rows = list(cur)
    if not rows:
        return 0, last_id
    conn.executemany(INSERT_SQL, [_call_log_to_decision(r) for r in rows])
    conn.commit()
    return len(rows), rows[-1]["id"]


def load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"last_call_log_id": 0}


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(UTC).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, default=OMNIROUTE_DB)
    p.add_argument("--backfill", action="store_true", help="Backfill all call_logs")
    p.add_argument("--watch", action="store_true", help="Poll for new call_logs")
    p.add_argument("--interval", type=float, default=30.0)
    args = p.parse_args()
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    state = load_state()
    if args.backfill:
        n = backfill(conn)
        max_id = conn.execute("SELECT MAX(id) FROM call_logs").fetchone()[0] or 0
        state["last_call_log_id"] = max_id
        save_state(state)
        print(f"Backfilled {n} routing_decisions")
    if args.watch:
        print(f"Watching call_logs from id>{state.get('last_call_log_id', 0)}")
        while True:
            n, last = sync_new(conn, state.get("last_call_log_id", 0))
            if n:
                state["last_call_log_id"] = last
                save_state(state)
                print(f"Synced {n} new decisions (last_id={last})")
            time.sleep(args.interval)
    elif not args.backfill:
        n, last = sync_new(conn, state.get("last_call_log_id", 0))
        if n:
            state["last_call_log_id"] = last
            save_state(state)
        print(f"Incremental sync: {n} rows")
    conn.close()


if __name__ == "__main__":
    main()
