# Absorbed Crate: Eidolon (KooshaPari/Eidolon)

## Source

| Field | Value |
| --- | --- |
| Source repo | KooshaPari/Eidolon |
| Source size | 6094 LOC Rust (5 crates) |
| Source branches | 92 |
| Source absorbed on | 2026-07-18 |
| Target | pheno monorepo `crates/eidolon-{core,desktop,mobile,sandbox,phenotype-error-core}/` |

## Why absorbed

Eidolon is the Phenotype-org agentic runtime substrate. It contains 5 crates:

- **eidolon-core** — core runtime + agent loop
- **eidolon-desktop** — desktop (Tauri-style) wrapper
- **eidolon-mobile** — mobile (iOS/Android) bindings
- **eidolon-sandbox** — sandboxed execution harness
- **phenotype-error-core** — error type taxonomy (already partially absorbed via ADR-097 / refactor/dedupe-phenotype-error-core-2026-06-08)

## Contents copied here

```
Cargo.toml         # workspace root
Cargo.lock
README.md
rust-toolchain.toml
deny.toml
crates/
  eidolon-core/
  eidolon-desktop/
  eidolon-mobile/
  eidolon-sandbox/
  phenotype-error-core/
```

6086 LOC of Rust total.

## Verification

- 5 crates, all workspace members
- 92 branches on origin (verify via `git ls-remote --heads`)
- Build via `cargo check --workspace` inside pheno monorepo
- phenotype-error-core has a duplicate in pheno monorepo per `refactor/dedupe-phenotype-error-core-2026-06-08`; need to merge before pushing

## Notes

- Phase 1: registry forensic copy at `registry/absorbed-crates/eidolon/`
- Phase 2: pheno monorepo workspace member + tests (portage-federation handoff)
- Phase 3: archive source `gh repo archive KooshaPari/Eidolon -y`

Registry row: repo-Eidolon → absorbed (this commit).
