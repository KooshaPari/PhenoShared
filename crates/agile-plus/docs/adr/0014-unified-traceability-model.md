# ADR-0014: Unified Traceability Model

## Status

Proposed

## Context

AgilePlus uses a 5-layer `trace.json` schema, FR/NFR catalogs, and IntentGraph derivatives.
Tracera uses Requirement / Artifact / TraceLink / CoverageMatrix. ADR-0005 unified spine
types; ADR-0010 binds acceptance to matrix coverage. NFR-AP-001 requires bidirectional
trace confirmation.

The harmonization track must define how these models **compose** without duplicate or
conflicting links — especially after Tracera embeds AgilePlus (ADR-0011).

## Decision

1. **Single ID namespace:** `RequirementId` (`FR-xxx`, `NFR-xxx`) is canonical. Imported
   ids (`REQ-XX`, `IC-##`, OpenSpec capability ids) map via harmonizer alias table stored
   in feature `meta.json`.
2. **Intent source vs evidence projection:**
   - **Source of intent:** `kitty-specs/` markdown + FR catalogs (ADR-0012).
   - **IntentGraph:** validated DAG derivative (ADR-0008); node ids MUST match spine ids.
   - **TraceLink graph:** runtime evidence mesh; Tracera builds and queries.
   - **trace.json:** per-change CI evidence bundle consumed by trace-validator.
3. **Edge semantics union:**

   | Semantics | IntentGraph | TraceLink | trace.json |
   |-----------|-------------|-----------|------------|
   | implements | `Edge::Implements` | `IMPLEMENTS` | code anchor |
   | verifies | `Edge::Verifies` | `VERIFIES` | test ref |
   | derives | `Edge::Derives` | `DERIVES` | — |
   | documents | `Edge::Documents` | `DOCUMENTS` | spec path |

4. **CoverageMatrix authority for acceptance:** `AcceptanceContract::is_satisfied(matrix)`
   (ADR-0010) remains the automation gate. Tracera derives matrix from TraceLinks; AgilePlus
   enforces ship denial.
5. **Bidirectional confirmation:** Internal `TraceabilityPort` (post-embed: in-process, not
   network) MUST confirm link creation before AgilePlus persists `TraceRef` locally
   (NFR-AP-001).
6. **Audit chain:** Hash-chained worklogs and events (ADR-004) are L0 evidence artifacts
   linkable from TraceLink `DOCUMENTS` edges.

## Consequences

- trace-validator and Tracera ingest share predicate vocabulary from spine.
- Impact analysis queries TraceLink graph; remediation loops use `unsatisfied_criteria()`.
- Legacy Tracera-only links require one-time harmonize import with id mapping.
- Graph projection failures surface as FSM gate failures, not warnings.

## References

- [`UNIFIED_PM_MODEL.md`](../harmonization/UNIFIED_PM_MODEL.md) §6
- ADR-0005, ADR-0008, ADR-0010
- ADR-0011: Tracera embeds AgilePlus
- `docs/specs/NFR-AP-001-traceability-requirements.md`
- [`FRAMEWORK_ANALYSIS.md`](../harmonization/FRAMEWORK_ANALYSIS.md) §4.3 traceability union
