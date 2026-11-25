# Conditional Row Blocker Ledger

**Audit date:** 2026-07-31  
**Scope:** evidence-only governance closeout for the conditional consolidation rows  
**Registry baseline:** metadata normalization commit `269b3283`  
**Mutation policy:** this document changes no catalog/index fields, source refs, or Git history.

## Purpose

This ledger records the remaining gates before any FSM or disposition transition. The
technical absorption references remain valid provenance, but a target ref alone is not
an ownership, build, or release decision.

## Gate matrix

| Row | Source ref (latest) | Technical target ref | Current result | Remaining gate | Safe disposition now |
|---|---|---|---|---|---|
| Sidekick | `474d72311` | PhenoObservability `8d53e704` | Target tree and `pheno-otel` mapping are evidenced; independent build is blocked by missing `phenotype-errors`/uncached HexaKit dependencies. | Restore the complete dependency graph, run metadata/check/tests, and confirm consumer ownership. | Preserve source and target refs; keep FSM/disposition unchanged. |
| phenoUtils | `170145827` | expected absorption ref `8e0b25506` | The expected target ref is not currently discoverable on the remote; the standalone manifest also fails virtual-workspace validation. | Recover the exact target ref or prove that it was registry-only; then map consumers and run a bounded build. | Preserve source SHA; unresolved/preserve-only until target provenance is recovered. |
| phenoData | `896faa586` | `absorb/pheno-data-2026-07-17 @ 3bd35bd875554ee18ef8833ee59b44edd5213d42` | Five target crates, source mapping, license evidence, and source-side tests are recorded. Target workspace resolution/build remains caveated; active source maintenance is separate. | Decide source-of-truth ownership, validate target workspace where dependencies permit, and adopt the split-maintenance drift policy. | Keep `fsm=live`/existing disposition; retain technical absorption and archive refs. |
| PhenoPlugins | `e57ee798` | `absorb/pheno-plugins-2026-07-17 @ 20457e5ad1b6c89dd40fd0ebcdc243ca69737c32` | Five target crates and mapping commit `d8eb80d68d337a9dc2826b37a25a918f1d76e3f1` are evidenced; current source ownership diverges from the historical absorption branch. | Confirm terminal owner, consumer/build evidence, and archive governance against current main. | Preserve evidence and provenance; no new runtime transition in this ledger. |

## Invariants

```text
FSM/disposition fields       unchanged
technical target refs        retained
source refs                  retained
archive/Airlock refs         retained
source repositories          untouched
branch deletion/rename       prohibited
force-push/history rewrite   prohibited
credential rotation/purge    out of scope
```

## Relation to metadata normalization

The sponsor-approved metadata-only normalization was applied in commit
`269b3283`. That change records current source metadata and audit context; it does
not assert that any conditional row is absorbed, build-complete, or release-ready.
This ledger is additive evidence for the next review and must not be interpreted as
authorization to change `registry/disposition-index.json` again.

## Exit criteria

A conditional row may advance only when all of the following are attached to its
review packet:

1. exact source and target refs, including an archive ref;
2. source-to-target tree and consumer mapping;
3. reproducible metadata/build/test result, with dependency blockers explicit;
4. ownership, license, and issue-routing decision;
5. rollback/Airlock evidence and sponsor approval for the proposed transition.

Until then, preserve-first handling is the authoritative decision: keep the source,
keep the refs, document the blocker, and do not delete or rewrite history.
