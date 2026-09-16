# AGENTS.md — pheno-config (now lives in Configra)

**Date:** 2026-06-18
**Status:** ABSORBED into `<REDACTED>/Configra` at `crates/pheno-config/` (ADR-031 follow-up, L5-104.7)
**MSRV:** 1.82 (see `Cargo.toml`)
**Original location:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/pheno-config/` (meta-repo subdir; this subdir is now slated for removal post-PR-merge)

## Purpose

Canonical typed-config loader for the `pheno-*` fleet. One crate to load
your service's `Config { url, port, log_level, db_path, feature_flags }`
from env vars, JSON files, or TOML files — with a canonical **12-factor
`combine()`** that overlays env over TOML.

## Where it lives now

This crate was absorbed into `<REDACTED>/Configra` on 2026-06-18 following
the pattern set by ADR-031 (which absorbed `phenotype-config/crates/settly`
into Configra PR #44). The crate name (`pheno-config`) and public API are
preserved verbatim — every consumer's `Cargo.toml` keeps working without
modification.

| | Before | After |
|--|--|--|
| Source-of-truth repo | meta-repo's `repos/pheno-config/` subdir | `<REDACTED>/Configra` (workspace member `crates/pheno-config/`) |
| Crate name | `pheno-config` | `pheno-config` (unchanged) |
| Lib name | `pheno_config` | `pheno_config` (unchanged) |
| Version | 0.2.0 | 0.2.0 (unchanged) |
| Public API | env, JSON, TOML, builder, `combine()` | identical |
| Consumer changes | n/a | **none required** |

## Build (inside Configra)

```bash
git clone https://github.com/<REDACTED>/Configra
cd Configra
cargo build -p pheno-config --release
cargo test  -p pheno-config
cargo build --workspace   # builds both settly + pheno-config
cargo test  --workspace   # runs all tests across the workspace
```

## Substrate Placement

`pheno-*-lib` (ADR-023) — pure reusable Rust library; single concern
(config loading), single crate.

## Authority

phenotype-org-governance/SUPERSEDED.md