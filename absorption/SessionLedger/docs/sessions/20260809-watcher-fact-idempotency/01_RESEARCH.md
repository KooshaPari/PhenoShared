# Research

- `crates/sl-daemon/src/watcher.rs` forwards each create or modify event for a transcript; FSEvents may report repeated events for unchanged input.
- `crates/sl-daemon/src/etl.rs::transform_file` invokes `compile_and_store` once per parsed session when SQLite memory is configured.
- `src/ports/sqlite_memory.rs::store` currently assigns an incrementing identifier, so reprocessing the same session/key/content creates another durable row.
- `DistillMemoryWriter` already constructs a stable key from session id and bundle kind. A deterministic identity over session id, key, and content can make the SQLite primary key idempotent without changing watcher timing or HTTP behavior.

The red regression test transformed one JSONL fixture twice and recalled six SQLite facts where the three stable distilled facts were expected. This confirms the duplicate originates at the durable SQLite identity boundary.
