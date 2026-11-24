-- Preserve chronological recall when durable fact ids are content-addressed.
--
-- v1 ordered recall by monotonically allocated ids. v2 keeps deterministic ids
-- for idempotency and records an immutable insertion ordinal for recall.

CREATE TABLE memory_facts_v2 (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('EPISODIC', 'SEMANTIC')),
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    insertion_order INTEGER NOT NULL UNIQUE
);

INSERT INTO memory_facts_v2 (
    id,
    session_id,
    kind,
    payload_json,
    created_at,
    insertion_order
)
SELECT id, session_id, kind, payload_json, created_at, rowid
FROM memory_facts
ORDER BY rowid ASC;

DROP TABLE memory_facts;
ALTER TABLE memory_facts_v2 RENAME TO memory_facts;

CREATE INDEX idx_memory_facts_session
    ON memory_facts (session_id);
