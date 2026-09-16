# focus-storage

Storage ports and SQLite implementations. Defines abstract traits (`RuleStore`, `EventStore`, `WalletStore`, `PenaltyStore`, `AuditStore`) and concrete SQLite adapters. Migrations managed in `sqlite/migrations/` directory.

## Purpose

Abstracts persistence layer so core logic depends on traits, not concrete databases. Enables testing with in-memory implementations and swapping storage backends. SQLite is the shipped production implementation, but the trait-based design supports future backends (CloudKit, custom servers).

## Key Types

- `RuleStore` trait — upsert/delete/list rules, query by ID
- `EventStore` trait — ingest events with dedupe, query by cursor, list events
- `WalletStore` trait — query balance, append mutations
- `PenaltyStore` trait — query state, append mutations
- `AuditStore` trait — append records, verify chain, query range
- `SqlitePool` — connection pool with migrations

## Entry Points

- `SqlitePool::new()` — open database + run migrations
- All trait methods implemented by SQLite adapters
- `SqlitePool::close()` — graceful shutdown

## Functional Requirements

- FR-DATA-001 (SQLite storage + migrations)
- FR-DATA-002 (Audit append on mutation)
- FR-DATA-003 (Chain verification)

## Consumers

- All core layers (`focus-rules`, `focus-eval`, `focus-rewards`, etc.)
- `focus-sync::SyncOrchestrator` (event sink)
- Native apps via FFI (state access/updates)
