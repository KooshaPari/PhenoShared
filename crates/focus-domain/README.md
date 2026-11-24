# focus-domain

Canonical domain entities, IDs, aggregate roots, and invariants. Pure types with no persistence, no I/O. Defines `UserId`, `DeviceId`, `User`, `Device`, `Account` structures and domain-level validation logic.

## Purpose

Centralizes domain modeling so all layers (storage, API, rules, scheduler) use the same vocabulary and enforce the same invariants. Entities are value types or newtype wrappers (UUIDs) with no dependencies on external crates beyond serde/uuid.

## Key Types

- `UserId(Uuid)` / `DeviceId(Uuid)` — Strong type IDs
- `User` — aggregate root with devices, account, subscription, entitlements
- `Device` — model with device_id, name, platform, last_seen
- `Account` — subscription tier, feature gates, usage counters
- `DomainError` — validation failures (invalid state, invariant violation)

## Entry Points

- Type constructors for all entities (newtype wrappers for UUIDs)
- `User::validate()` / `Device::validate()` — invariant checks
- `DomainError` variants for all failure cases

## Functional Requirements

- Pure domain logic
- No I/O or persistence
- Invariants enforced at construction (not after)

## Consumers

- All storage adapters (conversions to/from domain types)
- `focus-eval`, `focus-rules`, `focus-scheduler` (domain context)
- `focus-entitlements` (subscription/feature gate checks)
