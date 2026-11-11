# Authvault Specification

## Scope

Authvault is a Rust authentication and authorization framework with JWT-first authentication and supporting security primitives (sessions, revocation, audit logging) in a hexagonal architecture.

This file is the canonical feature spec for repository-level feature status. Detailed behavior and acceptance criteria remain in the FR artifacts under `FRs/`.

## Feature Canonical Index

| FR | Title | Status | Evidence |
|---|---|---|---|
| [FR-AUTH-001](FRs/FR-AUTH-001.md) | JWT Token Generation | ✅ IMPLEMENTED | `src/token.rs`, `tests/token_tests.rs` |
| [FR-AUTH-002](FRs/FR-AUTH-002.md) | JWT Token Validation | ✅ IMPLEMENTED | `src/token.rs`, `src/middleware.rs`, `tests/token_tests.rs` |
| [FR-AUTH-003](FRs/FR-AUTH-003.md) | Token Refresh | ✅ IMPLEMENTED | `src/refresh.rs`, `tests/refresh_tests.rs` |
| [FR-AUTH-004](FRs/FR-AUTH-004.md) | API Key Management | ➡️ MIGRATED TO AUTHKIT | Not implemented here; tracked in [AuthKit](https://github.com/KooshaPari/AuthKit/issues) |
| [FR-AUTH-005](FRs/FR-AUTH-005.md) | Rate Limiting by Token | ➡️ MIGRATED TO AUTHKIT | Not implemented here; tracked in [AuthKit](https://github.com/KooshaPari/AuthKit/issues) |
| [FR-AUTH-006](FRs/FR-AUTH-006.md) | Token Revocation | ✅ IMPLEMENTED | `src/revocation.rs`, `tests/revocation_tests.rs` |
| [FR-AUTH-007](FRs/FR-AUTH-007.md) | OAuth2 Provider Integration | ➡️ MIGRATED TO AUTHKIT | Not implemented here; tracked in [AuthKit](https://github.com/KooshaPari/AuthKit/issues) |
| [FR-AUTH-008](FRs/FR-AUTH-008.md) | Session Management | ✅ IMPLEMENTED | `src/session.rs`, `tests/session_tests.rs` |
| [FR-AUTH-009](FRs/FR-AUTH-009.md) | Audit Logging | ✅ IMPLEMENTED | `src/audit.rs`, `tests/audit_tests.rs` |
| [FR-AUTH-010](FRs/FR-AUTH-010.md) | Multi-Factor Authentication | ➡️ MIGRATED TO AUTHKIT | Not implemented here; tracked in [AuthKit](https://github.com/KooshaPari/AuthKit/issues) |
| Multi-tenant auth-domain isolation | Multi-Tenant Support | ➡️ MIGRATED TO AUTHKIT | Not implemented here; tracked in [AuthKit](https://github.com/KooshaPari/AuthKit/issues) |

## Planned work not yet in FR catalog

All PLANNED features have been migrated to [AuthKit](https://github.com/KooshaPari/AuthKit).
No further implementation should occur in Authvault. File new issues in AuthKit.

## Delivery posture

- **Status**: Archived — historical reference only. Active auth development has moved to [AuthKit](https://github.com/KooshaPari/AuthKit).
- **Source of truth for new work**: [AuthKit SPEC](https://github.com/KooshaPari/AuthKit)
- **Source of truth for history**: `FRs/*.md` in this repo
