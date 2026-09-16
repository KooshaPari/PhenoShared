# Archived: phenotype-forge

> **Status (2026-09-08):** This file is a historical migration record. The
> migration to `tools/forge/` described below was recorded in documentation
> but the package in **this checkout** was **not** renamed or deleted. This
> archive marker is preserved so future readers know the relationship
> between `phenotype-forge` and the canonical `forge` CLI; it does **not**
> indicate that this repository is retired.

## Migration

- Source: `phenotype-forge` (this repository)
- Target: `tools/forge` (sibling CLI tool; canonical)
- New binary: `forge`

## Changes (originally claimed)

- Renamed package from `phenotype-forge` to `forge`
- Repository URL updated to `github.com/phenotype-dev/forge`

## Reconciliation with the current checkout

| Item | Migration claim | Current state in this checkout |
|------|-----------------|--------------------------------|
| Package name | renamed to `forge` | **still `phenotype-forge`** (see `Cargo.toml:2`) |
| Binary name | renamed to `forge` | **still `phenotype-forge`** (see `Cargo.toml:18-20`, `[[bin]]` block) |
| Repository URL | moved to `phenotype-dev/forge` | **still `KooshaPari/phenoForge`** (this checkout's `origin` remote) |
| Source deletion | migrated source removed here | **not removed**; `src/main.rs` and `src/lib.rs` are present |

The migration was recorded in `ARCHIVED.md` but the code rename never
landed in this checkout. This repository is preserved as a **scaffold-only
documentation snapshot** (see `README.md` and the `0.0.0` entry in
`CHANGELOG.md`). It is **not** the canonical Phenotype CLI; the canonical
CLI lives at `tools/forge/`.

## Why this file was retained

- **Provenance**: it documents the relationship between the two repositories.
- **Anti-fabrication**: removing this file would obscure the fact that the
  `phenotype-forge` -> `forge` rename was never executed in this checkout.
- **Reversibility**: if a future maintainer wants to actually complete the
  rename, the historical record is preserved.

## Provenance

- This file was authored when the project was originally archived.
- The reconciliation table and the "Status" block were added in commit
  `closure/audit-truthful-scaffold-20260908` (branched from `main` HEAD
  `2fccbc27591aa797fd9e038a2e422b9a6636b19f`).
