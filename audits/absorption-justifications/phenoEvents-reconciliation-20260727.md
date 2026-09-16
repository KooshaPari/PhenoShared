# phenoEvents boundary reconciliation (2026-07-27)

## Decision

Keep `KooshaPari/phenoEvents` as a live standalone event-bus library pending a
reproducible source-to-target integration proof. This is a metadata correction,
not a deletion or rollback: the 2026-07-17 absorption claim remains preserved
as historical evidence in the project record and the prior audit.

## Current remote evidence

| Field | Evidence |
| --- | --- |
| URL | <https://github.com/KooshaPari/phenoEvents> |
| Visibility | Public; `isArchived=false`; `archivedAt=null` |
| Default branch | `main` |
| Current main SHA | `3d6cc220e73bbc67652a1089bd801a12542e1f96` |
| Repository timestamps | updated `2026-07-22T00:37:22Z`; pushed `2026-07-22T11:42:32Z` |
| License | `LICENSE` contains MIT License followed by Apache License 2.0; README states `MIT OR Apache-2.0` |
| Scope | Rust event-bus library: SQLite outbox, at-least-once delivery, idempotency, DLQ, schema registry, projections, benches, and property tests |

The source also contains an unfilled boundary document dated 2026-06-17 and
an ownership-audit branch, so it is not evidence of a completed archival
operation.

## Target verification

The current `KooshaPari/pheno` `main` tree contains
`crates/phenotype-event-sourcing/` and AgilePlus event crates, but no
`crates/phenotype-event-bus/` path. Therefore the prior statement that the
source was archived and that this exact target path was integrated cannot be
reproduced from current target `main` without an additional commit/ref.

This is a target conflict, not proof that no historical transfer occurred.
The prior artifact `phenoEvents-2026-07-17.md` and all source history remain
untouched. A future absorption must name the exact source and target SHAs,
list copied files, prove Cargo workspace membership, and run the focused
unit/property tests in the target checkout.

## Routing

- Current disposition: `KEEP_CANONICAL_STANDALONE`.
- Do not merge into Eventra or `phenotype-event-sourcing` implicitly; their
  APIs and ownership boundaries need an explicit decision.
- Keep the historical target pointer for provenance and revisit after a
  commit-level reconciliation with the pheno maintainers.

## 2026-08-05 revalidation

`KooshaPari/phenoEvents` remains public and unarchived at main
`be6573c68797cc611a99533bca6dc1c3dcdb0c88`. Current `KooshaPari/pheno` main is
`81d850837848800aa7a3e6a6f007b91b6555ef07`; its tree still has no
`pheno-events`, `phenoevents-observability`, or `phenotype-event-bus` path.
The target claim is therefore historical and unverified, not a pending source
move. `2phenoEvents` is separately reconciled as a historical alias whose
preserved source commit is reachable in canonical phenoEvents.
