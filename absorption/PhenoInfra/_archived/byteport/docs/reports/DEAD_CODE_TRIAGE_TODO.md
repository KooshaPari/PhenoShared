# BytePort: Dead Code Triage — `todo!()` Markers

**Audited:** 2026-05-06
**Scope:** BytePort repository (`/Users/kooshapari/CodeProjects/Phenotype/repos/BytePort/`)
**Note:** BytePort is a Go/Rust hybrid. The Rust layer (`backend/nvms.rs`, `backend/byteport/tests/`) is a YAML parser and test harness. The Go layer has no `todo!()` markers.

---

## Summary

| Location | File Count | `todo!()` Count |
|---|---|---|
| Active source (`backend/`, `src/`) | 2 | **1** |
| `.history/` (historical scaffolds) | 51 | **49** |
| **Total (all .rs files)** | **53** | **50** |

**The DAG reported 741 markers. This was a stale scan including archived scaffolding. The actual active codebase has 1 `todo!()`.**

---

## Active Source: 1 `todo!()` Found

### `backend/nvms.rs:280` — `locateNVMS()`

```rust
fn locateNVMS(path: String) -> String {
    // Locate nvms.yaml in targetDirectory

    todo!()
}
```

- **Category:** Unimplemented utility function
- **Severity:** Low — `locateNVMS` is declared but never called in the active codebase
- **Action:** Either implement (walk target directory looking for `nvms.yaml`) or remove if unused

---

## `.history/` Directory: 49 `todo!()` Across 51 Scaffold Files

These are historical Rust code-generation artifacts stored in `.history/`. They are not compiled or tested.

Key clusters:

| Path Pattern | Files | Notes |
|---|---|---|
| `.history/temp/src/app_*.rs` | 2 | Frontend scaffold attempts (2024-09-22), some todos commented out |
| `.history/backend/rustScaffold/parser/parse_*.rs` | 49 | Rust parser scaffold snapshots (2024-11-29), each file has 1 `todo!()` |

- **Category:** Stale scaffold snapshots from abandoned Rust migration attempts
- **Action:** Candidate for archival or deletion — these files are not part of any active build

---

## Recommendations

| Priority | Item | Action |
|---|---|---|
| P2 | `locateNVMS()` in `backend/nvms.rs` | Implement or remove if dead code |
| P3 | `.history/` Rust scaffold files | Move to `.archive/` or delete — these predate the Go rewrite and are not compiled |
| Informational | BytePort's Go layer has 0 `todo!()` markers | No action needed |

---

## File Breakdown (Active Source)

```
backend/byteport/tests/smoke_test.rs  — 0 todo!()
backend/nvms.rs                       — 1 todo!()  (line 280)
```

---

## Methodology

- Source: `grep -rn "todo!(" --include="*.rs" BytePort/ --exclude-dir=".history"`
- History: `grep -rn "todo!(" --include="*.rs" BytePort/.history/`
- Go layer: `grep -rn "todo!" --include="*.go" BytePort/` (1 result in commented historical Go file)
- Call-graph check: `locateNVMS` is defined in `backend/nvms.rs` but not referenced elsewhere in the active source
