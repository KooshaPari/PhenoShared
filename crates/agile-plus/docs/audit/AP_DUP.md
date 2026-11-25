# AgilePlus Duplicate-Code Audit (AP_DUP)

**Date:** 2026-06-14
**Scope:** `crates/*` — repeated error enums, builder/validation logic, copy-pasted functions
**Method:** Source search (grep/read) only — no builds or tests run.

---

## Cluster 1 — Dashboard routes monolith (21 dead copies)

`agileplus-dashboard/src/routes.rs` still contains full copies of functions that were extracted into smaller route modules, but the originals were never deleted. The duplicated helpers + handlers now live in four files:

| Function | Dead copy in `routes.rs` | Live copy |
|----------|--------------------------|-----------|
| `is_htmx` | `routes.rs:222` | `routes/helpers.rs:27` |
| `html_escape` | `routes.rs:231` | — (only in routes.rs) |
| `render<T: Template>` | `routes.rs:270` | `routes/helpers.rs:35` / `module_cycle.rs:68` |
| `load_projects` | `routes.rs:282` | `routes/helpers.rs:46` |
| `build_project_summaries` | `routes.rs:304` | `routes/helpers.rs:66` |
| `env_or_none` | `routes.rs:329` | `routes/helpers.rs:88` |
| `parse_bool_env` | `routes.rs:336` | `routes/helpers.rs:95` |
| `plane_api_key_hint` | `routes.rs:348` | `routes/pages.rs:20` |
| `plane_health_endpoints` | `routes.rs:358` | `routes/pages.rs:30` |
| `build_feature_events` | `routes.rs:377` | `routes/dashboard.rs:23` |
| `build_feature_evidence_bundles` | `routes.rs:486` | `routes/dashboard.rs:63` |
| `build_feature_media_assets` | `routes.rs:561` | `routes/dashboard.rs:126` |
| `build_feature_reports` | `routes.rs:592` | `routes/dashboard.rs:157` |
| `plane_sync_mode` | `routes.rs:612` | `routes/pages.rs:49` |
| `plane_connection_checks` | `routes.rs:620` | `routes/pages.rs:57` |
| `percentage_coverage` | `routes.rs:642` | `routes/pages.rs:79` |
| `dashboard_filter_from_query` | `routes.rs:658` | `routes/helpers.rs:107` |
| `feature_matches_filter` | `routes.rs:667` | `routes/helpers.rs:116` |
| `build_kanban_cards` | `routes.rs:692` | `routes/helpers.rs:143` |
| `sample_events` | `routes.rs:713` | `routes/helpers.rs:163` |
| `calculate_uptime` | `routes.rs:1010` | `routes/dashboard.rs` (implicit) |

**DRY recommendation:** Delete the dead copies in `routes.rs` (lines ~220–720). The canonical implementations are already in `routes/helpers.rs`, `routes/dashboard.rs`, `routes/pages.rs`, and `module_cycle.rs`. Extract `html_escape` and `DEFAULT_PLANE_*` constants into `routes/helpers.rs` as well.

---

## Cluster 2 — `ExportError` enum identical in two files

`agileplus-p2p/src/export.rs:32` and `agileplus-p2p/src/export/errors.rs:4` define the exact same 6-variant enum:

```rust
pub enum ExportError {
    Io(#[from] std::io::Error),
    Serialization(#[from] serde_json::Error),
    EventStore(String),
    SnapshotStore(String),
    DeviceStore(#[from] ConnectionError),
    SyncStore(String),
}
```

**DRY recommendation:** Keep the definition in `export/errors.rs` (the dedicated error module). Delete the copy in `export.rs` and re-export `pub use crate::export::errors::ExportError;`.

---

## Cluster 3 — `SyncError` name collision (two different enums)

`agileplus-p2p/src/error.rs:26` and `agileplus-sync/src/error.rs:7` both declare `pub enum SyncError`. They have different variants and `From` impls, which causes confusion at import sites and breaks the “one name, one meaning” rule.

**DRY recommendation:** Rename the `agileplus-p2p` variant to `P2pSyncError` (or `ReplicationError`) and the `agileplus-sync` variant to `SyncAdapterError` (or `AgileplusSyncError`) to disambiguate. If they truly represent the same concept, extract a shared `agileplus-sync` crate type and re-export it.

---

## Cluster 4 — `#[from] std::io::Error` repeated across 6 crates

9 occurrences of the identical `#[from] std::io::Error` pattern appear in 6 crates:

- `crates/agileplus-integration-tests/src/common/harness.rs:27`
- `crates/agileplus-p2p/src/error.rs:18` (PeerDiscoveryError)
- `crates/agileplus-p2p/src/error.rs:77` (ConnectionError)
- `crates/agileplus-p2p/src/export.rs:34` (ExportError)
- `crates/agileplus-p2p/src/export/errors.rs:6` (ExportError)
- `crates/agileplus-p2p/src/import.rs:28` (ImportError)
- `crates/agileplus-p2p/src/git_merge/types.rs:6` (MergeError)
- `crates/agileplus-p2p/src/lib.rs:71` (P2pError)
- `crates/agileplus-telemetry/src/config.rs:23` (ConfigError)

**DRY recommendation:** Introduce a thin `agileplus-error-core` crate (or extend `phenotype_error_core`) with a macro or derive that auto-generates the `Io` variant and `From<std::io::Error>` impl. Alternatively, create a single `IoError` wrapper type that all crates can reuse.

---

## Cluster 5 — `#[from] serde_json::Error` repeated across 7 crates

8 occurrences of the identical `#[from] serde_json::Error` pattern appear in 7 crates:

- `crates/agileplus-integration-tests/src/common/harness.rs:30`
- `crates/agileplus-nats/src/nats_adapter.rs:57`
- `crates/agileplus-p2p/src/error.rs:15` (PeerDiscoveryError)
- `crates/agileplus-p2p/src/error.rs:34` (SyncError)
- `crates/agileplus-p2p/src/export.rs:37` (ExportError)
- `crates/agileplus-p2p/src/export/errors.rs:9` (ExportError)
- `crates/agileplus-plane/src/sync_queue.rs:30`
- `crates/agileplus-sync/src/error.rs:18`

**DRY recommendation:** Same as Cluster 4 — provide a shared macro or wrapper type for serialization errors, or collapse the `p2p` error hierarchy into a single enum that re-uses variants rather than copy-pasting them into every sub-module enum.

---

## Cluster 6 — Use-case `new()` constructor boilerplate (5 copies)

Five application-layer use cases in `agileplus-application/src/use_cases/` share the exact same constructor body:

- `advance_feature.rs:20`
- `create_epic.rs:19`
- `create_feature.rs:19`
- `create_story.rs:19`
- `transition_story.rs:18`

All are:
```rust
pub fn new(repo: Arc<dyn X>, publisher: Arc<dyn DomainEventPublisher>) -> Self {
    Self { repo, publisher }
}
```

**DRY recommendation:** Introduce a small macro (e.g., `use_case!`) in `agileplus-application` that generates the struct, fields, and `new` constructor. Or, for the simpler cases, use a generic `UseCase<R, P>` wrapper that stores the two `Arc` fields and delegates to a trait.

---

## Cluster 7 — API route `NotFound` / `BadRequest` error formatting (31 copies)

Across `agileplus-api/src/routes/*.rs` there are 20 `ApiError::NotFound(format!(...))` calls and 11 `ApiError::BadRequest(...)` calls. Every route handler repeats the same pattern:

```rust
.ok_or_else(|| ApiError::NotFound(format!("Feature '{slug}' not found")))?;
```

Occurrences:
- `routes/audit.rs:62`, `routes/audit.rs:92`
- `routes/backlog.rs:211`, `routes/backlog.rs:243`
- `routes/cycle.rs:116`, `routes/cycle.rs:191`
- `routes/events.rs:240`
- `routes/features.rs:114`, `routes/features.rs:212`, `routes/features.rs:254`
- `routes/governance.rs:61`, `routes/governance.rs:69`, `routes/governance.rs:93`, `routes/governance.rs:101`
- `routes/module.rs:88`
- `routes/work_packages.rs:83`, `routes/work_packages.rs:103`, `routes/work_packages.rs:139`, `routes/work_packages.rs:196`, `routes/work_packages.rs:239`

**DRY recommendation:** Add a helper trait or extension method on `Option<T>` in `agileplus-api/src/error.rs`:
```rust
impl<T> ApiResultExt for Option<T> {
    fn ok_or_not_found(self, msg: impl Display) -> Result<T, ApiError>;
    fn ok_or_bad_request(self, msg: impl Display) -> Result<T, ApiError>;
}
```

---

## Cluster 8 — CLI commands directly open `rusqlite::Connection` (29 calls)

29 `Connection::open` calls appear across 12 CLI command files. Each command duplicates the DB connection logic instead of using the `StoragePort` abstraction:

- `dashboard.rs:491` (test)
- `gate_add.rs:64`, `gate_add.rs:124` (test), `gate_add.rs:142` (test)
- `gate_run.rs:70`, `gate_run.rs:325` (test), `gate_run.rs:348` (test), `gate_run.rs:363` (test), `gate_run.rs:377` (test)
- `import_dagctl.rs:116`, `import_dagctl.rs:135`
- `run_record.rs:63`, `run_record.rs:166` (test), `run_record.rs:203` (test), `run_record.rs:219` (test)
- `scope_status.rs:58`, `scope_status.rs:339` (test), `scope_status.rs:351` (test), `scope_status.rs:362` (test), `scope_status.rs:370` (test)
- `sidecar_status.rs:175` (test)
- `worklog.rs` (implied via `use rusqlite::Connection`)

**DRY recommendation:** Add a `connect_db(path: &Path) -> Result<Connection>` helper in `agileplus-cli/src/db.rs` (or `agileplus-sqlite`). For production commands, migrate them to use `StoragePort` via the `agileplus-sqlite::SqliteStorageAdapter` rather than raw `rusqlite::Connection`.

---

## Cluster 9 — `MemEventStore` / `MemSnapshotStore` test fixtures duplicated (3 copies)

In-memory event and snapshot store implementations are copy-pasted across three test modules in `agileplus-p2p`:

- `export.rs:219` (MemEventStore), `export.rs:296` (MemSnapshotStore)
- `export/tests.rs:16` (MemEventStore), `export/tests.rs:89` (MemSnapshotStore)
- `import.rs:288` (MemEventStore), `import.rs:362` (MemSnapshotStore)

Each implementation is ~50–80 lines of identical `Mutex<Vec<...>>` + `EventStore`/`SnapshotStore` trait logic.

**DRY recommendation:** Extract a `agileplus-p2p/src/testing.rs` (or `tests/common/mod.rs`) module with `MemEventStore` and `MemSnapshotStore`. Re-export them from a single place. Use `#[cfg(test)]` to keep them out of the release binary.

---

## Cluster 10 — Dashboard `Config::load().unwrap_or(Config {...})` fallback (4 copies)

Four route handlers in `agileplus-dashboard/src/routes.rs` spell out the full default struct literal when config loading fails:

- `routes.rs:1231`
- `routes.rs:1255`
- `routes.rs:1863`
- `routes.rs:1912`

Each is:
```rust
let config = Config::load().unwrap_or(Config {
    plane: None,
    agents: None,
    services: None,
    dashboard: None,
});
```

**DRY recommendation:** Implement `Default` for `Config` (or add a `Config::load_or_default()` method) so the fallback becomes a one-liner: `Config::load().unwrap_or_default()`.

---

## Honorable Mentions

| Pattern | Count | Locations |
|---------|-------|-----------|
| `Config(String)` error variant | 3 | `agileplus-cache/src/lib.rs:26`, `agileplus-governance/src/error.rs:13`, `agileplus-graph/src/lib.rs:12` |
| `Database(String)` error variant | 2 | `agileplus-governance/src/error.rs:17`, `agileplus-p2p/src/error.rs:71` |
| `Internal(String)` error variant | 2 | `agileplus-api/src/error.rs:27`, `agileplus-governance/src/error.rs:53` |
| `NotFound(String)` error variant | 11 | `agileplus-api`, `agileplus-application`, `agileplus-domain` (5 variants), `agileplus-events`, `agileplus-governance`, `agileplus-graph`, `agileplus-domain/src/ports.rs` |
| `MigrationRunner::new(&conn)` | 4 | `agileplus-cli/src/commands/trace.rs:344`, `agileplus-sqlite/src/bin/seed_db.rs:31`, `agileplus-sqlite/src/lib/adapter.rs:39`, `agileplus-sqlite/src/lib.rs:83` |

---

## Summary

- **Biggest offender:** `agileplus-dashboard` — 21 functions duplicated between `routes.rs` and its newer sub-modules.
- **Cross-crate error duplication:** `#[from] std::io::Error` and `#[from] serde_json::Error` are copy-pasted into 6–7 different error enums.
- **Abstraction leak:** 12 CLI command files open raw `rusqlite::Connection` instead of using the `StoragePort` trait.
- **Test-only duplication:** `MemEventStore` / `MemSnapshotStore` are copy-pasted across 3 test modules in `agileplus-p2p`.
