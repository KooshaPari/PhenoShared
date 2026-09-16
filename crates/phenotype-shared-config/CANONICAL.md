# CANONICAL — `phenotype-shared-config`

**Date:** 2026-06-18
**ADRs:**
- [ADR-031](https://github.com/<REDACTED>/repos/blob/main/docs/adr/2026-06-17/ADR-031-configra-absorb.md) (Configra absorb)
- [ADR-022](https://github.com/<REDACTED>/repos/blob/main/docs/adr/2026-06-15/ADR-022-config-consolidation-two-crate-split.md) (superseded by ADR-031, preserved for history)
- L5-104 §4 Step 3 (re-point the embedded sub-crate markers)

---

This crate is a **legacy SDK helper** for the `pheno*` fleet. Its
`ConfigSource` / `ConfigValue` / `SourcePriority` / `ConfigFormat` /
`ConfigMeta` types and the `ConfigError` / `search_config_dirs` helpers
are now superseded by the canonical config substrate.

> **Note on naming:** despite the `phenotype-shared-config` name, this
> crate is **NOT** the canonical shared config. The name is misleading.
> The canonical Rust config is `<REDACTED>/Configra:crates/pheno-config/`
> (the substrate absorbed via Configra PR #45 on 2026-06-18).
> The canonical hexagonal config is
> `<REDACTED>/Configra:crates/settly/` (absorbed via Configra PR #44).

## Canonical replacement

| Concern | Old location | New canonical location |
|---|---|---|
| Type-gated `Config` struct (URL, PORT, LOG_LEVEL, DB_PATH, FEATURE_FLAGS) + `load_from_env` / `load_from_file` / `load_from_toml_file` / `combine` / `ConfigBuilder` / `Config::merge` | `pheno-config` crate (local-only) | [`<REDACTED>/Configra:crates/pheno-config/`](https://github.com/<REDACTED>/Configra/tree/main/crates/pheno-config) |
| Generic SDK helpers (`ConfigSource`, `ConfigValue`, `SourcePriority`, `ConfigFormat`, `FormatDetect`, `ConfigMeta`, `ConfigError`, `search_config_dirs`, `AppDirs`, `ConfigDir`) | `pheno/crates/phenotype-shared-config/` (this crate) | **No direct replacement** — these are intentionally NOT absorbed; the `pheno*` fleet has no current consumer of this API after the Configra migration. Open a `Configra` PR to upstream a specific helper if a need arises. |
| TS edge bindings | `<REDACTED>/Conft` (archived) | [`<REDACTED>/Configra:typescript/`](https://github.com/<REDACTED>/Configra/tree/main/typescript) |
| Hexagonal config (`settly` domain/application/adapters/infrastructure) | `<REDACTED>/phenotype-config` (DEPRECATED 2026-06-17, archive 2026-07-15) | [`<REDACTED>/Configra:crates/settly/`](https://github.com/<REDACTED>/Configra/tree/main/crates/settly) (absorbed via [Configra PR #44](https://github.com/<REDACTED>/Configra/pull/44) 2026-06-18) |

## Why this marker

Per ADR-031, `<REDACTED>/Configra` is the canonical Rust config substrate.
This `phenotype-shared-config` crate contains a small (33 LoC) `lib.rs`
that re-exports 4 modules (`dirs`, `error`, `format`, `source`) and
defines a `ConfigMeta` struct. The `pheno*` fleet has no current consumer
of this API after the Configra migration; the crate is preserved as a
historical artifact, not a substrate.

## What stays here

- This `CANONICAL.md` marker
- The 33-LoC SDK helper as a historical artifact
- Historical commit log

## Consumers that must update

| Consumer | Was | Now |
|---|---|---|
| `pheno*` services using `ConfigSource` / `ConfigValue` / `SourcePriority` / `ConfigFormat` | `phenotype_shared_config::*` | **Migrate to `pheno_config::Config` from `Configra`** — see migration notes in the L5-110 findings doc |
| `pheno*` services using `ConfigError` / `Result` from this crate | `phenotype_shared_config::ConfigError` | `pheno_config::ConfigError` (from `Configra/crates/pheno-config/`) |
| `pheno*` services using `search_config_dirs` / `AppDirs` / `ConfigDir` | `phenotype_shared_config::search_config_dirs` | **No replacement** — use `std::env::var` + `pheno_config::load_from_env(prefix)` |

## See also

- [ADR-031](https://github.com/<REDACTED>/repos/blob/main/docs/adr/2026-06-17/ADR-031-configra-absorb.md) — Configra absorb (canonical home)
- [ADR-022](https://github.com/<REDACTED>/repos/blob/main/docs/adr/2026-06-15/ADR-022-config-consolidation-two-crate-split.md) — superseded two-crate split
- [`<REDACTED>/Configra`](https://github.com/<REDACTED>/Configra) — canonical Rust config substrate
- [`<REDACTED>/phenotype-config`](https://github.com/<REDACTED>/phenotype-config) — deprecated; archive 2026-07-15
- `findings/2026-06-18-L5-110-adr-035-impl.md` (this turn) — L5-110 implementation log
