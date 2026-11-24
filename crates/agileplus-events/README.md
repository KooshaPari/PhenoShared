# agileplus-events

![MSRV](https://img.shields.io/badge/MSRV-1.86-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

Event sourcing engine for AgilePlus with append-only event storage, hash-chain verification, snapshot management, aggregate replay, and query filtering.

## Public API Index

- `hash::{compute_hash, verify_chain, HashError}` - deterministic event hashing and hash-chain validation.
- `query::{EventQuery, QueryError}` - event filtering and query model.
- `replay::{Aggregate, replay_events, replay_events_since, ReplayError}` - aggregate replay from event streams.
- `snapshot::{SnapshotConfig, SnapshotStore, SnapshotError, should_snapshot}` - snapshot storage and cadence decisions.
- `store::{EventStore, EventError}` - event-store trait and storage errors.
- `EventSourcingError` - top-level error enum spanning store, hash, replay, snapshot, and query failures.

## Build

```bash
cargo build -p agileplus-events
```

