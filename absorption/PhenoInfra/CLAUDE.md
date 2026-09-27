# CLAUDE.md — phenotype-infra

Extends parent governance. See:
- Global baseline: `~/.claude/CLAUDE.md`
- Plan: `~/plans/2026-06-23-master-compute-infra-observability-dag-v1.md`

## Project Overview

- **Name:** phenotype-infra
- **Description:** Compute/Infra Consolidation Monorepo — nanovms + PhenoCompose + BytePort
- **Language Stack:** Go 1.23+, Rust (edition 2021), TypeScript/Svelte
- **Key Areas:** `crates/`, `tools/`, `docs/`, `.github/workflows/`
- **Status:** Active (L1-Alpha consolidation)

## Repository Layout

- `crates/nanovms-core/` — Go source for 3-tier isolation
- `crates/nvms-ffi/` — Rust FFI bindings to NVMS Go Core
- `crates/pheno-compose/` — High-level Rust driver
- `tools/byteport/` — Svelte infra tooling
- `docs/adr/` — Architecture Decision Records
- `docs/specs/` — Specifications
- `docs/governance/` — Governance documents
- `docs/audit/` — Audit scorecards
- `.github/workflows/` — CI/CD

## Quality Checks

From this repository root:

```bash
# Go vet + test
go vet ./crates/nanovms-core/...
go test ./crates/nanovms-core/...

# Rust checks
cargo check --workspace
cargo test --workspace
cargo clippy --workspace -- -D warnings
cargo fmt -- --check

# Pre-commit
pre-commit run --all-files
```

## Worktree & Git Discipline

- Feature work uses repo-specific worktrees
- Canonical repo stays on `main` except during explicit merge operations
- All feature branches are temporary; integrate via pull request or squash commit
- Git commit after each wave with wave-tagged message

## Related Documents

- `README.md` — project overview and quick start
- `AGENTS.md` — agent-facing repository guidance
- `PLAN.md` — master DAG plan

---

For CI, scripting language hierarchy, and other policies, see the canonical sources listed above.
