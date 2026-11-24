-- SessionLedger L14 — Initial Schema
-- Sessions + ingest events + OKF bundles
-- Migration: 0001_initial.sql

PRAGMA foreign_keys = ON;

-- Sessions: a recorded run of the daemon capturing one or more source streams.
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    started_at  INTEGER NOT NULL,
    ended_at    INTEGER,
    source_kind TEXT NOT NULL,
    label       TEXT,
    metadata    TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_source_kind ON sessions(source_kind);

-- Ingest events: individual records captured during a session.
CREATE TABLE IF NOT EXISTS ingest_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    occurred_at INTEGER NOT NULL,
    kind        TEXT NOT NULL,
    payload     TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_events_session_time
    ON ingest_events(session_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_kind ON ingest_events(kind);

-- OKF bundles: serialized exports ready for replay.
CREATE TABLE IF NOT EXISTS okf_bundles (
    id            TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    created_at    INTEGER NOT NULL,
    byte_size     INTEGER NOT NULL CHECK (byte_size >= 0),
    digest        TEXT NOT NULL,
    location      TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_bundles_session ON okf_bundles(session_id);
CREATE INDEX IF NOT EXISTS idx_bundles_digest ON okf_bundles(digest);

-- Replay runs: bookkeeping for OKF replay sessions.
CREATE TABLE IF NOT EXISTS replay_runs (
    id          TEXT PRIMARY KEY,
    bundle_id   TEXT NOT NULL,
    started_at  INTEGER NOT NULL,
    ended_at    INTEGER,
    status      TEXT NOT NULL DEFAULT 'pending',
    FOREIGN KEY (bundle_id) REFERENCES okf_bundles(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_replay_bundle ON replay_runs(bundle_id);

-- Migration tracker (kept consistent with Tokn's naming for tool reuse).
CREATE TABLE IF NOT EXISTS schema_migrations (
    version   TEXT PRIMARY KEY,
    applied_at INTEGER NOT NULL
);
