# Migration: phenotype-logging → PhenoObservability

**Date:** 2026-06-18  
**Disposition row:** HexaKit DISPOSITION #26 — Wave A  
**Canonical repo:** https://github.com/KooshaPari/PhenoObservability  
**Git pin:** `PhenoObservability` branch `main` (PhenoObservability#169)

## What changed

- Local source **pruned** wave 13 — this directory is a redirect stub only.
- Canonical implementation at `PhenoObservability/rust/phenotype-logging`.
- Repointed from interim **phenoShared** pin (HexaKit#258, phenoShared#177).

## For consumers

```toml
phenotype-logging = { git = "https://github.com/KooshaPari/PhenoObservability", branch = "main", package = "phenotype-logging" }
```

## For HexaKit maintainers

- Wave A observability lane — do not relocate other observability crates in this PR.
- Remove this stub directory once downstream references are cleared (follow-up PR).
