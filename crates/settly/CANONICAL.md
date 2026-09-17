# Canonical Source Notice

**This crate has been promoted to the `phenotype-config` substrate (ADR-022 RFC 002).**

The canonical source for `phenotype-config-loader` now lives at:

- Repository: https://github.com/KooshaPari/phenotype-config
- Substrate crate: https://github.com/KooshaPari/phenotype-config/tree/main/crates/settly

## Origin

This crate was originally `pheno/crates/phenotype-config-loader` (JSON + TOML
file loaders, ~64 LoC). It has been absorbed into the `settly` hexagonal
crate as part of the ADR-022 two-crate config consolidation:

- `crates/settly/src/domain/sources.rs` — source cascade (env, TOML, JSON)
- `crates/settly/src/ports.rs` — file-loading ports (`FileConfigSource`,
  `LayeredSource`, `Source` traits)
- `crates/settly/src/adapters/` — concrete TOML/JSON adapters

## Status

The copy in `pheno/crates/phenotype-config-loader/` (Dmouse92 fork of
`pheno`) is **deprecated** and retained only for backward compatibility with
existing path-based consumers. No new feature work should land there.

The `phenoShared/crates/phenotype-config-loader/` redirect (which predates
ADR-022) is also **stale** — it predates the two-crate split and now
redirects to a crate path that no longer exists in the canonical substrate.

## Migration Guidance

New consumers should depend on `phenotype-config` (the substrate) and use
`settly::ports::Source` / `settly::adapters::toml::TomlSource` /
`settly::adapters::json::JsonSource`. Existing path-based consumers will be
migrated forward-only as part of the L5-104 ADR-012 → ADR-022 closure work.

Do **not** edit the deprecated `pheno/crates/phenotype-config-loader/` copy
for non-trivial changes — open the change against `phenotype-config` instead,
then re-sync.

Refs: ADR-012 (config consolidation), ADR-022 RFC 002 (two-crate split to
`phenotype-config` Rust core + `Conft` TS edge), L5-104 migration plan.