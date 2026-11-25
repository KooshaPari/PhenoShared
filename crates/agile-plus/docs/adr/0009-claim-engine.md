# ADR-0009: Claim Engine

## Status

Accepted

## Context

Two claim domains overlap in AgilePlus: (a) **traceability claims** — assertions that a
layer or transition is satisfied (evidence present, acceptance met, implementation linked);
(b) **resource claims** — exclusive agent ownership of repo/branch/worktree during execution.
Without a unified evaluation model, gates and triage drift apart.

## Decision

1. **Spine claim evaluation** (traceability): `ProgressionGate` in
   `traceability-core::contract` is the claim engine for layer advancement. It evaluates
   `GatePredicate` values (`not_approved`, `missing_acceptance`, `missing_evidence`,
   `missing_implementation`, `missing_test`) against a `GateContext` built from spine
   types (`Requirement`, `AcceptanceContract`, `CoverageMatrix`, `Evidence`).
2. **Governance claims** compose with progression: lifecycle transitions consult
   `GovernanceContract` rules first; progression gates enforce artifact-level claims second.
3. **Resource claims** (orchestration): `agileplus-triage::ClaimStore` handles TTL/heartbeat
   resource locks (`ClaimKind`: Repo, Branch, Worktree, Subproject). Structured `ClaimReason`
   ties locks to work-package ids — not free-form strings.
4. **Fail closed**: any failing predicate or expired resource claim blocks the requested
   action; no silent downgrade to ungated paths.
5. **Tracera** evaluates progression/governance claims read-only; resource claims stay
   local to AgilePlus CLI/agent runtime.

## Consequences

- One predicate vocabulary for "why was this blocked?" across API, CLI, and BDD fixtures.
- Agent coordination and traceability gates share FR/WP identifiers in claim reasons.
- Claim evaluation is deterministic and testable without I/O (pure spine functions + in-memory store).
- New predicates require a spine change and semver bump in `traceability-core`.

## References

- ADR-0007: governance contract model
- ADR-0010: acceptance contract and progression gates
- `crates/traceability-core/src/contract.rs` (`ProgressionGate`, `GateContext`)
- `crates/agileplus-triage/src/claim.rs`
