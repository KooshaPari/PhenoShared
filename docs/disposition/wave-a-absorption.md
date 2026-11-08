# Wave A — HexaKit observability absorption map

**Date:** 2026-06-17  
**Lane:** Wave A observability (`feat/wave-a-obs-stubs`)  
**Source repo:** [<REDACTED>/HexaKit](https://github.com/KooshaPari/HexaKit)  
**Canonical owner:** [<REDACTED>/PhenoObservability](https://github.com/KooshaPari/PhenoObservability)  
**Authority:** [HexaKit DISPOSITION §3](https://github.com/KooshaPari/HexaKit/blob/main/docs/boundary/DISPOSITION.md) rows #22, #26, #35, #39, #48, #49

This document records where HexaKit observability modules land inside PhenoObservability. Wave A step 6 adds `MIGRATED.md` redirect stubs in HexaKit; source trees remain until downstream repoint completes.

---

## Absorption table

| HexaKit path | DISPOSITION # | HexaKit crate / alias | PhenoObservability target | Status |
|---|---|---|---|---|
| `Metron/` | 48 | `metrickit` | `rust/phenotype-metrics` | **Existing** — metrics facade and Prometheus export |
| `Traceon/` | 49 | `tracingkit` | `crates/tracingkit` | **Existing** — distributed tracing (OTLP/Jaeger/Zipkin) |
| `crates/phenotype-logging` | 26 | `phenotype-logging` | `rust/phenotype-logging` | **Existing** — structured logging + OTEL bridge |
| `crates/phenotype-telemetry` | 39 | `phenotype-telemetry` | `rust/phenotype-telemetry` | **Existing** — telemetry facade |
| `crates/phenotype-health` | 22 | `phenotype-health` | `rust/phenotype-health` | **Existing** — health-check primitives |
| `crates/phenotype-health` | 22 | — | `rust/phenotype-health-axum`, `rust/phenotype-health-cli` | **Existing** — HTTP/CLI adapters (PhenoObservability-only) |
| `crates/phenotype-sentry-config` | 35 | `phenotype-sentry-config` | `rust/phenotype-sentry-config` | **Absorbed** — HexaKit source ported 2026-06-18 |

---

## Related PhenoObservability surfaces

These modules were not HexaKit workspace members but already cover adjacent observability concerns:

| Surface | Path | Notes |
|---|---|---|
| Tracing core | `crates/tracely-core` | Shared tracing/logging primitives |
| Sentinel / resilience hooks | `crates/tracely-sentinel` | Rate limiting, circuit breaking around trace export |
| Structured logging (Logify) | `crates/logkit` | Logify subtree; complements `phenotype-logging` |
| OTEL Go reference | `tracing/` | Go OpenTelemetry reference implementation |
| TS telemetry ports | `ports/telemetry.ts`, `ports/adapters/otel.ts`, `ports/adapters/prom.ts` | Language-edge adapters |
| ObservabilityKit | `ObservabilityKit/` | Multi-language SDK umbrella |

---

## Consumer redirect

1. **Do not** add new path or git dependencies on HexaKit for rows in the table above.
2. **Do** depend on PhenoObservability crates (git pin or registry once published).
3. HexaKit paths retain `MIGRATED.md` until fleet repoint PRs merge and stubs are removed (runbook step 7+).

---

## Follow-up lanes (out of scope for Wave A stubs)

- Manifest surgery: remove HexaKit workspace members after chokepoint dependents repoint.
- ~~`phenotype-sentry-config`: add `rust/phenotype-sentry-config` workspace member and port HexaKit source.~~ Done 2026-06-18.
- Metron `metrickit` hexagonal exporters: reconcile with `phenotype-metrics` API where implementations diverge.
- Update `phenotype-registry/registry/disposition-index.json` FSM → `done` when exit gates close.

---

## Citation

- HexaKit [crate relocation runbook step 6](https://github.com/KooshaPari/HexaKit/blob/main/docs/operations/crate-relocation-runbook.md)
- HexaKit [DISPOSITION.md](https://github.com/KooshaPari/HexaKit/blob/main/docs/boundary/DISPOSITION.md)
- Registry disposition rows: wave **A**, target **PhenoObservability**
