# Debt Hotspot Audit — 2026-06-15

Audit of `crates/` for technical debt indicators:
TODO/FIXME/HACK, `.unwrap()`, untested crates, and FR-AGP traceability coverage.

---

## Unwrap Count

**Total `.unwrap()` calls across all `crates/` source files:** 1715

### Top 10 files by unwrap count

| Count | File |
|-------|------|
| 295 | `crates/agileplus-sqlite/src/lib.rs` |
| 78 | `crates/agileplus-sqlite/src/lib/tests/feature_work_packages.rs` |
| 77 | `crates/agileplus-sqlite/src/lib/tests/modules_cycles.rs` |
| 61 | `crates/agileplus-triage/src/router.rs` |
| 54 | `crates/agileplus-trace-validator/tests/edge_cases.rs` |
| 40 | `crates/agileplus-cache/tests/integration_tests.rs` |
| 36 | `crates/agileplus-p2p/src/import.rs` |
| 35 | `crates/agileplus-p2p/src/import/tests.rs` |
| 32 | `crates/agileplus-dashboard/src/routes.rs` |
| 29 | `crates/agileplus-api/tests/api_integration.rs` |

**Primary hotspot:** `crates/agileplus-sqlite/src/lib.rs` alone accounts for **295 unwraps** (17.2% of total).

---

## TODO/FIXME/HACK Count

**Total TODO/FIXME/HACK annotations across all `crates/` source files:** 2

### Files with items

| File | Annotation |
|------|------------|
| `crates/phenotype-dep-guard/src/lib.rs:4` | `// TODO: Implement dep-guard logic` |
| `crates/phenotype-mcp-sdk-rs/src/transport.rs:128` | `// TODO: implement Axum/Actix-based SSE streaming.` |

The TODO/FIXME/HACK count is low (2 items). The dominant debt indicator is `.unwrap()` at 1715 instances.

---

## Untested Crates

**11 crates have 0 `#[test]` functions across all `.rs` files:**

| Crate |
|-------|
| `agileplus-convoy` |
| `agileplus-contract-tests` |
| `agileplus-hook` |
| `agileplus-factory` |
| `agileplus-mcp-intent` |
| `agileplus-proto` |
| `phenotype-dep-guard` |
| `agileplus-refinery` |
| `agileplus-artifacts` |
| `agileplus-witness` |

**Crates with the most tests:**

| Crate | Test count |
|-------|-----------|
| `agileplus-triage` | 169 |
| `agileplus-dashboard` | 76 |
| `agileplus-subcmds` | 48 |
| `agileplus-plane` | 47 |
| `agileplus-domain` | 45 |

---

## FR-AGP Traceability Coverage

**20 files reference FR-AGP annotations:**

```
crates/agileplus-api/src/middleware/token_verifier.rs
crates/agileplus-api/tests/api_integration.rs
crates/agileplus-application/src/dto/mod.rs
crates/agileplus-application/src/use_cases/persist_synced_stories.rs
crates/agileplus-application/src/use_cases/triage.rs
crates/agileplus-cli/src/commands/dag.rs
crates/agileplus-cli/src/commands/import_dagctl.rs
crates/agileplus-cli/src/commands/list_tests.rs
crates/agileplus-github/src/map.rs
crates/agileplus-grpc/src/lib.rs
crates/agileplus-grpc/src/work_items.rs
crates/agileplus-proto/src/lib.rs
crates/agileplus-proto/src/stubs.rs
crates/agileplus-sqlite/src/seed/catalog.rs
crates/agileplus-sqlite/src/seed/mod.rs
crates/agileplus-triage/src/claim.rs
crates/agileplus-triage/src/dedup.rs
crates/agileplus-triage/src/engine.rs
crates/agileplus-triage/src/lib.rs
crates/agileplus-triage/src/repo_introspect.rs
```

Traceability is concentrated in **8 crates**: `agileplus-api`, `agileplus-application`, `agileplus-cli`, `agileplus-github`, `agileplus-grpc`, `agileplus-proto`, `agileplus-sqlite`, `agileplus-triage`.

---

## Summary

| Metric | Value |
|--------|-------|
| `.unwrap()` calls | 1715 |
| TODO/FIXME/HACK | 2 |
| Crates with 0 tests | 11 of 42 (26%) |
| FR-AGP referenced files | 20 |

Immediate priorities:
1. **`agileplus-sqlite/src/lib.rs`** — 295 unwraps, single highest-debt file.
2. **11 untested crates** — no test coverage at all.
3. **1715 unwraps total** — systematic `?` / proper error-handling migration needed.
