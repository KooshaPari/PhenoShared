# phenoEvents - Canonical Event-bus Boundary

**Status:** `KEEP_CANONICAL_STANDALONE`

| Field | Current evidence |
| --- | --- |
| Canonical owner | `KooshaPari/phenoEvents` |
| Default branch | `main` |
| Verified main | `be6573c68797cc611a99533bca6dc1c3dcdb0c88` |
| Remote state | public and unarchived (verified 2026-08-05) |
| Boundary | durable SQLite outbox, retries, DLQ, idempotency, projections, schema registry, and OTLP tracing |

## Current ownership

`phenoEvents` is the live canonical event-bus repository. New consumers that
need this boundary should depend on its published or explicitly versioned API;
they must not infer a local `pheno` path dependency from old registry records.

The `2phenoEvents` name is a historical alias tombstone. Its preserved source
commit is reachable in this repository, so it provides no separate source
material for absorption.

## Historical pheno claim

The 2026-07-17 records claimed that `phenoEvents` was absorbed into
`KooshaPari/pheno`. That claim is **historical and unverified**. At recheck,
pheno main `81d850837848800aa7a3e6a6f007b91b6555ef07` contains no
`crates/pheno-events`, `crates/phenoevents-observability`, or
`crates/phenotype-event-bus` path. The registry preserves the old claim as
provenance, not as current ownership or an instruction to mutate either repo.

A future integration requires exact source and target SHAs, a file/dependency
mapping, target workspace membership, and focused target tests. Until then,
Eventra and `phenotype-event-sourcing` are adjacent boundaries rather than
implicit targets.

## Evidence

- `audits/absorption-justifications/phenoEvents-reconciliation-20260727.md`
- `audits/absorption-justifications/2phenoEvents-reconciliation-20260805.md`
- `projects/phenoEvents.json`
- `projects/2phenoEvents.json`
