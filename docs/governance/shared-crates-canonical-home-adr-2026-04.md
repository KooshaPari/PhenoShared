---
title: ADR — Canonical home for shared Rust infrastructure crates
status: Accepted
date: 2026-04-25
supersedes: cross-project-reuse-audit-2026-04-25.md (triplicate-home finding)
adr-id: SHARED-CRATES-CANONICAL-2026-04
owners: phenotype-org / shared-platform
---

## Background

The 2026-04-25 cross-project reuse audit
(`docs/governance/cross-project-reuse-audit-2026-04-25.md`) flagged a
"three-canonical-home" problem: `phenotype-event-sourcing`,
`phenotype-cache-adapter`, `phenotype-state-machine`, and
`phenotype-policy-engine` are each defined in **multiple parallel Cargo
workspaces** with no single source of truth. Filesystem reconnaissance on
2026-04-25 confirms the crates physically exist in:

| Home | Repo (origin) | Has crates? | Last-touched |
|------|---------------|-------------|--------------|
| `phenoShared` | `<REDACTED>/phenoShared` | ES, CA, SM, PE | 2026-04-25 (today) |
| `pheno` | `<REDACTED>/pheno` | ES, CA, SM, PE | 2026-03-31 |
| `PhenoProc` | `<REDACTED>/PhenoProc` | ES, CA, SM, PE (+ nested `crates/phenotype-shared/crates/*`) | 2026-04-03 |
| `DataKit/rust` | `<REDACTED>/DataKit` | ES, CA | 2026-04-05 (snapshot) |
| `HexaKit/crates` + `PhenoKits/HexaKit/crates` | `<REDACTED>/HexaKit`, `PhenoKits` | SM, PE (+ ES, CA in PhenoKits) | 2026-03-31 |
| `AuthKit/rust` | `<REDACTED>/AuthKit` | PE | snapshot |
| `ResilienceKit/rust` | `<REDACTED>/ResilienceKit` | SM | snapshot |
| `hwLedger/vendor` | `<REDACTED>/hwLedger` | ES (vendored copy) | snapshot |
| `phenotype-shared` (intended canonical per audit) | `<REDACTED>/phenotype-shared` | **none locally; remote `main` has empty `members = []`** | dormant |

ES = event-sourcing, CA = cache-adapter, SM = state-machine, PE = policy-engine.

API drift is already observed (e.g. `phenotype-event-sourcing/src/lib.rs`
is 26 LOC in `pheno` and `PhenoKits/HexaKit`, but 42 LOC in `phenoShared`
and 57 LOC in `PhenoProc`/`DataKit`). All declare `version = "0.2.0"` or
inherit from workspace, so semver alone cannot distinguish them.

External consumers outside these workspaces: **0** (all existing dep
declarations are internal `path = "crates/..."` references). This means
consolidation has near-zero blast radius.

## Decision

**Canonical home: `phenoShared` (`github.com/KooshaPari/phenoShared`).**

Rationale, in order of weight:

1. **Activity:** the only home with same-day commits explicitly evolving
   the crates (`refactor(state): adopt versioning pattern —
   phenotype-event-sourcing`, 2026-04-25).
2. **Completeness:** ships all four target crates plus adjacent shared
   infrastructure (`phenotype-port-interfaces`, `phenotype-domain`,
   `phenotype-application`, `phenotype-health`, `phenotype-retry`,
   `phenotype-policy-engine-py`).
3. **Charter fit:** dedicated org-shared workspace; not coupled to a
   product (unlike `PhenoProc`, `pheno`, `DataKit`, `AuthKit`,
   `ResilienceKit`, `HexaKit`, `hwLedger`).
4. **`phenotype-shared` is paper-only:** remote `main` has
   `members = []`; the local checkout's origin actually points at
   `PhenoKits`. It cannot serve as canonical without first being
   re-bootstrapped, which is strictly more work than adopting the
   already-populated `phenoShared`.

The audit doc's earlier preference for "phenotype-shared" is superseded
by this ADR on the basis of filesystem reality.

## Migration matrix

| Crate | Source homes (to deprecate) | Target version source | Consumers to update | Notes |
|-------|------------------------------|------------------------|----------------------|-------|
| `phenotype-event-sourcing` | `pheno`, `PhenoProc` (×2 nested), `DataKit/rust`, `PhenoKits/HexaKit`, `hwLedger/vendor` | `phenoShared/crates/phenotype-event-sourcing` (42 LOC, 2026-04-25) | 6 internal workspace refs; 0 external | Reconcile 26→42→57 LOC variants; `phenoShared` is mid-evolution — finalize API before extraction |
| `phenotype-cache-adapter` | `pheno`, `PhenoProc` (×2), `DataKit/rust`, `PhenoKits/HexaKit` | `phenoShared/crates/phenotype-cache-adapter` | 5 internal | API parity check required |
| `phenotype-state-machine` | `pheno`, `PhenoProc` (×2), `ResilienceKit/rust`, `HexaKit/crates`, `PhenoKits/HexaKit` | `phenoShared/crates/phenotype-state-machine` | 6 internal | `ResilienceKit` is a snapshot; verify no domain-specific divergence |
| `phenotype-policy-engine` | `pheno`, `PhenoProc` (×2), `HexaKit/crates`, `PhenoKits/HexaKit`, `AuthKit/rust` | `phenoShared/crates/phenotype-policy-engine` | 6 internal | `AuthKit` may have auth-specific extensions — capture as feature flag in canonical, do not fork |

Total deduplications: **23 redundant crate copies** across 8 host
workspaces. **Zero external (cross-workspace) consumer Cargo.toml
edits required** — all dependencies are local `path =` refs that will
be replaced by `git = "...phenoShared..."` or path refs to a shared
worktree, depending on workspace strategy chosen at implementation time.

## Deprecation plan

For each non-canonical home listed above, the implementation task MUST:

1. Add `DEPRECATED.md` at the root of each duplicated crate directory:
   ```
   ---
   status: deprecated
   canonical: github.com/KooshaPari/phenoShared/crates/<crate>
   adr: docs/governance/shared-crates-canonical-home-adr-2026-04.md
   replaced-on: <YYYY-MM-DD>
   ---
   This crate has moved to phenoShared. Do not edit here.
   New consumers MUST depend on the canonical version.
   ```
2. Add a top-of-file `// DEPRECATED — see DEPRECATED.md` banner to the
   crate's `src/lib.rs`.
3. Switch the host workspace's `Cargo.toml` `members = [...]` to remove
   the duplicate path; replace any internal `path = "crates/..."`
   dependency with a workspace dep targeting `phenoShared`.
4. Remove the duplicated source tree only **after** all reverse-deps
   inside that host workspace compile against the canonical crate.

The audit doc (`cross-project-reuse-audit-2026-04-25.md`) gets a
trailing one-line "Superseded for canonical-home decision: see
shared-crates-canonical-home-adr-2026-04.md" note as part of the
implementation PR.

## Acceptance criteria

- `find repos -path '*/crates/phenotype-{event-sourcing,cache-adapter,state-machine,policy-engine}' -not -path '*phenoShared*' -not -path '*target*' -not -path '*.archive*' -not -path '*-wtrees*'` returns `0` results.
- All host workspaces (`pheno`, `PhenoProc`, `DataKit`, `HexaKit`, `PhenoKits/HexaKit`, `AuthKit`, `ResilienceKit`, `hwLedger`) build green against the canonical `phenoShared` crates.
- The 4 deprecated crate directories per home each carry a `DEPRECATED.md` with the canonical pointer, until physical removal lands.
- `cargo metadata --workspace` from any host shows exactly one entry per crate name across the resolved graph.
- The cross-project audit doc gets a "superseded" pointer back to this ADR.

## Out of scope (next tasks)

- **No code dedup in this PR.** This is planning only, per the
  Planner-Agents-No-Code rule. A follow-up implementation task per crate
  (4 tasks) will execute the migration matrix.
- API reconciliation between the 26 / 42 / 57 LOC variants of
  `phenotype-event-sourcing` is delegated to the implementation task —
  the canonical baseline is whatever `phenoShared` ships at task-start.
- Re-purposing the dormant `<REDACTED>/phenotype-shared` repo (rename,
  archive, or repoint) is a separate org-hygiene task.

## Predecessors / DAG

- depends-on: `cross-project-reuse-audit-2026-04-25.md` (this ADR resolves its §"Three-canonical-home problem")
- enables: 4 implementation work packages (one per crate) — sequential within a host workspace, parallel across workspaces.
