# Block-C Audit — <REDACTED>/PhenoObservability

**Date:** 2026-06-17  
**Auditor:** ecosystem disposition wave (Block-C)  
**Charter:** [`phenotype-registry/docs/rationalization/boundary-shaping.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/boundary-shaping.md)  
**Registry:** [`phenotype-registry/BOUNDARY_OWNERS.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/BOUNDARY_OWNERS.md) §Observability  
**Wave A:** [`docs/disposition/wave-a-absorption.md`](../disposition/wave-a-absorption.md)

---

## Executive summary

| Signal | Finding |
|--------|---------|
| **Repo role** | Canonical `observe` domain workspace — Rust core + language edges |
| **Boundary lock** | **ACTIVE** — AFFIRM owner per BOUNDARY_OWNERS Cluster D |
| **Wave A (HexaKit)** | **PARTIAL** — tracingkit/metrickit/health/logging/telemetry landed; sentry-config pending |
| **RFC 001 (Traceon)** | **COMPLETE** — source parity verified; HexaKit stub retained |
| **G2 chokepoint repoint** | **COMPLETE** — no HexaKit git deps in active manifests (PR #159) |
| **Python facade** | **REDIRECT** — ObservabilityKit subtree removed; SDK is consumer default |
| **phenotype-otel merge** | **PENDING** | Separate repo still open boundary |
| **GitHub archive flag** | **NOT ARCHIVED** — intentional active owner |
| **Primary risk** | Misplaced `rust/` crates (security, compliance, mock); dual metrics APIs |
| **Recommended action** | Publish Block-C disposition; execute P1–P3 consolidation; **KEEP ACTIVE** |

---

## Baseline checks

| Check | Result | Notes |
|-------|--------|-------|
| Root `cargo check --workspace` | **PASS** | Verified 2026-06-17 (~3m 43s) |
| No HexaKit git deps in manifests | **PASS** | G2 repoint; vendor/ transitional |
| `crates/tracingkit` source parity vs HexaKit Traceon | **PASS** | RFC 001 doc |
| `crates/metrickit` present (Metron absorption) | **PASS** | PR #157 |
| `ObservabilityKit/` subtree removed | **PASS** | PR #157 |
| `rust/phenotype-sentry-config` | **FAIL** | Wave A #35 — planned, not ported |
| `docs/boundary/DISPOSITION.md` | **FAIL** | This Block-C PR |
| `BOUNDARY.md` active lock | **FAIL** | This Block-C PR |
| README disposition banner | **FAIL** | Stale work-state (2026-06-08) |
| STATUS.md current | **FAIL** | Last updated 2026-05-02; lists removed workspace members |
| phenotype-otel merged | **FAIL** | Open boundary per BOUNDARY_OWNERS |
| `vendor/` eliminated | **FAIL** | Awaiting phenoShared Wave E publish |

---

## Observability plane split (registry authority)

Per `BOUNDARY_OWNERS.md` §Observability — **SDK file parity does not close the Rust boundary**:

| Slice | Canonical owner | PhenoObservability role after Block-C |
|-------|-----------------|---------------------------------------|
| Rust tracing hex core (`tracingkit`, tracely-*) | **PhenoObservability** `crates/` | **DYNAMIC-KEEP** — canonical |
| Rust metrics (`metrickit`, phenotype-metrics) | **PhenoObservability** | **DYNAMIC-KEEP** — reconcile APIs |
| Rust logging / telemetry / health | **PhenoObservability** `rust/` | **DYNAMIC-KEEP** — Wave A landed |
| Thin OTLP production init | **phenotype-otel** → PO merge | **ABSORB** — P2 |
| Python observability facade | **phenotype-python-sdk** `packages/observability-kit` | **Redirect** — not install target here |
| Standalone Metron / Traceon / ObservabilityKit repos | **ARCHIVE** after gate | Absorption evidence in PO |
| Profiling (Profila) | **PhenoObservability** `profiling/` | **DYNAMIC-KEEP** — evaluate depth |

---

## Cross-repo boundary overlaps

| Concern | Also present in | Canonical owner | PhenoObservability role |
|---------|-----------------|-----------------|---------------------------|
| Traceon hexagonal core | HexaKit `Traceon/` (stub) | **PhenoObservability** `tracingkit` | Absorption complete; stub until fleet repoint |
| Metron metrics | HexaKit `Metron/` (stub) | **PhenoObservability** `metrickit` | Absorption complete |
| Python observability kit | `phenotype-python-sdk` | **phenotype-python-sdk** | Subtree removed from PO |
| OTLP init | `phenotype-otel` | **PO post-merge** | Merge pending |
| Compliance scanner | TestingKit `rust/` | **TestingKit** or compliance repo | Misplaced duplicate in PO `rust/` |
| Security aggregator | Authvault target | **Authvault** | Misplaced in PO `rust/` |
| phenotype-errors / event-bus | phenoShared | **phenoShared** | Vendor copy transitional |
| Domain SDK monolith plan | Retired rationalization rows | **Role-based owners** | PO affirmed for `observe` |

---

## Archive gate status (for absorbed *source* repos — not PO itself)

Per `BOUNDARY_OWNERS.md` delete gate for Metron / Traceon / ObservabilityKit:

| Repo | Gate status | Verdict |
|------|-------------|---------|
| Traceon | 2 done in PO | **KEEP_ARCHIVED** |
| Metron | 2 partial (HexaKit copy remains) | **ARCHIVE** after HexaKit strip |
| ObservabilityKit | 2–4 partial | **DELETE** after SDK + PO cleanup |

PhenoObservability itself: **not a delete candidate** — unique Rust observe workspace.

---

## Related documents

- [`docs/boundary/DISPOSITION.md`](../boundary/DISPOSITION.md)
- [`docs/audit/BLOCK-C-CONSOLIDATION-PLAN.md`](./BLOCK-C-CONSOLIDATION-PLAN.md)
- [`docs/disposition/wave-a-absorption.md`](../disposition/wave-a-absorption.md)
- [`docs/disposition/rfc001-traceon-wave2.md`](../disposition/rfc001-traceon-wave2.md)
