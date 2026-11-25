# pheno-harness Configuration Reference

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PHENO_DB_PATH` | `~/.pheno-harness/bench.db` | SQLite database path |
| `PHENO_CACHE_DIR` | `~/.pheno-harness/cache` | Benchmark cache directory |
| `PHENO_LOG_LEVEL` | `INFO` | Log verbosity (DEBUG/INFO/WARNING/ERROR) |
| `PHENO_MAX_PARALLEL` | `4` | Max concurrent benchmark runs |
| `PHENO_TIMEOUT_SECS` | `300` | Per-benchmark timeout |
| `PHENO_SEED` | `42` | Random seed for reproducibility |

## pyproject.toml Settings

```toml
[tool.pheno-harness]
cache_strategy = "lru"       # lru | always | never
max_cache_entries = 1000
report_format = "json"       # json | markdown | html
db_backend = "sqlite"        # sqlite
```

## Config File Locations

1. `~/.pheno-harness/config.toml` — user-level config
2. `./pheno.toml` — project-level config (overrides user)
3. Environment variables (overrides all)
