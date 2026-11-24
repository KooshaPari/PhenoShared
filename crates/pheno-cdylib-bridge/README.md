# pheno-cdylib-bridge

C-ABI shared library (`cdylib` + `staticlib`) that exposes the `pheno-*` Rust
crates to Go (forgecode) and other FFI consumers. The primary consumer is the
upstream `antinomyhq/forgecode` agent CLI; the bridge lets forgecode load our
pure-Rust crates via `cgo` or `plugin.Open()` without rewriting them in Go.

## Status: ABSORBED into `pheno` workspace

This crate was absorbed from https://github.com/KooshaPari/pheno-cdylib-bridge
on **2026-08-14** per docket `plans/dockets/N15-pheno-substrate-family.md`.

## C-ABI Surface

| Function | Purpose |
|---|---|
| `pheno_bridge_version` | Static `*const c_char` with semver |
| `pheno_last_error`     | Most recent error message |
| `pheno_memory_new`     | Open a memory port (`"sm"`, `"letta"`, `"cognee"`, `"mem0"`, `"graphiti"`, `"hippo"`, `"zep"`, `"composite"`) |
| `pheno_memory_store`   | Store a value (returns 0/1/2/3) |
| `pheno_memory_recall`  | Run a recall query (heap-allocated JSON out) |
| `pheno_memory_forget`  | Delete (`scope`, `key`) |
| `pheno_memory_free`    | Close the port |
| `pheno_string_free`    | Free a heap-allocated C string returned by the bridge |

## Cross-repo dependency

This crate imports `thegent-memory` via a path-dep at
`../../../thegent/crates/thegent-memory`. The bridge IS the C-ABI wrapper for
`thegent-memory` v2; they must evolve together.

## Build

```bash
cargo build --release -p pheno-cdylib-bridge
# Produces:
#   target/release/libpheno_bridge.{dylib,so,dll}
```

## Layout

- `src/lib.rs` — C-ABI implementation
- `tests/ffi_smoke.rs` — 12 C-ABI smoke tests
- `c/examples/` — C consumer example
- `scripts/` — `build-c-smoke.sh`, `run-c-smoke.sh` — C build & run wrappers
