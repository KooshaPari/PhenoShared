# agileplus-sqlite

![MSRV](https://img.shields.io/badge/MSRV-1.86-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

SQLite persistence adapter for AgilePlus. It implements domain storage ports with rusqlite, WAL mode, foreign keys, migrations, repository helpers, and event-store support.

## Public API Index

- `SqliteStorageAdapter` - SQLite-backed implementation of `agileplus_domain::ports::StoragePort`.
- `SqliteStorageAdapter::new` - opens a file-backed database, configures WAL/FK pragmas, and runs migrations.
- `SqliteStorageAdapter::in_memory` - opens a migrated in-memory database for tests.
- `SqliteStorageAdapter::conn_for_bench` - exposes a locked rusqlite connection for benchmark and test helpers.
- `migrations` - migration runner and schema migration definitions.
- `ports` - adapter-side port implementations.
- `rebuild` - rebuild workflows for derived state.
- `repository` - repository functions for audit, backlog, cycles, events, evidence, features, governance, metrics, modules, projects, sync mappings, and work packages.

## Build

```bash
cargo build -p agileplus-sqlite
cargo build -p agileplus-sqlite --features async
```

