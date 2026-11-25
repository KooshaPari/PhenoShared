# pheno-harness Migrations

pheno-harness stores bench results and metadata in a small SQLite database
(`bench.db` by default). Schema changes are managed by `bench.migrations`, a
lightweight forward + backward migration runner.

## Layout

```
migrations/
├── 0001_initial.json          # bench_runs + bench_verdicts
└── 0002_add_seed_corpus.json  # bench_seed_corpus (regression prompts)
```

Each file is JSON with `version`, `up`, `down`, `note`.

## Usage

```python
import sqlite3
from bench.migrations import apply_migrations, status, rollback

conn = sqlite3.connect("bench.db")
apply_migrations(conn)                  # apply pending
for v, state, note in status(conn):
    print(f"{v:24s} {state:8s} {note}")

rollback(conn, "0002_add_seed_corpus") # revert a single version
```

## CLI

```bash
python -m bench.migrations apply
python -m bench.migrations status
python -m bench.migrations rollback --version 0002_add_seed_corpus
```

## Tracking

Applied versions are stored in `_bench_migrations(version, applied_at, note)`.
The runner is idempotent — re-running `apply` is safe.

## Adding a Migration

1. Create `migrations/NNNN_description.json` with `up` (required) and `down`
   (optional) SQL statements.
2. Run `apply_migrations(conn)` to apply.
3. Document the change here if it adds a new table or breaks an existing
   consumer.

## Safety

- Always provide a `down` for reversible migrations.
- The runner executes one statement at a time so syntax errors are easy to
  localize.
- The runner does **not** run migrations inside a transaction by default — wrap
  your `apply_migrations` call in `with conn:` if you want atomic semantics.
