# `config-schema`

[![crates.io](https://img.shields.io/crates/v/config-schema.svg)](https://crates.io/crates/config-schema)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE-MIT)
[![Tier](https://img.shields.io/badge/substrate--tier-2-blueviolet.svg)](#tier-2-substrate)

Extensible configuration schema validation for JSON-based configs.
Absorbed from `Conft` and folded into the Configra workspace per ADR-031
(L5-110).

## What this crate does

- `SchemaField` — declares a single field: name, required?, type-hint.
- `ConfigSchema` — composes a list of `SchemaField`; validates a
  `serde_json::Value` against the list.
- `SchemaError` — typed error for missing-field and wrong-type failures.

This is the **field-shape validator**, not a full JSON-schema engine. It
catches "did the caller forget to set this required key?" and "did the
caller pass a string where a number was expected?". For richer schemas
(Draft 4/7/2020-12), use a dedicated JSON-schema crate.

## When to use

- You want to assert "this JSON config has the right shape" with a
  builder-style API and zero external schema DSL.
- You want a `no_std`-friendly primitive (the only deps are
  `serde_json` + `thiserror`).

## When **not** to use

- You need to validate complex schemas (oneOf, allOf, $ref) — pull in a
  full JSON-schema library.
- You need runtime env-var cascade — use [`pheno-config`](./pheno-config).
- You need file loaders — use [`phenotype-config-loader`](./phenotype-config-loader).

## Quickstart

```rust,no_run
use config_schema::{ConfigSchema, SchemaError};
use serde_json::json;

let schema = ConfigSchema::new()
    .field("name", true, "string")
    .field("port", true, "integer")
    .field("log_level", false, "string");

let config = json!({
    "name": "my-app",
    "port": 8080,
});

schema.validate(&config)?;
# Ok::<_, SchemaError>(())
```

## Tier-2 substrate

This crate is a **tier-2 library** per the ADR-023 / ADR-040 substrate
quality bar. It ships:

- `README.md` (this file)
- `CHANGELOG.md`
- `AGENTS.md`
- 80%+ line coverage gate (current: 100% on the validator path)

## Cross-references

- ADR-031 — Configra absorb
- ADR-022 — Config consolidation (two-crate canonical split)
- ADR-040 — Test coverage gates per tier
- ADR-023 — Agent-effort governance
