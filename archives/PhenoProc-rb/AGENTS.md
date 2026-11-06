# AGENTS.md — PhenoProc

High-performance process orchestration and lifecycle management library for Rust (Tokio async, UDS, SHM, priority queues).

## Repository identity

- Language: Rust (Edition 2024)
- Workspace: cargo workspace (see `Cargo.toml`)
- Entry point: `Cargo.toml` (root manifest); spec lives in `SPEC.md`, plan in `PLAN.md`.
- Sub-crates referenced in README: `pheno-proc-core`, `pheno-proc-dedup`, `pheno-proc-queue`, `pheno-proc-shm`, `pheno-proc-uds` (under `crates/`, `libs/`, or top-level `phenotype-*` directories).

## Build & test (verified from README)

```bash
cargo build --release
cargo test --workspace
cargo clippy --workspace -- -D warnings
```

Pre-commit hooks: `.pre-commit-config.yaml` is committed; install with `pre-commit install` if contributing.

## Governance

- Spec: `SPEC.md`
- Plan: `PLAN.md`
- ADRs: `ADRs/`
- Changelog: `CHANGELOG.md`
- Security policy: `SECURITY.md`
- Contributing guide: `CONTRIBUTING.md`
- License: dual MIT / Apache-2.0 (`LICENSE-MIT`, `LICENSE-APACHE`).

## Commit & branch convention

- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`).
- Branch: `<type>/<topic>` (e.g. `feat/queue-priority`, `fix/uds-leak`).
- PRs: keep scoped; reference SPEC IDs where applicable.

## Agent guardrails

- Do NOT invent commands not present in this repo. Verify against `Cargo.toml` and existing CI before suggesting new tooling.
- Workspace status is "maintenance" — prioritize stability fixes and test coverage over new features.
