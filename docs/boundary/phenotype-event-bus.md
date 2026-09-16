# Boundary: phenotype-event-bus Historical Claim

**Status:** historical and unverified

Earlier registry records described `phenotype-event-bus` as a crate absorbed
from `KooshaPari/phenoEvents` into `KooshaPari/pheno`. That description is
retained as provenance only. The 2026-08-05 recheck of pheno main
`81d850837848800aa7a3e6a6f007b91b6555ef07` found no documented
`crates/phenotype-event-bus`, `crates/pheno-events`, or
`crates/phenoevents-observability` target path.

The live canonical owner of the runtime event-bus boundary is
`KooshaPari/phenoEvents` at
`be6573c68797cc611a99533bca6dc1c3dcdb0c88`. This document does not establish a
current pheno package, dependency, interface contract, or restore procedure.

Any future pheno integration must be proposed as a new, evidence-backed change
with exact source and target SHAs, explicit Cargo membership/dependency proof,
and focused target tests. No source movement is authorized by this historical
record.

## Cross-references

- `docs/boundary/phenoEvents.md`
- `audits/absorption-justifications/phenoEvents-reconciliation-20260727.md`
- `audits/absorption-justifications/2phenoEvents-reconciliation-20260805.md`
