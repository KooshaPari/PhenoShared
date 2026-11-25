-- SessionLedger L14 — Seed data for development & tests.
-- One minimal session + one event + one bundle to verify the schema works.

INSERT OR IGNORE INTO sessions (id, started_at, source_kind, label, metadata)
    VALUES ('seed-0001', strftime('%s','now') * 1000, 'claude_code', 'Seed session', '{}');

INSERT OR IGNORE INTO ingest_events (session_id, occurred_at, kind, payload)
    VALUES ('seed-0001', strftime('%s','now') * 1000, 'tool_call',
            '{"name":"Read","args":{"file_path":"README.md"}}');

INSERT OR IGNORE INTO okf_bundles
    (id, session_id, schema_version, created_at, byte_size, digest, location)
    VALUES
    ('bundle-0001', 'seed-0001', 'okf/v1', strftime('%s','now') * 1000,
     1024, 'sha256:0000000000000000000000000000000000000000000000000000000000000000',
     'file:///tmp/seed-0001.okf');

INSERT OR REPLACE INTO schema_migrations (version, applied_at)
    VALUES ('0002_seed', strftime('%s','now') * 1000);
