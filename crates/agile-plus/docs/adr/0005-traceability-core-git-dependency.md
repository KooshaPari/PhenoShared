# ADR-0005: traceability-core Git Dependency

## Status

Accepted

## Context

AgilePlus duplicated lifecycle, governance, and intent-graph vocabulary in
`crates/agileplus-domain` while the Phenotype org extracted a shared PM spine into
[`phenotype-pm-core`](https://github.com/KooshaPari/phenotype-pm-core). A vendored
`crates/traceability-core` copy would drift from Tracera and other consumers.

## Decision

1. Depend on `traceability-core` via **git**, not a workspace path:
   `traceability-core = { git = "https://github.com/KooshaPari/phenotype-pm-core", branch = "master" }`.
2. Remove any local `crates/traceability-core` workspace member if present.
3. Re-export `IntentGraph`, `lifecycle` (`FeatureState`), and `governance` types from
   `agileplus-domain` so existing import paths remain stable.

## Consequences

- Single source of truth for PM/traceability vocabulary across AgilePlus and Tracera.
- `cargo update -p traceability-core` pulls spine fixes; CI must have network for first fetch.
- AgilePlus-local aggregates (`Feature`, `WorkPackage`, ports) stay in `agileplus-domain`;
  only shared spine types move to the git crate.
