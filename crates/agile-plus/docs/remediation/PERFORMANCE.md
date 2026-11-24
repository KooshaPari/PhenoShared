# Performance Remediation — Audit Gap H-Perf (46%)

> **Scope:** Claim engine hot paths, trace-matrix derivation, caching strategy, complexity notes, and benchmark plan.  
> **Status:** Remediation doc + Criterion stubs added (`crates/agileplus-benchmarks/benches/`).  
> **Constraint:** No builds run in this lane; wire benchmarks in a follow-up PR.

## Executive summary

AgilePlus performance risk concentrates in two subsystems audited as under-instrumented:

| Subsystem | Primary code | Dominant cost | Target SLO (proposed) |
|-----------|--------------|---------------|------------------------|
| **Claim engine** | `crates/agileplus-triage/src/claim.rs`, `claim_store_sqlite.rs` | Contention on `claim` / `lookup`; full-store scan on `reap_expired` | ≥5,000 claims/sec (in-memory); ≥500 claims/sec (SQLite WAL) |
| **Trace-matrix derivation** | `agileplus-trace-validator` + `docs/requirements/traceability/MATRIX.md` seed | O(FR × layers) filesystem + JSON parse; no incremental cache | Full repo ≤2s for ≤200 FRs; incremental ≤200ms |

---

## 1. Claim engine — hot paths

### 1.1 In-memory store (`ClaimStore`)

**File:** `crates/agileplus-triage/src/claim.rs`

| Operation | Data structures | Hot-path behavior | Complexity |
|-----------|-----------------|-------------------|------------|
| `claim` | `HashMap<id, Claim>` + `HashMap<(ClaimKind, String), id>` | Resource lookup → active-state check → insert | **O(1)** amortized |
| `heartbeat` | `claims` map | Single `get_mut` + timestamp update | **O(1)** |
| `lookup` | `by_resource` → `claims` | Two hash lookups + clone | **O(1)** |
| `release` | Both maps | Remove id + resource key | **O(1)** |
| `reap_expired` | Full `claims` iteration | Filter expired → collect ids → remove | **O(n)** where *n* = total claims |
| `claim_transfer` | Both maps | Owner/state validation + drain old + insert new | **O(1)** |
| `active` / `all` | Full iteration + filter/clone | Allocates `Vec<Claim>` | **O(n)** |

**Production note:** `ClaimWatcher` (`claim_watcher.rs`) wraps the store and fans out events on every mutation. High churn workloads should batch `reap_expired` on a timer (e.g. every 30s) rather than per-request.

### 1.2 SQLite store (`SqliteClaimStore`, feature `sqlite`)

**File:** `crates/agileplus-triage/src/claim_store_sqlite.rs`

| Operation | SQL pattern | Index use |
|-----------|-------------|-----------|
| `claim` | `SELECT` by `(resource, kind)` then `INSERT` | `idx_claims_resource` |
| `lookup` | `SELECT … WHERE kind = ? AND resource = ?` | `idx_claims_resource` |
| `reap_expired` | `SELECT id … WHERE state = 'active'` then per-row update/delete | `idx_claims_state` (partial scan) |
| `heartbeat` | `UPDATE claims SET last_heartbeat = ? WHERE id = ?` | PK |

**Hot-path risk:** `reap_expired` loads all active rows when TTL reaper runs. For fleets with thousands of concurrent claims, prefer:

```sql
SELECT id FROM claims
 WHERE state = 'active'
   AND julianday(last_heartbeat) + ttl_seconds/86400.0 < julianday(?)
```

…with a covering index on `(state, last_heartbeat)` (additive migration, not yet present).

### 1.3 Caching recommendations

| Layer | What to cache | TTL / invalidation |
|-------|---------------|-------------------|
| **Process-local** | `lookup(kind, resource) → Option<ClaimId>` | Invalidate on claim/release/transfer/reap for that resource |
| **SQLite read path** | Prepared statements for `lookup`, `heartbeat` | Connection lifetime |
| **Multi-agent** | None in-process — use `SqliteClaimStore` behind `Mutex` or dedicated claim service | N/A |
| **Watcher subscribers** | Per-claim `mpsc` channels | Drop on `Expired` / `Released` |

**Do not cache** `active()` / `all()` results across await points — TTL drift makes stale views dangerous for convoy coordination (`agileplus-witness` integration tests).

---

## 2. Trace-matrix derivation — hot paths

### 2.1 Intended pipeline (FR-024-5)

Today `docs/requirements/traceability/MATRIX.md` is a **hand-written seed**. The target auto-derivation path:

```
FUNCTIONAL_REQUIREMENTS.md  ──►  enumerate FR ids
        │
        ▼
traces/<FR-id>.json         ──►  parse 5-layer trace schema
        │                          (spec, docs, tests, code, journeys)
        ▼
filesystem probes           ──►  existence + anchor checks (FR-024-7)
        │
        ▼
status rollup               ──►  🟢/🟡/🔴 per layer
        │
        ▼
MATRIX.md / JSON emit       ──►  `trace-validator --emit-matrix`
```

**Validator touchpoints (existing tests):**

- `crates/agileplus-trace-validator/tests/edge_cases.rs` — schema validation, missing fields
- `docs/TRACEABILITY_MATRIX.md` — gap analysis (FR-024-5: no `--emit-matrix` yet)

### 2.2 Complexity

Let **F** = number of FR rows, **L** = average layers per trace file (≤5), **T** = trace JSON files.

| Phase | Complexity | Notes |
|-------|------------|-------|
| Parse `FUNCTIONAL_REQUIREMENTS.md` | O(F) | Line scan for `- FR-…` bullets |
| Load trace JSON | O(T) | One `serde_json` deserialize per file |
| Layer probe (code/tests/docs) | O(F × L × P) | *P* = path entries per layer; dominates without cache |
| Matrix render | O(F) | Template / table generation |

**Incremental derivation (recommended):**

1. Hash `FUNCTIONAL_REQUIREMENTS.md` + all `traces/*.json` mtime/size → cache key.
2. Store last matrix in `.agileplus/cache/trace-matrix.json`.
3. On cache hit with matching key, skip filesystem probes; only re-probe changed FR files.

### 2.3 Caching recommendations

| Cache | Key | Invalidation |
|-------|-----|--------------|
| Parsed FR list | SHA-256 of `FUNCTIONAL_REQUIREMENTS.md` | File change |
| Per-FR layer status | `(fr_id, trace_json_mtime, probe_targets_hash)` | Trace edit or referenced path mtime |
| Full matrix artifact | Repo cache key + git HEAD | Any invalidation above |

CLI surfacing (future): `agileplus trace matrix --json --cache` reading the same cache directory as the validator.

---

## 3. Benchmark plan

### 3.1 Existing Criterion benches

`crates/agileplus-benchmarks/` already measures event append, replay, API latency, sync roundtrip, and graph queries. Constitution gates are documented per bench (e.g. event append ≥10k events/sec).

### 3.2 New stubs (this PR — additive only)

| Bench file | Measures | Registration |
|------------|----------|--------------|
| `benches/claim_engine_perf.rs` | `claim`, `lookup`, `heartbeat`, `reap_expired` at 100/1k/10k claims | Add `[[bench]]` entries to `crates/agileplus-benchmarks/Cargo.toml` + `agileplus-triage` dependency |
| `benches/trace_matrix_derivation.rs` | Synthetic FR list + trace JSON parse + layer rollup | Same; add `serde_json` fixture helpers |

See `benches/BENCH_REGISTRATION.snippet.toml` for copy-paste `Cargo.toml` blocks.

### 3.3 Run commands (after wiring)

```bash
# Claim engine
cargo bench -p agileplus-benchmarks --bench claim_engine_perf

# Trace matrix derivation (synthetic)
cargo bench -p agileplus-benchmarks --bench trace_matrix_derivation

# Full perf suite (CI nightly)
cargo bench -p agileplus-benchmarks -- --save-baseline main
```

### 3.4 Proposed SLO gates

| Bench | Threshold | Action on regression |
|-------|-----------|----------------------|
| `claim_issue_1000` | p95 < 2ms (in-memory) | Block merge if >3× baseline |
| `claim_lookup_hot` | p95 < 50µs | Warn |
| `reap_expired_10000` | p95 < 20ms | Block if >2× baseline |
| `trace_matrix_200fr` | p95 < 2s (cold); <200ms (cached) | Track only until `--emit-matrix` lands |

### 3.5 CI integration (follow-up)

1. Nightly workflow: `cargo bench -p agileplus-benchmarks -- --noplot` with JSON output uploaded as artifact.
2. Compare against `benches/baselines/` (git-tracked medians).
3. Wire `agileplus-benchmarks` into workspace `members` when perf gate is enforced.

---

## 4. Quick wins checklist

- [ ] Register new bench targets in `agileplus-benchmarks/Cargo.toml`
- [ ] Add `(state, last_heartbeat)` index migration for SQLite claim store
- [ ] Implement `trace-validator --emit-matrix` with incremental cache under `.agileplus/cache/`
- [ ] Expose `agileplus claim reap` CLI hook for ops (manual TTL sweep)
- [ ] Document perf baselines in `.github/workflows/` nightly job

---

## References

- `crates/agileplus-triage/src/claim.rs` — FR-AGP-019
- `docs/TRACEABILITY_MATRIX.md` — FR-024-* gap table
- `docs/requirements/traceability/MATRIX.md` — seed matrix
- `crates/agileplus-benchmarks/benches/event_append_throughput.rs` — pattern for constitution gates
