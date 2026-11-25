<!-- Base: platforms/thegent/dotfiles/governance/CLAUDE.base.md -->
<!-- Last synced: 2026-03-29 -->

# heliosCLI — CLAUDE.md

Extends thegent governance base. See `platforms/thegent/dotfiles/governance/CLAUDE.base.md` for canonical definitions.

## Project Overview

- **Name**: heliosCLI
- **Description**: Rust-based CLI for managing Helios CLI applications with multi-backend support and sandboxing.
- **Location**: repo-relative — this checkout (`./`). See `AGENTS.md` for the dual-workspace map (`crates/` harness workspace + vendored `codex-rs/`).
- **Language Stack**: Rust (root edition 2021; vendored codex-rs edition 2024)
- **Published**: Internal

## AgilePlus Mandate

All work MUST be tracked in the external AgilePlus service. Cite
`AP-ITEM:<id>` for queue work or `AP-FEATURE:<slug>/WP<n>` for a service-backed
feature/work package in the branch, commits, and pull request. Do not create,
copy, or commit tracker artifacts in the AgilePlus source repo or in
HeliosCLI.

## Work Requirements

1. **Create or reference an external AgilePlus item before implementing**
2. **Record scope and acceptance criteria in that external item**
3. **Update its external tracker state when the service supports the transition**
4. **No untracked code**: every implementation change cites its AgilePlus identifier

## Branch Discipline

- Feature branches in `repos/worktrees/<project>/<category>/<branch>`
- Canonical repository tracks `main` only
- Return to `main` for merge/integration checkpoints

## UTF-8 Encoding

All markdown files must use UTF-8.

---

## Local Quality Checks

From this repository root:

```bash
cargo test --all
cargo clippy --all-targets -- -D warnings
cargo fmt --check
```

## Testing & Specification Traceability

All tests MUST reference a Functional Requirement (FR):

```rust
// Traces to: FR-HELIOS-NNN
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

heliosCLI provides a comprehensive CLI for Helios CLI application management with multiple execution backends:

### Architecture

```
src/
├── main.rs              # CLI entrypoint
├── commands/            # Command handlers
├── config/              # Configuration loading
├── execution/           # Backend executors (Docker, Kubernetes, Local)
├── app/                 # Core application logic
├── models/              # Data models
└── utils/               # Utilities
```

### Build & Run

```bash
# Build release binary
cargo build --release

# Run with help
./target/release/helios-cli --help

# Run in development
cargo run -- <command>
```

### Key Features

- Multi-backend execution support (Docker, Kubernetes, Local, Sandbox)
- TUI-based application management and monitoring
- Comprehensive logging and error handling
- Type-safe configuration management

### Conventions

- All CLI commands derive from `clap` with subcommands
- Error types use `thiserror` for clear error propagation
- Async runtime: `tokio` for concurrent operations
- All public types are documented with examples
- Tests are inline with source files

---

## Architecture

### Design Patterns

- **Command Pattern**: Each CLI command is a self-contained handler
- **Builder Pattern**: Configuration builders for complex types
- **Strategy Pattern**: Pluggable execution backends
- **Adapter Pattern**: Backend-specific implementations

### Design Principles

| Principle | Description                                                                                          | Application                                                     |
| --------- | ---------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| **SOLID** | Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion | Commands are single-purpose; backends implement trait interface |
| **DRY**   | Don't Repeat Yourself                                                                                | Shared utilities in `src/utils/`                                |
| **KISS**  | Keep It Simple, Stupid                                                                               | Clear command structure, minimal abstractions                   |
| **YAGNI** | You Aren't Gonna Need It                                                                             | Build features as needed                                        |

---

## Governance Reference

See thegent governance base for:

- Complete CI completeness policy
- Phenotype Git and Delivery Workflow Protocol
- Phenotype Org Cross-Project Reuse Protocol
- Phenotype Long-Term Stability and Non-Destructive Change Protocol
- Worktree Discipline guidelines

Location: `platforms/thegent/dotfiles/governance/CLAUDE.base.md`
