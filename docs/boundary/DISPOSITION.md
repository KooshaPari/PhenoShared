# PhenoObservability — Per-Module Boundary Disposition

**Status:** Approved assessment  
**Date:** 2026-06-17  
**Repo:** `<REDACTED>/PhenoObservability`  
**Charter:** [`phenotype-registry/docs/rationalization/boundary-shaping.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/boundary-shaping.md)  
**Audit:** [`docs/audit/BLOCK-C-AUDIT.md`](../audit/BLOCK-C-AUDIT.md)  
**Registry:** [`phenotype-registry/BOUNDARY_OWNERS.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/BOUNDARY_OWNERS.md) — `observe` domain  
**Wave A:** [`docs/disposition/wave-a-absorption.md`](../disposition/wave-a-absorption.md)  
**RFC 001:** [`docs/disposition/rfc001-traceon-wave2.md`](../disposition/rfc001-traceon-wave2.md)

> **Doctrine:** Stubs and scaffolds receive an owner and a migration path — not silent deletion.
> Hard delete applies only after absorption evidence and consumer manifest scan (registry gate §5).

---

## 1. Summary — recommended end-state

**PhenoObservability is the canonical `observe` role workspace** — active, not a migration
source to archive away.

| Concern | Owner after disposition |
|---------|-------------------------|
| Rust tracing hexagonal core (`tracingkit`, tracely-*) | **PhenoObservability** `crates/` |
| Rust metrics (`metrickit`, phenotype-metrics) | **PhenoObservability** `crates/` + `rust/` |
| Rust logging / telemetry / health | **PhenoObservability** `rust/` + `crates/logkit` |
| Production OTLP init (thin) | **phenotype-otel** → **merge into PO** (RFC 001) |
| Python observability facade | **phenotype-python-sdk** `packages/observability-kit` |
| HexaKit observability inbound (#22, #26, #35, #39, #48, #49) | **PhenoObservability** (Wave A) |
| Go OTEL reference | **PhenoObservability** `tracing/` (edge reference) |
| TS telemetry ports | **PhenoObservability** `ports/` (edge reference) |
| Profiling harness | **PhenoObservability** `profiling/` (Profila absorption target) |
| Misplaced security aggregator | **Authvault** (decompose out) |
| Misplaced compliance scanner duplicate | **TestingKit** or `phenotype-compliance` (evaluate) |
| Domain squatters (LLM, MCP server crates) | **Removed** from workspace; dirs frozen |
| Cross-cutting vendor copies | **phenoShared** (Wave E) — delete `vendor/` after repoint |
| This repository | **KEEP ACTIVE** — org-wide observability SSOT |

**Do not** treat ObservabilityKit file parity in python-sdk as permission to shrink this
repo. Rust workspace + Wave A inbound remain unique.

---

## 2. Method

- Git tree `main` @ e8af398 (2026-06-17, post PR #161 RFC 001)
- Cross-repo compare: HexaKit DISPOSITION rows #22, #26, #35, #39, #48, #49; `phenotype-otel`; SDK `packages/observability-kit`
- Registry: `BOUNDARY_OWNERS.md` §Observability, `DOMAIN_ROLES.md` `observe` row
- Prior work: PR #157 Metron/metrickit, PR #158 Wave A map, PR #159 G2 chokepoint repoint, PR #161 Traceon status
- Build verification: `cargo check --workspace` PASS (2026-06-17)

---

## 3. Top-level modules — disposition table

| # | Module (path) | What it is | Disposition | Target repo | Rationale |
|---|---------------|------------|-------------|-------------|-----------|
| 1 | `crates/tracingkit` | Hexagonal tracing core (Traceon absorption) | **DYNAMIC-KEEP** | PhenoObservability | Wave A #49; RFC 001 source parity verified |
| 2 | `crates/metrickit` | Hexagonal metrics (Metron absorption) | **DYNAMIC-KEEP** | PhenoObservability | Wave A #48; PR #157 landed |
| 3 | `crates/tracely-core` | Core tracing + logging primitives | **DYNAMIC-KEEP** | PhenoObservability | Production OTEL path; absorbed helix-* |
| 4 | `crates/tracely-sentinel` | Rate limit / circuit break around trace export | **DYNAMIC-KEEP** | PhenoObservability | Sentinel layer adjacent to tracing |
| 5 | `crates/logkit` | Logify hexagonal logging SDK | **DYNAMIC-KEEP** | PhenoObservability | Complements `rust/phenotype-logging` |
| 6 | `crates/phenotype-observably-*` (5 crates) | OTel tracing/logging/sentinel/macros/ports facade | **DYNAMIC-KEEP** | PhenoObservability | Fleet consumer-facing API surface |
| 7 | `crates/pheno-dragonfly` | Dragonfly metrics backend adapter | **DYNAMIC-KEEP** | PhenoObservability | Storage adapter under observe role |
| 8 | `crates/pheno-questdb` | QuestDB time-series adapter | **DYNAMIC-KEEP** | PhenoObservability | Storage adapter under observe role |
| 9 | `crates/helix-logging` | Legacy logging (merged into tracely-core) | **DELETE** | — | Deprecated; ponytail on cut PR |
| 10 | `crates/phenotype-llm` | LLM observability (workspace removed) | **DECOMPOSE** | Agentora / python-sdk LLM edge | NFR-OBS-010 domain squatting; dir frozen |
| 11 | `crates/phenotype-mcp-server` | MCP server for obs tools (workspace removed) | **DECOMPOSE** | PhenoMCPServers | Connect domain; not observe core |
| 12 | `rust/phenotype-health` (+ axum, cli) | Health-check primitives + HTTP/CLI adapters | **DYNAMIC-KEEP** | PhenoObservability | Wave A #22; PO-only adapters |
| 13 | `rust/phenotype-logging` | Structured logging + OTEL bridge | **DYNAMIC-KEEP** | PhenoObservability | Wave A #26 |
| 14 | `rust/phenotype-metrics` | Metrics facade / Prometheus export | **DYNAMIC-KEEP** | PhenoObservability | Wave A #48 reconciliation with metrickit |
| 15 | `rust/phenotype-telemetry` | Telemetry facade | **DYNAMIC-KEEP** | PhenoObservability | Wave A #39 |
| 16 | `rust/phenotype-sentry-config` (planned) | Sentry init helper | **ABSORB** | PhenoObservability `rust/` | Wave A #35 — port from HexaKit pending |
| 17 | `rust/phenotype-mock` | Call-recording mock context | **DECOMPOSE** | TestingKit | Test utility misplaced in observe workspace |
| 18 | `rust/phenotype-compliance-scanner` | Docs/governance compliance scan | **DECOMPOSE** | TestingKit (existing) or `phenotype-compliance` | Duplicate of TestingKit scanner; not observe runtime |
| 19 | `rust/phenotype-security-aggregator` | Security aggregation | **DECOMPOSE** | Authvault | HexaKit DISPOSITION #34 → AuthKit neighbor |
| 20 | `rust/phenotype-project-registry` | Project registry types | **DECOMPOSE** | phenoShared | Cross-cutting; too small for observe workspace |
| 21 | `vendor/phenotype-errors`, `vendor/phenotype-event-bus` | G2 chokepoint vendored copies | **DECOMPOSE** | phenoShared git deps | Transitional; delete after Wave E publish |
| 22 | `tracing/` | Go OpenTelemetry reference | **DYNAMIC-KEEP** | PhenoObservability | Language-edge reference (Tier 3 Go justified) |
| 23 | `ports/`, `ts/` | TS telemetry port adapters | **DYNAMIC-KEEP** | PhenoObservability | Bun/TS edge per LANGUAGE_PLACEMENT |
| 24 | `python/` | Python subtree (ADR stub) | **ABSORB** | phenotype-python-sdk `packages/observability-kit` | BOUNDARY_OWNERS: Py facade canonical in SDK |
| 25 | `profiling/` | Profiler harness + specs | **DYNAMIC-KEEP** | PhenoObservability | Profila absorption lane; adjacent to observe |
| 26 | `ai-prompt-logger/` | AI prompt logging utility | **DYNAMIC-KEEP** | PhenoObservability | Observability-adjacent; evaluate SDK extra later |
| 27 | `alerting/`, `dashboards/`, `metrics/`, `logging/`, `health/`, `logctx/` | Legacy / parallel doc trees | **DYNAMIC-KEEP** → slim | PhenoObservability or ponytail | Reconcile with crate SSOT; trim duplicates |
| 28 | `bindings/`, `ffi/`, `mojo/`, `zig/`, `wasi/` | Multi-lang binding scaffolds | **DYNAMIC-KEEP** | PhenoObservability edges | Core langs per placement policy; stubs OK |
| 29 | `phenotype-docs-engine/`, `phenotype-research-engine/` | Doc/research engines | **DECOMPOSE** | phenotype-tooling or registry sessions | Not observe runtime |
| 30 | `examples/`, `tests/` | Integration examples + smoke tests | **DYNAMIC-KEEP** | PhenoObservability | Standard workspace hygiene |
| 31 | `docs/disposition/wave-a-absorption.md` | Wave A lane tracker | **DYNAMIC-KEEP** | PhenoObservability | Active absorption SSOT |
| 32 | `docs/disposition/rfc001-traceon-wave2.md` | RFC 001 status | **DYNAMIC-KEEP** | PhenoObservability | Traceon parity evidence |
| 33 | `docs/history/chokepoint-repoint-2026-06-17.md` | G2 repoint log | **DYNAMIC-KEEP** | PhenoObservability | Chokepoint evidence |
| 34 | `docs/adr/ADR-001`–`005` | Architecture decisions | **DYNAMIC-KEEP** | PhenoObservability | Trim aspirational rows on ponytail PR |
| 35 | `docs/operations/iconography/` | Unused SVG assets | **DELETE** | — | No fleet consumer |
| 36 | Root governance (`PLAN.md`, `PRD.md`, `CHARTER.md`, …) | Planning markdown zoo | **DYNAMIC-KEEP** → slim | phenotype-registry session artifacts | Trim on cut PR |
| 37 | `.github/workflows/` | CI (rust, deny, audit, …) | **DYNAMIC-KEEP** | PhenoObservability | Active repo — required |
| 38 | `README.md` | Consumer entry + crate table | **DYNAMIC-KEEP** | This repo | Update disposition banner (this PR) |
| 39 | `BOUNDARY.md` | Boundary lock | **DYNAMIC-KEEP** | PhenoObservability | Links to this disposition |
| 40 | Repo itself | Org-wide observe workspace SSOT | **KEEP ACTIVE** | phenotype-registry `observe` role | AFFIRM owner — execute Wave A–C consolidation |

---

## 4. Supersession map

| Retired surface | Successor | Evidence |
|-----------------|-----------|----------|
| `Metron` standalone repo | `crates/metrickit` | PR #157; Wave A #48 |
| `Traceon` standalone repo | `crates/tracingkit` | RFC 001; Wave A #49 |
| `ObservabilityKit` subtree in PO | `phenotype-python-sdk/packages/observability-kit` | PR #157 removal |
| HexaKit git deps for errors/event-bus | `vendor/` → phenoShared | G2 repoint PR #159 |
| `phenotype-otel` as separate boundary | PhenoObservability merge | BOUNDARY_OWNERS §Observability |
| HexaKit observability crates | PhenoObservability `rust/` + `crates/` | Wave A stubs + disposition-index |

---

## 5. Execution phases

| Phase | Scope | Acceptance |
|-------|-------|------------|
| **P0** (this PR) | Block-C disposition + audit + consolidation plan | Docs on `main` |
| **P1** | Port `phenotype-sentry-config`; reconcile metrickit ↔ phenotype-metrics API | HexaKit stub removed |
| **P2** | Merge `phenotype-otel`; fleet OTLP consumer repoint | Single observe workspace |
| **P3** | phenoShared publish → delete `vendor/`; decompose misplaced `rust/` crates | Manifest scan clean |
| **P4** | Python consumer default → SDK observability-kit extra | README redirect complete |
| **P5** | Archive Metron/Traceon/ObservabilityKit after registry gate | disposition-index `fsm: done` |

---

## 6. Related documents

- [`docs/audit/BLOCK-C-AUDIT.md`](../audit/BLOCK-C-AUDIT.md)
- [`docs/audit/BLOCK-C-CONSOLIDATION-PLAN.md`](../audit/BLOCK-C-CONSOLIDATION-PLAN.md)
- [`docs/disposition/wave-a-absorption.md`](../disposition/wave-a-absorption.md)
- [`BOUNDARY.md`](../../BOUNDARY.md)
- [phenotype-registry RFC 001](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rfc/001-traceon-observe-role.md)
- [HexaKit DISPOSITION rows #22, #26, #35, #39, #48, #49](https://github.com/KooshaPari/HexaKit/blob/main/docs/boundary/DISPOSITION.md)
