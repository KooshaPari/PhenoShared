#!/usr/bin/env python3
"""
spend_extractor.py — Provider-level spend aggregation (round-4, Blk 1 close).

Sources (read-only):
  ~/.jcode/provider_activity.json
    entries: {provider_id: {last_used_unix_secs, spend?: {day_date, day_usd,
                                                          month, month_usd,
                                                          all_time_usd}}}
  ~/.jcode/openai_oauth_usage.json
    accounts: {default: {lifetime: {requests, input, output, cached,
                                     known_usd, unpriced_requests,
                                     incomplete_requests},
                          days: {YYYY-MM-DD: {requests, input, output, cached,
                                              known_usd, unpriced_requests,
                                              incomplete_requests}}}}

Output: provider_spend table (PK = (provider, day_date)).

The PK is composite so a re-run updates the same day's snapshot rather than
adding duplicate rows. This matches jcode's behavior of "rewrite the day's
stats on every flush".

Note (round-3 finding): The 75 opencode.log events are all session-creation
events with all-zero token counts — the actual spend data lives in
provider_activity.json (per-provider aggregator) and
openai_oauth_usage.json (per-OAuth-account aggregator). This file ingests both.

Round-5 (W4-1): assigns source_local_visibility per provider based on whether
the spend can be cross-checked against local turn records. See
ledger_db.provider_spend for the schema and VISIBILITY dict below for the
rule.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone

from ledger_db import insert_provider_spend


# Round-5 (W4-1): operator-judged source_local_visibility per provider.
# The 4 visible stealth/union-alpha turns in model-usage-v1.sqlite3 were free
# (operator-confirmed 2026-10-13), but provider_activity.json reports $7,886.57
# all-time on openrouter — meaning that spend originated from outside jcode
# (direct openrouter.ai dashboard, or other tools sharing the key).
#
# openai:oauth:default has 81% unpriced requests in openai_oauth_usage.json
# (466/573 lifetime), so its $61.23 known_usd understates the real cost.
#
# opencode-go (1562 turns) and zai (3 turns) reconcile cleanly with the
# recorded spend, so they are 'visible'.
VISIBILITY = {
    "openrouter": "external",
    "openai:oauth:default": "unpriced",
    "openai-compatible:opencode-go": "visible",
    "openai-compatible:zai": "visible",
}


def _ensure_visibility_column(conn):
    """Round-5 (W4-1) migration: add source_local_visibility if missing.

    Idempotent: uses PRAGMA to check, only ALTERs if absent. The CREATE TABLE
    in ledger_db.py declares the column for fresh DBs; this migration is for
    the round-4 DB that already has 5 provider_spend rows without the column.
    """
    cols = {row[1] for row in conn.execute("PRAGMA provider_spend_info").fetchall()}
    if "source_local_visibility" not in cols:
        conn.execute(
            "ALTER TABLE provider_spend ADD COLUMN source_local_visibility TEXT "
            "NOT NULL DEFAULT 'visible'"
        )
        conn.commit()


def _ts_iso(epoch_sec):
    """epoch_sec -> ISO 8601 UTC string, or None."""
    if not epoch_sec:
        return None
    try:
        return datetime.fromtimestamp(int(epoch_sec), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except (OSError, ValueError, OverflowError):
        return None


def extract_provider_activity(conn, jcode_root, ingested_at):
    """Ingest ~/.jcode/provider_activity.json into provider_spend.

    Each provider's `spend` block (if present) becomes one row with:
      provider = the entry key (e.g. "openai-compatible:opencode-go")
      day_date = the most recent day with spend data
      day_usd, month_usd, all_time_usd = from the spend block
      last_used = ISO of last_used_unix_secs
    """
    path = os.path.join(jcode_root, "provider_activity.json")
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return 0
    entries = data.get("entries", {})
    n = 0
    for provider, info in entries.items():
        spend = info.get("spend")
        if not spend:
            # Provider has activity but no spend tracking (e.g. free tier or
            # unknown pricing). Skip — we only store rows with USD values.
            continue
        day_date = spend.get("day_date")
        if not day_date:
            continue
        visibility = VISIBILITY.get(provider, "visible")
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO provider_spend
                (provider, day_date, month, day_usd, month_usd, all_time_usd,
                 last_used, raw_json, source_path, ingested_at,
                 source_local_visibility)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provider,
                    day_date,
                    spend.get("month"),
                    float(spend.get("day_usd", 0.0)),
                    float(spend.get("month_usd", 0.0)),
                    float(spend.get("all_time_usd", 0.0)),
                    _ts_iso(info.get("last_used_unix_secs")),
                    json.dumps(info),
                    path,
                    ingested_at,
                    visibility,
                ),
            )
            n += 1
        except (sqlite3.Error, ValueError, TypeError) as e:
            print(f"[spend] provider_activity insert failed for {provider}: {e}")
    return n


def extract_openai_oauth_usage(conn, jcode_root, ingested_at):
    """Ingest ~/.jcode/openai_oauth_usage.json into provider_spend.

    Each (account, day) pair becomes one row. The provider is synthesized as
    `openai:oauth:<account>` (e.g. "openai:oauth:default") so the OAuth accounts
    live alongside the openai-compatible: providers without colliding.
    """
    path = os.path.join(jcode_root, "openai_oauth_usage.json")
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return 0
    accounts = data.get("accounts", {})
    n = 0
    for account_name, account in accounts.items():
        provider = f"openai:oauth:{account_name}"
        days = account.get("days", {})
        visibility = VISIBILITY.get(provider, "visible")
        for day_date, day_info in days.items():
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO provider_spend
                    (provider, day_date, month, day_usd, month_usd, all_time_usd,
                     last_used, raw_json, source_path, ingested_at,
                     source_local_visibility)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        provider,
                        day_date,
                        day_date[:7],  # YYYY-MM
                        float(day_info.get("known_usd", 0.0)),
                        None,  # monthly is not in the daily JSON
                        float(account.get("lifetime", {}).get("known_usd", 0.0)),
                        None,  # no per-day last_used
                        json.dumps(day_info),
                        path,
                        ingested_at,
                        visibility,
                    ),
                )
                n += 1
            except (sqlite3.Error, ValueError, TypeError) as e:
                print(f"[spend] openai_oauth insert failed for {provider}/{day_date}: {e}")
    return n


def extract_spend(conn, jcode_root=None):
    """Top-level: ingest both jcode spend files. Returns total row count."""
    if jcode_root is None:
        jcode_root = os.path.expanduser("~/.jcode")
    ingested_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    _ensure_visibility_column(conn)
    n = 0
    n += extract_provider_activity(conn, jcode_root, ingested_at)
    n += extract_openai_oauth_usage(conn, jcode_root, ingested_at)
    conn.commit()
    return n
