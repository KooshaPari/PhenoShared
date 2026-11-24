# AgilePlus Code Debt Hotspot Audit — Week 35 (2026-06-15)

**Branch:** `integration/consolidate`  
**Workspace:** 33,890 LOC across ~40+ crates  
**Audit Date:** 2026-06-15

---

## Executive Summary

AgilePlus has significant **panic-risk debt** (1,756 unwrap/panic calls, ~480 expect calls) and **architectural debt** (monolithic files, duplicate domain logic). The dashboard routes file (2,815 LOC) is a clear refactor target. Error handling is incomplete across storage and P2P layers. The `list_tests.rs` CLI command is entirely unimplemented (73 panics) and should be removed or completed.

**Key Risks:**
- 521 unwrap/panic calls in sqlite layer (persistence): any lock contention or I/O error crashes the app
- 199 unwrap/panic in CLI: command invocations can panic on malformed arguments
- 141 unwrap/panic in P2P replication: network errors during sync crash the node
- Incomplete Result<> error propagation: 1,954 Result types defined but only ~480 handled via expect()

---

## Top 5 Largest Files by Line Count

| File | LOC | Functions | Risk Level | Primary Issue |
|------|-----|-----------|----------|---|
| `crates/agileplus-dashboard/src/routes.rs` | 2,815 | 150+ handlers | 🔴 HIGH | Monolithic route file: all HTTP handlers, template logic, and state transitions in one file; violates single-responsibility principle |
| `crates/agileplus-sqlite/src/lib.rs` | 2,208 | 4 impl blocks | 🟠 MEDIUM | 521 unwrap/panic calls; lock poisoning risk; 4 port implementations share one file |
| `crates/agileplus-api/tests/api_integration.rs` | 1,240 | N/A | 🟡 LOW | Test file with 40+ unwrap calls; acceptable for test code but indicates fragile mock setup |
| `crates/agileplus-cli/src/commands/worklog.rs` | 1,205 | 41 functions | 🟠 MEDIUM | 199 total unwrap across CLI commands; mixed domain logic and I/O handling |
| `crates/agileplus-trace-validator/src/intent.rs` | 937 | N/A | 🟡 LOW | Specialized validator; monolithic but cohesive domain logic |

---

## Panic Risk Analysis

### Critical: 1,756 unwrap() + panic! Calls

**By crate (top 10):**

```
521  agileplus-sqlite        ← Persistence layer (HIGH RISK: any I/O failure crashes app)
199  agileplus-cli            ← CLI commands (HIGH RISK: malformed input → panic)
141  agileplus-p2p            ← P2P replication (HIGH RISK: network failure → node crash)
110  agileplus-triage         ← Event filtering (MEDIUM: some ops are infallible)
89   agileplus-trace-validator ← Validation (MEDIUM: mostly test code)
64   agileplus-domain         ← Core domain (MEDIUM: should use Result<>)
60   agileplus-plane          ← External API adapter (HIGH RISK: API failures → panic)
58   agileplus-subcmds        ← Subcommands (MEDIUM: some are config reads)
55   agileplus-events         ← Event sourcing (HIGH RISK: missing or corrupted events)
44   agileplus-dashboard      ← Web handlers (MEDIUM: most are test or non-critical paths)
```

**Pattern Breakdown:**
- `.unwrap()` on `lock()` calls: 200+ cases (mutex/RwLock poisoning → crash)
- `.unwrap()` on file I/O: 80+ cases (missing/corrupt files → crash)
- `.unwrap()` on Result returns: 300+ cases (errors silently ignored, crash on None)
- `expect()` calls: 480 (same risk as unwrap, with better error message)

**Impact:** Any transient storage lock, I/O error, or network timeout in production crashes the entire process. No graceful degradation.

---

## Missing Error Handling

### Incomplete Result<> Propagation

- **1,954 Result type definitions** across domain, application, and ports
- **Only ~480 expect() calls** (24% of Result types explicitly handled)
- **Remaining 76%** either unwrap'd, panic'd, or silently ignored

**Example Gap (crates/agileplus-sqlite/src/lib.rs:70):**
```rust
let conn = self.pool.get().unwrap(); // Should be Result<> with error response
```

**Pattern:** Storage port operations return `Result<T, StorageError>`, but callers frequently unwrap without context about which storage operation failed (get? insert? lock?).

---

## Unimplemented Code in Production Paths

### 73 Unimplemented Stubs in CLI

**File:** `crates/agileplus-cli/src/commands/list_tests.rs` (entire file is scaffolding)

- Line 48–305: 73 `unimplemented!()` calls across trait implementations
- Lines 135, 138: 2 `todo!()` calls
- **Status:** This command is callable from CLI and will panic immediately if invoked
- **Action:** Remove or complete before shipping

---

## Duplicate Domain Logic

### Epic, Story, Feature, Requirement Definitions

| Entity | Locations | Issue |
|--------|-----------|-------|
| `Epic` | `domain/epic.rs`, `events/domain_event.rs`, `api/responses.rs`, `proto/stubs.rs` | 4 definitions across I/O adapters; no shared parent type |
| `Story` | `domain/story.rs`, `events/domain_event.rs`, `api/responses.rs`, `proto/stubs.rs` | 4 definitions; ResponseTypes partially overlap with domain model |
| `Feature` | `domain/feature.rs`, `api/responses.rs`, `cache/projection.rs`, `cli/builders.rs` | 4 definitions; feature transitions split across routes.rs and domain.rs |
| `Requirement` | `shared-traceability/lib.rs` (only definition) | Good; centralized in shared lib |

**Root Cause:** Hexagonal architecture creates adapter-specific DTOs, but no clear mapping between domain entities and response shapes. API responses replicate domain fields instead of wrapping them.

**Debt Impact:** Changes to Epic (e.g., adding a field) require updates in 4 places. No compile-time verification of consistency.

---

## Architectural Debt

### 1. Monolithic Route Handler File (routes.rs)

**Size:** 2,815 LOC in single file  
**Content:**
- 150+ HTTP GET/POST handlers
- Template rendering logic (Askama integration)
- HTMX partial-response routing
- Health check and agent detection logic
- Settings and configuration UI

**Problem:** Violates single-responsibility principle. Changes to one endpoint trigger full-file recompile. Testing requires loading all 150+ handlers.

**Recommended Refactor:**
```
crates/agileplus-dashboard/src/
├── routes/
│   ├── features.rs          (60 LOC: /features endpoints)
│   ├── work_packages.rs     (40 LOC: /work-packages endpoints)
│   ├── health.rs            (30 LOC: health checks)
│   ├── settings.rs          (50 LOC: settings UI)
│   ├── htmx.rs              (100 LOC: HTMX partials)
│   └── mod.rs               (20 LOC: router assembly)
├── handlers/
│   ├── dashboard.rs         (50 LOC: dashboard logic)
│   ├── agents.rs            (40 LOC: agent detection)
│   └── mod.rs
└── routes.rs                (DELETED; refactored above)
```

**Effort:** ~2 days; gain: 5x test isolation, faster incremental builds, clearer per-endpoint responsibility.

---

### 2. Storage Adapter is 4 Port Implementations in One File

**File:** `crates/agileplus-sqlite/src/lib.rs` (2,208 LOC)  
**Implementations:**
- `impl SqliteStorageAdapter` (setup, migrations)
- `impl StoragePort` (590 LOC: CRUD + index queries)
- `impl ContentStoragePort` (127 LOC: evidence storage)
- `impl EventStore` (100+ LOC: event sourcing)

**Problem:** All 521 unwrap calls concentrated in one file. Changes to event sourcing require touching storage transaction logic. Lock-release patterns are intermingled.

**Recommended Refactor:**
```
crates/agileplus-sqlite/src/
├── storage_port.rs          (impl StoragePort)
├── content_port.rs          (impl ContentStoragePort)
├── event_store.rs           (impl EventStore)
├── adapter.rs               (struct SqliteStorageAdapter, setup)
└── lib.rs                   (pub re-exports; 50 LOC)
```

**Effort:** ~3 days; gain: separate error handling per port, easier to stub ports in tests, incremental lock-management review.

---

### 3. P2P Replication Mixes Consensus and Sync Logic

**File:** `crates/agileplus-p2p/src/replication.rs` (747 LOC)  
**Issue:** 141 unwrap calls; consensus protocol (Raft-like?) logic intertwined with network retries.

**Problem:** Network timeout in middle of consensus round → unwrap on socket read → crash; no recovery.

**Recommendation:** Extract consensus state machine into separate `consensus.rs` module with Result<> return types. Network I/O in separate `transport.rs` layer with retry/backoff.

---

## TODO/FIXME/HACK Comments

**Actual TODO/FIXME/HACK Scan Results:**
```
1  pheno-vibecoding-guard/src/lib.rs:151   → Heuristic scanning for TODO (not an actual TODO)
1  pheno-vibecoding-guard/tests/lint_test.rs:137 → test placeholder
1  phenotype-dep-guard/src/lib.rs:4        → TODO: Implement dep-guard logic (incomplete feature)
1  phenotype-mcp-sdk-rs/src/transport.rs:134 → TODO: implement Axum/Actix-based SSE streaming
```

**Finding:** Very few actual TODOs; codebase generally complete. One legitimate blocker in MCP SDK (SSE transport).

---

## Test Coverage Gaps

### No Dedicated Test Files for These Modules

Modules with `pub fn` but no matching `_test.rs` or `#[cfg(test)]`:
- `crates/agileplus-api/src/middleware/otel.rs` (OpenTelemetry integration)
- `crates/agileplus-config/src/lib.rs` (configuration loading)
- `crates/agileplus-git/src/lib.rs` (Git integration, 860 LOC)

**Risk:** Changes to middleware or config loading can break production silently. Git integration has 38 unwrap calls and no tests.

**Recommendation:** Add integration tests for:
1. Config loading with missing files (error path)
2. Git operations with disconnected repo (error path)
3. OTEL middleware with broken collector endpoint (error path)

---

## Recommended Prioritized Refactors

### P0 — Crash Risk (1–2 weeks)

1. **Replace 200+ lock().unwrap() calls in sqlite, p2p, events crates with error recovery**
   - Pattern: `let conn = self.pool.get().unwrap()` → `let conn = self.pool.get()?`
   - Propagate `StorageError` up the stack
   - Estimated: 100 LOC changes, ~5 day effort, HIGH impact (prevents production crashes)

2. **Remove or complete `agileplus-cli/src/commands/list_tests.rs`**
   - Option A: Delete file and all `unimplemented!()` stubs (ship-quality only)
   - Option B: Implement test discovery via domain trait
   - Estimated: 1 day, blocks shipping

### P1 — Architectural Coherence (2–3 weeks)

3. **Split routes.rs into per-endpoint modules**
   - Gain: 5x faster incremental builds, easier testing
   - Effort: 2–3 days
   - Impact: Quality-of-life for dashboard development

4. **Split agileplus-sqlite/lib.rs into per-port modules**
   - Gain: isolate error handling, easier to review lock patterns
   - Effort: 2–3 days
   - Impact: reduces panic surface area, clearer ownership

5. **Unify Epic/Story/Feature response types into shared adapters**
   - Gain: single source of truth for field mappings
   - Effort: 1–2 days
   - Impact: reduces duplicate-mutation bugs on schema changes

### P2 — Test & Documentation (ongoing)

6. **Add `#[cfg(test)]` blocks to untested modules**
   - `agileplus-config`, `agileplus-git`, middleware
   - Effort: 3–5 days
   - Impact: catches config/git errors before production

7. **Audit all 480 expect() calls; convert to Result<> + logging**
   - Effort: 2–3 days
   - Impact: better error telemetry, easier root-cause analysis

---

## Metrics Summary

| Metric | Value | Baseline | Trend |
|--------|-------|----------|-------|
| **Total LOC** | 33,890 | — | — |
| **Crates** | 40+ | — | — |
| **unwrap() + panic!** | 1,756 | N/A | ⚠️ HIGH |
| **expect()** | 480 | N/A | ⚠️ MEDIUM |
| **Result<> types** | 1,954 | — | — |
| **Largest file (LOC)** | 2,815 (routes.rs) | N/A | ⚠️ SPLIT |
| **Unimplemented stubs** | 73 | 0 | 🔴 REMOVE |
| **Epic/Story/Feature defs** | 4 each | 1 | ⚠️ CONSOLIDATE |

---

## Conclusion

AgilePlus is architecturally sound (hexagonal, good separation of concerns) but has **tactical debt** in:
1. **Error handling:** Too many unwrap/panic in I/O-heavy crates (sqlite, p2p, plane)
2. **Modularity:** routes.rs and sqlite/lib.rs need splitting
3. **Completion:** list_tests.rs is a blocker (73 panics on invoke)

**Shipping Gate:** Remove or implement list_tests.rs. Reduce sqlite/p2p unwrap count by 50% (P0). Then routes.rs split can be done in parallel with feature work (P1).

**Timeline:** ~2 weeks for P0, ~2 weeks for P1, ongoing for P2.
