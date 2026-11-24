# Pheno Source Manifest Capture

## Purpose

This preservation-only ref supplements `wip/preserve-20260801/pheno-dirty-capture-0955`
(`61401334849e8ebb31f5b30313c847dd15f96451`) with source-bearing Cargo manifests and
small ignored metadata that were present in the local `pheno` checkout but absent from
that recovery tree. It does not authorize a merge, absorption, archive, or deletion.

## Provenance

- Recovery parent: `61401334849e8ebb31f5b30313c847dd15f96451`
- Local source observed: `pheno` `main` at `be5da947` (working tree also had an unrelated
  `WORKLOG.md` delta, intentionally excluded)
- Capture scope: `crates/agile-plus/` and `crates/hexa-kit/`
- Missing manifests copied: 119
- Total nested `Cargo.toml`/`Cargo.lock` files now present in scope: 151

## Included ignored source metadata

- `crates/agile-plus/buf.gen.yaml`
- `crates/agile-plus/buf.yaml`
- `crates/agile-plus/kitty-specs/INDEX.md`
- `crates/agile-plus/README.md`
- `crates/hexa-kit/buf.gen.yaml`
- `crates/hexa-kit/buf.yaml`

## Explicit exclusions

Generated/runtime/cache content remains excluded: `target/`, `node_modules/`, build and
distribution outputs, `.git/` and worktree metadata, databases, logs, temporary files,
and the unrelated `WORKLOG.md` working-tree delta.

This ref is a source-completeness preservation artifact only. API parity, dependency
parity, tests, and parent-boundary decisions remain open evidence gates.
