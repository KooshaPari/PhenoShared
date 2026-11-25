#!/usr/bin/env python3
"""
ledger_db.py — SQLite schema + write contract for the session ledger.

Used by both extractors.py (row insertion from per-harness extractors) and
extract_sessions.py (driver: CLI, --assert-min, Mac/desk orchestration).

Split out in round-4 so that extractors.py could stay under the AGENTS.md
500-line hard limit (was 625, now 358).

Schema (round-3, current):
  sessions (harness, device, session_id PK, host, started_at, ended_at,
            title, model, provider, tokens_total, cwd, git_branch, path,
            extra_json)
  opencode_usage (host, month_yyyymm, model, day_yyyymmdd, requests,
                  cached_tokens, uncached_tokens, total_tokens, source)

Privacy (round-1+ invariant):
  s9  insert_session NEVER writes secrets. raw_line is stripped (truncated
      to 8 KiB, redaction patterns applied) before any other column reads it.
  s10 extra_json is the only column that may carry non-PII diagnostics; it
      is always JSON-encoded and does not include raw user content.
"""
import json
import os
import sqlite3
from pathlib import Path


def open_db(db_path):
    """Create/open the ledger sqlite. Returns sqlite3 connection."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            harness TEXT NOT NULL,
            session_id TEXT NOT NULL,
            device TEXT NOT NULL,
            host TEXT,
            started_at TEXT,
            ended_at TEXT,
            title TEXT,
            model TEXT,
            provider TEXT,
            tokens_total INTEGER,
            cwd TEXT,
            git_branch TEXT,
            path TEXT NOT NULL,
            extra_json TEXT,
            PRIMARY KEY (harness, session_id, device)
        )
    """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_harness ON sessions(harness)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_device ON sessions(device)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_provider ON sessions(provider)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS opencode_usage (
            rowid INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            profile TEXT,
            session_id TEXT,
            model TEXT,
            cached_tokens INTEGER,
            uncached_tokens INTEGER,
            reasoning_tokens INTEGER,
            retry_count INTEGER,
            http_status INTEGER,
            session_header_present INTEGER,
            quota_window TEXT,
            raw_line TEXT,
            source_path TEXT
        )
    """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_opencode_usage_timestamp ON opencode_usage(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_opencode_usage_profile ON opencode_usage(profile)")
    # Round-4: provider-level spend aggregator (Blk 1 close).
    # Source: ~/.jcode/provider_activity.json + ~/.jcode/openai_oauth_usage.json
    # PK: (provider, day_date) so daily snapshots can be updated in place.
    #
    # Round-5 (W4-1): added source_local_visibility column. Three values:
    #   'visible'  — the spend is supported by per-turn records in
    #                model-usage-v1.sqlite3 that we can cross-check
    #                (e.g. opencode-go: 1562 turns, $62.27 spend, ~$0.04/turn)
    #   'unpriced' — turn records exist but most responses had no cost data
    #                (e.g. openai:oauth:default: 81% of 573 lifetime requests
    #                are recorded as unpriced; $61.23 known_usd underestimates
    #                true cost)
    #   'external' — no jcode turn records; the spend is from non-jcode
    #                activity on the same key (e.g. openrouter: 4 visible
    #                stealth/union-alpha calls in turns table were free, but
    #                provider_activity.json reports $7,886.57 all_time_usd,
    #                meaning most of that spend came from outside jcode —
    #                operator-confirmed 2026-10-13 that "union was free")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_spend (
            provider TEXT NOT NULL,
            day_date TEXT NOT NULL,
            month TEXT,
            day_usd REAL,
            month_usd REAL,
            all_time_usd REAL,
            last_used TEXT,
            raw_json TEXT,
            source_path TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            source_local_visibility TEXT NOT NULL DEFAULT 'visible',
            PRIMARY KEY (provider, day_date)
        )
    """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_provider_spend_provider ON provider_spend(provider)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_provider_spend_day ON provider_spend(day_date)")
    # Round-5 export import: openai data export (conversations.json)
    # Source: ~/Downloads/conversations.json (openai ChatGPT data export).
    # Privacy note: the export contains user message TEXT and assistant TEXT.
    # The extractor stores the full content_json for tool_use/tool_result/thinking
    # but truncates message.text to 4 KiB so a single human message cannot
    # accidentally bloat the ledger. The export file is read-only and
    # referenced by source_path, so the same file can be re-ingested idempotently.
    #
    # Tables:
    #   openai_chatgpt_conversations — 1 row per conversation (786 expected)
    #   openai_chatgpt_messages      — 1 row per message (10885 expected)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS openai_chatgpt_conversations (
            uuid TEXT PRIMARY KEY,
            name TEXT,
            summary TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            account_uuid TEXT,
            n_messages INTEGER NOT NULL,
            source_path TEXT NOT NULL,
            ingested_at TEXT NOT NULL
        )
    """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS openai_chatgpt_messages (
            uuid TEXT PRIMARY KEY,
            conversation_uuid TEXT NOT NULL,
            sender TEXT NOT NULL,
            text TEXT,
            content_json TEXT,
            n_content_items INTEGER NOT NULL,
            has_attachments INTEGER NOT NULL,
            n_attachments INTEGER NOT NULL DEFAULT 0,
            has_files INTEGER NOT NULL,
            n_files INTEGER NOT NULL,
            parent_message_uuid TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            source_path TEXT NOT NULL,
            ingested_at TEXT NOT NULL
        )
    """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_msg_conv ON openai_chatgpt_messages(conversation_uuid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_msg_created ON openai_chatgpt_messages(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_msg_sender ON openai_chatgpt_messages(sender)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_conv_created ON openai_chatgpt_conversations(created_at)")
    # W6-4: index on n_messages to speed up the chatgpt-conversations preset
    # which does ORDER BY n_messages DESC LIMIT 20. Without this index SQLite
    # would full-scan + sort the 786 rows. With it the top-20 query is an
    # index-only walk. Idempotent (IF NOT EXISTS).
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_conv_n_messages ON openai_chatgpt_conversations(n_messages)")
    # Round-7 (W7-2.1/2.2/2.5): three child tables for export data that was
    # previously dropped on the floor. All idempotent (IF NOT EXISTS) and
    # composite-keyed so re-ingest replaces in place.
    #
    #   openai_chatgpt_files             — files[] links (file_uuid + name)
    #   openai_chatgpt_attachment_content — attachments[] extracted_content
    #                                       (the FULL pasted text/code; this
    #                                       is the searchable code-history)
    #   openai_chatgpt_tool_results      — tool_result content blocks from
    #                                       content_json (name, is_error,
    #                                       payload; 23 MB across 8572 blocks)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS openai_chatgpt_files (
            msg_uuid TEXT NOT NULL,
            conversation_uuid TEXT NOT NULL,
            file_uuid TEXT NOT NULL,
            file_name TEXT,
            source_path TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            PRIMARY KEY (msg_uuid, file_uuid)
        )
    """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_files_msg ON openai_chatgpt_files(msg_uuid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_files_uuid ON openai_chatgpt_files(file_uuid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_files_conv ON openai_chatgpt_files(conversation_uuid)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS openai_chatgpt_attachment_content (
            msg_uuid TEXT NOT NULL,
            conversation_uuid TEXT NOT NULL,
            file_name TEXT,
            file_size INTEGER,
            file_type TEXT,
            extracted_content TEXT,
            content_len INTEGER NOT NULL DEFAULT 0,
            source_path TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            PRIMARY KEY (msg_uuid, file_name)
        )
    """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_attcontent_msg ON openai_chatgpt_attachment_content(msg_uuid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_attcontent_conv ON openai_chatgpt_attachment_content(conversation_uuid)")
    # W7-2.10: FTS5 full-text index over the pasted-code table (external
    # content pattern — the text lives in openai_chatgpt_attachment_content,
    # FTS holds only the inverted index + rowid map). Three triggers keep it
    # in sync: REPLACE semantics in the importer fire delete+insert pairs,
    # so all three triggers are required for consistency.
    # Query with: SELECT rowid, snippet(openai_chatgpt_attcontent_fts, 0,
    # '[', ']', '…', 12) FROM openai_chatgpt_attcontent_fts WHERE
    # openai_chatgpt_attcontent_fts MATCH '<terms>'
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS openai_chatgpt_attcontent_fts USING fts5(
            extracted_content,
            file_name,
            content='openai_chatgpt_attachment_content',
            content_rowid='rowid'
        )
    """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS attcontent_fts_ai AFTER INSERT ON openai_chatgpt_attachment_content BEGIN
            INSERT INTO openai_chatgpt_attcontent_fts(rowid, extracted_content, file_name)
            VALUES (new.rowid, new.extracted_content, new.file_name);
        END
    """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS attcontent_fts_ad AFTER DELETE ON openai_chatgpt_attachment_content BEGIN
            INSERT INTO openai_chatgpt_attcontent_fts(openai_chatgpt_attcontent_fts, rowid, extracted_content, file_name)
            VALUES ('delete', old.rowid, old.extracted_content, old.file_name);
        END
    """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS attcontent_fts_au AFTER UPDATE ON openai_chatgpt_attachment_content BEGIN
            INSERT INTO openai_chatgpt_attcontent_fts(openai_chatgpt_attcontent_fts, rowid, extracted_content, file_name)
            VALUES ('delete', old.rowid, old.extracted_content, old.file_name);
            INSERT INTO openai_chatgpt_attcontent_fts(rowid, extracted_content, file_name)
            VALUES (new.rowid, new.extracted_content, new.file_name);
        END
    """
    )
    # W7-2.10 migration guard: when the FTS table is created on a DB whose
    # attachment_content rows already exist, the FTS starts EMPTY while the
    # source has rows. Any subsequent DELETE then fires the ad trigger with
    # unindexed rowids, which corrupts the FTS (observed as "database disk
    # image is malformed" during truncate-first). Rebuild the index here —
    # before the importer can DELETE anything — so triggers always operate
    # on a consistent index. No-op when both sides are empty (fresh DB).
    #
    # CRITICAL: COUNT(*) on an external-content FTS table reads the CONTENT
    # table and returns 817 even when the index is empty (confirmed
    # 2026-10-14: _docsize=0, MATCH=0 rows, but COUNT(*)=817). The true
    # indexed-doc count lives in the _docsize shadow table — use that.
    n_src = conn.execute(
        "SELECT COUNT(*) FROM openai_chatgpt_attachment_content WHERE extracted_content IS NOT NULL"
    ).fetchone()[0]
    n_fts = conn.execute(
        "SELECT COUNT(*) FROM openai_chatgpt_attcontent_fts_docsize"
    ).fetchone()[0]
    if n_fts == 0 and n_src > 0:
        conn.execute(
            "INSERT INTO openai_chatgpt_attcontent_fts(openai_chatgpt_attcontent_fts) VALUES('rebuild')"
        )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS openai_chatgpt_tool_results (
            msg_uuid TEXT NOT NULL,
            conversation_uuid TEXT NOT NULL,
            block_index INTEGER NOT NULL,
            name TEXT,
            tool_use_id TEXT,
            is_error INTEGER,
            content_json TEXT,
            content_len INTEGER NOT NULL DEFAULT 0,
            source_path TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            PRIMARY KEY (msg_uuid, block_index)
        )
    """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_tr_msg ON openai_chatgpt_tool_results(msg_uuid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_tr_conv ON openai_chatgpt_tool_results(conversation_uuid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_tr_name ON openai_chatgpt_tool_results(name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_tr_tooluse ON openai_chatgpt_tool_results(tool_use_id)")
    # Round-5 (W5-VALIDATION-2): idempotent column add for existing DBs.
    # n_attachments mirrors n_files (count) for symmetry. has_attachments is
    # the boolean; n_attachments > 0 ⇔ has_attachments == 1.
    try:
        conn.execute("ALTER TABLE openai_chatgpt_messages ADD COLUMN n_attachments INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            raise
    # Round-5 (W5-VALIDATION-3): add parent_message_uuid for thread tracking.
    try:
        conn.execute("ALTER TABLE openai_chatgpt_messages ADD COLUMN parent_message_uuid TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            raise
    # After migrations: create indexes on the new columns. Safe for new
    # DBs (column was just created above) and existing DBs (column was
    # just added by the ALTER).
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_msg_parent ON openai_chatgpt_messages(parent_message_uuid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chatgpt_conv_updated ON openai_chatgpt_conversations(updated_at)")
    conn.commit()
    return conn


def insert_session(conn, **kw):
    """Insert one session row, REPLACE on conflict."""
    cols = (
        "harness", "session_id", "device", "host", "started_at", "ended_at",
        "title", "model", "provider", "tokens_total", "cwd", "git_branch",
        "path", "extra_json",
    )
    vals = tuple(kw.get(c) for c in cols)
    placeholders = ",".join("?" * len(cols))
    conn.execute(
        f"INSERT OR REPLACE INTO sessions ({','.join(cols)}) VALUES ({placeholders})",
        vals,
    )


def insert_provider_spend(conn, **kw):
    """Insert one provider_spend row, REPLACE on (provider, day_date) conflict.

    Round-4: idempotent so re-runs of extract_sessions.py update daily snapshots
    in place rather than creating duplicate rows.

    Round-5 (W4-1): accepts source_local_visibility kw (default 'visible').
    """
    cols = (
        "provider", "day_date", "month", "day_usd", "month_usd", "all_time_usd",
        "last_used", "raw_json", "source_path", "ingested_at",
        "source_local_visibility",
    )
    vals = tuple(kw.get(c) for c in cols)
    placeholders = ",".join("?" * len(cols))
    conn.execute(
        f"INSERT OR REPLACE INTO provider_spend ({','.join(cols)}) VALUES ({placeholders})",
        vals,
    )


# ----------------------------------------------- OPENAI CHATGPT EXPORT (W5) ----
def insert_chatgpt_conversation(conn, **kw):
    """Insert one row into openai_chatgpt_conversations. Idempotent (REPLACE on uuid)."""
    cols = (
        "uuid", "name", "summary", "created_at", "updated_at",
        "account_uuid", "n_messages", "source_path", "ingested_at",
    )
    vals = tuple(kw.get(c) for c in cols)
    placeholders = ",".join("?" * len(cols))
    conn.execute(
        f"INSERT OR REPLACE INTO openai_chatgpt_conversations ({','.join(cols)}) VALUES ({placeholders})",
        vals,
    )


def insert_chatgpt_message(conn, **kw):
    """Insert one row into openai_chatgpt_messages. Idempotent (REPLACE on uuid)."""
    cols = (
        "uuid", "conversation_uuid", "sender", "text", "content_json",
        "n_content_items", "has_attachments", "n_attachments", "has_files", "n_files",
        "parent_message_uuid",
        "created_at", "updated_at", "source_path", "ingested_at",
    )
    vals = tuple(kw.get(c) for c in cols)
    placeholders = ",".join("?" * len(cols))
    conn.execute(
        f"INSERT OR REPLACE INTO openai_chatgpt_messages ({','.join(cols)}) VALUES ({placeholders})",
        vals,
    )


# Round-7 (W7-2.1-2.5): insert helpers for the three new child tables.
# Same INSERT OR REPLACE idempotency contract as the conv/message helpers;
# composite PKs mean re-ingest replaces rows in place.
def insert_chatgpt_file(conn, **kw):
    """Insert one files[] link row. Idempotent (REPLACE on msg_uuid+file_uuid)."""
    cols = ("msg_uuid", "conversation_uuid", "file_uuid", "file_name",
            "source_path", "ingested_at")
    vals = tuple(kw.get(c) for c in cols)
    placeholders = ",".join("?" * len(cols))
    conn.execute(
        f"INSERT OR REPLACE INTO openai_chatgpt_files ({','.join(cols)}) VALUES ({placeholders})",
        vals,
    )


def insert_chatgpt_attachment_content(conn, **kw):
    """Insert one attachments[] extracted_content row.

    Idempotent (REPLACE on msg_uuid+file_name). extracted_content is the FULL
    pasted text/code — no truncation, matching the content_json contract
    (message.text is the only truncated column).
    """
    cols = ("msg_uuid", "conversation_uuid", "file_name", "file_size",
            "file_type", "extracted_content", "content_len",
            "source_path", "ingested_at")
    vals = tuple(kw.get(c) for c in cols)
    placeholders = ",".join("?" * len(cols))
    conn.execute(
        f"INSERT OR REPLACE INTO openai_chatgpt_attachment_content ({','.join(cols)}) VALUES ({placeholders})",
        vals,
    )


def insert_chatgpt_tool_result(conn, **kw):
    """Insert one tool_result content block. Idempotent (REPLACE on msg_uuid+block_index).

    content_json stores the block's `content` field (list of typed items:
    text/knowledge/image/rag_reference/local_resource) — full, untruncated.
    """
    cols = ("msg_uuid", "conversation_uuid", "block_index", "name",
            "tool_use_id", "is_error", "content_json", "content_len",
            "source_path", "ingested_at")
    vals = tuple(kw.get(c) for c in cols)
    placeholders = ",".join("?" * len(cols))
    conn.execute(
        f"INSERT OR REPLACE INTO openai_chatgpt_tool_results ({','.join(cols)}) VALUES ({placeholders})",
        vals,
    )


# ------------------------------------------------------------------ CODEX ----
