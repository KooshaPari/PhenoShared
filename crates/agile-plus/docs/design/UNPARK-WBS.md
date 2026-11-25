# AgilePlus Spec-Engine Un-Park — WBS & DAG

**Status:** planning (step-1 wiring landed in `3a47520`; traceability-core green)
**Goal:** get `agileplus-domain` → `agileplus-application` → `agileplus-cli` compiling, then make `specify`/`plan`/`gate-run` runnable + dogfoodable.
**Canonical direction:** `traceability-core` is the superset spine — when domain code drifts from it, traceability-core wins unless the type is AgilePlus-local (Story/Epic/WorkPackage aggregates stay in `domain::*`).

## Error inventory (2026-07-04)

- `agileplus-domain`: 20 errors (blocks the other two)
- `agileplus-application`: 21 (mostly cascade from domain + own drift)
- `agileplus-cli`: 21 (cascade + `crate::builder`/command wiring)

Dominant domain clusters:
- **9× E0195** in `ports.rs` — `#[async_trait]` blanket impls (`impl<T: StoragePort> StoryRepository/EpicRepository/ProjectRepository for T`) have lifetime/sig drift vs the trait defs in `ports/{story,epic,project}.rs`.
- **DomainError** missing `Other` + `NoOpTransition` variants (`error.rs:27`).
- **Story.requirement_id** field dropped (`domain/story.rs:71`) but still used by `ports/story.rs:28-40` (E0609 ×2).
- **backlog.rs** E0592 duplicate `default_priority` (lines 50 & 162), E0004 non-exhaustive `Intent::Docs` match, E0034 ambiguous call.
- **cycle/{entity,state}.rs** E0599 — DomainError variant refs.
- **credentials/** — `zeroize`/`keychain` cfg imports (now that deps are wired, mostly resolve; verify).
- **intent_graph.rs / api_key.rs** — `crate::builder` (lib.rs dropped `builder`/`validate` for `adapters`/`traceability`) + `super::feature::hex_bytes` moved.

## Canonical-API decisions

- **FeatureState/Transition/LifecycleError** → canonical in `traceability_core::lifecycle` (`lifecycle.rs:17,64,79`), re-exported via domain lib.rs. Domain state_machine.rs must map its errors to `LifecycleError`, not `DomainError` (E0308 at state_machine.rs:107,115).
- **Story.requirement_id** → RESTORE as `Option<String>` on `domain::story::Story`. It's the FR-traceability key (`ports/story.rs` upsert-by-requirement-id is the whole point). Canonical = keep the field.
- **DomainError** → add `Other(String)` + `NoOpTransition` variants (domain-local error; traceability-core has its own `LifecycleError`/`GovernanceError`). Canonical = domain owns DomainError.
- **StoryRepository/EpicRepository traits** → align the trait defs (`ports/story.rs:8`, `ports/epic.rs:8`) with the `#[async_trait]` blanket impls in `ports.rs`. Canonical = the async_trait signature (the impls are the newer form).
- **builder/validate vs adapters/traceability** → lib.rs migrated to `adapters`+`traceability`; `builder.rs`/`validate.rs` are stale. Callers of `crate::builder` (intent_graph.rs, api_key.rs) should move to the traceability-core equivalent or the retained builder — decide per-caller (mostly: re-point to traceability_core::intent_graph builder).
- **EvidenceRequirement / governance types** → canonical in `traceability_core::governance` (re-exported); domain governance.rs should use those, not redefine.

## Work-packages (WBS)

| WP | title | crate | file_scope | error codes | fix | depends_on | eff |
|----|-------|-------|-----------|-------------|-----|-----------|-----|
| U1 | DomainError variants | domain | `src/error.rs` | E0599 (Other, NoOpTransition) | add 2 enum variants + Display arms | — | S |
| U2 | Restore Story.requirement_id | domain | `src/domain/story.rs`, `src/ports/story.rs` | E0609 ×2 | add `requirement_id: Option<String>` field + constructor/serde | — | S |
| U3 | backlog dedup + exhaustive | domain | `src/domain/backlog.rs` | E0592, E0004, E0034 | remove duplicate `default_priority` (keep one), add `Intent::Docs` match arm | — | S |
| U4 | ports trait/impl align | domain | `src/ports.rs`, `src/ports/{story,epic,project}.rs` | E0195 ×9 | align trait method sigs with `#[async_trait]` blanket impls (lifetimes) | U1 | M |
| U5 | builder/feature import repoint | domain | `src/intent_graph.rs`, `src/domain/api_key.rs`, `src/lib.rs` | E0432 (crate::builder, hex_bytes) | re-point to traceability_core / retained module; restore `hex_bytes` vis | U1 | M |
| U6 | cycle DomainError refs | domain | `src/domain/cycle/{entity,state}.rs` | E0599 ×3 | use restored DomainError variants (from U1) | U1 | S |
| U7 | state_machine LifecycleError map | domain | `src/domain/state_machine.rs` | E0308 ×2, E0428 (dup tests) | map to LifecycleError; remove duplicate `tests` mod | U1 | S |
| U8 | credentials cfg/deps verify | domain | `src/credentials/*` | (resolves w/ deps) | confirm zeroize/keychain compile now deps wired; gate keychain behind cfg | — | S |
| U9 | domain green gate | domain | (whole crate) | — | `cargo check -p agileplus-domain` == 0 | U1–U8 | S |
| U10 | application reconcile | application | (triage on green domain) | ~21 | re-run check; fix cascade + own drift | U9 | M |
| U11 | cli reconcile + builder cmd | cli | `src/commands/*`, `src/main.rs` | ~21 | fix cascade; wire `specify`/`plan`/`gate-run` command paths | U10 | M |
| U12 | full engine green gate | all | — | — | `cargo build -p agileplus-cli` == 0 | U11 | S |

## PR grouping (dependency-ordered, each independently mergeable)

- **PR-A "domain leaf fixes"** = U1+U2+U3+U6+U7+U8 (all the S-effort, no cross-dependency beyond U1). Small, safe, no trait surgery.
- **PR-B "domain ports + imports"** = U4+U5 (the M-effort trait/lifetime + import repoint). Depends on PR-A (needs DomainError variants). Lands U9 domain-green.
- **PR-C "application reconcile"** = U10. Depends on PR-B.
- **PR-D "cli reconcile + command wiring"** = U11+U12. Depends on PR-C. Lands full-engine-green.

(All on/after `feat/speckitty-pillars-catalog` or fresh worktrees off it; keep the P2 scorecard slices separate.)

## Post-green WBS (make it dogfoodable)

1. **DB init** — `agileplus-cli seed-requirements --db ./agileplus.db` works? confirm schema/migrations apply (the specify/plan flow writes to SQLite).
2. **Smoke `specify`** — `agileplus specify --feature speckitty-merge-gate --from-file <spec.md> --target-branch main` creates a Feature in the graph; verify governance/constitution checks run.
3. **Smoke `plan` + `tasks`** — decompose the Feature into WorkPackages + Tasks; verify DAG + file_scope written.
4. **Smoke `gate-add` + `gate-run`** — register the scorecard rubric as gate rules; confirm `gate-run` invokes a rule-interpreter (this is where the SpecKitty ScoringEngine plugs in).
5. **Wire ScoringEngine (P2.4)** into `gate-run` as the rule-interpreter (the doc-comment admits it's a stub) — the merge-gate.
6. **Dogfood** — author the SpecKitty-merge-gate spec THROUGH `agileplus specify` (not by hand), per operator directive.
