# Canonical Source Notice — legacy `phenotype-shared-config`

**This crate has been promoted to the `phenotype-config` substrate (ADR-022 RFC 002).**

The legacy `phenotype-shared-config` crate (originally Dmouse92-style
shared-config schema in `pheno/crates/phenotype-shared-config/`) has been
absorbed into the substrate at:

- Repository: https://github.com/KooshaPari/phenotype-config
- Substrate crate: https://github.com/KooshaPari/phenotype-config/tree/main/crates/settly

## Why a second marker

The original Dmouse92 cherry-pick (`af0d5d5`) introduced two separate
`CANONICAL.md` markers — one per absorbed crate. While the substrate has
collapsed both into the single hexagonal `settly` crate, we preserve the
two-marker structure so that path-based consumers searching for
`phenotype-shared-config` can still find an authoritative redirect.

## Canonical mapping

| Original crate | Substrate destination |
| --- | --- |
| `pheno/crates/phenotype-config-loader` | `phenotype-config/crates/settly` (ports, sources, adapters) |
| `pheno/crates/phenotype-shared-config` | `phenotype-config/crates/settly` (domain `config.rs`, `validation.rs`) |

Both concepts now live in `settly`:

- `crates/settly/src/domain/config.rs` — `Priority`, `ConfigSource`,
  `LayeredConfig`, `ConfigValue` schema (shared-config content)
- `crates/settly/src/domain/validation.rs` — shared validation rules
- `crates/settly/src/ports.rs` — file-loading ports (loader content)

## Status

The copy in `pheno/crates/phenotype-shared-config/` is **deprecated** and
retained only for backward compatibility with existing path-based consumers.
No new feature work should land there.

The legacy `phenoShared/crates/phenotype-shared-config/` redirect is also
**stale** — it predates ADR-022 and points to a path that no longer
represents the canonical substrate.

## Migration Guidance

New consumers should depend on `phenotype-config` and use
`settly::domain::config::ConfigValue` /
`settly::domain::config::LayeredConfig`. Existing path-based consumers will
be migrated forward-only as part of the L5-104 closure work.

Do **not** edit the deprecated `pheno/crates/phenotype-shared-config/` copy
for non-trivial changes — open the change against `phenotype-config` instead,
then re-sync.

Refs: ADR-012 (config consolidation), ADR-022 RFC 002 (two-crate split),
L5-104 migration plan (`findings/2026-06-17-L5-104-pheno-adr012-migration-plan.md`).