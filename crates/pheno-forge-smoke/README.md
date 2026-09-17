# pheno-forge-smoke

End-to-end smoke test for the 4-PR forgecode improvement stack (ADR-096).
Validates the `pheno-cdylib-bridge` C-ABI surface by routing store/recall/forget
through each of the 4 memory scopes.

## Status: ABSORBED into `pheno` workspace

This crate was absorbed from https://github.com/KooshaPari/pheno-forge-smoke
on **2026-08-14** per docket `plans/dockets/N15-pheno-substrate-family.md`.

## Usage

```bash
# From the workspace root, build everything:
cargo build --release -p pheno-forge-smoke -p pheno-cdylib-bridge

# Run mock-mode smoke (validates bridge loads + C-ABI round-trip):
./crates/pheno-forge-smoke/scripts/run-smoke.sh mock

# Run with live sidecars (requires supermemory/letta/mem0 sidecars):
./crates/pheno-forge-smoke/scripts/run-smoke.sh sidecar
```

## Layout

- `src/lib.rs` — pure-Rust facade over the loaded cdylib (Bridge, Provider, Scope, MemoryValue)
- `src/main.rs` — binary driver (clap, JSONL/human-readable reports)
- `scripts/run-smoke.sh` — wrapper that locates the bridge `.dylib`/`.so`
- `sidecars/` — stub HTTP server (`pheno-sidecar-stub`) for local end-to-end
