# Eidolon Absorption

Eidolon (the Phenotype-org agentic runtime substrate, 6094 LOC Rust
across 5 crates) was absorbed from `KooshaPari/Eidolon` into the pheno
monorepo as `crates/eidolon-{core,desktop,mobile,sandbox,phenotype-error-core}/`.

## Source

| Field | Value |
| --- | --- |
| Source repo | `KooshaPari/Eidolon` |
| Source size | 6094 LOC Rust |
| Source branches | 92 |
| Absorbed on | 2026-07-18 |
| Target | pheno monorepo `crates/eidolon-{core,desktop,mobile,sandbox,phenotype-error-core}/` |

## What was absorbed

The 5 workspace crates:

- **eidolon-core** — core runtime + agent loop
- **eidolon-desktop** — desktop (Tauri-style) wrapper
- **eidolon-mobile** — mobile (iOS/Android) bindings
- **eidolon-sandbox** — sandboxed execution harness
- **phenotype-error-core** — error type taxonomy

## Conflicts to resolve

`phenotype-error-core` duplicates pheno monorepo's existing error module per
`refactor/dedupe-phenotype-error-core-2026-06-08` branch (commit e2ca6d83) —
merge with `thiserror v2` upgrade during absorption.

## Forensic copy

Forensic retention of the full source (Cargo.toml, Cargo.lock, README,
rust-toolchain.toml, deny.toml, all 5 crates/) is at
`registry/absorbed-crates/eidolon/` — ~6086 LOC of Rust preserved
verbatim until the portage-federation handoff completes.

Boundary spec: `docs/boundary/eidolon.md`.

Source archive pending GH auth restoration.
