"""v003: Add routing decision history."""

UPGRADE_SQL = [
    """CREATE TABLE IF NOT EXISTS routing_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_hash TEXT NOT NULL UNIQUE,
        route_chosen TEXT NOT NULL,
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        cost_usd REAL NOT NULL DEFAULT 0,
        latency_ms INTEGER NOT NULL DEFAULT 0,
        tokens_in INTEGER NOT NULL DEFAULT 0,
        tokens_out INTEGER NOT NULL DEFAULT 0,
        success INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_routing_history_provider ON routing_history(provider)",
    "CREATE INDEX IF NOT EXISTS idx_routing_history_model ON routing_history(model)",
]

DOWNGRADE_SQL = [
    "DROP INDEX IF EXISTS idx_routing_history_model",
    "DROP INDEX IF EXISTS idx_routing_history_provider",
    "DROP TABLE IF EXISTS routing_history",
]

META = {"version": 3, "description": "Add routing decision history"}
