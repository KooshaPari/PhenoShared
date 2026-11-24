# Migration: phenotype-telemetry → PhenoObservability

**Date:** 2026-06-18  
**Disposition row:** HexaKit DISPOSITION #39 — Wave A  
**Canonical repo:** https://github.com/KooshaPari/PhenoObservability  
**Git pin:** `PhenoObservability` branch `main`

## What changed

- Local source **pruned** Phase 3 — this directory is a redirect stub only.
- Canonical implementation at `PhenoObservability/rust/phenotype-telemetry`.
- `phenotype-core::telemetry` re-exports PO API (`MetricsCollector`, `Metric`, `SpanContext`, …).

## For consumers

```toml
phenotype-telemetry = { git = "https://github.com/KooshaPari/PhenoObservability", branch = "main", package = "phenotype-telemetry" }
```
