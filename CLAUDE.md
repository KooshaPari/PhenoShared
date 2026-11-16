# CLAUDE.md — pheno (Phenotype Shared Crates)

**This project is managed through AgilePlus.**

## AgilePlus Mandate

All work MUST be tracked in AgilePlus:
- Reference: `/Users/<REDACTED>/CodeProjects/Phenotype/repos/AgilePlus`
- CLI: `cd /Users/<REDACTED>/CodeProjects/Phenotype/repos/AgilePlus && agileplus <command>`

## Work Requirements

1. **Check for AgilePlus spec before implementing**
2. **Create spec for new work**: `agileplus specify --title "<feature>" --description "<desc>"`
3. **Update work package status**: `agileplus status <feature-id> --wp <wp-id> --state <state>`
4. **No code without corresponding AgilePlus spec**

## Branch Discipline

- Feature branches in `repos/worktrees/<project>/<category>/<branch>`
- Canonical repository tracks `main` only
- Return to `main` for merge/integration checkpoints

## UTF-8 Encoding

All markdown files must use UTF-8.

## CI Completeness Policy

- Always evaluate and fix ALL CI check failures on a PR, including pre-existing failures inherited from main.
- Never dismiss a CI failure as "pre-existing" or "unrelated to our changes" — if it fails on the PR, fix it in the PR.
- This includes: build, lint, test, docs build, security scanning (CodeQL), code review gates (CodeRabbit), workflow guard checks, and any other CI jobs.
- When a failure is caused by infrastructure outside the branch (e.g., rate limits, external service outages), implement or improve automated retry/bypass mechanisms in CI workflows.
- After fixing CI failures, verify locally where possible (build, vet, tests) before pushing.

## Structure

This is the pheno project within the Phenotype organization.

### Project Overview

- **Name**: pheno
- **Description**: Phenotype Shared Crates (Rust workspace)
- **Location**: `/Users/<REDACTED>/CodeProjects/Phenotype/repos/pheno`
- **Language Stack**: Rust (edition 2021)
- **Published**: Internal (shared across Phenotype org)

### Work Requirements

1. **Check for AgilePlus spec before implementing**
2. **Create spec for new work**: `agileplus specify --title "<feature>" --description "<desc>"`
3. **Update work package status**: `agileplus status <feature-id> --wp <wp-id> --state <state>`
4. **No code without corresponding AgilePlus spec**

### Branch Discipline

- Feature branches in `repos/worktrees/<project>/<category>/<branch>`
- Canonical repository tracks `main` only
- Return to `main` for merge/integration checkpoints

### Worktree Convention

- Feature work goes in `.worktrees/<topic>/`
- Legacy `PROJECT-wtrees/` and `repo-wtrees/` roots are for migration only and must not receive new work.
- Canonical repository remains on `main` for final integration and verification.

---

## Local Quality Checks

From this repository root:

```bash
cargo test --workspace
cargo clippy --workspace -- -D warnings
cargo fmt --check
```

## Testing & Specification Traceability

All tests MUST reference a Functional Requirement (FR):

```rust
// Traces to: FR-XXX-NNN
#[test]
fn test_feature_name() {
    // Test body
}
```

**Verification**:
- Every FR in FUNCTIONAL_REQUIREMENTS.md MUST have >=1 test
- Every test MUST reference >=1 FR
- Run: `cargo test` to verify

---

## Project-Specific Configuration

This monorepo consists of domain-agnostic, independently consumable Rust crates:

### Crate Structure

```
crates/
  phenotype-event-sourcing/   # Append-only event store with SHA-256 hash chains
  phenotype-cache-adapter/    # Two-tier LRU + DashMap cache with TTL
  phenotype-policy-engine/    # Rule-based policy evaluation with TOML config
  phenotype-state-machine/    # Generic FSM with transition guards
  phenotype-contracts/        # Shared traits and types
  phenotype-error-core/       # Canonical error types
  phenotype-health/           # Health check abstraction
  phenotype-config-core/      # Configuration management
```

### Conventions

- All public types implement `Debug`, `Clone` where possible
- Error types use `thiserror` with `#[from]` for conversions
- Serialization via `serde` with `Serialize`/`Deserialize` derives
- No inter-crate dependencies; each crate stands alone
- Workspace-level dependency versions in root `Cargo.toml`
- Tests are inline (`#[cfg(test)]` modules) within each source file

### Adding a New Crate

1. Create `crates/<name>/` with `Cargo.toml` and `src/lib.rs`
2. Add to `members` in root `Cargo.toml`
3. Use `workspace = true` for shared dependencies
4. Include inline tests with `#[cfg(test)]`
5. Update `README.md` crate table

---

## Architecture

### Hexagonal Architecture (Ports & Adapters)

This project follows Hexagonal Architecture with clear separation of concerns:

```
crates/                        # Rust workspace members
├── phenotype-event-sourcing/
├── phenotype-cache-adapter/
├── phenotype-policy-engine/
├── phenotype-state-machine/
├── phenotype-contracts/
├── phenotype-error-core/
├── phenotype-health/
└── phenotype-config-core/
```

## Agent Rules

**READ `AGENTS.md` FIRST.** It contains the authoritative agent interaction rules for this project. Key points:

- When working on pheno, cd into the project directory first (e.g., `cd pheno`)
- All feature work uses `.worktrees/<topic>/`
- Test commands must run inside the project directory, not shelf root
- File reads should specify the correct path from pheno root

## Architecture Design Principles

This project follows:
- Hexagonal Architecture with clear port/adapter separation
- Specification-driven development via AgilePlus
- Test-first mandate with FR traceability
- Rust workspace conventions per `CLAUDE.md`

---

## Governance Reference

For complete governance, see:
- Phenotype org governance: `/Users/<REDACTED>/CodeProjects/Phenotype/repos/CLAUDE.md`
- Global agent guidance: `~/.claude/AGENTS.md`
- Phenotype git and delivery protocol: Phenotype-org CLAUDE.md
- CI completeness policy: This file (see above)

---
