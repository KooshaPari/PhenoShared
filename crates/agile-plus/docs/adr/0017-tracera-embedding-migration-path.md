# ADR-0017: Tracera Embedding Migration Path

## Status

Proposed

## Context

ADR-0011 mandates that Tracera embed AgilePlus and MUST NOT run standalone. Current
production Tracera deployments:

- Standalone Go binary + Postgres (or equivalent) graph store.
- Dependency on `traceability-core` / shared types only.
- Local `ProgressionGate` evaluation and checklist-style governance UI.
- Optional sidecar calls to AgilePlus — not a hard dependency.

AgilePlus deployments may run without Tracera today. Migration must not break existing
AgilePlus-only workflows.

## Decision

### Phase 0 — Documentation and spine alignment (current harmonization track)

- Publish [`UNIFIED_PM_MODEL.md`](../harmonization/UNIFIED_PM_MODEL.md) and ADRs 0011–0016.
- Freeze new standalone Tracera governance features; direct effort to embed design.
- Ensure `traceability-core` / `pm-core` releases include all predicate types both sides need.

### Phase 1 — Hard dependency wiring (flagged)

- Introduce `TRACERA_AGILEPLUS_REQUIRED=true` (default `false` during transition).
- Tracera startup probes AgilePlus gRPC/embedded library health; fails fast when flag true.
- Route `EvaluateGovernance` and FSM transition checks to AgilePlus; keep local fallback
  behind flag for one release cycle only.

### Phase 2 — In-process embed

- Ship `tracera-agileplus-adapter` crate/library consumed by Tracera Go via FFI or sidecar
  default-on (process-compose bundle per ADR-010).
- Remove duplicated `ProgressionGate` evaluation from Tracera Go services.
- Tracera graph ingest subscribes to AgilePlus domain events (NATS JetStream, ADR-006).

### Phase 3 — Standalone removal

- Default `TRACERA_AGILEPLUS_REQUIRED=true`; remove fallback checklist path.
- Tracera Helm/docker images declare AgilePlus as required companion container.
- Document AgilePlus-only mode explicitly as "Tracera disabled."

### Phase 4 — Data migration

- Import existing Tracera Requirement/TraceLink graphs into AgilePlus `TraceabilityPort`
  with id alias table (ADR-0014).
- Reconcile orphan links: reject or quarantine until mapped to canonical `RequirementId`.
- One-time `tracera migrate --to-embedded` CLI.

### AgilePlus-only consumers

- No migration required. Tracera enablement is opt-in via compose profile or feature flag.
- `trace-validator` and kitty-specs workflows unchanged.

## Consequences

- ~2 release cycles of dual-path maintenance during Phase 1–2.
- Ops teams must co-version Tracera + AgilePlus images.
- Standalone Tracera SaaS/offers sunset after Phase 3.
- Migration CLI required for long-lived graph data.

## Rollback

- Phase 1 flag revert restores checklist fallback (time-limited).
- Post-Phase 3 rollback requires restored standalone Tracera image pin — not supported
  for new installs.

## References

- ADR-0011: Tracera embeds AgilePlus
- ADR-0014: unified traceability model
- ADR-0006: process-compose local orchestration
- ADR-0006 (workspace): spec harmonizer for id mapping during import
- [`UNIFIED_PM_MODEL.md`](../harmonization/UNIFIED_PM_MODEL.md) §1.2
- `docs/audit/XREPO_DRY.md` §7.1 (`tracera-core` → phenoShared)
