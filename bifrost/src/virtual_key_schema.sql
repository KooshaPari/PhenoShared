-- B5: Virtual key store schema for Bifrost gateway authentication.
-- Virtual keys are short-lived bearer tokens minted per provider.
-- Safe to re-run (CREATE IF NOT EXISTS, indexes idempotent).
CREATE TABLE IF NOT EXISTS virtual_keys (
    id         TEXT PRIMARY KEY,
    provider   TEXT NOT NULL,
    issued_at  TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    status     TEXT NOT NULL CHECK (status IN ('active', 'revoked', 'expired'))
);
CREATE INDEX IF NOT EXISTS idx_virtual_keys_provider   ON virtual_keys(provider);
CREATE INDEX IF NOT EXISTS idx_virtual_keys_expires_at ON virtual_keys(expires_at);
CREATE INDEX IF NOT EXISTS idx_virtual_keys_status     ON virtual_keys(status);
