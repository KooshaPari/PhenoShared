# Workspace Crate Dependency Graph

This document describes the crate layout, purpose, and inter-crate dependency
relationships across the SessionLedger repository.

---

## Crates

| Crate | Path | Workspace Root | Purpose |
|-------|------|----------------|---------|
| `session-ledger` | `.` (repo root) | **Yes** (primary) | Core library: compile / distill agent sessions into injectable continuation bundles (Acceptance, Contract, Context, Intent). Provides ingestion adapters, distillation pipeline, envelope crypto, OKF export, schema migration, PII redaction, i18n, and viewer stubs. |
| `sl-viewer` | `crates/sl-viewer` | No (member) | Dioxus desktop + web viewer for SessionLedger compiled bundles. Provides bundle list / detail / search / replay / memory / history views, corpus loading (SQLite, Parquet), live daemon feed, and command palette. |
| `sl-daemon` | `crates/sl-daemon` | **Yes** (isolated) | Background daemon that watches session directories, compiles sessions via the core library, and exports OKF documents over an SSE HTTP bridge (axum). Includes CLI, OpenTelemetry tracing, and platform allocators. |

### Why `sl-daemon` is its own workspace root

`sl-daemon` is excluded from the primary workspace (`Cargo.toml` line 5:
`exclude = ["crates/sl-daemon"]`) and declares its own `[workspace]` section.
This is intentional: `sl-viewer` pulls `dioxus-desktop -> wry -> webkit2gtk-sys`,
which **cannot resolve on macOS**. Isolating `sl-daemon` into a separate
workspace lets `cargo test -p sl-daemon` / `cargo build` work on macOS without
being dragged into the viewer's platform-specific dependency graph.

---

## Inter-Crate Dependency Diagram

```
+-----------------------------------------+
|           sl-daemon (workspace root)     |
|  watches dirs, compiles, exports OKF    |
|  axum SSE bridge, CLI, OTel, jemalloc   |
+-----------------+-----------------------+
                  |
                  | path dep (crate = "../..")
                  v
+-----------------------------------------+
|        session-ledger (core library)    |
|  ingestion -> distill -> export pipeline|
|  domain model, schema, envelope crypto  |
|  PII redact, i18n, inject, ports        |
+-----------------+-----------------------+
                  ^
                  | path dep (crate = "../..")
                  |
+-----------------------------------------+
|           sl-viewer (workspace member)  |
|  Dioxus desktop + web UI               |
|  bundle list/detail/search/replay       |
|  corpus loading, live daemon feed       |
+-----------------------------------------+
```

### Direction summary

```
sl-daemon  ---depends on-->  session-ledger  <--depends on---  sl-viewer
```

Both `sl-daemon` and `sl-viewer` depend on the core `session-ledger` crate via
relative path dependencies. Neither leaf crate depends on the other; the core
crate has **zero** internal workspace dependencies (it is self-contained).

---

## Dependency Matrix

| Dependent | Depends On | Dependency Type | Feature Passthrough |
|-----------|-----------|-----------------|---------------------|
| `sl-viewer` | `session-ledger` | `path = "../.."` | `compressed-sessions` enables `session-ledger/compress`; `sqlite` enables `session-ledger/sqlite` |
| `sl-daemon` | `session-ledger` | `path = "../.."` | `compress` enables `session-ledger/compress`; `sqlite` enables `session-ledger/sqlite` |

---

## Feature Propagation

### `sl-viewer` -> `session-ledger`

| Viewer Feature | Activates on `session-ledger` | Also Pulls |
|----------------|-------------------------------|------------|
| `compressed-sessions` (on by default via `desktop`) | `compress` | `zstd` |
| `sqlite` | `sqlite` | `rusqlite` (bundled) |

### `sl-daemon` -> `session-ledger`

| Daemon Feature | Activates on `session-ledger` | Also Pulls |
|----------------|-------------------------------|------------|
| `compress` (default on) | `compress` | `zstd` |
| `sqlite` | `sqlite` | `rusqlite` (bundled) |

---

## Module Map (session-ledger core)

```
session-ledger/src/
  lib.rs               -- crate root
  distill/              -- session distillation pipeline
    mod.rs
    dedup_compiler.rs   -- cross-session dedup during distillation
    extractor.rs        -- extract continuation signals from sessions
    memory_writer.rs    -- memory/context writer
    token_estimator.rs  -- token counting for budgeting
  domain/               -- core domain types
    mod.rs
    contract.rs         -- Acceptance / Contract bundles
    context.rs          -- Context bundle
    dedup.rs            -- deduplication helpers
    intent.rs           -- Intent bundle
    merge.rs            -- lost-work localization & merge
    session.rs          -- session representation
    worklog.rs          -- work log domain model
  envelope.rs           -- soft-envelope crypto (sha2 keystream, C02)
  export/               -- OKF export
    mod.rs
    okf.rs              -- OKF document writer
  i18n.rs               -- i18n stub (pre-Fluent)
  i18n_fluent.rs        -- Fluent catalog i18n (C01 L16)
  ingestion/            -- session ingestion adapters
    mod.rs
    claude_code.rs      -- Claude Code session adapter
    codex.rs            -- Codex session adapter
    cursor.rs           -- Cursor session adapter
    forge.rs            -- Forge ingestion (optional, feature-gated)
    json_source.rs      -- generic JSONL source
  inject.rs             -- bundle injection helpers
  pii_redact.rs         -- PII redaction
  ports/                -- port abstractions (hexagonal)
  schema/               -- schema definition & migration
    mod.rs
    migrate.rs          -- schema migration logic
  viewer/               -- viewer integration stubs
    mod.rs
```

---

## Module Map (sl-viewer)

```
sl-viewer/src/
  lib.rs                -- crate root
  app.rs                -- main Dioxus application shell
  async_states.rs       -- async state management
  bundle_diff.rs        -- bundle comparison / diff view
  bundle_list.rs        -- bundle list panel
  cli_help.rs           -- CLI help overlay
  command_palette.rs    -- keyboard command palette
  corpus_cta.rs         -- corpus call-to-action
  corpus_loader.rs      -- corpus discovery & loading
  corpus_paths.rs       -- persisted corpus path management
  corpus_tab.rs         -- corpus browser tab
  daemon_url.rs         -- daemon URL resolution
  detail_pane.rs        -- bundle detail pane
  fixture.rs            -- test fixture helpers
  help_overlay.rs       -- help overlay UI
  history_tab.rs        -- history navigation tab
  live_feed.rs          -- live SSE feed from daemon
  memory_tab.rs         -- memory / context tab
  menu.rs               -- application menu
  mock_data.rs          -- mock data for development
  parquet_source.rs     -- Parquet ingestion (optional)
  replay_view.rs        -- session replay viewer
  search_view.rs        -- advanced search UI
  settings_tab.rs       -- settings panel
  unfinished_tab.rs     -- unfinished work tracker
  web_exports.rs        -- WASM/web export helpers
```

---

## Module Map (sl-daemon)

```
sl-daemon/src/
  lib.rs                -- crate root (async main entry)
  resolver.rs           -- path / bundle resolution
  tag.rs                -- bundle tagging (add / list)
  traceparent.rs        -- W3C TraceParent propagation
  traceparent_sidecar.rs-- traceparent sidecar file helpers
  update_check.rs       -- version update checker
  validation.rs         -- post-message / bundle validation
  watcher.rs            -- filesystem watcher (notify crate)
  worker.rs             -- background compilation worker
  shutdown.rs           -- graceful shutdown handling
  otel_metrics.rs       -- OpenTelemetry metrics setup
```

---

## Build Graph (non-code)

```
sl-viewer  <-- builds on macOS/Windows/Linux (Dioxus desktop or web)
sl-daemon  <-- builds on macOS/Unix (FSEvent); Windows (mimalloc)
                 excluded from parent workspace to avoid webkit2gtk-sys
```
