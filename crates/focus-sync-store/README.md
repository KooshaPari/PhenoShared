# focus-sync-store

Multi-device sync store trait and in-memory implementations. Defines abstract sync interface for syncing state (rules, tasks, wallet, penalties) across devices. Backend-agnostic; implementations can use CloudKit (iOS/macOS), CRDT replication, or custom servers.

## Purpose

Enables cross-device sync so user changes on iPhone propagate to iPad and Android. Uses last-writer-wins (LWW) conflict resolution with a 30-second grace period. Wallet and penalty mutations are synced as deltas in a log (accumulates credits/penalties).

## Key Types

- `SyncRecord` — id, record_type, device_id, modified_at, payload_hash, version
- `SyncStore` trait — push, pull, conflict resolution
- `ConflictResolution` enum — LWW, AcceptLocal, AcceptRemote, PromptUser
- In-memory implementation for testing

## Entry Points

- `SyncStore::push()` — send local change to sync backend
- `SyncStore::pull()` — fetch remote changes with conflict detection
- Conflict resolution via timestamp + grace period (30s)

## Functional Requirements

- Multi-device sync with LWW conflict resolution
- Synced: Rules, Tasks, Wallet, Penalties
- Non-synced: Audit (device-local), Tokens (Keychain per-device)

## Consumers

- iOS app (CloudKit integration, planned)
- Android app (sync backend TBD, planned)
- `focus-ffi` (exposes sync APIs to native)
