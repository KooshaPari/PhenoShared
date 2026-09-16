"""v003: Add benchmark energy tracking."""

UPGRADE_SQL = [
    "CREATE TABLE IF NOT EXISTS bench_energy (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, gpu_power_watts REAL, gpu_temp_celsius REAL, cpu_power_watts REAL, wall_time_seconds REAL, peak_memory_mb REAL, recorded_at TEXT NOT NULL DEFAULT (datetime('now')))",
    "CREATE INDEX IF NOT EXISTS idx_bench_energy_run ON bench_energy(run_id)",
]

DOWNGRADE_SQL = ["DROP TABLE IF EXISTS bench_energy"]

META = {"version": 3, "description": "Add benchmark energy tracking"}
