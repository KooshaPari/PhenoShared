<!-- Base: platforms/thegent/governance/AGENTS.base.md -->
<!-- Last synced: 2026-04-02 -->

# AGENTS.md — Authvault

Extends thegent governance base. See `platforms/thegent/governance/AGENTS.base.md` for canonical definitions.

## Project Identity

- **Name**: Authvault (formerly authkit)
- **Description**: Authentication and authorization framework with OAuth2, JWT, and RBAC/ABAC support
- **Location**: `/Users/kooshapari/CodeProjects/Phenotype/repos/Authvault`
- **Language Stack**: Rust (edition 2021)
- **Published**: Internal

## AgilePlus Integration

All work MUST be tracked in AgilePlus:
- Reference: `/Users/kooshapari/CodeProjects/Phenotype/repos/.agileplus`
- CLI: `agileplus <command>`
- No code without corresponding AgilePlus spec

---

## Repository Mental Model

### Project Structure

```
src/
├── domain/          # Core domain logic (pure)
│   ├── identity/   # User, role, permission entities
│   ├── auth/       # Authentication logic
│   ├── policy/     # Authorization policies
│   ├── session/    # Session management
│   ├── ports/      # Interface definitions
│   └── errors/     # Domain errors
├── application/    # Application services
│   ├── commands/  # Auth commands
│   └── queries/   # Auth queries
├── adapters/       # Infrastructure adapters
│   ├── jwt/       # JWT implementation
│   ├── oauth2/    # OAuth2 implementation
│   ├── storage/   # User storage
│   └── hashers/   # Password hashing
└── infrastructure/ # Cross-cutting concerns
tests/             # Integration tests
examples/          # Usage examples
benches/           # Benchmarks
```

### Style Constraints

- **Line length**: 100 characters
- **Formatter**: `cargo fmt` (mandatory)
- **Linter**: `cargo clippy` with `-- -D warnings` (zero warnings)
- **File size target**: ≤350 lines per source file

### Key Constraints

- Hexagonal architecture: domain has NO external dependencies
- All ports (traits) defined in `domain/ports/`
- Adapters implement domain ports
- Error handling via `thiserror`

---

## Key Commands

```bash
cargo build            # Build library
cargo test             # Run all tests
cargo clippy -- -D warnings   # Lint
cargo fmt              # Format
cargo doc --open       # View docs
```

---

## Quality Gates

- `cargo clippy -- -D warnings` — 0 warnings required
- `cargo test` — all pass required
- `cargo doc` — 0 missing doc warnings on public items
