# pheno-config

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE-MIT)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE-APACHE)
[![Rust](https://img.shields.io/badge/rust-1.82+-orange.svg?logo=rust&logoColor=white)](Cargo.toml)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)](#)

> **Canonical typed-config loader for the `pheno-*` fleet.**
> Load your service's `Config { url, port, log_level, db_path, feature_flags }`
> from env vars, JSON files, or TOML files — with a canonical **12-factor
> `combine()`** that overlays env over TOML.

> **Heads-up — this crate now lives inside `<REDACTED>/Configra`.**
> The source-of-truth repo moved on 2026-06-18 (ADR-031 follow-up,
> L5-104.7). The crate name, version, and public API are unchanged;
> every consumer's `Cargo.toml` keeps working without modification.
> See `AGENTS.md` for the migration table.

---

## Quick start

Add to your `Cargo.toml`:

```toml
[dependencies]
pheno-config = "0.2"
```

Then in your service:

```rust
use pheno_config::{combine, ConfigBuilder};

let cfg = ConfigBuilder::new()
    .url("https://api.example.com")
    .db_path("/var/lib/app.db")
    .port(9090)
    .log_level("debug")
    .feature_flag("beta")
    .build()
    .expect("config");
```

For the canonical **12-factor path** (TOML file filled by env vars):

```rust
use pheno_config::combine;

let cfg = combine("config.toml", "MYAPP")?;
```

`config.toml` carries defaults; `MYAPP_*` env vars override at runtime.
See [`docs/twelve-factor.md`](docs/twelve-factor.md) for the deep dive.

## API surface

| Function / type                                          | Since | Notes                                                                |
| -------------------------------------------------------- | ----- | -------------------------------------------------------------------- |
| `Config { url, port, log_level, db_path, feature_flags }` | 0.1.0 | `Serialize`/`Deserialize`; round-trips through JSON, TOML, env, builder |
| `ConfigError` (3-variant: `MissingField`, `ParseError`, `IoError`) | 0.1.0 | Closed enum, no `#[non_exhaustive]` — exhaustiveness checks are useful |
| `ConfigBuilder`                                          | 0.1.0 | Sensible defaults: `port=8080`, `log_level="info"`, flags=`Vec::new()` |
| `load_from_env(prefix)`                                  | 0.1.0 | Reads `<PREFIX>_*` env vars; requires `URL` + `DB_PATH`              |
| `load_from_file(path)`                                   | 0.1.0 | Reads a JSON file                                                     |
| `load_from_toml_file(path)`                              | 0.2.0 | Reads a TOML file                                                     |
| `Config::merge(&mut self, other)`                        | 0.2.0 | Deep-merge with non-default-wins semantics                           |
| `combine(file, env_prefix)`                              | 0.2.0 | 12-factor cascade: file fills, env overrides                         |

## Env-var names (for `load_from_env` / `combine`)

Substituting `<PREFIX>` for whatever you pass in (e.g. `"MYAPP"`):

| Env var                  | Required? | Type            | Default          |
| ------------------------ | --------- | --------------- | ---------------- |
| `<PREFIX>_URL`           | yes       | string          | —                |
| `<PREFIX>_PORT`          | no        | `u16`           | `8080`           |
| `<PREFIX>_LOG_LEVEL`     | no        | string          | `"info"`         |
| `<PREFIX>_DB_PATH`       | yes       | path string     | —                |
| `<PREFIX>_FEATURE_FLAGS` | no        | comma-separated | `Vec::new()`     |

## Error type

`ConfigError` is a deliberately closed 3-variant enum:

- `MissingField(String)` — a required env var or JSON/TOML key is unset.
- `ParseError { field, message }` — value is present but malformed.
- `IoError(std::io::Error)` — file read failed (via `#[from]`).

No `anyhow` boundary is used so the dependency surface stays tiny and
downstream `match` exhaustiveness is meaningful.

## Consumers

L5 #81–85 across the `pheno-*` fleet use this crate as the single source
of truth for runtime configuration.

## License

Dual-licensed under [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE),
at your option.