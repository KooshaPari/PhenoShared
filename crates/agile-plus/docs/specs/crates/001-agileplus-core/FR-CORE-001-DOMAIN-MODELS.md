# FR-CORE-001-DOMAIN-MODELS — Event and Snapshot Domain Models

> Spec anchor: `specs/001-agileplus-core/`
> Status: PROPOSED → accepted on `cargo test -p agileplus-domain` pass
> Crate: `agileplus-domain`
> Note: this FR is the canonical anchor for the domain-model BDD feature.
> A peer copy currently lives at `specs/002-agileplus-dashboard/FR-DOMAIN-001.md`
> from an earlier misfile; both are retained per "never delete" governance
> and refer to the same `agileplus-domain` implementation. The 001 anchor
> is the source of truth going forward.

## Description

The `agileplus-domain` crate exposes stable event-sourcing primitives for
domain event append and aggregate rehydration. `Event` captures append-only
entity changes with payload, actor, timestamp, hash-chain, and sequence
metadata. `Snapshot` captures a point-in-time aggregate state at a known
event sequence. Both types must preserve their constructor-supplied fields,
initialize store-managed fields to safe defaults, expose a non-future
construction timestamp, and round-trip cleanly through `serde_json`.

## Acceptance Criteria

| AC  | Criterion |
|-----|-----------|
| AC1 | `Event::new(entity_type, entity_id, event_type, payload, actor)` preserves entity identity, event type, payload, and actor. |
| AC2 | `Event::new` initializes store-managed fields to safe defaults: `id == 0`, `sequence == 0`, `prev_hash == [0; 32]`, and `hash == [0; 32]`. |
| AC3 | `Event` timestamps are generated at construction time and are not in the future relative to the caller's post-construction clock. |
| AC4 | `Event` round-trips through `serde_json` without losing payload, identity, sequence, or hash metadata. |
| AC5 | `Snapshot::new(entity_type, entity_id, state, event_sequence)` preserves entity identity, aggregate state, and event sequence. |
| AC6 | `Snapshot::new` initializes store-managed `id` to `0`. |
| AC7 | `Snapshot` timestamps are generated at construction time and are not in the future relative to the caller's post-construction clock. |
| AC8 | `Snapshot` round-trips through `serde_json` without losing state, identity, or event sequence. |
| AC9 | Unit tests in `crates/agileplus-domain/src/domain/{event,snapshot}.rs` prove the Event/Snapshot contracts above. |

## Traceability

- Spec: `specs/001-agileplus-core/FR-CORE-001-DOMAIN-MODELS.md`
- Code: `crates/agileplus-domain/src/domain/event.rs`
- Code: `crates/agileplus-domain/src/domain/snapshot.rs`
- BDD: `specs/001-agileplus-core/bdd/domain.feature`
- Tests: `crates/agileplus-domain/src/domain/event.rs`
- Tests: `crates/agileplus-domain/src/domain/snapshot.rs`
- Journey: `docs/journeys/domain-models.md`
- Peer (legacy): `specs/002-agileplus-dashboard/FR-DOMAIN-001.md`
