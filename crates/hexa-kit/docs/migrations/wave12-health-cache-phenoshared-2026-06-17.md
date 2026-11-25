# Wave 12 — phenotype-health + cache-adapter — HexaKit

**Date:** 2026-06-17  
**Predecessor:** P3 wave 4 ([#260](https://github.com/KooshaPari/HexaKit/pull/260))

## Workspace exclude + git pin (phenoShared)

| Crate | Canonical | Notes |
|-------|-----------|-------|
| `phenotype-health` | phenoShared | Traits crate (`HealthChecker`, `HealthMonitor`, project health model) — API twin of HexaKit stub |
| `phenotype-cache-adapter` | phenoShared | `CacheAdapter` placeholder — API-compatible |

## PhenoObservability boundary

PhenoObservability `rust/phenotype-health*` (axum/cli/runtime) is a **superset runtime layer** on different trait surface (`HealthCheck` / `HealthRegistry`). HexaKit consumers use phenoShared traits; PO absorption is runtime-only and already in PO workspace.

## Consumers verified

- `phenotype-core` — `health::*` and `cache::CacheAdapter` re-exports
- `phenotype-project-registry` — `LanguageStack`
- `phenotype-security-aggregator` (git) — `DimensionScore`, `Finding`, `Severity`
