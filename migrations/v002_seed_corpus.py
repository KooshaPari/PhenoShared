"""v002: Add seed regression prompt corpus."""

UPGRADE_SQL = [
    "CREATE TABLE IF NOT EXISTS seed_corpus (id INTEGER PRIMARY KEY AUTOINCREMENT, prompt_hash TEXT NOT NULL UNIQUE, prompt_text TEXT NOT NULL, expected_verdict TEXT NOT NULL DEFAULT 'unknown', source TEXT DEFAULT 'manual', tags TEXT DEFAULT '[]', created_at TEXT NOT NULL DEFAULT (datetime('now')))",
    "CREATE INDEX IF NOT EXISTS idx_seed_corpus_hash ON seed_corpus(prompt_hash)",
]

DOWNGRADE_SQL = ["DROP TABLE IF EXISTS seed_corpus"]

META = {"version": 2, "description": "Add seed regression prompt corpus"}
