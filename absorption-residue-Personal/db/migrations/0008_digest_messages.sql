-- Migration 0008: digest_messages (append-only backfill target for Dot digest history).
-- Written only by the sanctioned relay writer / chunked INSERT OR IGNORE backfill;
-- ad-hoc wrangler stays read-only. Append-only: corrections are new rows, never UPDATE/DELETE.
CREATE TABLE IF NOT EXISTS digest_messages (
  digest_id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  channel TEXT,
  author TEXT,
  author_original TEXT,             -- author as it appeared in the source, before normalisation
  thread_anchor TEXT,
  text TEXT NOT NULL,
  project_ids TEXT,                 -- JSON array of project ids
  percent_claims TEXT,              -- JSON array of percent claims found in the text
  kind TEXT,
  source TEXT NOT NULL DEFAULT 'backfill',
  recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) -- NOSONAR: SQLite DDL has no constant mechanism; the ISO timestamp default is repeated per table by design
);
CREATE INDEX IF NOT EXISTS digest_messages_ts ON digest_messages(ts);
CREATE INDEX IF NOT EXISTS digest_messages_channel ON digest_messages(channel, ts);
