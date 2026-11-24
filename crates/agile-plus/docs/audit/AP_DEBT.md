# AgilePlus Tech-Debt Audit

**Date:** 2026-06-14
**Scope:** `crates/*/src/**/*.rs` (Rust source files under all crate `src` directories)
**Method:** Direct text search (grep/read) for `TODO`, `FIXME`, `XXX`, `unwrap()`, `expect(`, `panic!`, `unimplemented!`.
**Files scanned:** 116 unique `.rs` files across 24 crates.

---

## Executive Summary

| Pattern | Total | Lib (non-test) | Test |
|---|---|---|---|
| `unwrap()` | 1,353 | 989 | 364 |
| `expect(` | 77 | 57 | 20 |
| `panic!` | 26 | 15 | 11 |
| `unimplemented!` | 67 | 67 | 0 |
| `TODO` | 4 | 4 | 0 |
| `XXX` | 4 | 4 | 0 |
| `FIXME` | 0 | 0 | 0 |
| **Total** | **1,531** | **1,136** | **395** |

**Key risk:** 989 `unwrap()` calls and 15 `panic!` calls in non-test library code. `unwrap()` is the dominant debt category (88.4% of all hotspots).

---

## Top 20 Hotspot Files (by total count)

| Rank | File | Total | `unwrap()` | `expect(` | `panic!` | `unimplemented!` |
|---|---|---|---|---|---|---|
| 1 | `crates/agileplus-sqlite/src/lib.rs` | 304 | 295 | 9 | 0 | 0 |
| 2 | `crates/agileplus-cli/src/commands/list_tests.rs` | 83 | 16 | 0 | 0 | 67 |
| 3 | `crates/agileplus-sqlite/src/lib/tests/feature_work_packages.rs` | 78 | 78 | 0 | 0 | 0 |
| 4 | `crates/agileplus-sqlite/src/lib/tests/modules_cycles.rs` | 77 | 77 | 0 | 0 | 0 |
| 5 | `crates/agileplus-triage/src/router.rs` | 61 | 61 | 0 | 0 | 0 |
| 6 | `crates/agileplus-dashboard/src/routes.rs` | 44 | 38 | 6 | 0 | 0 |
| 7 | `crates/agileplus-p2p/src/import.rs` | 36 | 36 | 0 | 0 | 0 |
| 8 | `crates/agileplus-p2p/src/import/tests.rs` | 35 | 35 | 0 | 0 | 0 |
| 9 | `crates/agileplus-p2p/src/git_merge/tests.rs` | 28 | 28 | 0 | 0 | 0 |
| 10 | `crates/agileplus-sqlite/src/lib/tests/mvp_story_work_packages.rs` | 24 | 18 | 6 | 0 | 0 |
| 11 | `crates/agileplus-graph/src/graph_store.rs` | 24 | 24 | 0 | 0 | 0 |
| 12 | `crates/agileplus-cli/src/commands/worklog.rs` | 24 | 23 | 1 | 0 | 0 |
| 13 | `crates/agileplus-sqlite/src/seed/runner.rs` | 23 | 22 | 1 | 0 | 0 |
| 14 | `crates/agileplus-events/src/domain_event.rs` | 22 | 15 | 3 | 4 | 0 |
| 15 | `crates/agileplus-nats/src/bus.rs` | 22 | 22 | 0 | 0 | 0 |
| 16 | `crates/agileplus-cli/src/commands/trace.rs` | 21 | 21 | 0 | 0 | 0 |
| 17 | `crates/agileplus-cli/src/commands/gate_run.rs` | 19 | 19 | 0 | 0 | 0 |
| 18 | `crates/agileplus-sync/src/store.rs` | 19 | 19 | 0 | 0 | 0 |
| 19 | `crates/agileplus-sqlite/src/lib/tests/governance_metrics.rs` | 16 | 16 | 0 | 0 | 0 |
| 20 | `crates/agileplus-cli/src/commands/dashboard.rs` | 16 | 16 | 0 | 0 | 0 |

---

## Risk Register — `unwrap()` / `panic!` in Non-Test Library Code

Files ranked by `unwrap()` + `panic!` count in non-test source.

| Rank | File | `unwrap()` | `panic!` | Risk Notes |
|---|---|---|---|---|
| 1 | `crates/agileplus-sqlite/src/lib.rs` | 295 | 0 | Massive storage-layer unwrap cluster; any DB failure will abort the process. |
| 2 | `crates/agileplus-triage/src/router.rs` | 61 | 0 | High-density unwrap in routing logic; malformed input may crash. |
| 3 | `crates/agileplus-dashboard/src/routes.rs` | 38 | 0 | Web-handler unwrap on DB and JSON operations; operational risk. |
| 4 | `crates/agileplus-p2p/src/import.rs` | 36 | 0 | Network/import path unwraps; could fail on bad peer data. |
| 5 | `crates/agileplus-graph/src/graph_store.rs` | 24 | 0 | Graph storage unwraps; data inconsistency will panic. |
| 6 | `crates/agileplus-cli/src/commands/worklog.rs` | 23 | 0 | CLI worklog command unwrap on I/O and DB calls. |
| 7 | `crates/agileplus-sqlite/src/seed/runner.rs` | 22 | 0 | Seed runner unwrap; init-time risk only. |
| 8 | `crates/agileplus-nats/src/bus.rs` | 22 | 0 | NATS bus mock/test helper code with unwraps; still in lib path. |
| 9 | `crates/agileplus-cli/src/commands/trace.rs` | 21 | 0 | CLI trace command unwrap on tempdir and DB calls. |
| 10 | `crates/agileplus-cli/src/commands/gate_run.rs` | 19 | 0 | Gate run command unwrap on in-memory SQLite and metrics. |
| 11 | `crates/agileplus-sync/src/store.rs` | 19 | 0 | Sync store unwrap on lock and DB operations. |
| 12 | `crates/agileplus-events/src/domain_event.rs` | 15 | 4 | **4 panic! in variant matching**; protocol deserialization crash risk. |
| 13 | `crates/agileplus-plane/src/webhook.rs` | 0 | 5 | **5 panic! on webhook payload type matching**; external input can trigger. |
| 14 | `crates/agileplus-subcmds/src/tracera_bridge.rs` | 0 | 3 | **3 panic! on reference-type matching**; graph traversal crash risk. |
| 15 | `crates/agileplus-p2p/src/replication.rs` | 0 | 2 | **2 panic! on expected story/user**; data sync crash risk. |
| 16 | `crates/agileplus-nats/src/nats_adapter.rs` | 0 | 1 | **1 panic! on unexpected variant**; deserialization risk. |

---

## Detailed Findings by Pattern

### `TODO` — 4 occurrences

| File | Line | Text |
|---|---|---|
| `crates/agileplus-github/src/sync.rs` | 14 | `//! TODO(WP19-T114): wire `sync_repository` to `agileplus-sqlite` by having` |
| `crates/agileplus-governance/src/client.rs` | 216 | `let iteration = 1; // TODO: Track iterations per channel` |
| `crates/agileplus-governance/src/client.rs` | 234 | `// TODO: Sync to remote if enabled` |
| `crates/agileplus-governance/src/client.rs` | 261 | `last_sync: None, // TODO: Track last sync` |

### `FIXME` — 0 occurrences

No `FIXME` comments found in `crates/*/src/**/*.rs`.

### `XXX` — 4 occurrences

| File | Line | Text |
|---|---|---|
| `crates/agileplus-dashboard/src/process_detector.rs` | 107 | `// Look for task identifiers like WP13, FR-XXX, etc. in command line` |
| `crates/agileplus-sqlite/src/seed/catalog.rs` | 4 | `//!   ### FR-XXX-NNN — Title text` |
| `crates/agileplus-sqlite/src/seed/catalog.rs` | 48 | `// Match heading lines: `### FR-XXX-NNN — Title`` |
| `crates/agileplus-sqlite/src/seed/catalog.rs` | 49 | `// Also handle `### FR-XXX-NNN\n\n**Title:** ...` (Authvault style via next line)` |

### `panic!` in Non-Test Library Code — 15 occurrences

| File | Line | Text |
|---|---|---|
| `crates/agileplus-events/src/domain_event.rs` | 494 | `other => panic!("unexpected variant: {other:?}"),` |
| `crates/agileplus-events/src/domain_event.rs` | 508 | `other => panic!("unexpected: {other:?}"),` |
| `crates/agileplus-events/src/domain_event.rs` | 522 | `other => panic!("unexpected: {other:?}"),` |
| `crates/agileplus-events/src/domain_event.rs` | 677 | `other => panic!("unexpected: {other:?}"),` |
| `crates/agileplus-nats/src/nats_adapter.rs` | 665 | `other => panic!("unexpected variant: {other:?}"),` |
| `crates/agileplus-p2p/src/replication.rs` | 620 | `_ => panic!("expected story"),` |
| `crates/agileplus-p2p/src/replication.rs` | 647 | `_ => panic!("expected user"),` |
| `crates/agileplus-plane/src/webhook.rs` | 286 | `panic!("expect IssueDeleted");` |
| `crates/agileplus-plane/src/webhook.rs` | 308 | `panic!("expect ModuleUpdated");` |
| `crates/agileplus-plane/src/webhook.rs` | 320 | `panic!("expect ModuleDeleted");` |
| `crates/agileplus-plane/src/webhook.rs` | 333 | `panic!("expect CycleUpdated");` |
| `crates/agileplus-plane/src/webhook.rs` | 346 | `panic!("expect CycleDeleted");` |
| `crates/agileplus-subcmds/src/tracera_bridge.rs` | 215 | `other => panic!("expect SelfLoop, got {other:?}"),` |
| `crates/agileplus-subcmds/src/tracera_bridge.rs` | 266 | `other => panic!("expect Requirement from-ref, got {other:?}"),` |
| `crates/agileplus-subcmds/src/tracera_bridge.rs` | 272 | `other => panic!("expect Test to-ref, got {other:?}"),` |

### `unimplemented!` — 67 occurrences (all in one file)

All 67 `unimplemented!()` calls are in `crates/agileplus-cli/src/commands/list_tests.rs` (lines 49–308). This file is a stub command implementation with virtually every branch unimplemented. Key lines:

- `crates/agileplus-cli/src/commands/list_tests.rs:49` `unimplemented!()`
- `crates/agileplus-cli/src/commands/list_tests.rs:52` `unimplemented!()`
- `crates/agileplus-cli/src/commands/list_tests.rs:55` `unimplemented!()`
- `crates/agileplus-cli/src/commands/list_tests.rs:58` `unimplemented!()`
- `crates/agileplus-cli/src/commands/list_tests.rs:71` `unimplemented!()`
- ... (continuing through line 308)

### `expect(` in Non-Test Library Code — 57 occurrences (top 10 files)

| File | Count | Sample refs |
|---|---|---|
| `crates/agileplus-sqlite/src/lib.rs` | 9 | `784` `1494` `2157` `2158` `2170` `2171` `2173` `2174` `2200` |
| `crates/agileplus-nats/src/nats_adapter.rs` | 8 | `637` `638` `655` `656` `680` `681` `718` `729` |
| `crates/agileplus-dashboard/src/routes.rs` | 6 | `2522` `2548` `2826` `2848` `2882` `2904` |
| `crates/agileplus-triage/src/embeddings.rs` | 6 | `228` `229` `231` `305` `306` `308` |
| `crates/agileplus-events/src/domain_event.rs` | 3 | `483` `484` `581` |
| `crates/agileplus-grpc/src/server/mod.rs` | 2 | `562` `568` |
| `crates/agileplus-import/src/report.rs` | 2 | `50` `51` |
| `crates/agileplus-subcmds/src/tracera_bridge.rs` | 2 | `261` `282` |
| `crates/agileplus-p2p/src/lib.rs` | 2 | `243` `260` |
| `crates/agileplus-domain/src/domain/snapshot.rs` | 2 | `85` `86` |

### `unwrap()` in Non-Test Library Code — 989 occurrences (top 10 files with sample refs)

| File | Count | Sample refs |
|---|---|---|
| `crates/agileplus-sqlite/src/lib.rs` | 295 | `797` `802` `803` `815` `818` `819` `827` `831` `834` `835` |
| `crates/agileplus-triage/src/router.rs` | 61 | `37` `38` `39` `40` `45` `46` `50` `54` `56` `58` |
| `crates/agileplus-dashboard/src/routes.rs` | 38 | `2441` `2468` `2470` `2475` `2476` `2481` `2499` `2501` `2506` `2507` |
| `crates/agileplus-p2p/src/import.rs` | 36 | `260` `295` `304` `317` `335` `352` `369` `383` `418` `423` |
| `crates/agileplus-graph/src/graph_store.rs` | 24 | `45` `51` `61` `71` `88` `94` `100` `106` `116` `144` |
| `crates/agileplus-cli/src/commands/worklog.rs` | 23 | `937` `950` `1058` `1066` `1068` `1070` `1072` `1075` `1083` `1086` |
| `crates/agileplus-nats/src/bus.rs` | 22 | `148` `163` `170` `175` `195` `202` `209` `224` `260` `266` |
| `crates/agileplus-sqlite/src/seed/runner.rs` | 22 | `167` `168` `170` `210` `224` `230` `242` `248` `260` `261` |
| `crates/agileplus-cli/src/commands/trace.rs` | 21 | `396` `425` `427` `440` `444` `453` `463` `465` `478` `482` |
| `crates/agileplus-cli/src/commands/gate_run.rs` | 19 | `287` `296` `302` `308` `314` `320` `325` `328` `335` `341` |

---

## Methodology

1. Enumerated all `.rs` files under `crates/*/src/` using `Get-ChildItem -Recurse` with a regex filter `crates\\[^\\]+\\src\\`.
2. Ran `Select-String` (case-sensitive) for each pattern: `TODO`, `FIXME`, `XXX`, `unwrap\(\)`, `expect\(`, `panic!`, `unimplemented!`.
3. Classified each hit as `test` or `lib` based on path: filenames matching `tests?\.rs$|_tests\.rs$` or any segment `/tests/` were classified as test; all others as lib.
4. Aggregated counts per file, per pattern, and per test/lib split.
5. No builds, compilation, or git operations were performed. Only read-only file inspection.

---

## 5-Line Summary

- **1,531 total hotspots** found across 116 source files in 24 crates.
- **`unwrap()` dominates** with 1,353 hits (989 in library code), making it the single largest debt category.
- **`crates/agileplus-sqlite/src/lib.rs` is the #1 hotspot** with 295 `unwrap()` calls in one file; any DB failure will panic.
- **`panic!` in library code** (15 instances) is concentrated in event deserialization, webhook handling, and graph traversal—paths that can be triggered by external input.
- **Zero `FIXME` markers** and only 4 `TODO` comments suggest the team is not leaving explicit cleanup breadcrumbs; the debt is primarily hidden in `unwrap()` and `expect()` calls.
