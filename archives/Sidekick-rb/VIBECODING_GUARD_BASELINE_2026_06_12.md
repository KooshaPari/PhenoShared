# VIBECODING_GUARD_BASELINE_2026_06_12.md — Sidekick

## Protected Paths (Do-Not-Touch Zones)

| # | Protected Path | Rationale |
|---|--------------|-----------|
| 1 | `Cargo.lock` | Workspace lockfile — reproducible builds depend on exact versions |
| 2 | `crates/sidekick-messaging/Cargo.toml` | Rust crate manifest — dependency and metadata contract |
| 3 | `crates/cheap-llm-mcp/pyproject.toml` | Python package manifest — vendored crate build config |
| 4 | `crates/cheap-llm-mcp/src/cheap_llm_mcp/config.py` | Core configuration module — runtime behavior contract |
| 5 | `.github/workflows/` | CI/CD pipeline definitions — delivery and quality gates |

## Guard Adoption

- Hook: `pheno-vibecoding-guard scan`
- Stage: `pre-commit`
- Baseline date: 2026-06-12
- Source: `pheno-vibecoding-guard` (local system install)

## Reference

- `AGENTS.md` — Sidekick agent operating contract
- `CLAUDE.md` — Project-specific guidance and quality gates
- Parent governance: `/Users/kooshapari/CodeProjects/Phenotype/repos/CLAUDE.md`
