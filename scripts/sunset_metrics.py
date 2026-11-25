#!/usr/bin/env python3
"""Compute local/cloud mix from call_logs + routing_decisions; append sunset metrics."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import CONFIG_DIR, OMNIROUTE_DB, TRAINING_DIR

CLOUD_TIERS = CONFIG_DIR / "cloud_tiers.yaml"
DEFAULT_OUT = TRAINING_DIR / "sunset_metrics.jsonl"

BUCKETS = ("local", "minimax", "kimi", "claude", "openai", "other")

LOCAL_RE = re.compile(
    r"qwen3?\.5-4b|qwen|granite|zaya|pheno-dense|dense-12|llama|ollama",
    re.I,
)
MINIMAX_RE = re.compile(r"minimax", re.I)
KIMI_RE = re.compile(r"kimi|fireworks", re.I)
CLAUDE_RE = re.compile(r"claude|opus|sonnet|antigravity|agy|ag/", re.I)
OPENAI_RE = re.compile(r"gpt|codex|openai", re.I)
EMERGENCY_RE = re.compile(r"opus-4-8|opus-4\.8|gpt-5\.5|gpt-5-5|emergency", re.I)


def classify_bucket(provider: str | None, model: str | None) -> str:
    p = (provider or "").lower()
    m = (model or "").lower()
    blob = f"{p}/{m}"
    if p in ("local", "llama-server", "llama") or LOCAL_RE.search(blob):
        return "local"
    if MINIMAX_RE.search(blob):
        return "minimax"
    if KIMI_RE.search(blob):
        return "kimi"
    if CLAUDE_RE.search(blob):
        return "claude"
    if OPENAI_RE.search(blob):
        return "openai"
    return "other"


def _pct(n: int, total: int) -> float:
    return round(100.0 * n / max(total, 1), 2)


def _load_criteria() -> dict[str, Any]:
    if not CLOUD_TIERS.exists():
        return {}
    data = yaml.safe_load(CLOUD_TIERS.read_text(encoding="utf-8")) or {}
    return (data.get("roles") or {}).get("sunset", {}).get("criteria", {})


def fetch_rows(
    conn: sqlite3.Connection, since: str | None
) -> list[tuple[str | None, str | None]]:
    rows: list[tuple[str | None, str | None]] = []
    q_logs = "SELECT provider, model FROM call_logs"
    params: list = []
    if since:
        q_logs += " WHERE timestamp >= ?"
        params.append(since)
    rows.extend(conn.execute(q_logs, params).fetchall())

    q_rd = "SELECT provider_selected, model_selected FROM routing_decisions"
    params_rd: list = []
    if since:
        q_rd += " WHERE created_at >= ?"
        params_rd.append(since)
    rows.extend(conn.execute(q_rd, params_rd).fetchall())
    return rows


def compute_metrics(conn: sqlite3.Connection, since: str | None) -> dict[str, Any]:
    rows = fetch_rows(conn, since)
    counts = Counter(classify_bucket(p, m) for p, m in rows)
    total = sum(counts[b] for b in BUCKETS)
    emergency = sum(1 for p, m in rows if EMERGENCY_RE.search(f"{p or ''}/{m or ''}"))
    counts["local"]
    criteria = _load_criteria()
    pct = {b: _pct(counts[b], total) for b in BUCKETS}
    return {
        "ts": datetime.now(UTC).isoformat(),
        "window_since": since,
        "total_calls": total,
        "counts": {b: counts[b] for b in BUCKETS},
        "pct": pct,
        "pct_local": pct["local"],
        "pct_minimax": pct["minimax"],
        "pct_kimi": pct["kimi"],
        "pct_claude": pct["claude"],
        "pct_openai": pct["openai"],
        "pct_emergency": _pct(emergency, total),
        "sources": {
            "call_logs": conn.execute("SELECT COUNT(*) FROM call_logs").fetchone()[0],
            "routing_decisions": conn.execute(
                "SELECT COUNT(*) FROM routing_decisions"
            ).fetchone()[0],
        },
        "sunset_criteria": criteria,
        "sunset_ok": {
            "routine_local_pct": pct["local"]
            >= 100 * criteria.get("routine_local_pct", 0),
            "emergency_pct_max": _pct(emergency, total)
            <= 100 * criteria.get("emergency_pct_max", 1),
        },
    }


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description="Append sunset transition metrics JSONL")
    p.add_argument("--db", type=Path, default=OMNIROUTE_DB)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--since", default=None, help="ISO timestamp window start")
    p.add_argument("--print", action="store_true", help="Print latest record to stdout")
    args = p.parse_args()

    conn = sqlite3.connect(args.db)
    record = compute_metrics(conn, args.since)
    conn.close()
    append_jsonl(args.out, record)
    print(
        f"Appended sunset metrics: local={record['pct_local']}% "
        f"minimax={record['pct_minimax']}% kimi={record['pct_kimi']}% "
        f"claude={record['pct_claude']}% openai={record['pct_openai']}% "
        f"-> {args.out}"
    )
    if args.print:
        print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
