# Migration: Traceon → PhenoObservability

**Date:** 2026-06-17  
**Disposition row:** HexaKit DISPOSITION #49 — `Traceon/`  
**Canonical repo:** https://github.com/KooshaPari/PhenoObservability  
**Absorption map:** [wave-a-absorption.md](https://github.com/KooshaPari/PhenoObservability/blob/main/docs/disposition/wave-a-absorption.md)

## What changed

- This path received a **redirect stub** per [crate relocation runbook step 6](../../docs/operations/crate-relocation-runbook.md).
- Canonical distributed tracing ownership moves to **`PhenoObservability`** (`crates/tracingkit`; HexaKit `Traceon/` workspace member).
- **Source is retained** in HexaKit for this wave — removal follows downstream repoint (runbook steps 4–5, 7).

## For consumers

1. Depend on tracing from **PhenoObservability** `tracingkit`, not HexaKit `Traceon/`.
2. Do not add new HexaKit path dependencies on `Traceon/`.
3. Crate name in HexaKit workspace is `tracingkit`; canonical home is `PhenoObservability/crates/tracingkit`.

## For HexaKit maintainers

- Wave A observability lane — do not relocate other observability crates in this PR.
- **Wave 3 (2026-06-17):** `Traceon/` removed from workspace members; Pyron repointed to PhenoObservability `tracingkit` git dep.
