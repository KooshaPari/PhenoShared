-- B4: Bifrost model catalog cache (matches L5-111 schema in the lifetime/pheno-style repo)
-- Idempotent: all CREATE IF NOT EXISTS; safe to re-run.

CREATE TABLE IF NOT EXISTS bifrost_models (
    id           TEXT NOT NULL,
    provider     TEXT NOT NULL,
    object       TEXT NOT NULL,
    owned_by     TEXT,
    display_name TEXT,
    fetched_at   TEXT NOT NULL,
    expires_at   TEXT NOT NULL,
    payload      TEXT NOT NULL,
    PRIMARY KEY (provider, id)
);

CREATE INDEX IF NOT EXISTS idx_bifrost_models_provider     ON bifrost_models(provider);
CREATE INDEX IF NOT EXISTS idx_bifrost_models_expires_at   ON bifrost_models(expires_at);

CREATE TABLE IF NOT EXISTS bifrost_models_meta (
    provider    TEXT PRIMARY KEY,
    last_status TEXT NOT NULL CHECK (last_status IN ('ok', 'error', 'partial')),
    last_error  TEXT,
    last_count  INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT NOT NULL
);