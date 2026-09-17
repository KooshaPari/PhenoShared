# ADR-0007: Governance Contract Model

## Status

Accepted

## Context

AgilePlus gates feature lifecycle transitions (spec → ship) with versioned rules and
evidence requirements. That vocabulary was duplicated in `agileplus-domain` while Tracera
and other Phenotype consumers need the same semantics. ADR-0005 moved shared types to
[`traceability-core`](https://github.com/KooshaPari/phenotype-pm-core) (PM-core spine).

## Decision

1. **Canonical types** live in `traceability-core::governance`:
   `GovernanceContract`, `GovernanceRule`, `EvidenceRequirement`, `EvidenceType`,
   `PolicyRule`, and `BuiltinPolicy`.
2. **Contracts are immutable** once bound to a feature (`bound_at` set). Policy changes
   create a new contract version; prior versions remain auditable.
3. **Rules are transition-scoped**: each `GovernanceRule` names a lifecycle transition
   (e.g. `Review → Approved`) and lists required evidence (`fr_id` + `EvidenceType`) and
   optional `policy_refs`.
4. **AgilePlus owns authoring and persistence** (`agileplus-domain` re-exports,
   `agileplus-sqlite` stores). **Tracera reads** contracts for gate evaluation but does
   not author them.
5. **CLI/API surface**: `governance:check:gates`, `governance:evaluate:policy`, and
   `GetGovernanceContract` operate on spine types, not local duplicates.

## Consequences

- Single governance vocabulary across AgilePlus, Tracera, and future PM consumers.
- Feature promotion fails closed when required evidence or policies are missing.
- Contract versioning adds storage overhead but preserves audit trail for compliance.
- Local policy extensions stay in `PolicyRule` registry; contracts reference by id only.

## References

- ADR-0005: traceability-core git dependency
- `crates/traceability-core/src/governance.rs`
- `docs/specs/NFR-AP-001-traceability-requirements.md`
