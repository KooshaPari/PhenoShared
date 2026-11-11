# Durable schema migrations

SessionLedger keeps domain logic in pure Rust modules. When a SQLite-backed
[`MemoryStore`](../../src/ports/mod.rs) adapter graduates beyond process-local
storage, it should open the database and call
[`schema::migrate::apply_all`](../../src/schema/migrate.rs) before serving
reads or writes.

## Manifest

| Version | Name                   | SQL                                                                                    |
| ------- | ---------------------- | -------------------------------------------------------------------------------------- |
| 1       | `initial_memory_facts` | [`src/schema/migrations/001_initial.sql`](../../src/schema/migrations/001_initial.sql) |

The ordered manifest lives in [`src/schema/mod.rs`](../../src/schema/mod.rs).
Add new migrations by appending a file under `src/schema/migrations/` and
registering it in the manifest. Never rewrite or delete a shipped migration.

## Local check

```powershell
cargo test --features sqlite schema::
cargo test --features sqlite sqlite_memory
```

CI runs the manifest unit tests on every pull request through the default
`cargo test` invocation. SQLite-gated migration apply tests run when the
`sqlite` feature is enabled locally or in downstream adapter work.

## Limits

This scaffold ships a feature-gated [`SqliteMemoryStore`](../../src/ports/sqlite_memory.rs)
that applies the manifest at open time. `sl-daemon serve` opens the store when
`--memory-db` or `SL_MEMORY_DB` is set (requires `sl-daemon` built with
`--features sqlite`) and probes it from `GET /readyz`. Cancellation semantics and FSM
allow-lists remain separate C00 work.
