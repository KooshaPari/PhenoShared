# CLAUDE.md — KlipDot

Extends parent governance. See the following for canonical definitions:
- **Global baseline:** `~/.claude/CLAUDE.md`
- **Phenotype root:** `/Users/kooshapari/CodeProjects/Phenotype/repos/CLAUDE.md`
- **AgilePlus mandate:** `/Users/kooshapari/CodeProjects/Phenotype/repos/AgilePlus`
- **Governance reference:** `AGENTS.md` (local, this repository)

## Project Overview

- **Name:** KlipDot
- **Description:** Universal terminal image interceptor that maps images to file paths for any CLI/TUI application
- **Location:** `repos/KlipDot`
- **Language Stack:** Rust (edition 2021) + Node.js helpers under `src/*.js`
- **Status:** Active (single-package workspace)

## Quick Orientation

| Item | Value |
| ---- | ----- |
| Crate | `klipdot` |
| Binary | `klipdot` (`src/main.rs`) |
| Library | `klipdot` (`src/lib.rs`) |
| Cargo workspace | root crate (no sub-crates) |
| Edition | 2021 |
| Build entrypoint | `just build` → `cargo build --workspace` |
| Test entrypoint | `just test` → `cargo test --workspace` |
| Lint entrypoint | `just lint` → `cargo clippy --workspace --all-targets --all-features -- -D warnings` |
| Tier-0 umbrella | `just tier0` |

## AgilePlus Mandate

All work MUST be tracked in AgilePlus:
- CLI: `cd /Users/kooshapari/CodeProjects/Phenotype/repos/AgilePlus && agileplus <command>`
- Check for existing specs before implementing
- Create spec for new work: `agileplus specify --title "<feature>" --description "<desc>"`
- No code without corresponding AgilePlus spec

## Quality Checks

From this repository root:

```bash
# Tier-0 umbrella — covers fmt + clippy + deny + audit + pre-commit
just tier0

# Linting and formatting
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings

# Testing
cargo test --workspace

# Supply-chain
cargo deny check
cargo audit

# Documentation
cargo doc --workspace --no-deps
```

## Worktree & Git Discipline

- Feature work uses repo-specific worktrees: `repos/KlipDot-wtrees/<topic>/`
- Canonical repo stays on `main` except during explicit merge operations
- All feature branches are temporary; integrate via pull request or squash commit
- See parent governance for non-destructive change protocol

## Cross-Project Reuse

During development, proactively identify code that is sharable across
Phenotype repositories. Prefer extraction into existing shared modules;
propose new shared packages when appropriate. See the parent
`/Users/kooshapari/CodeProjects/Phenotype/repos/CLAUDE.md` for the
canonical cross-project policy.

## Related Documents

- `AGENTS.md` — Local agent contract and operating loop
- `FUNCTIONAL_REQUIREMENTS.md` — Functional requirements and test traceability (if present)
- `docs/worklogs/README.md` — Work audit and decision log
- `SPEC.md`, `PRD.md`, `SOTA.md` — Specification documents (large; consult as needed)
- Parent `README.md` — Project-specific documentation

---

For CI, scripting language hierarchy, and other policies, see the
canonical sources listed above.
