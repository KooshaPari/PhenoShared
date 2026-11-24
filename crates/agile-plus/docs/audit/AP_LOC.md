# AgilePlus LOC + Size Audit Report

Generated: 2026-06-14
Scope: All `.rs` files in the workspace (crates + non-crate sources)

---

## Workspace Totals

| Metric | Value |
|--------|-------|
| Total `.rs` files | 465 |
| Total workspace LOC | 84,952 |
| Crates LOC | 84,116 |
| Non-crate LOC | 836 |

---

## Per-Crate Line Counts (crates/*)

Sorted by LOC descending.

| Crate | Files | LOC |
|-------|-------|-----|
| agileplus-cli | 77 | 15,991 |
| agileplus-sqlite | 41 | 9,125 |
| agileplus-api | 50 | 7,440 |
| agileplus-dashboard | 17 | 5,792 |
| agileplus-plane | 26 | 4,709 |
| agileplus-subcmds | 37 | 4,693 |
| agileplus-triage | 15 | 4,238 |
| agileplus-p2p | 23 | 4,232 |
| agileplus-governance | 11 | 3,199 |
| agileplus-domain | 30 | 3,171 |
| agileplus-integration-tests | 16 | 2,819 |
| agileplus-grpc | 18 | 2,552 |
| agileplus-application | 12 | 2,242 |
| agileplus-events | 7 | 1,787 |
| agileplus-telemetry | 7 | 1,688 |
| agileplus-nats | 9 | 1,509 |
| agileplus-sync | 8 | 1,256 |
| agileplus-benchmarks | 7 | 1,172 |
| agileplus-fixtures | 5 | 1,008 |
| agileplus-github | 4 | 900 |
| agileplus-trace-validator | 7 | 895 |
| agileplus-cache | 8 | 873 |
| agileplus-import | 10 | 781 |
| agileplus-proto | 3 | 611 |
| agileplus-graph | 3 | 329 |
| pheno-ssot-template | 2 | 299 |
| agileplus-artifacts | 2 | 245 |
| agileplus-validate | 1 | 218 |
| agileplus-config | 1 | 205 |
| agileplus-git | 1 | 108 |
| agileplus-contract-tests | 1 | 11 |

---

## Non-Crate Rust Sources

| File | LOC |
|------|-----|
| `libs\xdd-lib-rs\src\lib.rs` | 581 |
| `xtask-anti-patterns\src\main.rs` | 227 |
| `rust\build.rs` | 15 |
| `rust\src\lib.rs` | 11 |
| `src\lib.rs` | 2 |

---

## 15 Largest Source Files

| Rank | File | LOC |
|------|------|-----|
| 1 | `crates/agileplus-dashboard/src/routes.rs` | 2,920 |
| 2 | `crates/agileplus-sqlite/src/lib.rs` | 2,203 |
| 3 | `crates/agileplus-cli/src/commands/worklog.rs` | 1,212 |
| 4 | `crates/agileplus-api/tests/api_integration.rs` | 1,209 |
| 5 | `crates/agileplus-application/src/lib.rs` | 1,007 |
| 6 | `crates/agileplus-integration-tests/tests/modules_and_cycles.rs` | 905 |
| 7 | `crates/agileplus-p2p/src/replication.rs` | 747 |
| 8 | `crates/agileplus-nats/src/nats_adapter.rs` | 731 |
| 9 | `crates/agileplus-subcmds/src/device.rs` | 701 |
| 10 | `crates/agileplus-cli/src/commands/retrospective.rs` | 682 |
| 11 | `crates/agileplus-events/src/domain_event.rs` | 680 |
| 12 | `crates/agileplus-cli/src/commands/dashboard.rs` | 672 |
| 13 | `crates/agileplus-governance/src/audit.rs` | 668 |
| 14 | `crates/agileplus-cli/src/commands/list_tests.rs` | 610 |
| 15 | `crates/agileplus-grpc/src/server/mod.rs` | 604 |

---

## Refactor Candidates (> 600 lines)

The following **14 files** exceed the 600-line threshold and are flagged for potential refactoring.

| File | LOC |
|------|-----|
| `crates/agileplus-dashboard/src/routes.rs` | 2,920 |
| `crates/agileplus-sqlite/src/lib.rs` | 2,203 |
| `crates/agileplus-cli/src/commands/worklog.rs` | 1,212 |
| `crates/agileplus-api/tests/api_integration.rs` | 1,209 |
| `crates/agileplus-application/src/lib.rs` | 1,007 |
| `crates/agileplus-integration-tests/tests/modules_and_cycles.rs` | 905 |
| `crates/agileplus-p2p/src/replication.rs` | 747 |
| `crates/agileplus-nats/src/nats_adapter.rs` | 731 |
| `crates/agileplus-subcmds/src/device.rs` | 701 |
| `crates/agileplus-cli/src/commands/retrospective.rs` | 682 |
| `crates/agileplus-events/src/domain_event.rs` | 680 |
| `crates/agileplus-cli/src/commands/dashboard.rs` | 672 |
| `crates/agileplus-governance/src/audit.rs` | 668 |
| `crates/agileplus-cli/src/commands/list_tests.rs` | 610 |

**Notable hotspots:**
- `crates/agileplus-dashboard/src/routes.rs` is the single largest file at 2,920 lines -- nearly 4x the threshold.
- `crates/agileplus-sqlite/src/lib.rs` is 2,203 lines and likely contains mixed concerns (schema, queries, migrations, tests) that could be split into submodules.
- `agileplus-cli` contributes 5 of the 14 refactor candidates, indicating the CLI command surface is dense and may benefit from extracting shared logic into `agileplus-subcmds` or library crates.
- `agileplus-api/tests/api_integration.rs` (1,209 lines) and `agileplus-integration-tests/tests/modules_and_cycles.rs` (905 lines) are large test files; consider test helper modules or parameterized test suites.

---

*Report produced by read-only analysis -- no build or git operations performed.*
