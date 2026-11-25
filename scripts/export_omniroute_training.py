#!/usr/bin/env python3
"""Export OmniRoute call_logs + compression_analytics to training JSONL."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import OMNIROUTE_DB, TRAINING_DIR


def _row_to_training(row: dict[str, Any], kind: str) -> dict[str, Any]:
    base = {
        "kind": kind,
        "exported_at": datetime.now(UTC).isoformat(),
    }
    base.update(row)
    return base


def export_call_logs(conn: sqlite3.Connection, out: Path, since: str | None) -> int:
    q = """
        SELECT id, timestamp, method, path, status, model, requested_model,
               provider, combo_name, duration, tokens_in, tokens_out,
               tokens_cache_read, tokens_cache_creation, tokens_reasoning,
               tokens_compressed, error_summary, request_summary
        FROM call_logs
    """
    params: list = []
    if since:
        q += " WHERE timestamp >= ?"
        params.append(since)
    q += " ORDER BY timestamp ASC"
    cur = conn.execute(q, params)
    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()
    n = 0
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            rec = dict(zip(cols, row))
            rec["avg_context_class"] = (
                "giant"
                if (rec.get("tokens_in") or 0) >= 32768
                else "large"
                if (rec.get("tokens_in") or 0) >= 8192
                else "normal"
            )
            f.write(
                json.dumps(_row_to_training(rec, "call_log"), ensure_ascii=False) + "\n"
            )
            n += 1
    return n


def export_compression(conn: sqlite3.Connection, out: Path, since: str | None) -> int:
    q = """
        SELECT id, timestamp, combo_id, provider, mode, original_tokens,
               compressed_tokens, tokens_saved, duration_ms, request_id,
               actual_prompt_tokens, actual_completion_tokens, engine
        FROM compression_analytics
    """
    params: list = []
    if since:
        q += " WHERE timestamp >= ?"
        params.append(since)
    q += " ORDER BY timestamp ASC"
    cur = conn.execute(q, params)
    cols = [c[0] for c in cur.description]
    n = 0
    with out.open("w", encoding="utf-8") as f:
        for row in cur:
            rec = dict(zip(cols, row))
            f.write(
                json.dumps(_row_to_training(rec, "compression"), ensure_ascii=False)
                + "\n"
            )
            n += 1
    return n


def export_summary(conn: sqlite3.Connection, out: Path) -> None:
    stats = conn.execute("""
        SELECT COUNT(*) AS calls,
               AVG(tokens_in) AS avg_in,
               AVG(tokens_out) AS avg_out,
               SUM(tokens_in) AS total_in,
               SUM(tokens_out) AS total_out,
               SUM(CASE WHEN tokens_in >= 32768 THEN 1 ELSE 0 END) AS giant_calls
        FROM call_logs
    """).fetchone()
    comp = conn.execute("""
        SELECT SUM(tokens_saved) AS total_saved,
               COUNT(*) AS comp_events
        FROM compression_analytics
    """).fetchone()
    summary = {
        "exported_at": datetime.now(UTC).isoformat(),
        "call_logs": {
            "calls": stats[0],
            "avg_input_tokens": round(stats[1] or 0, 1),
            "avg_output_tokens": round(stats[2] or 0, 1),
            "total_input_tokens": stats[3],
            "total_output_tokens": stats[4],
            "giant_input_calls_32k_plus": stats[5],
            "giant_pct": round(100 * (stats[5] or 0) / max(stats[0] or 1, 1), 2),
        },
        "compression_analytics": {
            "events": comp[1],
            "total_tokens_saved": comp[0],
        },
    }
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Export OmniRoute analytics to training JSONL"
    )
    p.add_argument("--db", type=Path, default=OMNIROUTE_DB)
    p.add_argument("--out-dir", type=Path, default=TRAINING_DIR)
    p.add_argument("--since", default=None, help="ISO timestamp filter")
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    n_calls = export_call_logs(conn, args.out_dir / f"call_logs_{ts}.jsonl", args.since)
    n_comp = export_compression(
        conn, args.out_dir / f"compression_{ts}.jsonl", args.since
    )
    export_summary(conn, args.out_dir / "analytics_summary.json")
    conn.close()
    print(f"Exported {n_calls} call_logs, {n_comp} compression rows -> {args.out_dir}")


if __name__ == "__main__":
    main()
