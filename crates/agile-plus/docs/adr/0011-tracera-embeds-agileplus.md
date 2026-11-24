# ADR-0011: Tracera Embeds AgilePlus

## Status

Proposed

## Context

AgilePlus and Tracera evolved as sibling products with a **shared vocabulary spine**
(`traceability-core` / `phenotype-pm-core`, ADR-0005) but **separate runtimes**.

**Current Tracera posture (pre-embed):**

- Depends on `traceability-core` types only — not on AgilePlus CLI, domain FSM, or SQLite store.
- Runs as a standalone Go API with its own persistence.
- Treats governance as a **checklist**: evaluates `ProgressionGate` predicates and coverage
  cells read-only; does not own `FeatureState` transitions or `GovernanceContract` authoring.
- Cannot block or advance work — it reports link health and matrix coverage.

**AgilePlus posture:**

- **Process machine**: `FeatureState` FSM, versioned `GovernanceContract` (ADR-0007),
  `IntentGraph` authoring (ADR-0008), unified claim engine (ADR-0009), and
  `AcceptanceContract` satisfaction via coverage matrix (ADR-0010).
- Owns work execution: WP lanes, resource claims, worktrees, audit chain.
- Optionally standalone for teams that need process control without Tracera graph UI.

[`FRAMEWORK_ANALYSIS.md`](../harmonization/FRAMEWORK_ANALYSIS.md) and
[`UNIFIED_PM_MODEL.md`](../harmonization/UNIFIED_PM_MODEL.md) conclude that evidence
projection (Tracera) without process ownership (AgilePlus) produces checklist governance
that drifts from the FSM and allows illegal state transitions when Tracera is consulted
in isolation.

## Decision

1. **Tracera embeds AgilePlus.** Tracera MUST depend on AgilePlus process runtime
   (directly or via a shared `pm-core` crate that AgilePlus owns and publishes).
2. **Tracera MUST NOT run without AgilePlus.** Starting Tracera without an available
   AgilePlus process backend (local embedded library, sidecar, or in-process adapter) is
   a fatal configuration error — not a degraded read-only mode.
3. **AgilePlus remains optionally standalone.** Teams may run AgilePlus CLI/API without
   Tracera for process control, spec authoring, and CI gates. Tracera is an optional
   **evidence and graph projection layer** on top of AgilePlus — not the reverse.
4. **Ownership split:**
   - **AgilePlus owns:** FSM, governance authoring, claim evaluation side effects,
     WP execution, audit/event store, harmonizer ingress.
   - **Tracera owns (embedded):** TraceLink graph storage/query, CoverageMatrix
     derivation, impact analysis UI/API, compliance RTM export — all fed by AgilePlus events.
5. **Spine crate role:** `traceability-core` / `pm-core` holds shared **types and pure
   predicates**; AgilePlus owns **mutation and enforcement**. Tracera MUST NOT fork
   enforcement logic.

## Consequences

### Positive

- Single source of truth for lifecycle state; no split-brain between checklist and FSM.
- Governance contracts authored once in AgilePlus; Tracera visualizes satisfaction.
- Agent workflows see one denial reason chain (governance → progression → resource → CI).
- Compliance exports (Waterfall RTM vocabulary) derive from an enforced process machine.

### Negative

- Tracera deployments gain an AgilePlus dependency — larger ops footprint, version coupling.
- Existing standalone Tracera installations require migration (ADR-0017).
- Tracera cannot be marketed or deployed as an independent traceability-only product.

### Neutral

- ADR-0007 §4 ("Tracera reads contracts") is refined: Tracera still does not **author**
  contracts, but MUST **subscribe** to AgilePlus enforcement — not re-implement it.
- `traceability-core` git dependency (ADR-0005) remains; embed adds runtime coupling beyond types.

## Alternatives Considered

| Alternative | Rejected because |
|-------------|------------------|
| Status quo: shared types, separate runtimes | Checklist governance drifts from FSM; dual ops burden |
| AgilePlus embeds Tracera | Process machine is authoritative; evidence is derivative |
| Merge repos into one binary | Loses Go graph stack; unnecessary big-bang |
| Tracera re-implements FSM in Go | Third copy of transition rules; guaranteed drift |

## References

- [`UNIFIED_PM_MODEL.md`](../harmonization/UNIFIED_PM_MODEL.md) §1.2, §2 P1
- ADR-0005: traceability-core git dependency
- ADR-0007: governance contract model
- ADR-0009: claim engine
- [`FRAMEWORK_ANALYSIS.md`](../harmonization/FRAMEWORK_ANALYSIS.md) §4.3
