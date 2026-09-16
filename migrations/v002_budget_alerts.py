"""v002: Add budget alerts and spending thresholds."""

UPGRADE_SQL = [
    """CREATE TABLE IF NOT EXISTS budget_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_type TEXT NOT NULL CHECK (alert_type IN ('threshold', 'daily', 'monthly', 'anomaly')),
        threshold_pct REAL NOT NULL DEFAULT 0.8,
        current_spend REAL NOT NULL DEFAULT 0,
        budget_limit REAL NOT NULL DEFAULT 0,
        channel TEXT NOT NULL DEFAULT 'log',
        enabled INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        triggered_at TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_budget_alerts_type ON budget_alerts(alert_type)",
    "CREATE INDEX IF NOT EXISTS idx_budget_alerts_enabled ON budget_alerts(enabled)",
]

DOWNGRADE_SQL = [
    "DROP INDEX IF EXISTS idx_budget_alerts_enabled",
    "DROP INDEX IF EXISTS idx_budget_alerts_type",
    "DROP TABLE IF EXISTS budget_alerts",
]

META = {"version": 2, "description": "Add budget alerts and spending thresholds"}
