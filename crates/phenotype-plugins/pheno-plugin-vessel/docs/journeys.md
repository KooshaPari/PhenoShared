# User Journeys — pheno-plugin-vessel

This document describes the key developer journeys for consumers of the
`phenotype-vessel` crate.

---

## Journey 1: Register and look up a VCS plugin

**Actor:** Host application developer embedding the PhenoPlugins SDK.

**Goal:** Register a Git adapter and retrieve it by name for use in a feature
workflow.

**Steps:**

1. Add `pheno-plugin-core` and `pheno-plugin-git` to `Cargo.toml`.
2. Instantiate `PluginRegistry::new()`.
3. Construct `GitPlugin::new(repo_path)` and call `registry.register_vcs(Box::new(plugin))`.
4. Call `registry.finalize()` to lock the registry against further mutations.
5. Retrieve the adapter: `registry.vcs("git").expect("git adapter registered")`.
6. Call `vcs.create_worktree("feat/my-feature", "WP01").await` — receives
   the worktree path.

**Success criteria:**
- `register_vcs` returns `Ok(())`.
- A second `register_vcs` call with the same name returns
  `Err(AlreadyRegistered)`.
- After `finalize()`, any `register_*` call returns `Err(Initialization)`.
- `registry.health_check().await` returns `Ok(())` when the git repo is
  accessible.

---

## Journey 2: Persist and retrieve a feature via the SQLite adapter

**Actor:** Host application developer using `pheno-plugin-sqlite`.

**Goal:** Create a feature record, add a work package, and append an audit
entry — all using the `StoragePlugin` trait.

**Steps:**

1. Instantiate `SqliteStoragePlugin::new("~/.omniroute/agileplus.db")`.
2. Register it: `registry.register_storage(Box::new(plugin))`.
3. Retrieve: `let storage = registry.storage("sqlite").unwrap()`.
4. Call `storage.create_feature(&json!({ "slug": "feat-001", "name": "My feature", "state": "draft" })).await`.
5. Call `storage.create_work_package(&json!({ "feature_id": 1, "title": "WP01", "state": "backlog", "priority": "high" })).await`.
6. Call `storage.append_audit_entry(&json!({ "feature_id": 1, "entry_type": "created", "actor": "agent" })).await`.
7. Retrieve the trail: `storage.get_audit_trail(1).await`.

**Success criteria:**
- Feature row is created with auto-incremented id.
- Work package is linked via `feature_id` foreign key.
- Audit trail contains the created entry.
- Duplicate `slug` on a second `create_feature` call returns
  `Err(AlreadyExists)` or a storage-level constraint error.

---

## Journey 3: Health check across a mixed registry

**Actor:** Operator monitoring the plugin subsystem.

**Goal:** Verify all registered adapters are healthy in a single async call.

**Steps:**

1. Build a registry with both a VCS and a storage adapter.
2. Call `registry.health_check().await`.
3. Inspect the result: `Ok(())` means all adapters passed their individual
   `health_check()` implementations.

**Observability:** Each adapter's health check emits a `tracing` span at the
`DEBUG` level. Wire a `tracing_subscriber` to capture structured health
events.

**Failure path:** If any adapter returns `Err(…)`, `health_check` returns
that error immediately (fail-fast). The error carries `ErrorCode` and a
`recovery_hint()` to guide remediation.

---

## Journey 4: Error handling with typed codes

**Actor:** Host application error handler.

**Goal:** Map `PluginError` to a structured error response without parsing
message strings.

**Steps:**

1. Receive a `PluginError` from any trait method.
2. Call `err.code()` to get the `ErrorCode` enum variant.
3. Call `err.code().as_str()` to get the stable string token
   (e.g. `"PLUGIN_REG_002"`) for logging.
4. Call `err.recovery_hint()` to get a human-readable remediation suggestion.

**Example:**

```rust
match registry.register_vcs(plugin) {
    Ok(()) => { /* proceed */ }
    Err(e) => {
        tracing::error!(
            error.code = e.code().as_str(),
            error.hint = e.recovery_hint(),
            "Plugin registration failed: {}", e,
        );
    }
}
```
