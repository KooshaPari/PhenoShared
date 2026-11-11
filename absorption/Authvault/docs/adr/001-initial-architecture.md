# ADR-001: Initial Architecture — Hexagonal Auth Library

**Status**: Accepted (archived; active development continues in [AuthKit](https://github.com/KooshaPari/AuthKit))
**Date**: 2025-01-01
**Deciders**: Phenotype Team

## Context

Authvault needs a clean, testable architecture for auth primitives (JWT, sessions, audit,
policy/RBAC) that can be embedded in any Rust service without coupling business logic to
infrastructure.

## Decision

Adopt hexagonal architecture (ports-and-adapters) with three layers:

- **Domain** (`src/domain/`) — pure Rust; no external crate dependencies. Defines entities
  (`Identity`, `Session`, `Policy`), domain errors, and port traits (`AuthProvider`,
  `SessionStore`, `AuditSink`, `PolicyEngine`).
- **Application** (`src/application/`) — orchestrates use-cases by composing domain
  types through ports. Allowed to depend on `async-trait`, `anyhow`.
- **Adapters** (`src/adapters/`) — concrete implementations wiring domain ports to real
  infrastructure (JWT via `jsonwebtoken`, password hashing via `argon2`, encryption via
  `chacha20poly1305`/`zeroize`).

## Consequences

**Positive**:
- Domain logic is testable without any I/O or external services.
- Adapters are swappable; a different JWT library or hash scheme can be dropped in.
- Clean dependency direction: domain ← application ← adapters.

**Negative**:
- More boilerplate than a flat module structure for a small library.
- Consumer must wire adapters manually (no default DI framework).

## Migration Note

This architecture was absorbed into AuthKit (`authkit/crates/`) as-is. If you need the
runtime auth primitives, depend on `authkit-core` instead of `authvault`.
