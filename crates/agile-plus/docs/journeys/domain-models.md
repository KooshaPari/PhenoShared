---
fr_id: FR-DOMAIN-001
spec_slug: 002-agileplus-dashboard
spec_anchor: "#fr-domain-001"
status: pending-capture
captured_at: null
---

# Journey: Domain Event and Snapshot Models

> **Status: stub** — `FR-DOMAIN-001`. See
> `specs/002-agileplus-dashboard/FR-DOMAIN-001.md` for the source of truth
> and `specs/001-agileplus-core/bdd/domain.feature` for the executable
> acceptance scenarios.

## User story

As an **application-layer developer**, I construct `Event` and `Snapshot`
values from `agileplus-domain` so I can append domain changes and snapshot
aggregate state for fast rehydration, trusting that the store-managed
fields (`id`, `sequence`, hash bytes) start from safe defaults and that
payload / state round-trip through `serde_json` without loss.

## Steps

1. Construct a new event via `Event::new("story", 42, "Created", json, "user@host")`.
   *Stub (TODO):* `docs/journeys/assets/stubs/domain-event-construction.gif` — capture pending.
2. Construct a new snapshot via `Snapshot::new("story", 42, json, 100)`.
   *Stub (TODO):* `docs/journeys/assets/stubs/domain-snapshot-construction.gif` — capture pending.
3. Serialize both values to JSON and back, then compare payload / state.
   *Stub (TODO):* `docs/journeys/assets/stubs/domain-event-roundtrip.gif` — capture pending.
4. Inspect store-managed fields: `id == 0`, `sequence == 0`,
   `prev_hash == [0; 32]`, `hash == [0; 32]` for `Event`;
   `id == 0` for `Snapshot`.
   *Stub (TODO):* `docs/journeys/assets/stubs/domain-store-managed-defaults.gif` — capture pending.
5. Confirm timestamps are non-future and the hash-chain remains available
   for the event store to populate.
   *Stub (TODO):* `docs/journeys/assets/stubs/domain-hash-chain-handoff.gif` — capture pending.

## Traceability

| AC  | Criterion | Test / Evidence |
|-----|-----------|-----------------|
| AC1 | `Event::new` preserves identity, event_type, payload, actor | `event.rs::event_new_preserves_identity_payload_actor` |
| AC2 | `Event::new` defaults `id`, `sequence`, `prev_hash`, `hash` | `event.rs::event_new_initializes_store_managed_fields` |
| AC3 | `Event` timestamp is non-future relative to post-construction clock | `event.rs::event_new_timestamp_is_non_future` |
| AC4 | `Event` round-trips through `serde_json` | `event.rs::event_round_trips_through_serde_json` |
| AC5 | `Snapshot::new` preserves identity, state, event_sequence | `snapshot.rs::snapshot_new_preserves_identity_state_sequence` |
| AC6 | `Snapshot::new` defaults `id` to `0` | `snapshot.rs::snapshot_new_initializes_id_to_zero` |
| AC7 | `Snapshot` timestamp is non-future relative to post-construction clock | `snapshot.rs::snapshot_new_timestamp_is_non_future` |
| AC8 | `Snapshot` round-trips through `serde_json` | `snapshot.rs::snapshot_round_trips_through_serde_json` |
| AC9 | Unit tests in `crates/agileplus-domain/src/domain/{event,snapshot}.rs` cover ACs | this file + the two source files |

## Eval checklist

- [ ] `cargo test -p agileplus-domain` exits 0.
- [ ] All 9 ACs above have at least one passing test in
      `crates/agileplus-domain/src/domain/event.rs` or
      `crates/agileplus-domain/src/domain/snapshot.rs`.
- [ ] BDD scenarios in `specs/001-agileplus-core/bdd/domain.feature` are
      one-to-one with the ACs.
- [ ] No existing spec under `kitty-specs/` or
      `docs/requirements/agileplus-frnfr.md` is regressed.
- [ ] Payload / state round-trips through `serde_json` with no loss.
- [ ] Store-managed fields start at safe defaults (0 / zero hash).
- [ ] Stub GIFs referenced above exist or are tracked for capture under
      `docs/journeys/assets/stubs/`.
