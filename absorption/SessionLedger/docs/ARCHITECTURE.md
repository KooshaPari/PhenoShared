# SessionLedger Architecture

## Workspace (3 crates)

```
SessionLedger/
  crates/sl-daemon/   Core daemon (ingest, store, export, query)
  crates/sl-viewer/   Dioxus desktop viewer
  crates/sl-kms/      Key management for envelope crypto
  web/                Web viewer
  migrations/         SQL migrations
  schema/             Typed row structs
```

## Dependency Graph

```
sl-daemon --> sl-kms (encryption)
sl-viewer --> sl-daemon (data access)
sl-daemon --> rusqlite, sha2, zstd, tracing
```

## Module Responsibilities (sl-daemon)

| Module | Responsibility |
|---|---|
| plugin.rs | IngestionAdapter + Exporter + Port traits |
| event.rs | EventBus + typed pub/sub |
| archive.rs | OKF bundle archive/restore |
| discovery.rs | Auto-discover JSONL sources |
| metrics.rs | Prometheus metrics endpoint |
