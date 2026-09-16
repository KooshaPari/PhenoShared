# pheno-runtime-config absorption

**Source repo**: `KooshaPari/pheno-runtime-config`
**Absorbing repo**: `KooshaPari/pheno` (monorepo)
**Target path**: `crates/pheno-runtime-config/`
**Recorded**: 2026-07-17, registry commit TBD (v1.6.30)
**Disposition row**: `repo-pheno-runtime-config` (id 168 region)

## What was absorbed

pheno-runtime-config is a small (~405 LOC) Rust library crate that provides
hot-reloadable runtime configuration for the pheno-* fleet. It is the
canonical implementation of the L37 reloadable-config idiom:

| Source                | bytes | language |
| --------------------- | ----- | -------- |
| Cargo.toml            |  791  | Rust (manifest) |
| README.md             | ~3 KB | docs     |
| CHANGELOG.md          |  ~1KB | docs     |
| AGENTS.md             |  ~2KB | docs     |
| WORKLOG.md            | ~3 KB | docs     |
| llms.txt              | ~1 KB | docs     |
| src/lib.rs            |  148  | Rust     |
| src/file.rs           |   77  | Rust     |
| src/sighup.rs         |  180  | Rust     |
| tests/                | ~6 KB | Rust     |
| Justfile, deny.toml   |  ~1KB | build    |

## Why this crate exists

ADR-095 (June 2026) introduced a `Reloadable<T>` pattern for hot-reloading
config files in long-lived Phenotype Rust binaries. The pattern was
implemented inside various repos (pheno, Configra) and consolidated into
`pheno-runtime-config` for fleet-wide reuse.

## Boundary

| Aspect       | Value |
| ------------ | ----- |
| ABI stability | pinned to Phenotype-org Rust toolchain |
| Crate name   | `pheno-runtime-config` |
| Edition      | 2021   |
| MSRV         | 1.82   |
| depends on   | `notify` (file watcher), `arc-swap`, `tokio`, `serde`, `toml`, `tracing` |
| features     | `default` (notify/macos_kqueue watcher); `inotify` (Linux); `windows` |
| API surface  | `Reloadable<T>` trait, `notify::*` SIGHUP fallback, atomic swap |

## Cross-references

- Boundary doc: `docs/boundary/pheno-runtime-config.md`
- Audit justification: `audits/absorption-justifications/pheno-runtime-config-2026-07-17.md`
- ADR: ADR-095 (Reloadable pattern)

## Status (recorded 2026-07-17)

- Source repo `KooshaPari/pheno-runtime-config` was last pushed 2026-06-28.
- No subsequent pushes since absorption queue pickup 2026-07-17.
- Target `KooshaPari/pheno` workspace is being dismantled per `gw-pheno`
  gate (in-progress). Until agileplus-* and phenotype-* crate relocations
  settle (planned 2026-08-01), pheno-runtime-config sits at
  `crates/pheno-runtime-config` in pheno as the canonical Rust home.
- Once `gw-pheno` completes, this crate will reland at
  `KooshaPari/AgilePlus/crates/pheno-runtime-config` (per pheno-monorepo
  split plan). This row will be re-affirmed at that time.
