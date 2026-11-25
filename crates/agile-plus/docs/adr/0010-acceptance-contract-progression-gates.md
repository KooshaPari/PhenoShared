# ADR-0010: Acceptance Contract and Progression Gates

## Status

Accepted

## Context

Stories and features cannot reach terminal states without testable acceptance criteria linked
to evidence. Tracera owns coverage matrices; AgilePlus owns authoring. NFR-AP-001 requires
verified acceptance before `Done`. The PM-core spine adds `AcceptanceContract` and
matrix-backed satisfaction checks so both sides share one contract shape.

## Decision

1. **AcceptanceContract** (`traceability-core::contract`) binds to an `ArtifactRef` and
   holds `Criterion` entries (`id`, `test_ref`, `evidence_ref`), optional `GherkinRef`
   scenarios, and a `VerificationMethod`.
2. **Satisfaction is matrix-derived**: `AcceptanceContract::is_satisfied(matrix)` returns
   true only when every criterion maps to a `CoverageState::Covered` cell in the supplied
   `CoverageMatrix` — no ad-hoc boolean flags.
3. **Layer stack**: `Layer` enum orders Intent → IntentDoc → SpecAdr → PlanWbs → Execution
   → Evidence. `ProgressionGate` pairs `(from_layer, to_layer)` with predicates; advancement
   requires prior layer claims to pass (ADR-0009).
4. **Ship gate**: AgilePlus domain/CLI reject transitions to terminal states when acceptance
   is unsatisfied or criteria list is empty.
5. **BDD linkage**: Gherkin refs are advisory metadata; matrix coverage remains the
   authoritative satisfaction signal for automation.

## Consequences

- FR/NFR traceability and acceptance criteria share one coverage matrix (Tracera builds,
  AgilePlus consumes).
- Unsatisfied criteria are enumerable via `unsatisfied_criteria()` for agent remediation loops.
- Empty criteria contracts are always rejected — prevents "Done" without testable bar.
- Contract schema changes propagate via PM-core; AgilePlus avoids local acceptance DTOs.

## References

- ADR-0005: traceability-core git dependency
- ADR-0009: claim engine
- `crates/traceability-core/src/contract.rs`
- `docs/specs/FR-AP-001-domain-entities.md` (§ AcceptanceContract)
- `docs/specs/NFR-AP-001-traceability-requirements.md`
