# F1 Review: DAG Foundation (`bp-dag-foundation-2026-06-12`)

**Reviewer:** Forge  
**Branch:** `bp-dag-foundation-2026-06-12` (commit `8d96dd64`)  
**Base:** `main` (commit `62a04cc4`)  
**Area:** compute-infra  
**Epic:** epic_F — DAG foundation + automation  
**Date:** 2026-06-25  

---

## Diffstat

```
 Cargo.toml                     |   1 +
 crates/byteport-dag/Cargo.toml |  11 +
 crates/byteport-dag/src/lib.rs | 441 +++++++++++++++++++++++++++++++++
 3 files changed, 453 insertions(+)
```

---

## Summary

This branch introduces the `byteport-dag` crate — a Directed Acyclic Graph engine for modelling and validating compute/infrastructure orchestration workflows. The crate is wired into the workspace via `Cargo.toml`.

### What's included

- **Core types:** `Dag` (graph container), `Node` (task/step), `NodeId` (string alias), `Payload` (arbitrary JSON payload per node)
- **Cycle detection:** DFS-based detection at edge-insertion time (`add_edge`) and full-graph validation (`validate`)
- **Topological sort:** Kahn's algorithm implementation in `topological_sort`
- **Error handling:** `DagError` enum with `DuplicateNode`, `NodeNotFound`, `CycleDetected`, `EmptyDag` variants
- **Test suite:** 8 tests covering empty DAGs, duplicate nodes, edge validation, cycle detection, linear ordering, diamond ordering, and raw-construction validation

### Architecture notes

- Dependencies are stored as `BTreeSet<NodeId>` on each `Node`, providing ordered iteration and cheap O(log n) lookups.
- The `Dag` struct uses `BTreeMap<NodeId, Node>` for deterministic iteration — important for reproducible execution plans.
- `serde_json::Value` is used for `Payload`, keeping the type open for consumers while maintaining serializability.
- The `from_raw` constructor explicitly defers to `validate()` so deserialization from external sources can be checked.

---

## Findings

### F1.1 — Dead code in `topological_sort` (medium)

**File:** `crates/byteport-dag/src/lib.rs:157-177`  
**Severity:** medium  
**Category:** code-quality  

The `topological_sort` method contains three blocks that build and discard `in_degree` before the correct computation at line 180. Lines 158-165 and 167-176 are dead code — they allocate maps and iterate without effect.

**Recommendation:** Remove lines 158-177 and keep only the clean computation at line 180 onward.

### F1.2 — `topological_sort` internal loop scans all nodes O(n²) (low)

**File:** `crates/byteport-dag/src/lib.rs:192-202`  
**Severity:** low  
**Category:** performance  

The inner loop of Kahn's algorithm scans every node to find dependants of the current node (lines 194-201). This yields O(n²) runtime for the topological sort. For small DAGs (tens of nodes) this is fine, but it won't scale to hundreds/thousands.

**Recommendation:** Pre-compute a reverse-adjacency map (`children: BTreeMap<NodeId, Vec<NodeId>>`) alongside the node map so the inner loop becomes an O(1) lookup. This should be indexed when edges are added.

### F1.3 — `CycleDetected` error loses node identity in `validate` (low)

**File:** `crates/byteport-dag/src/lib.rs:236`  
**Severity:** low  
**Category:** observability  

When `validate()` detects a cycle, the error message uses `"unknown"` for both node IDs. The DFS implementation tracks the stack, so the back-edge node is available but not captured.

**Recommendation:** Thread the cycle-start node ID back through `_detect_cycle_from` so the error reports which node is part of the cycle.

### F1.4 — `Payload` forces `serde_json` dependency on all consumers (info)

**File:** `crates/byteport-dag/src/lib.rs:24`  
**Severity:** info  
**Category:** architecture  

`Payload` is hardcoded as `serde_json::Value`, which means every consumer must pull in `serde_json`. For environments where the payload is a domain struct, this adds friction.

**Recommendation:** Consider making Payload generic: `pub type Payload<T = serde_json::Value> = T` with a default, or expose a trait for custom payload types.

### F1.5 — Missing `#[non_exhaustive]` on `DagError` (info)

**File:** `crates/byteport-dag/src/lib.rs:31`  
**Severity:** info  
**Category:** api-design  

`DagError` is a public enum without `#[non_exhaustive]`. Adding new error variants in the future would be a breaking change for consumers that match exhaustively.

**Recommendation:** Add `#[non_exhaustive]` to `DagError`.

### F1.6 — Missing ergonomic builder API (info)

**File:** `crates/byteport-dag/src/lib.rs`  
**Severity:** info  
**Category:** usability  

The API requires separate `add_node` then `add_edge` calls. For workflows with 5+ steps this becomes verbose.

**Recommendation:** Add a `DagBuilder` with a chained API:

```rust
Dag::define()
    .step("build", |s| s.label("Build").depends_on("checkout"))
    .step("test", |s| s.depends_on("build"))
    .step("deploy", |s| s.depends_on("test"))
    .build()?;
```

---

## Conclusion

The DAG foundation is well-structured, properly tested, and follows Rust best practices (serde, thiserror, workspace integration). The findings are mostly code-quality improvements and future-proofing — nothing blocking.

The 8-test suite covers the critical paths. After addressing F1.1 (dead code removal) the crate should compile cleanly. F1.2 and F1.6 are enhancement suggestions for the next iteration.
