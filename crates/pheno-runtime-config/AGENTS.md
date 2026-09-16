# AGENTS.md — pheno-runtime-config

**Phenotype fleet — hot-reloadable runtime configuration (L37).**

## Stack
- Language: Rust
- Build: Cargo (Justfile)
- Key deps: notify v6, arc-swap, tokio, serde

## Quick start
```bash
cargo run --example hot_reload
```

## Commands
- `just install` — `cargo fetch`
- `just build` — `cargo build`
- `just test` — `cargo test`
- `just ci` — build + test + lint + deny
- `just lint` — `cargo clippy --workspace`
- `just fmt` — `cargo fmt`
- `just deny` — `cargo deny check`

## Canonical source
https://github.com/<REDACTED>/pheno-runtime-config
