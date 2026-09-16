# `phenotype-config-loader`

[![crates.io](https://img.shields.io/crates/v/phenotype-config-loader.svg)](https://crates.io/crates/phenotype-config-loader)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE-MIT)
[![Tier](https://img.shields.io/badge/substrate--tier-2-blueviolet.svg)](#tier-2-substrate)

Generic, type-safe JSON and TOML file loaders for the Phenotype ecosystem.
Absorbed from `<REDACTED>/phenotype-config` per ADR-031 (L5-110) and folded
into the Configra workspace.

## What this crate does

- `load_json::<T>(path)` — read a JSON file and deserialize into `T`.
- `load_toml::<T>(path)` — read a TOML file and deserialize into `T`.
- `ConfigLoadError` — a single error type that covers missing-file,
  parse-error, and IO-error cases.

Downstream consumers can depend on this crate without pulling in the
heavier `pheno-config` runtime — it is the smallest viable config-loading
primitive in the Configra split.

## When to use

- You need to read a JSON or TOML file at runtime and parse it into a
  `serde::Deserialize` type.
- You want a stable, minimal dependency surface (no async runtime, no
  `ConfigBuilder`, no `combine()` cascade).

## When **not** to use

- You need env-var cascade, TOML+env overlay, or `combine()` — use
  [`pheno-config`](./pheno-config) instead.
- You need settings lifecycle (validation, migration, versioning) — use
  [`settly`](./settly) instead.
- You need runtime schema validation against field constraints — use
  [`config-schema`](./config-schema) instead.

## Quickstart

```rust,no_run
use serde::Deserialize;
use std::path::Path;
use phenotype_config_loader::load_toml;

#[derive(Deserialize, Debug)]
struct AppConfig {
    name: String,
    port: u16,
}

let cfg: AppConfig = load_toml(Path::new("app.toml"))?;
println!("{} on :{}", cfg.name, cfg.port);
# Ok::<_, phenotype_config_loader::ConfigLoadError>(())
```

## Tier-2 substrate

This crate is a **tier-2 library** per the ADR-023 / ADR-040 substrate
quality bar. That means it ships:

- `README.md` (this file)
- `CHANGELOG.md`
- `AGENTS.md`
- 80%+ line coverage gate (`cargo tarpaulin`)
- unit tests in `src/lib.rs`
- 0 lints via `cargo clippy --all-targets -- -D warnings`

## Cross-references

- ADR-031 — Configra absorb: phenotype-config → Configra
- ADR-022 — Config consolidation (two-crate canonical split)
- ADR-040 — Test coverage gates per tier
- ADR-023 — Agent-effort governance
