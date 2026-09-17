# Migration: Metron → PhenoObservability

**Date:** 2026-06-17  
**Disposition row:** HexaKit DISPOSITION #48 — `Metron/`  
**Canonical repo:** https://github.com/KooshaPari/PhenoObservability  
**Absorption map:** [wave-a-absorption.md](https://github.com/KooshaPari/PhenoObservability/blob/main/docs/disposition/wave-a-absorption.md)

## What changed

- This path received a **redirect stub** per [crate relocation runbook step 6](../../docs/operations/crate-relocation-runbook.md).
- Canonical metrics ownership moves to **`PhenoObservability`** (`rust/phenotype-metrics`; HexaKit `metrickit` absorbed there).
- **Source removed** from HexaKit after PhenoObservability absorption (PR #157); only this redirect stub remains.

## For consumers

1. Depend on metrics from **PhenoObservability**, not HexaKit `Metron/` or workspace `metrickit`.
2. Do not add new HexaKit path dependencies on `Metron/`.
3. See absorption doc for crate name mapping (`metrickit` → `phenotype-metrics`).

## For HexaKit maintainers

- Wave A observability lane — do not relocate other observability crates in this PR.
- Remove this stub directory once downstream references are cleared (follow-up PR).
