# Authvault — CLAUDE.md

## Project Summary

Authvault is an authentication and authorization framework with OAuth2, JWT, and RBAC/ABAC support. Built with hexagonal architecture for clean separation of concerns.

## Stack

| Layer | Crate | Version |
|-------|-------|---------|
| Web | `axum` | 0.8 |
| Auth | `jsonwebtoken` | 10 |
| Password | `argon2` | 0.5 |
| Error | `thiserror` | 2.0 |

## Key Commands

```bash
cargo build
cargo test
cargo clippy -- -D warnings
cargo fmt
```

## Structure

```
src/
├── domain/      # Pure domain logic (flat files)
│   ├── identity.rs  # User, role, permission entities
│   ├── auth.rs      # Authentication logic
│   ├── policy.rs    # Authorization policies
│   ├── session.rs   # Session management
│   ├── ports.rs     # Interface definitions
│   └── errors.rs    # Domain errors
├── application/  # Use cases
├── adapters/     # Infrastructure (jwt, hashers)
└── infrastructure/  # Cross-cutting concerns
```

## Development Rules

- Domain layer has NO external dependencies (pure Rust)
- All interfaces defined as traits in `domain/ports.rs`
- Error types use `thiserror` with `#[from]` conversions
- New features: add to domain first, then application, then adapter

## Quality Gates

- `cargo clippy -- -D warnings` — 0 warnings
- `cargo test` — all pass
- `cargo doc` — no missing docs on public items
