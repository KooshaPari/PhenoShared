# BytePort Project Constitution

> Auto-provisioned by compute/infra DAG Phase E rollout
> Date: 2026-06-25
> Pattern: mirrors `_cu_audit/templates/.kittify/memory/constitution.md`

## Purpose

This constitution captures the technical standards, code quality expectations,
tribal knowledge, and governance rules for BytePort. All features and pull
requests should align with these principles.

## Technical Standards

### Language and Toolchain

- **Primary languages**: Go (backend), Rust (Tauri/CLI), TypeScript (Svelte frontend)
  - Go: see `backend/byteport/go.mod`
  - Rust: see `Cargo.toml` (workspace) and `rust-toolchain.toml`
  - TypeScript: see `frontend/web/package.json`
- **Formatter**: `go fmt` for Go, `rustfmt` for Rust, `prettier` for TS/Svelte
  - Strict, enforced via CI tier-0 gate
- **Linter**: `golangci-lint` for Go, `clippy` for Rust, ESLint for TS
  - Treat warnings as fatal in CI
- **License audit**: `deny.toml` — `cargo deny check` blocks release

### Governance Gates

See `.github/workflows/` in this repo. Standard gates:

- Tier-0: build, test, fmt, lint, typecheck (per PR)
- Tier-1: security audit, SBOM, LICENSE check, CHANGELOG check (per PR)
- Tier-2: coverage gate (Rust lib >=71%, Go >=70%, service >=60%)
- cargo-deny: supply-chain license/advisory/source audit

### Branch and PR Hygiene

- Branch names: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `recover/<slug>`
- One logical change per PR
- Reference: compute/infra DAG Epic E (BytePort OTel/TUI completion)
- Reference: phenotype-org-governance ADR-039 (fork-tracking-archive-not-delete)

## BytePort-Specific Knowledge

- BytePort is the phenotype-org CLI distribution hub + infrastructure tooling
  repository.
- Key crates: `byteport-cli` (CLI), `byteport-otel` (OTel instrumentation),
  `byteport-dag` (DAG engine), `byteport-transport` (transport layer).
- Backend is Go in `backend/byteport/` — API Link server.
- Frontend is SvelteKit in `frontend/web/`.
- Recover branches (`recover/E*`, `recover/stash-*`) contain WIP from stash
  recovery — promote to feature branches or close when content is absorbed.
- 18 recover/stash branches were created from stash recovery operation.
  Some are already merged into main; ones still diverged need rebase or close.
- OTel work is in `crates/byteport-otel/` (metrics, tracing, propagation, OTLP).
- Cargo workspace at root — `crates/*` directories.

## Code Quality

- Treat security warnings as fatal
- Run all required tests before claiming work complete
- State what was done, what was not, and why

## Versioning

- SemVer for public crates
- Calendar version for governance documents (YYYY.MM.DD)

## Quick Reference

- Path: always specify exact locations in agent prompts
- Encoding: UTF-8 only
- Context: read what you need, don't re-read unnecessarily
- Quality: secure, tested, documented
- Git: clean commits, descriptive messages
